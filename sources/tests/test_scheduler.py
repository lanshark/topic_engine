# sources/tests/test_scheduler.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.utils import timezone
from django.core.cache import cache
from django.test import override_settings
from core.models import Source, Content, TopicPrediction
from sources.scheduler import ContentScheduler
from sources.tests.conftest import get_unique_url

pytestmark = [
    pytest.mark.django_db,  # Enable DB access for all tests
    pytest.mark.asyncio,  # Mark all tests as async
]


async def test_scheduler_startup():
    """Test scheduler starts properly"""
    with patch("sources.scheduler.AsyncIOScheduler") as mock_scheduler:
        # Create scheduler after mocking to ensure it uses the mock
        scheduler = ContentScheduler()
        mock_instance = mock_scheduler.return_value

        # Mock check_feeds to prevent database access
        with patch.object(scheduler, "check_feeds"):
            await scheduler.start()
            assert scheduler._running == True
            mock_instance.start.assert_called_once()


async def test_feed_checking(db, source):
    """Test feed checking with mock source"""
    source = await source
    scheduler = ContentScheduler()
    scheduler.processor = AsyncMock()
    scheduler.processor.process_source.return_value = True

    await scheduler.check_feeds()

    scheduler.processor.process_source.assert_called_once_with(source)
    updated_source = await Source.objects.aget(id=source.id)
    assert updated_source.last_checked is not None


async def test_feed_check_frequency(db):
    """Test feed checking respects frequency"""
    source = await Source.objects.acreate(
        name="Test Source",
        url="http://example2.com/feed",  # Different URL
        source_type="rss",
        active=True,
        last_checked=timezone.now(),
    )

    scheduler = ContentScheduler()
    with patch("sources.services.FeedProcessor") as mock_processor:
        mock_processor.return_value.process_source = AsyncMock()
        await scheduler.check_feeds()
        mock_processor.return_value.process_source.assert_not_called()


async def test_prediction_processing(db):
    """Test prediction processing"""
    with patch("django.core.management.call_command") as mock_call:
        source = await Source.objects.acreate(
            name="Test Source", url=get_unique_url("pred"), source_type="rss", active=True
        )

        content = await Content.objects.acreate(
            title="Test Article", url=get_unique_url("article"), source=source
        )

        cache.set("pending_prediction_content", {str(content.id)})
        scheduler = ContentScheduler()
        await scheduler.process_predictions()

        mock_call.assert_called_once_with("predict_topics", content_ids=[str(content.id)])


async def test_scheduler_shutdown():
    """Test scheduler shutdown sequence"""
    with patch("sources.scheduler.AsyncIOScheduler") as mock_scheduler:
        scheduler = ContentScheduler()
        mock_instance = mock_scheduler.return_value

        await scheduler.start()
        await scheduler.stop()

        mock_instance.shutdown.assert_called_once()
        assert scheduler._running == False


async def test_empty_feed_check(db):
    """Test feed checking with no active sources"""
    scheduler = ContentScheduler()
    with patch("sources.services.FeedProcessor") as mock_processor:
        # Delete any existing sources
        await Source.objects.all().adelete()

        await scheduler.check_feeds()
        mock_processor.return_value.process_source.assert_not_called()
