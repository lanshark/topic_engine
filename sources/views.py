import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from core.models import Content, Source, TopicPrediction

from .forms import SourceForm


class UUIDEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)


def home_list(request):
    sources = Source.objects.all()
    return render(request, "core/home_list.html", {"sources": sources})


def article_list(request, source_id):
    source = get_object_or_404(Source, pk=source_id)
    articles = (
        Content.objects.filter(source=source).select_related("source").order_by("-publish_date")
    )

    predictions = TopicPrediction.objects.filter(content__in=articles).select_related(
        "model_config"
    )

    pred_dict = {pred.content_id: pred for pred in predictions}

    articles_with_predictions = []
    for article in articles:
        pred = pred_dict.get(article.id)
        try:
            confidence = float(pred.confidence) if pred else 0.0
            articles_with_predictions.append(
                {
                    "id": str(article.id),
                    "title": article.title,
                    "url": article.url,
                    "date": (
                        article.publish_date.strftime("%Y-%m-%d %H:%M")
                        if article.publish_date
                        else "Unknown"
                    ),
                    "prediction": pred.result if pred else "unknown",
                    "confidence": confidence,
                    "confidence_pct": f"{confidence * 100:.1f}",
                }
            )
        except AttributeError as e:
            articles_with_predictions.append(
                {
                    "id": str(article.id),
                    "title": getattr(article, "title", "Untitled"),
                    "url": getattr(article, "url", "#"),
                    "publish_date": None,
                    "prediction": "unknown",
                    "confidence": 0.0,
                    "confidence_pct": "0.0",
                }
            )

    return render(
        request,
        "sources/article_list.html",
        {"source": source, "articles": articles_with_predictions},
    )


def article_detail(request, article_id):
    article = get_object_or_404(Content, pk=article_id)
    return render(request, "sources/article_detail.html", {"article": article, "prediction": 0})


def mark_relevance(request, article_id):
    if request.method == "POST":
        article = get_object_or_404(Content, pk=article_id)
        action = request.POST.get("action")
        if action == "relevant":
            article.is_relevant = True
        elif action == "irrelevant":
            article.is_relevant = False
        article.save()
        return JsonResponse({"status": "success", "action": action})
    return JsonResponse({"status": "failed"})


class SourceListView(ListView):
    model = Source
    paginate_by = 50  # if pagination is desired
    template_name = "sources/source_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class SourceCreateView(CreateView):
    model = Source
    form_class = SourceForm
    template_name = "sources/source_form.html"
    success_url = reverse_lazy("source-list")
    # fields = ["name"]


class SourceDetailView(DetailView):
    model = Source
    template_name = "sources/source_detail.html"
    # fields = ["name"]


class SourceUpdateView(UpdateView):
    model = Source
    form_class = SourceForm
    template_name = "sources/source_form.html"
    success_url = reverse_lazy("source-list")
    # fields = ["name"]


class SourceDeleteView(DeleteView):
    model = Source
    template_name = "sources/source_confirm_delete.html"
    success_url = reverse_lazy("source-list")
