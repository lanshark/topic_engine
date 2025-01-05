# sources/scheduler.py
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import Q
from django.utils import timezone

from core.models import Source

from .services import FeedProcessor

logger = logging.getLogger(__name__)


class ContentScheduler:
    """Manages scheduled feed checks and content processing"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.processor = FeedProcessor()
        self._running = False

    async def start(self):
        """Start the scheduler"""
        if self._running:
            return

        # Initialize scheduler
        self.scheduler.start()
        self._running = True

        # Schedule feed checks
        self.scheduler.add_job(
            self.check_feeds,
            IntervalTrigger(minutes=5),
            name="feed_check",
            replace_existing=True,
        )

        # Schedule prediction processing
        self.scheduler.add_job(
            self.process_predictions,
            IntervalTrigger(minutes=1),
            name="prediction_process",
            replace_existing=True,
        )

        # Start initial feed check
        await self.check_feeds()

    async def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return

        self.scheduler.shutdown()
        await self.processor.aclose()
        self._running = False

    async def check_feeds(self):
        """Check all active feeds"""
        try:
            async for source in Source.objects.filter(
                active=True,
                source_type="rss",
            ).filter(
                Q(last_checked__isnull=True)
                | Q(last_checked__lte=timezone.now() - timezone.timedelta(seconds=300)),
            ):
                try:
                    await self.processor.process_source(source)
                    await Source.objects.filter(id=source.id).aupdate(
                        last_checked=timezone.now(),
                    )
                except Exception:
                    logger.exception(f"Error checking source {source.id}")
        except Exception:
            logger.exception("Error during feed check")

    async def process_predictions(self):
        """Process any pending predictions"""
        pending_ids = cache.get("pending_prediction_content", set())
        if pending_ids:
            try:
                # Run prediction command with content IDs
                call_command("predict_topics", content_ids=list(pending_ids))
                cache.delete("pending_prediction_content")
                logger.info(f"Processed predictions for {len(pending_ids)} articles")
            except Exception:
                logger.exception("Error processing predictions")
