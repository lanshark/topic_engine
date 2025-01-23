import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

BASE_TRAINING_PATH = Path(settings.DATA_DIR, "training_data")


class Command(BaseCommand):
    help = "Update training data for topics"

    def add_arguments(self, parser):
        parser.add_argument("topic", type=str, help="The name of the training topic to update")
        parser.add_argument(
            "label", type=str, choices=["relevant", "irrelevant"], help="Label for the headline"
        )
        parser.add_argument("headline", type=str, help="The news headline")

    def handle(self, *args, **options):
        topic = options["topic"]
        label = options["label"]
        headline = options["headline"]

        training_dir = BASE_TRAINING_PATH / topic
        training_file = training_dir / f"{label}.txt"

        # Ensure the setup directory exists
        if not training_dir.exists():
            logger.info(self.style.ERROR(f"Topic directory '{topic}' does not exist."))
            return

        # Append the headline to the correct file
        with open(training_file, "a") as file:
            file.write(headline + "\n")

        logger.info(
            self.style.SUCCESS(f"Successfully added headline to {label} data in setup {topic}.")
        )
