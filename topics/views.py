from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from core.models import Content

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
