import xml.etree.ElementTree as ET
from io import StringIO

from django import forms
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html

from .models import Content, ModelConfig, Source, TrainingExample


class OPMLUploadForm(forms.Form):
    opml_file = forms.FileField()


def process_opml_file(opml_content):
    """Process OPML file and create sources"""
    if isinstance(opml_content, StringIO):
        tree = ET.parse(opml_content)
    else:
        tree = ET.parse(opml_content)
    root = tree.getroot()

    sources = []
    for outline in root.findall('.//outline[@type="rss"]'):
        url = outline.get("xmlUrl")
        if url:
            source, created = Source.objects.get_or_create(
                url=url,
                defaults={"name": outline.get("text", url), "source_type": "rss", "active": True},
            )
            sources.append(source)

    return sources


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "url",
        "source_type",
        "active",
        "health_status",
        "last_checked",
        "error_count",
    )
    list_filter = ("source_type", "active")
    search_fields = ("name", "url")
    readonly_fields = ("last_checked", "last_success", "error_count")

    def health_status(self, obj):
        if obj.is_healthy():
            return format_html('<span style="color: green;">●</span> Healthy')
        return format_html('<span style="color: red;">●</span> Unhealthy')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-opml/", self.import_opml, name="import-opml"),
        ]
        return custom_urls + urls

    def import_opml(self, request):
        if request.method == "POST":
            form = OPMLUploadForm(request.POST, request.FILES)
            if form.is_valid():
                sources = process_opml_file(request.FILES["opml_file"])
                self.message_user(
                    request, f"Successfully imported {len(sources)} RSS feeds from OPML"
                )
                return redirect("admin:core_source_changelist")
        else:
            form = OPMLUploadForm()

        return render(request, "admin/core/source/opml_upload.html", {"form": form})


@admin.register(Content)
class ContentAdmin(GISModelAdmin):
    list_display = ("title", "source", "processed", "publish_date")
    list_filter = ("processed", "source", "publish_date")
    search_fields = ("title", "raw_content")
    readonly_fields = ("processing_version", "processing_errors")

    fieldsets = (
        (None, {"fields": ("source", "url", "title", "raw_content")}),
        (
            "Processing",
            {
                "fields": (
                    "processed",
                    "processed_content",
                    "processing_version",
                    "processing_errors",
                )
            },
        ),
        ("Geographic", {"fields": ("location", "geo_context")}),
        ("Metadata", {"fields": ("publish_date", "authors", "metadata")}),
    )


@admin.register(TrainingExample)
class TrainingExampleAdmin(admin.ModelAdmin):
    list_display = ("text", "topic", "label", "validated", "validation_score")
    list_filter = ("topic", "label", "validated")
    search_fields = ("text",)
    readonly_fields = ("embedding",)


@admin.register(ModelConfig)
class ModelConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "topic", "get_model_type", "created_at")
    list_filter = ("topic", "name")
    search_fields = ("name", "topic__name")

    fieldsets = (
        (None, {"fields": ("name", "description", "topic")}),
        (
            "Model Parameters",
            {
                "fields": ("parameters",),
                "description": "Parameters should include: model_type (small/medium/large), num_epochs, num_iterations, batch_size",
            },
        ),
    )

    def get_model_type(self, obj):
        return obj.parameters.get("model_type", "Not set")

    get_model_type.short_description = "Model Type"
