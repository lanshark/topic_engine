# conftest.py
import pytest
import asyncio
import logging
import os
import django


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_source(db):
    """Create a test source for use in tests."""
    from core.models import Source

    source = await Source.objects.acreate(
        url="http://test.com/feed",
        name="Test Feed",
        source_type="rss",
        active=True,
        check_frequency=300,
    )
    yield source
    await Source.objects.filter(id=source.id).adelete()


def pytest_configure():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    django.setup()
