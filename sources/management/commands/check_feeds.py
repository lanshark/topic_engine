# sources/management/commands/check_feeds.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async
import asyncio
import logging

from core.models import Source
from sources.services import FeedProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check RSS feeds for new content"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run once and exit")
        parser.add_argument("--verbose", action="store_true", help="Increase logging verbosity")

    async def process_sources(self):
        """Process all active sources"""
        processor = FeedProcessor()
        try:
            logger.info("Starting feed check process")

            # Query active RSS sources that need checking using sync_to_async
            sources = await sync_to_async(list)(
                Source.objects.filter(active=True, source_type="rss").filter(
                    Q(last_checked__isnull=True)
                    | Q(last_checked__lte=timezone.now() - timezone.timedelta(minutes=5))
                )
            )

            logger.info(f"Found {len(sources)} sources to check")

            for source in sources:
                try:
                    logger.info(f"Processing source: {source.name}")
                    result = await processor.process_source(source)

                    if result.error:
                        logger.error(f"Error processing {source.name}: {result.error}")
                    else:
                        logger.info(
                            f"Processed {source.name}: "
                            f"new_content={len(result.new_content)}, "
                            f"total_processed={result.processed_count}"
                        )

                    # Update last_checked timestamp
                    source.last_checked = timezone.now()
                    await sync_to_async(source.save)()

                except Exception as e:
                    logger.exception(f"Error processing source {source.name}")

        finally:
            await processor.aclose()

    def handle(self, *args, **options):
        # Configure logging
        if options["verbose"]:
            logging.getLogger("topic_engine").setLevel(logging.DEBUG)
            logging.getLogger("sources").setLevel(logging.DEBUG)

        # Run the async process
        asyncio.run(self.process_sources())
