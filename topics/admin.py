from django.contrib import admin

from core.models import Topic, TopicPrediction


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "depth", "path")
    list_filter = ("depth",)
    search_fields = ("name", "slug", "path")
    prepopulated_fields = {"slug": ("name",)}

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return ("path", "depth")
        return ()


@admin.register(TopicPrediction)
class TopicPredictionAdmin(admin.ModelAdmin):
    list_display = ("content", "model_config", "result", "confidence", "created_at")
    list_filter = ("result", "model_config", "content__processed")
    search_fields = ("content__title", "model_config__name")
