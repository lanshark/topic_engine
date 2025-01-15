import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class BaseModel(models.Model):
    """Base model with common fields and utility methods"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def is_healthy(self) -> bool:
        """Check if source is healthy based on error count and last success"""
        if self.error_count >= 3:
            return False
        if self.last_success and (timezone.now() - self.last_success) > timedelta(days=2):
            return False
        return True

    def next_check_due(self) -> datetime:
        """Calculate when the next check should occur"""
        if not self.last_checked:
            return timezone.now()
        return self.last_checked + timedelta(seconds=self.check_frequency)


# NOTE: this should be in sources/models.py
class Source(BaseModel):
    """Content source - RSS feed or webpage with validation and health tracking"""

    TYPE_CHOICES = [
        ("rss", "RSS Feed"),
        ("page", "Web Page"),
    ]

    url = models.URLField(unique=True)
    name = models.CharField(max_length=500)
    source_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    active = models.BooleanField(default=True)
    check_frequency = models.IntegerField(default=3600)  # seconds
    last_checked = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)
    error_count = models.IntegerField(default=0)

    # CSS selectors for webpage sources
    selectors = models.JSONField(null=True, blank=True)

    # Health metrics and metadata
    health_metrics = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "last_checked"]),
            models.Index(fields=["source_type", "error_count"]),
        ]

    error_log = models.JSONField(default=list, blank=True)

    def add_processing_error(self, error: str):
        """Add error to processing log"""
        if not isinstance(self.error_log, list):
            self.error_log = []

        self.error_log.append(
            {"error": str(error), "timestamp": timezone.now().isoformat(), "url": self.url}
        )

        # Keep only last 100 errors
        self.error_log = self.error_log[-100:]
        self.save(update_fields=["error_log"])

    def clear_errors(self):
        """Clear error log"""
        self.error_log = []
        self.save(update_fields=["error_log"])

    def clean(self):
        """Validate source configuration"""
        super().clean()
        if self.source_type == "page" and not self.selectors:
            raise ValidationError("Webpage sources must have CSS selectors defined")

    def is_healthy(self) -> bool:
        """Check if source is healthy based on error count and last success"""
        if self.error_count >= 3:
            return False
        if self.last_success:
            time_since_success = timezone.now() - self.last_success
            if time_since_success > timedelta(days=2):
                return False
        return True

    def next_check_due(self) -> datetime:
        """Calculate when the next check should occur"""
        if not self.last_checked:
            return timezone.now()
        return self.last_checked + timedelta(seconds=self.check_frequency)

    def record_check(self, success: bool = True):
        """Record a check attempt"""
        self.last_checked = timezone.now()
        if success:
            self.last_success = self.last_checked
            self.error_count = 0
        else:
            self.error_count += 1
        self.save(update_fields=["last_checked", "last_success", "error_count"])

    def __str__(self):
        return f"{self.name} ({self.source_type})"


# NOTE: this should be in topics/models.py
class Topic(BaseModel):
    """Topic for content classification with hierarchy support"""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    # Templates for content generation
    templates = models.JSONField(default=dict, blank=True)

    # Topic hierarchy path for efficient traversal
    path = models.CharField(max_length=1000, blank=True)
    depth = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["path"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # Update path and depth
        if self.parent:
            self.path = f"{self.parent.path}/{self.slug}"
            self.depth = self.parent.depth + 1
        else:
            self.path = self.slug
            self.depth = 0

        super().save(*args, **kwargs)

    def get_ancestors(self) -> List["Topic"]:
        """Get all ancestor topics"""
        if not self.path:
            return []
        paths = self.path.split("/")[:-1]
        return list(Topic.objects.filter(slug__in=paths).order_by("depth"))

    def get_descendants(self) -> models.QuerySet["Topic"]:
        """Get all descendant topics"""
        return Topic.objects.filter(path__startswith=f"{self.path}/")


# NOTE: this should be in content/models.py
class Content(BaseModel):
    """Content item with processing state and geographic context"""

    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    url = models.URLField(max_length=2000, unique=True)
    title = models.CharField(max_length=500)
    raw_content = models.TextField()

    # Processing state and metadata
    processed = models.BooleanField(default=False)
    processed_content = models.JSONField(null=True, blank=True)
    processing_errors = models.JSONField(default=list, blank=True)
    processing_version = models.CharField(max_length=50, blank=True)

    # Topic classification
    topics = models.ManyToManyField(Topic, through="TopicScore")

    # Search and similarity
    search_vector = SearchVectorField(null=True)
    embedding = models.BinaryField(null=True)

    # Geographic context
    location = gis_models.PointField(null=True, blank=True, spatial_index=True)
    geo_context = models.JSONField(null=True, blank=True)

    # Content metadata
    publish_date = models.DateTimeField(null=True, blank=True)
    authors = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    # Example metadata structure for a fetched content item:
    # {
    #     'guid': '...',
    #     'original_title': '...',
    #     'fetch_strategy': 'browser',
    #     'content_quality': 'full',
    #     'fetch_timestamp': '2024-11-17T...',
    #     'fetch_error': '...',  # if failed
    #     'archive_source': '...'  # if from archive
    # }

    class Meta:
        indexes = [
            GinIndex(fields=["search_vector"]),
            models.Index(fields=["processed", "created_at"]),
            models.Index(fields=["publish_date"]),
        ]

    def mark_processed(self, version: str):
        """Mark content as processed with version tracking"""
        self.processed = True
        self.processing_version = version
        self.save(update_fields=["processed", "processing_version", "updated_at"])

    def add_processing_error(self, error: str):
        """Add processing error with timestamp"""
        self.processing_errors.append({"error": error, "timestamp": timezone.now().isoformat()})
        self.save(update_fields=["processing_errors", "updated_at"])

    def __str__(self):
        return f"{self.title[:50]}..."


class ModelConfig(BaseModel):
    """Configuration for SetFit models used in predictions"""

    def get_default_params():
        return {"model_type": "medium", "num_epochs": 2, "num_iterations": 20, "batch_size": 16}

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    parameters = models.JSONField(default=get_default_params)

    # Training metrics
    last_trained = models.DateTimeField(null=True, blank=True)
    training_examples = models.IntegerField(default=0)
    validation_accuracy = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name

    def update_training_metrics(self, num_examples: int, accuracy: float = None):
        """Update training metrics after model training"""
        self.last_trained = timezone.now()
        self.training_examples = num_examples
        if accuracy is not None:
            self.validation_accuracy = accuracy
        self.save(
            update_fields=["last_trained", "training_examples", "validation_accuracy", "updated_at"]
        )

    def get_model_path(self) -> str:
        """Get path where model should be stored"""
        return os.path.join(settings.DATA_DIR, "topics", "setfit_models", self.name)


# NOTE: this should be in topics/models.py
class TopicPrediction(BaseModel):
    """Score and confidence for content-topic relevance"""

    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    model_config = models.ForeignKey(ModelConfig, on_delete=models.CASCADE)
    result = models.CharField(max_length=50)  # 'relevant' or 'irrelevant'
    confidence = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ["content", "model_config"]
        indexes = [
            models.Index(fields=["result", "confidence"]),
        ]

    def __str__(self):
        return f"{self.content.title[:30]} - {self.model_config.name} ({self.result})"


# NOTE: this should be in topics/models.py
class TrainingExample(BaseModel):
    """Training example for topic classification"""

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    text = models.TextField()
    label = models.BooleanField()  # True for relevant, False for not relevant
    source_url = models.URLField(null=True, blank=True)

    # Vector embedding for similarity search
    embedding = models.BinaryField(null=True)

    # Training metadata
    added_by = models.CharField(max_length=200, blank=True)
    validated = models.BooleanField(default=False)
    validation_score = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["topic", "label"]),
            models.Index(fields=["validated", "validation_score"]),
        ]

    def __str__(self):
        return f"{self.text[:50]}... ({self.topic.name})"


# NOTE: this should be in topics/models.py
class TopicScore(BaseModel):
    """Through model for Content-Topic relationship with relevance score"""

    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    score = models.FloatField()
    confidence = models.FloatField()

    class Meta:
        unique_together = ["content", "topic"]
        indexes = [
            models.Index(fields=["score", "confidence"]),
        ]
