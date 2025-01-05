# sources/management/commands/check_feeds.py
import asyncio
import logging
import signal
from asyncio import Semaphore, TimeoutError

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import Source
from sources.services import FeedProcessor

logger = logging.getLogger(__name__)


class AsyncTimeout:
    """Context manager for timeouts with cleanup"""

    def __init__(self, seconds: float):
        self.seconds = seconds

    async def __aenter__(self):
        self.task = asyncio.current_task()
        self.handle = asyncio.get_running_loop().call_later(
            self.seconds,
            self.task.cancel,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.handle.cancel()
        if exc_type is asyncio.CancelledError:
            return True


class Command(BaseCommand):
    help = "Check RSS feeds for new content"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutdown = False
        self._tasks: list[asyncio.Task] = []
        self._processor = None

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run once and exit")
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Increase logging verbosity",
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            default=10,
            help="Maximum concurrent feed checks",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Timeout in seconds for each feed check",
        )

    def handle_sigterm(self, signum, frame):
        """Handle termination signals gracefully"""
        logger.info("Received shutdown signal, initiating graceful shutdown...")
        self._shutdown = True
        if self._processor:
            try:
                # Create a new event loop for cleanup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._processor.aclose())
                loop.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        raise SystemExit(0)

    @sync_to_async
    def get_sources(self):
        """Get sources within a transaction"""
        with transaction.atomic():
            return list(
                Source.objects.select_for_update(skip_locked=True)
                .filter(active=True, source_type="rss")
                .filter(
                    Q(last_checked__isnull=True)
                    | Q(
                        last_checked__lte=timezone.now()
                        - timezone.timedelta(minutes=5),
                    ),
                ),
            )

    async def process_single_source(
        self,
        source: Source,
        processor: FeedProcessor,
        timeout: int,
    ) -> None:
        """Process a single source with timeout and error handling"""
        try:
            async with AsyncTimeout(timeout):
                logger.info(f"Processing source: {source.name}")
                result = await processor.process_source(source)

                if result.error:
                    logger.error(f"Error processing {source.name}: {result.error}")
                    source.error_count = getattr(source, "error_count", 0) + 1
                else:
                    logger.info(
                        f"Processed {source.name}: "
                        f"new_content={len(result.new_content)}, "
                        f"total_processed={result.processed_count}",
                    )
                    source.error_count = 0

                # Handle consecutive failures
                if source.error_count >= 3:
                    source.active = False
                    logger.warning(
                        f"Source {source.name} has failed {source.error_count} times. "
                        "Deactivating source.",
                    )

                source.last_checked = timezone.now()
                await sync_to_async(source.save)()

        except TimeoutError:
            logger.error(f"Timeout processing source: {source.name}")
            source.error_count = getattr(source, "error_count", 0) + 1
            await sync_to_async(source.save)()
        except Exception:
            logger.exception(f"Error processing source {source.name}")
            source.error_count = getattr(source, "error_count", 0) + 1
            await sync_to_async(source.save)()

    async def cleanup(self):
        """Cleanup resources"""
        if self._processor:
            try:
                await self._processor.aclose()
            except Exception as e:
                logger.error(f"Error during processor cleanup: {e}")
            self._processor = None

        # Cancel any remaining tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def process_sources(self, concurrency: int, timeout: int):
        """Process all sources with proper resource management"""
        try:
            self._processor = FeedProcessor()
            semaphore = Semaphore(concurrency)

            sources = await self.get_sources()

            if not sources:
                logger.info("No sources to process")
                return

            logger.info(f"Found {len(sources)} sources to check")

            async def process_with_semaphore(source):
                if self._shutdown:
                    return
                async with semaphore:
                    await self.process_single_source(source, self._processor, timeout)

            tasks = []
            for source in sources:
                if self._shutdown:
                    break
                task = asyncio.create_task(process_with_semaphore(source))
                tasks.append(task)
                self._tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception:
            logger.exception("Error in process_sources")
            raise
        finally:
            await self.cleanup()

    def handle(self, *args, **options):
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)

        if options["verbose"]:
            logging.getLogger("topic_engine").setLevel(logging.DEBUG)
            logging.getLogger("sources").setLevel(logging.DEBUG)

        try:
            asyncio.run(
                self.process_sources(
                    concurrency=options["concurrency"],
                    timeout=options["timeout"],
                ),
            )
        except SystemExit:
            logger.info("Gracefully shut down")
        except Exception:
            logger.exception("Error in main process")
            raise
