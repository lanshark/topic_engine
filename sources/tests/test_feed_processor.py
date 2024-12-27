import pytest
from sources.services import FeedProcessor, PermanentFeedError
import asyncio
from django.test import TestCase
from unittest.mock import Mock, patch
from core.models import Source

pytestmark = pytest.mark.django_db

@pytest.mark.asyncio
async def test_feed_processor_lifecycle():
    processor = FeedProcessor()
    try:
        assert not processor.client.is_closed
        await asyncio.sleep(0.1)
        assert not processor.client.is_closed
    finally:
        await processor.aclose()
        assert processor.client.is_closed

@pytest.mark.asyncio
async def test_feed_processor_initialization():
    processor = FeedProcessor()
    try:
        assert processor.client is not None
        assert not processor.client.is_closed
        assert processor.executor is not None
        assert processor.semaphore._value == 10
    finally:
        await processor.aclose()

@pytest.mark.asyncio 
async def test_process_sources_batch():
    """Test processing multiple sources in batches"""
    processor = FeedProcessor()
    
    # Create test sources
    sources = [
        Mock(Source, name=f"test_source_{i}", url=f"http://test{i}.com")
        for i in range(3)
    ]
    
    try:
        results = await processor.process_sources(sources)
        assert len(results) == 3
    finally:
        await processor.aclose()

@pytest.mark.asyncio
async def test_client_cleanup():
    """Test client cleanup after batch processing"""
    processor = FeedProcessor()
    sources = [Mock(Source, name="test", url="http://test.com")]
    
    try:
        await processor.process_sources(sources)
        assert not processor.client.is_closed
    finally:
        await processor.aclose()
        assert processor.client.is_closed

@pytest.mark.asyncio
async def test_client_closure_handling():
    """Test handling of client closure during processing"""
    processor = FeedProcessor()
    
    # Create test sources
    sources = [
        Mock(Source, name=f"test_source_{i}", url=f"http://test{i}.com")
        for i in range(5)
    ]

    try:
        # Start processing
        process_task = asyncio.create_task(processor.process_sources(sources))
        
        # Wait briefly
        await asyncio.sleep(0.1)
        
        # Close processor
        await processor.aclose()
        
        # Verify client is closed
        assert processor.client.is_closed
        assert processor._is_closing
        
        # Verify attempting new processing raises error
        with pytest.raises(RuntimeError):
            await processor.process_sources([Mock(Source)])
            
    finally:
        # Cleanup
        if not process_task.done():
            process_task.cancel()