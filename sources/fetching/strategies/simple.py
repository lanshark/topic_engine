# sources/fetching/strategies/simple.py
import asyncio
import logging

import httpx

from ..config import FetcherConfig
from ..strategy import FetchStrategy
from ..types import ContentQuality, FetchResult
from .base import ContentFetchStrategy

logger = logging.getLogger(__name__)


class SimpleHttpStrategy(ContentFetchStrategy):
    """Simple HTTP fetch strategy"""

    strategy_type = FetchStrategy.SIMPLE

    def __init__(self):
        # Configure for HTTP/1.1 by default as it's more reliable
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            http2=False,  # Disable HTTP/2 for more reliable connections
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
            transport=httpx.AsyncHTTPTransport(
                retries=3,  # Enable retries
            ),
        )

    async def fetch(self, url: str, config: FetcherConfig) -> FetchResult:
        """Fetch content with better error handling"""
        try:
            if not hasattr(self, "client") or self.client.is_closed:
                logger.warning("Recreating closed HTTP client")
                self.__init__()  # Recreate client if closed

            for attempt in range(3):  # Try up to 3 times
                try:
                    response = await self.client.get(
                        url,
                        headers=config.browser_headers,
                        timeout=config.strategy_timeout,
                    )
                    response.raise_for_status()

                    content = response.text
                    if not content:
                        logger.warning(f"Empty content received for {url}")
                        return self.create_result(
                            content=None,
                            quality=ContentQuality.EMPTY,
                            error="Empty response",
                        )

                    quality = await self.validate_content(content, config)

                    return self.create_result(
                        content=content,
                        quality=quality,
                        metadata={
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type"),
                            "content_length": len(content),
                            "attempt": attempt + 1,
                        },
                    )

                except (httpx.ReadError, httpx.RemoteProtocolError) as e:
                    if attempt == 2:  # Last attempt
                        raise
                    logger.warning(f"Retry {attempt + 1} for {url} due to: {str(e)}")
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                    continue

        except httpx.ReadError as e:
            logger.warning(f"Read error for {url}: {str(e)}")
            return self.create_result(
                content=None,
                quality=ContentQuality.EMPTY,
                error=f"Network read error: {str(e)}",
            )
        except httpx.RemoteProtocolError as e:
            logger.warning(f"Protocol error for {url}: {str(e)}")
            return self.create_result(
                content=None,
                quality=ContentQuality.EMPTY,
                error=f"Protocol error: {str(e)}",
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} for {url}")
            return self.create_result(
                content=None,
                quality=ContentQuality.EMPTY,
                error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {str(e)}")
            return self.create_result(
                content=None,
                quality=ContentQuality.EMPTY,
                error=str(e),
            )

    async def cleanup(self):
        """Close HTTP client"""
        if hasattr(self, "client") and not self.client.is_closed:
            await self.client.aclose()
