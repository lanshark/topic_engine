from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from core.models import Content, Topic

from .forms import TopicForm

BASE_TRAINING_PATH = Path(settings.DATA_DIR, "training_data")
DEFAULT_TOPIC = ""


def add_training_data(request, article_id):
    if request.method == "POST":
        article = get_object_or_404(Content, pk=article_id)
        action = request.POST.get("action")  # either 'relevant' or 'irrelevant'

        topic = request.POST.get("topic", DEFAULT_TOPIC)  # you can specify different topics
        training_dir = BASE_TRAINING_PATH / topic
        training_file = training_dir / f"{action}.txt"

        # Ensure the setup directory exists
        training_dir.mkdir(0o755, parents=True, exist_ok=True)

        # Append the headline to the correct file
        with open(training_file, "a") as file:
            file.write(article.title + "\n")

        return JsonResponse({"status": "success", "action": action})

    return JsonResponse({"status": "failed"})


class TopicListView(ListView):
    model = Topic
    paginate_by = 50  # if pagination is desired
    template_name = "topics/topic_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class TopicCreateView(CreateView):
    model = Topic
    form_class = TopicForm
    template_name = "topics/topic_form.html"
    success_url = reverse_lazy("topic-list")


class TopicUpdateView(UpdateView):
    model = Topic
    form_class = TopicForm
    template_name = "topics/topic_form.html"
    success_url = reverse_lazy("topic-list")


class TopicDeleteView(DeleteView):
    model = Topic
    template_name = "topics/topic_confirm_delete.html"
    success_url = reverse_lazy("topic-list")
