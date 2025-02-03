from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from core.views import AllArticlesView, ModelConfigListView
from sources.views import (SourceListView, article_detail, article_list,
                           mark_relevance, source_list)
from topics.views import (TopicCreateView, TopicDeleteView, TopicDetailView,
                          TopicListView, TopicUpdateView, add_training_data)

urlpatterns = [
    path("", source_list, name="source_list"),
    path("sources/", SourceListView.as_view(), name="source_list"),
    path("source/<uuid:source_id>/", article_list, name="article_list"),
    path("articles/", AllArticlesView.as_view(), name="all_articles"),
    path("article/<uuid:article_id>/", article_detail, name="article_detail"),
    path("article/<uuid:article_id>/mark_relevance/", mark_relevance, name="mark_relevance"),
    path(
        "article/<uuid:article_id>/add_training_data/", add_training_data, name="add_training_data"
    ),
    path("topics/", TopicListView.as_view(), name="topic_list"),
    path("topics/create/", TopicCreateView.as_view(), name="topic-create"),
    path("topics/<slug:slug>/", TopicDetailView.as_view(), name="topic-detail"),
    path("topics/<slug:slug>/update/", TopicUpdateView.as_view(), name="topic-update"),
    path("topics/<slug:slug>/delete/", TopicDeleteView.as_view(), name="topic-delete"),
    path("modelconfigs/", ModelConfigListView.as_view(), name="modelconfig_list"),
    path("admin/", admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
