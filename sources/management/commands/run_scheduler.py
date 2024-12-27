# management/commands/run_scheduler.py
from django.core.management.base import BaseCommand
import asyncio
from sources.scheduler import ContentScheduler

class Command(BaseCommand):
    help = 'Run the content scheduler'

    def handle(self, *args, **options):
        scheduler = ContentScheduler()
        loop = asyncio.get_event_loop()
        
        try:
            loop.run_until_complete(scheduler.start())
            self.stdout.write('Scheduler started. Press Ctrl+C to stop.')
            loop.run_forever()
        except KeyboardInterrupt:
            self.stdout.write('Shutting down scheduler...')
            loop.run_until_complete(scheduler.stop())
            loop.close()