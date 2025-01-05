from datetime import timedelta
from io import StringIO

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from core.admin import process_opml_file
from core.models import Content, Source, Topic, TopicPrediction


class SourceModelTests(TestCase):
    def setUp(self):
        self.rss_source = Source.objects.create(
            url="http://example.com/feed.xml",
            name="Test RSS Feed",
            source_type="rss",
        )
        self.page_source = Source.objects.create(
            url="http://example.com/news",
            name="Test Page Source",
            source_type="page",
            selectors={
                "title": "h1.title",
                "content": "div.article-content",
            },
        )

    def test_health_tracking(self):
        """Test source health monitoring"""
        # Test initial state
        self.assertTrue(self.rss_source.is_healthy())

        # Test error count threshold
        self.rss_source.error_count = 3
        self.rss_source.save()
        self.assertFalse(self.rss_source.is_healthy())

        # Test last success threshold
        self.rss_source.error_count = 0
        old_time = timezone.now() - timedelta(days=3)
        self.rss_source.last_success = old_time
        self.rss_source.save()
        self.assertFalse(self.rss_source.is_healthy())

        # Test recovery
        self.rss_source.record_check(success=True)
        self.assertTrue(self.rss_source.is_healthy())

    def test_check_tracking(self):
        """Test check recording functionality"""
        # Test successful check
        self.rss_source.record_check(success=True)
        self.assertEqual(self.rss_source.error_count, 0)
        self.assertIsNotNone(self.rss_source.last_success)
        self.assertIsNotNone(self.rss_source.last_checked)

        # Test failed check
        self.rss_source.record_check(success=False)
        self.assertEqual(self.rss_source.error_count, 1)
        self.assertNotEqual(self.rss_source.last_checked, self.rss_source.last_success)

    def test_next_check_calculation(self):
        """Test check scheduling"""
        now = timezone.now()
        self.rss_source.last_checked = now
        self.rss_source.check_frequency = 1800  # 30 minutes
        self.rss_source.save()

        expected_next = now + timedelta(seconds=1800)
        self.assertAlmostEqual(
            self.rss_source.next_check_due().timestamp(),
            expected_next.timestamp(),
            delta=1,
        )


class TopicModelTests(TestCase):
    def setUp(self):
        self.parent = Topic.objects.create(
            name="Parent Topic",
            description="Parent topic for testing",
        )
        self.child = Topic.objects.create(
            name="Child Topic",
            description="Child topic for testing",
            parent=self.parent,
        )
        self.grandchild = Topic.objects.create(
            name="Grandchild Topic",
            description="Grandchild topic for testing",
            parent=self.child,
        )

    def test_slug_generation(self):
        """Test automatic slug generation"""
        topic = Topic.objects.create(name="Test Topic 123")
        self.assertEqual(topic.slug, "test-topic-123")

    def test_hierarchy_path(self):
        """Test path generation and hierarchy"""
        self.assertEqual(self.parent.path, "parent-topic")
        self.assertEqual(self.child.path, "parent-topic/child-topic")
        self.assertEqual(
            self.grandchild.path,
            "parent-topic/child-topic/grandchild-topic",
        )

    def test_ancestor_descendant_queries(self):
        """Test hierarchy traversal"""
        # Test ancestors
        grandchild_ancestors = self.grandchild.get_ancestors()
        self.assertEqual(len(grandchild_ancestors), 2)
        self.assertEqual(grandchild_ancestors[0], self.parent)
        self.assertEqual(grandchild_ancestors[1], self.child)

        # Test descendants
        parent_descendants = self.parent.get_descendants()
        self.assertEqual(parent_descendants.count(), 2)
        self.assertIn(self.child, parent_descendants)
        self.assertIn(self.grandchild, parent_descendants)


class ContentModelTests(TestCase):
    def setUp(self):
        self.source = Source.objects.create(
            url="http://example.com/feed.xml",
            name="Test Source",
            source_type="rss",
        )
        self.topic = Topic.objects.create(name="Test Topic")
        self.content = Content.objects.create(
            source=self.source,
            url="http://example.com/article1",
            title="Test Article",
            raw_content="Test content text",
        )

    def test_geographic_features(self):
        """Test geographic functionality"""
        location = Point(-122.4194, 37.7749)  # San Francisco
        self.content.location = location
        self.content.geo_context = {
            "city": "San Francisco",
            "state": "CA",
            "country": "USA",
        }
        self.content.save()

        # Test spatial query
        nearby = Content.objects.filter(
            location__distance_lte=(location, 5000),  # 5km radius
        )
        self.assertIn(self.content, nearby)

    def test_processing_tracking(self):
        """Test processing state management"""
        self.assertFalse(self.content.processed)

        # Test marking as processed
        self.content.mark_processed("v1.0")
        self.assertTrue(self.content.processed)
        self.assertEqual(self.content.processing_version, "v1.0")

        # Test error tracking
        self.content.add_processing_error("Test error")
        self.assertEqual(len(self.content.processing_errors), 1)
        self.assertEqual(self.content.processing_errors[0]["error"], "Test error")

    def test_topic_scoring(self):
        """Test topic relevance scoring"""
        TopicPrediction.objects.create(
            content=self.content,
            topic=self.topic,
            score=0.85,
            confidence=0.92,
            classifier_version="v1.0",
        )

        self.assertEqual(self.content.topics.count(), 1)
        self.assertEqual(
            # NOTE: content.topicscore_set is unknown...
            self.content.topicscore_set.first().score,
            0.85,
        )


class OPMLProcessingTests(TestCase):
    def setUp(self):
        # Remove leading whitespace and ensure proper XML declaration
        self.opml_content = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <head>
    <title>Test OPML</title>
  </head>
  <body>
    <outline text="News" title="News">
      <outline type="rss" text="Test Feed 1" xmlUrl="http://example.com/feed1.xml"/>
      <outline type="rss" text="Test Feed 2" xmlUrl="http://example.com/feed2.xml"/>
    </outline>
  </body>
</opml>"""

    def test_opml_import(self):
        """Test OPML feed import"""
        sources = process_opml_file(StringIO(self.opml_content))
        self.assertEqual(len(sources), 2)

        # Verify sources were created
        self.assertEqual(Source.objects.count(), 2)
        self.assertTrue(
            Source.objects.filter(url="http://example.com/feed1.xml").exists(),
        )
        self.assertTrue(
            Source.objects.filter(url="http://example.com/feed2.xml").exists(),
        )

        # Verify source properties
        source = Source.objects.first()
        # NOTE source_type and active are unknown...
        self.assertEqual(source.source_type, "rss")
        self.assertTrue(source.active)
