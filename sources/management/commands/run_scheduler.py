# management/commands/run_scheduler.py
import asyncio
import logging

from django.core.management.base import BaseCommand

from sources.scheduler import ContentScheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the content scheduler"

    def handle(self, *args, **options):
        scheduler = ContentScheduler()
        loop = asyncio.get_event_loop()

        try:
            loop.run_until_complete(scheduler.start())
            logger.info("Scheduler started. Press Ctrl+C to stop.")
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down scheduler...")
            loop.run_until_complete(scheduler.stop())
            loop.close()
