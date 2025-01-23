import logging
import xml.etree.ElementTree as ET
from typing import Dict, List

from django.core.management.base import BaseCommand, CommandError

from core.models import Source

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import RSS feeds from OPML file"

    def add_arguments(self, parser):
        parser.add_argument("opml_file", help="Path to OPML file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making changes",
        )

    def handle(self, *args, **options):
        try:
            # Parse OPML file
            tree = ET.parse(options["opml_file"])
            root = tree.getroot()

            # Find body element
            body = root.find("body")
            if body is None:
                raise CommandError("No body element found in OPML file")

            # Find all RSS feeds recursively
            feeds = []
            categories = []
            self._process_outline(body, categories, feeds)

            logger.info(f"Found {len(feeds)} feeds in OPML file")

            if options["dry_run"]:
                self._show_feeds(feeds)
                return

            # Import feeds
            imported, skipped = self._import_feeds(feeds)

            logger.info(
                self.style.SUCCESS(
                    f"Successfully imported {imported} feeds, skipped {skipped} existing feeds"
                )
            )

        except Exception as e:
            raise CommandError(f"Failed to import OPML: {str(e)}")

    def _process_outline(
        self, element: ET.Element, current_categories: List[str], feeds: List[Dict]
    ):
        """Recursively process outline elements"""
        for outline in element.findall("./outline"):
            # Get current category name
            category_name = outline.get("text", "").strip()

            # Check if it's a feed
            url = outline.get("xmlUrl")
            if url:
                feed = {
                    "url": url,
                    "name": outline.get("text", "").strip() or url,
                    "html_url": outline.get("htmlUrl", ""),
                    "category": " / ".join(current_categories) if current_categories else "",
                }
                feeds.append(feed)
            else:
                # It's a category - process its children
                if category_name:
                    current_categories.append(category_name)
                self._process_outline(outline, current_categories, feeds)
                if category_name:
                    current_categories.pop()

    def _show_feeds(self, feeds: List[Dict]):
        """Display feeds that would be imported"""
        logger.info("\nFeeds found in OPML file:")
        current_category = None

        for feed in sorted(feeds, key=lambda x: (x["category"], x["name"])):
            # Print category header if changed
            if feed["category"] != current_category:
                current_category = feed["category"]
                logger.info(f"\nCategory: {current_category or 'Uncategorized'}")
                logger.info("-" * 40)

            logger.info(f"\nName: {feed['name']}")
            logger.info(f"URL: {feed['url']}")
            if feed["html_url"]:
                logger.info(f"Website: {feed['html_url']}")

    def _import_feeds(self, feeds: List[Dict]) -> tuple[int, int]:
        """Import feeds into database"""
        imported = 0
        skipped = 0

        for feed in feeds:
            try:
                source, created = Source.objects.get_or_create(
                    url=feed["url"],
                    defaults={
                        "name": feed["name"],
                        "source_type": "rss",
                        "active": True,
                        "metadata": {"category": feed["category"], "html_url": feed["html_url"]},
                    },
                )

                if created:
                    imported += 1
                    logger.info(f"Imported: {feed['name']}")
                else:
                    skipped += 1
                    logger.info(f"Skipped existing: {feed['name']}")

            except Exception as e:
                logger.info(self.style.ERROR(f"Error importing {feed['url']}: {str(e)}"))

        return imported, skipped
