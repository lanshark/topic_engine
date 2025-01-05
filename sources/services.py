# sources/services.py
import sys
from dataclasses import dataclass, field
from datetime import datetime

import feedparser
import httpx
import pytz
from asgiref.sync import sync_to_async
from django.utils import timezone

from core.logging import get_logger
from core.models import Content, Source

from .fetching import ContentQuality, SmartContentFetcher

logger = get_logger("topic_engine.services")

# Constants
MAX_CONCURRENT_FEEDS = 20
FEED_TIMEOUT = 60.0
HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=FEED_TIMEOUT)
MAX_CONSECUTIVE_FAILURES = 3
MAX_FAILURE_RATE = 0.5
MIN_ATTEMPTS_BEFORE_RATE_CHECK = 5


@dataclass
class FeedEntry:
    """Represents a processed feed entry"""

    title: str
    url: str
    content: str | None
    guid: str | None
    author: str | None
    published_at: datetime | None

    @classmethod
    def from_parsed_entry(cls, entry: dict) -> "FeedEntry":
        """Create FeedEntry from feedparser entry"""
        # Extract publication date
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            # Create timezone-aware datetime using UTC
            naive_dt = datetime.fromtimestamp(
                datetime.timestamp(datetime(*published[:6])),
            )
            published_at = timezone.make_aware(naive_dt, timezone=pytz.UTC)
        else:
            published_at = None

        # Find best content field
        content = None
        if "content" in entry:
            content = max((c.get("value", "") for c in entry.content), key=len)
        elif "summary" in entry:
            content = entry.summary

        # Truncate title if needed
        title = entry.get("title", "").strip()
        if len(title) > 495:  # Leave room for ellipsis
            title = title[:495] + "..."

        return cls(
            title=title,
            url=entry.get("link", ""),
            content=content,
            guid=entry.get("id", ""),
            author=entry.get("author", ""),
            published_at=published_at,
        )


@dataclass
class ProcessingResult:
    """Result of processing a feed"""

    new_content: list[Content] = field(default_factory=list)
    error: str | None = None
    processed_count: int = 0
    fetch_failures: int = 0  # Track number of individual fetch failures
    all_attempts_failed: bool = False  # Flag if all fetches failed


class FeedProcessor:
    """Handles RSS feed processing with enhanced logging and error tracking"""

    FAILURE_THRESHOLD = 3  # Number of consecutive complete failures before backing off
    BACKOFF_MINUTES = 60  # Wait time after hitting failure threshold

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,  # Enable redirect following
        )
        self.fetcher = SmartContentFetcher()

    async def _fetch_feed(self, url: str) -> feedparser.FeedParserDict | None:
        """Fetch and parse RSS feed with improved error handling"""
        try:
            logger.info(f"Fetching feed: {url}")
            response = await self.client.get(url)
            response.raise_for_status()

            logger.info(
                f"Successfully fetched feed {url} (Status: {response.status_code})",
            )
            feed = await sync_to_async(feedparser.parse)(response.text)

            if not feed.entries:
                logger.warning(f"Feed {url} contains no entries")
                return None

            logger.info(f"Parsed {len(feed.entries)} entries from {url}")
            return feed

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching feed {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch feed {url}: {str(e)}")
            return None

    async def process_source(self, source: Source) -> ProcessingResult:
        """Process a single source with error tracking"""
        result = ProcessingResult()

        logger.info(f"Processing source: {source.name} ({source.url})")

        # Check if source is in backoff period
        if source.error_count >= self.FAILURE_THRESHOLD:
            if source.last_checked and (
                timezone.now() - source.last_checked
            ) < timezone.timedelta(
                minutes=self.BACKOFF_MINUTES,
            ):
                logger.warning(
                    f"Source {source.name} is in backoff period due to {source.error_count} failures. Skipping.",  # noqa: E501
                )
                result.error = f"In backoff period due to {source.error_count} failures"
                return result

        try:
            feed = await self._fetch_feed(source.url)
            if not feed:
                result.error = "Failed to fetch feed"
                await self._record_source_failure(source, "Feed fetch failed")
                return result

            entries = [FeedEntry.from_parsed_entry(entry) for entry in feed.entries]
            result.processed_count = len(entries)

            if not entries:
                logger.warning(f"No entries found in feed {source.name}")
                # Don't count empty feed as error if it was fetchable
                await self._record_source_success(source)
                return result

            logger.info(f"Found {len(entries)} entries in feed {source.name}")

            total_attempts = 0
            failed_attempts = 0
            consecutive_failures = 0

            for entry in entries:
                try:
                    total_attempts += 1
                    content = await self._process_entry(source, entry)
                    if content:
                        consecutive_failures = 0
                        result.new_content.append(content)
                        logger.info(f"Successfully processed entry: {entry.title}")
                    else:
                        failed_attempts += 1
                        consecutive_failures += 1
                        logger.debug(f"Failed to process entry: {entry.title}")
                except Exception as e:
                    failed_attempts += 1
                    consecutive_failures += 1
                    logger.error(f"Error processing entry {entry.url}: {e}")

                # Early failure detection
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        f"Stopping after {consecutive_failures} consecutive failures",
                    )
                    break

                # Check failure rate after minimum attempts
                if (
                    total_attempts >= MIN_ATTEMPTS_BEFORE_RATE_CHECK
                    and failed_attempts / total_attempts > MAX_FAILURE_RATE
                ):
                    logger.warning(
                        f"Stopping due to high failure rate: {failed_attempts}/{total_attempts}",  # noqa: E501
                    )
                    break

            result.fetch_failures = failed_attempts
            result.all_attempts_failed = (
                failed_attempts == total_attempts and total_attempts > 0
            )

            # Record source status based on fetch success rate
            if result.all_attempts_failed:
                await self._record_source_failure(
                    source,
                    f"All {total_attempts} fetch attempts failed",
                )
                logger.error(
                    f"Source {source.name} had {failed_attempts}/{total_attempts} failures",  # noqa: E501
                )
            elif failed_attempts > total_attempts / 2:
                # Partial failure - record it but don't
                # increment error count as severely
                await self._record_source_failure(
                    source,
                    f"High failure rate: {failed_attempts}/{total_attempts} attempts failed",  # noqa: E501
                    increment=0.5,
                )
                logger.warning(
                    f"Source {source.name} had high failure rate: {failed_attempts}/{total_attempts}",  # noqa: E501
                )
            else:
                await self._record_source_success(source)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Error processing source {source.name}: {str(e)}")
            await self._record_source_failure(source, str(e))

        return result

    async def _record_source_failure(
        self,
        source: Source,
        error_message: str,
        increment: float = 1.0,
    ):
        """Record a source failure and update error tracking"""
        source.error_count += increment
        source.last_checked = timezone.now()

        # Update error log
        error_entry = {
            "timestamp": timezone.now().isoformat(),
            "error": error_message,
            "error_count": source.error_count,
        }

        if not hasattr(source, "error_log") or not isinstance(source.error_log, list):
            source.error_log = []

        source.error_log.append(error_entry)
        # Keep only last 10 errors
        source.error_log = source.error_log[-10:]

        # Ensure error_count is an integer
        source.error_count = int(source.error_count + 0.5)

        await sync_to_async(source.save)()

        if source.error_count >= self.FAILURE_THRESHOLD:
            logger.warning(
                f"Source {source.name} has failed {source.error_count} times. "
                f"Entering {self.BACKOFF_MINUTES} minute backoff period.",
            )

    async def _record_source_success(self, source: Source):
        """Record a successful source processing"""
        if source.error_count > 0:
            logger.info(
                f"Resetting error count for source {source.name} after successful fetch",  # noqa: E501
            )
        source.error_count = 0
        source.last_checked = timezone.now()
        source.last_success = timezone.now()
        await sync_to_async(source.save)()

    async def _process_entry(self, source: Source, entry: FeedEntry) -> Content | None:
        """Process single feed entry with enhanced logging"""
        try:
            # Check for existing content
            if await Content.objects.filter(url=entry.url).aexists():
                logger.debug(f"Skipping existing content: {entry.url}")
                return None

            logger.info(f"Fetching content for: {entry.url}")
            fetch_result = await self.fetcher.fetch_content(entry.url)

            # Log fetch result details
            logger.info(
                f"Fetch result for {entry.url}: "
                f"quality={fetch_result.quality}, "
                f"strategy={fetch_result.strategy}, "
                f"success={fetch_result.success}",
            )

            if not fetch_result.success or fetch_result.quality in (
                ContentQuality.EMPTY,
                ContentQuality.BLOCKED,
            ):
                logger.warning(
                    f"Failed to fetch content for {entry.url}: {fetch_result.error}",
                )
                return None

            content = Content(
                source=source,
                title=entry.title,
                url=entry.url,
                raw_content=fetch_result.content,
                processed_content={
                    "fetch_quality": fetch_result.quality.value,
                    "fetch_strategy": (
                        fetch_result.strategy.value if fetch_result.strategy else None
                    ),
                    "metadata": fetch_result.metadata,
                },
                authors=[entry.author] if entry.author else [],
                publish_date=entry.published_at or timezone.now(),
            )

            await content.asave()
            logger.info(f"Successfully saved content: {entry.title}")
            return content

        except Exception:
            logger.exception(f"Error processing entry {entry.url}")
            return None

    async def aclose(self):
        """Close resources"""
        await self.client.aclose()


class PermanentFeedError(Exception):
    """Error indicating a feed should be deactivated"""

    pass


class FeedParseError(Exception):
    """Error parsing feed content"""

    pass


class FeedFetchError(Exception):
    """Error fetching feed content"""

    pass


class ContentFetchError(Exception):
    """Error fetching full content"""

    pass


# Add custom error handler
class ThreadSafeLogger:
    @staticmethod
    def error(msg, *args, **kwargs):
        exc_info = kwargs.pop("exc_info", None)
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        logger.error(msg, *args, exc_info=exc_info, **kwargs)


# Replace existing logger
safe_logger = ThreadSafeLogger()
