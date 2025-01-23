from typing import List

from django.db import models

from core.models import BaseModel, Content, ModelConfig


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
