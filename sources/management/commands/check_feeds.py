# sources/management/commands/check_feeds.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async
import asyncio
import logging
from asyncio import Semaphore

from core.models import Source
from sources.services import FeedProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check RSS feeds for new content"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run once and exit")
        parser.add_argument("--verbose", action="store_true", help="Increase logging verbosity")

    async def process_single_source(self, source, processor):
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

            source.last_checked = timezone.now()
            await sync_to_async(source.save)()

        except Exception as e:
            logger.exception(f"Error processing source {source.name}")

    async def process_sources(self):
        processor = None
        try:
            processor = FeedProcessor()
            semaphore = Semaphore(10)

            sources = await sync_to_async(list)(
                Source.objects.filter(active=True, source_type="rss").filter(
                    Q(last_checked__isnull=True)
                    | Q(last_checked__lte=timezone.now() - timezone.timedelta(minutes=5))
                )
            )

            logger.info(f"Found {len(sources)} sources to check")

            async def process_with_semaphore(source):
                async with semaphore:
                    return await self.process_single_source(source, processor)

            tasks = [asyncio.create_task(process_with_semaphore(source)) for source in sources]

            await asyncio.gather(*tasks, return_exceptions=True)

        finally:
            if processor:
                await processor.aclose()

    def handle(self, *args, **options):
        if options["verbose"]:
            logging.getLogger("topic_engine").setLevel(logging.DEBUG)
            logging.getLogger("sources").setLevel(logging.DEBUG)

        # Use asyncio.run with proper cleanup
        try:
            asyncio.run(self.process_sources())
        except Exception as e:
            logger.exception("Error in main process")
            raise
