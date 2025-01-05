# sources/fetching/strategies/archive.py
import asyncio
import logging
from urllib.parse import quote_plus

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import FetcherConfig
from ..strategy import FetchStrategy
from ..types import ContentQuality, FetchResult
from .base import ContentFetchStrategy

logger = logging.getLogger(__name__)


class ArchiveSource:
    """Base class for archive sources"""

    name: str = "base"

    async def get_archived_content(
        self,
        url: str,
        client: httpx.AsyncClient,
        config: FetcherConfig,
    ) -> dict | None:
        """Get content from archive"""
        raise NotImplementedError


class WaybackMachine(ArchiveSource):
    """Internet Archive's Wayback Machine"""

    name = "wayback"
    USER_AGENT = "TopicEngine/1.0 (https://github.com/NimbleMachine-andrew)"
    RATE_LIMIT = 1.0  # seconds between requests

    def __init__(self):
        self._last_request = 0
        self._lock = asyncio.Lock()

    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            if now - self._last_request < self.RATE_LIMIT:
                await asyncio.sleep(self.RATE_LIMIT - (now - self._last_request))
            self._last_request = now

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def get_archived_content(
        self,
        url: str,
        client: httpx.AsyncClient,
        config: FetcherConfig,
    ) -> dict | None:
        """Get content from Wayback Machine"""
        try:
            await self._rate_limit()

            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json",
            }

            # Check for available snapshots
            api_url = f"https://archive.org/wayback/available?url={quote_plus(url)}"
            logger.debug(f"Checking Wayback availability for {url}")

            response = await client.get(
                api_url,
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
            response.raise_for_status()

            data = response.json()
            if snapshot := data.get("archived_snapshots", {}).get("closest", {}):
                archive_url = snapshot.get("url")
                if not archive_url:
                    logger.debug(f"No archive URL found for {url}")
                    return None

                logger.debug(f"Found archive at {archive_url}")
                await self._rate_limit()

                # Get archived content
                response = await client.get(
                    archive_url,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=30.0,
                    follow_redirects=True,
                )
                response.raise_for_status()

                return {
                    "content": response.text,
                    "timestamp": snapshot.get("timestamp"),
                    "archive_url": archive_url,
                }

            logger.debug(f"No snapshots found for {url}")
            return None

        except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            logger.error(f"Timeout fetching {url} from Wayback: {str(e)}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Wayback error for {url}: {str(e)}")
            return None


class ArchiveStrategy(ContentFetchStrategy):
    """Archive-based fetch strategy"""

    strategy_type = FetchStrategy.ARCHIVE

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )

        # Initialize archive sources in priority order
        self.archives: list[ArchiveSource] = [
            WaybackMachine(),
            # Add more archives here
        ]

    async def fetch(self, url: str, config: FetcherConfig) -> FetchResult:
        """Fetch content from archives"""
        for archive in self.archives:
            try:
                if archived := await archive.get_archived_content(
                    url,
                    self.client,
                    config,
                ):
                    content = archived["content"]
                    quality = await self.validate_content(content, config)

                    return self.create_result(
                        content=content,
                        quality=quality,
                        metadata={
                            "archive_source": archive.name,
                            "archive_timestamp": archived.get("timestamp"),
                            "archive_url": archived.get("archive_url"),
                        },
                    )

            except Exception as e:
                logger.error(f"{archive.name} error for {url}: {str(e)}")
                continue

        return self.create_result(
            content=None,
            quality=ContentQuality.EMPTY,
            error="No archive content available",
        )

    async def cleanup(self):
        """Close HTTP client"""
        await self.client.aclose()
