# sources/fetching/config.py
from dataclasses import dataclass, field
from datetime import timedelta
import re
from typing import Dict, List, Pattern

from sources.fetching.types import ContentValidation


@dataclass
class FetcherConfig:
    """Configuration for content fetcher"""

    # Fetch settings
    max_retries: int = 3
    retry_delay: float = 1.0
    strategy_timeout: float = 30.0

    # Browser settings
    browser_pool_size: int = 5
    browser_headers: Dict[str, str] = field(
        default_factory=lambda: {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )

    # Archive settings
    archive_max_age: timedelta = field(default_factory=lambda: timedelta(days=30))
    archive_sources: List[str] = field(
        default_factory=lambda: ["wayback", "archive.today", "google"]
    )

    # Content validation
    validation: ContentValidation = field(default_factory=ContentValidation)

    # Connection settings
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

    # Content type settings
    allowed_content_types: List[str] = field(
        default_factory=lambda: [
            "text/html",
            "application/xhtml+xml",
            "application/xml",
            "text/plain",
        ]
    )
