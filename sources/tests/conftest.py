# sources/tests/conftest.py
import pytest
from unittest.mock import patch
from django.utils import timezone
from core.models import Source, Content


def get_unique_url(prefix="test"):
    """Generate unique URL for testing"""
    return f"http://{prefix}-{timezone.now().timestamp()}.com/feed"


@pytest.fixture
async def source(db):
    """Create test source"""
    return await Source.objects.acreate(
        name="Test Source",
        url=get_unique_url(),
        source_type="rss",
        active=True,
        last_checked=None,  # Important for testing check frequency
        health_metrics={},
        metadata={},
    )


@pytest.fixture
async def content(db, source):
    """Create a test content item"""
    source_obj = await source
    content = await Content.objects.acreate(
        title="Test Article",
        url="http://test.com/article",
        source=source_obj,
        raw_content="Test content",
    )
    try:
        yield content
    finally:
        await Content.objects.filter(id=content.id).adelete()
