import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from setfit import SetFitModel

from core.models import Content, ModelConfig, TopicPrediction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run topic predictions on content using trained SetFit models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of content items to process in each batch",
        )
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.0,
            help="Minimum confidence threshold for saving predictions",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing predictions before running",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify all content has predictions after processing",
        )
        parser.add_argument(
            "--content-ids",
            nargs="+",
            type=str,
            help="List of content IDs to process",
        )

    def _get_unpredicted_content(self, model_config: ModelConfig) -> QuerySet:
        """Get content without predictions using efficient subquery"""
        query = Content.objects.all()

        # Filter by content IDs if provided
        if self.content_ids:
            query = query.filter(id__in=self.content_ids)

        has_prediction = TopicPrediction.objects.filter(
            content=OuterRef("pk"),
            model_config=model_config,
        )

        return (
            query.annotate(has_prediction=Exists(has_prediction))
            .filter(has_prediction=False)
            .order_by("id")
        )

    def _process_model_config(
        self,
        model_config: ModelConfig,
        batch_size: int,
        min_confidence: float,
        reset: bool,
        verify: bool,
    ):
        """
        Process a single model config with improved error handling and verification
        """
        logger.info(f"\nStarting processing for model: {model_config.name}")

        # Reset existing predictions if requested
        if reset:
            count = TopicPrediction.objects.filter(model_config=model_config).count()
            TopicPrediction.objects.filter(model_config=model_config).delete()
            logger.info(f"Deleted {count} existing predictions")

        # Load model
        try:
            model_path = Path(model_config.get_model_path())
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found at {model_path}")

            model = SetFitModel.from_pretrained(str(model_path))
            logger.info("Model loaded successfully")
        except Exception:
            logger.exception("Error loading model")
            return

        # Process content in batches with cursor-based pagination
        processed_count = 0
        last_id = None

        while True:
            # Query for next batch using id-based pagination
            query = self._get_unpredicted_content(model_config)
            if last_id:
                query = query.filter(id__gt=last_id)

            batch = list(query[:batch_size])
            if not batch:
                break

            try:
                with transaction.atomic():
                    texts = [item.title for item in batch]
                    probs = model.predict_proba(texts)

                    predictions = []
                    for content, prob in zip(batch, probs, strict=False):
                        confidence = float(max(prob))
                        if confidence >= min_confidence:
                            result = "relevant" if prob[1] >= prob[0] else "irrelevant"
                            predictions.append(
                                TopicPrediction(
                                    content=content,
                                    model_config=model_config,
                                    result=result,
                                    confidence=confidence,
                                ),
                            )

                    if predictions:
                        TopicPrediction.objects.bulk_create(predictions)

                    processed_count += len(batch)
                    last_id = batch[-1].id

                    logger.info(f"Processed {processed_count} items total")

            except Exception:
                logger.exception(f"Error processing batch after id {last_id}")
                continue

        if verify:
            # Verify all content has predictions
            missing_count = self._get_unpredicted_content(model_config).count()
            if missing_count > 0:
                logger.error(f"Found {missing_count} items still missing predictions")
            else:
                logger.info("All content has predictions")

        logger.info(
            f"Finished processing {processed_count} items for {model_config.name}",
        )

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        self.content_ids = options.get("content_ids")

        for model_config in ModelConfig.objects.filter(active=True):
            self._process_model_config(
                model_config=model_config,
                batch_size=options["batch_size"],
                min_confidence=options["min_confidence"],
                reset=options["reset"],
                verify=options["verify"],
            )
