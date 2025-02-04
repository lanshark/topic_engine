# core/views.py
from django.db.models import Case, F, FloatField, Prefetch, Value, When
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .forms import ModelConfigForm
from .models import Content, ModelConfig, Source, TopicPrediction


class AllArticlesView(ListView):
    template_name = "core/all_articles.html"
    context_object_name = "articles"
    paginate_by = 50

    def get_queryset(self):
        # Start with all content, newest first
        queryset = Content.objects.select_related("source").order_by("-publish_date")

        # Filter by source if specified
        source_id = self.request.GET.get("source")
        if source_id:
            queryset = queryset.filter(source_id=source_id)

        # Filter by prediction if specified
        prediction = self.request.GET.get("prediction")
        if prediction:
            if prediction == "pending":
                queryset = queryset.filter(topicprediction__isnull=True)
            else:
                queryset = queryset.filter(topicprediction__result=prediction)

        # Filter for high confidence relevant predictions
        if self.request.GET.get("filter") == "relevant":
            queryset = queryset.filter(
                topicprediction__result="relevant", topicprediction__confidence__gte=0.9
            )

        # Add predictions with confidence percentage calculated
        return queryset.prefetch_related(
            Prefetch(
                "topicprediction_set",
                queryset=TopicPrediction.objects.select_related("model_config")
                .annotate(
                    confidence_pct=Case(
                        When(confidence__isnull=False, then=F("confidence") * 100),
                        default=Value(0),
                        output_field=FloatField(),
                    )
                )
                .order_by("-created_at"),
                to_attr="predictions",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add sources for the filter dropdown
        context["sources"] = Source.objects.filter(active=True).order_by("name")
        context["filter"] = self.request.GET.get("filter")
        return context


class ModelConfigListView(ListView):
    model = ModelConfig
    paginate_by = 50  # if pagination is desired
    template_name = "core/modelconfig_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #        topic_id = context["topic_id"]
        #        topic = Topic.objects.filter(pk=topic_id)
        #        context["topic_name"] = topic.name
        return context


class ModelConfigCreateView(CreateView):
    model = ModelConfig
    form_class = ModelConfigForm
    template_name = "core/modelconfig_form.html"
    success_url = reverse_lazy("modelconfig-list")


class ModelConfigDetailView(DetailView):
    model = ModelConfig
    template_name = "core/modelconfig_detail.html"


class ModelConfigUpdateView(UpdateView):
    model = ModelConfig
    form_class = ModelConfigForm
    template_name = "core/modelconfig_form.html"
    success_url = reverse_lazy("modelconfig-list")


class ModelConfigDeleteView(DeleteView):
    model = ModelConfig
    template_name = "core/modelconfig_confirm_delete.html"
    success_url = reverse_lazy("modelconfig-list")
