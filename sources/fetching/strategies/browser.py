# sources/fetching/strategies/browser.py
import asyncio
import logging
from typing import Dict, Optional

from playwright.async_api import Browser, Page, async_playwright

from ..config import FetcherConfig
from ..strategy import FetchStrategy
from ..types import ContentQuality, FetchResult
from .base import ContentFetchStrategy

logger = logging.getLogger(__name__)


class BrowserStrategy(ContentFetchStrategy):
    """Browser simulation fetch strategy"""

    strategy_type = FetchStrategy.BROWSER

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context_pool: Dict[str, Page] = {}
        self.pool_lock = asyncio.Lock()

    async def ensure_browser(self):
        """Ensure browser is initialized"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch()

    async def get_page(self) -> Page:
        """Get a page from the pool or create new one"""
        await self.ensure_browser()

        async with self.pool_lock:
            # Create new context and page
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080}, java_script_enabled=True
            )
            page = await context.new_page()
            return page

    async def fetch(self, url: str, config: FetcherConfig) -> FetchResult:
        """Fetch content using browser simulation"""
        page = None
        try:
            page = await self.get_page()

            # Set headers
            await page.set_extra_http_headers(config.browser_headers)

            # Navigate and wait for content
            response = await page.goto(
                url, wait_until="networkidle", timeout=config.strategy_timeout * 1000
            )

            if not response:
                return self.create_result(
                    content=None, quality=ContentQuality.EMPTY, error="No response from page"
                )

            # Wait for typical content selectors
            for selector in ["article", "main", ".article-content", ".post-content"]:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue

            # Get content
            content = await page.content()
            if not content:
                return self.create_result(
                    content=None, quality=ContentQuality.EMPTY, error="Empty page content"
                )

            quality = await self.validate_content(content, config)

            return self.create_result(
                content=content,
                quality=quality,
                metadata={
                    "status_code": response.status,
                    "content_type": response.headers.get("content-type"),
                    "url": response.url,  # Final URL after redirects
                },
            )

        except Exception as e:
            return self.create_result(content=None, quality=ContentQuality.EMPTY, error=str(e))
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass

    async def cleanup(self):
        """Cleanup browser resources"""
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
            self.browser = None
