# sources/fetching/types.py
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern

from .strategy import FetchStrategy

logger = logging.getLogger(__name__)


# Content Quality Types
class ContentQuality(Enum):
    FULL = "full"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    EMPTY = "empty"


def get_required_patterns() -> List[Pattern]:
    """Factory for required patterns with more lenient matching"""
    return [
        # Match any article-like container
        re.compile(
            r"<(article|main|div\s+class=['\"][^'\"]*(?:article|post|content)[^'\"]*['\"])[^>]*>"
        ),
        # Match typical content markers
        re.compile(r'class=["\'][^"\']*(?:content|article|post|story|text)[^"\']*["\']'),
        # Match article schema
        re.compile(r'(?:itemtype=["\']http://schema.org/Article["\']|typeof=["\']Article["\'])'),
    ]


def get_blocked_patterns() -> List[Pattern]:
    """Factory for blocked patterns - focus on clear paywall indicators"""
    return [
        re.compile(r"subscribe\s+to\s+continue|subscription\s+required", re.I),
        re.compile(r"premium\s+content|premium\s+access", re.I),
        re.compile(r"sign\s+in\s+to\s+read|login\s+to\s+continue", re.I),
    ]


@dataclass
class ContentValidation:
    """Content validation with improved logic"""

    min_length: int = 100  # Minimum content length
    max_length: int = 2_000_000  # Increased max length
    required_patterns: List[Pattern] = field(default_factory=get_required_patterns)
    blocked_patterns: List[Pattern] = field(default_factory=get_blocked_patterns)

    def validate(self, content: str) -> ContentQuality:
        """Validate content quality with improved logic"""
        try:
            if not content:
                return ContentQuality.EMPTY

            # Initialize patterns if needed
            if self.required_patterns is None:
                self.required_patterns = get_required_patterns()
            if self.blocked_patterns is None:
                self.blocked_patterns = get_blocked_patterns()

            # Length checks
            content_length = len(content)
            if content_length < self.min_length:
                return ContentQuality.EMPTY
            if content_length > self.max_length:
                return ContentQuality.PARTIAL

            # Check for blocked content first
            if any(pattern.search(content) for pattern in self.blocked_patterns):
                return ContentQuality.BLOCKED

            # Check for required patterns - need at least one match
            if any(pattern.search(content) for pattern in self.required_patterns):
                return ContentQuality.FULL

            # If content is substantial but doesn't match patterns, consider it partial
            if content_length > 1000:
                return ContentQuality.PARTIAL

            return ContentQuality.EMPTY

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return ContentQuality.PARTIAL if content else ContentQuality.EMPTY

    def __post_init__(self):
        """Ensure patterns are initialized"""
        if self.required_patterns is None:
            self.required_patterns = [
                re.compile(r"<(article|main)[^>]*>"),
                re.compile(r'class="[^"]*(?:post|article|story)[^"]*"'),
            ]
        if self.blocked_patterns is None:
            self.blocked_patterns = [
                re.compile(r"subscribe|subscription|paywall", re.I),
                re.compile(r"access denied|login required", re.I),
            ]


@dataclass
class FetchResult:
    """Result of a content fetch attempt"""

    content: Optional[str]
    quality: ContentQuality
    strategy: Optional[FetchStrategy] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if fetch was successful"""
        return self.content is not None and self.quality not in (
            ContentQuality.EMPTY,
            ContentQuality.BLOCKED,
        )

    def is_valid(self) -> bool:
        """Alias for success property"""
        return self.success
