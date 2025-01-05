import logging
import xml.etree.ElementTree as ET

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

            self.stdout.write(f"Found {len(feeds)} feeds in OPML file")

            if options["dry_run"]:
                self._show_feeds(feeds)
                return

            # Import feeds
            imported, skipped = self._import_feeds(feeds)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {imported} feeds, skipped {skipped} existing feeds",  # noqa: E501
                ),
            )

        except Exception as e:
            raise CommandError(f"Failed to import OPML: {str(e)}") from e

    def _process_outline(
        self,
        element: ET.Element,
        current_categories: list[str],
        feeds: list[dict],
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
                    "category": (
                        " / ".join(current_categories) if current_categories else ""
                    ),
                }
                feeds.append(feed)
            else:
                # It's a category - process its children
                if category_name:
                    current_categories.append(category_name)
                self._process_outline(outline, current_categories, feeds)
                if category_name:
                    current_categories.pop()

    def _show_feeds(self, feeds: list[dict]):
        """Display feeds that would be imported"""
        self.stdout.write("\nFeeds found in OPML file:")
        current_category = None

        for feed in sorted(feeds, key=lambda x: (x["category"], x["name"])):
            # Print category header if changed
            if feed["category"] != current_category:
                current_category = feed["category"]
                self.stdout.write(f"\nCategory: {current_category or 'Uncategorized'}")
                self.stdout.write("-" * 40)

            self.stdout.write(f"\nName: {feed['name']}")
            self.stdout.write(f"URL: {feed['url']}")
            if feed["html_url"]:
                self.stdout.write(f"Website: {feed['html_url']}")

    def _import_feeds(self, feeds: list[dict]) -> tuple[int, int]:
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
                        "metadata": {
                            "category": feed["category"],
                            "html_url": feed["html_url"],
                        },
                    },
                )

                if created:
                    imported += 1
                    self.stdout.write(f"Imported: {feed['name']}")
                else:
                    skipped += 1
                    self.stdout.write(f"Skipped existing: {feed['name']}")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error importing {feed['url']}: {str(e)}",
                    ),
                )

        return imported, skipped
