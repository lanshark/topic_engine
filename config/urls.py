from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from core.views import (AllArticlesView, ModelConfigCreateView,
                        ModelConfigDeleteView, ModelConfigDetailView,
                        ModelConfigListView, ModelConfigUpdateView)
from sources.views import (SourceCreateView, SourceDeleteView,
                           SourceDetailView, SourceListView, SourceUpdateView,
                           article_detail, article_list, home_list,
                           mark_relevance)
from topics.views import (TopicCreateView, TopicDeleteView, TopicListView,
                          TopicUpdateView, add_training_data)

urlpatterns = [
    path("", home_list, name="home_list"),
    path("sources/", SourceListView.as_view(), name="source-list"),
    path("sources/create/", SourceCreateView.as_view(), name="source-create"),
    path("sources<slug:slug>/", SourceDetailView.as_view(), name="source-detail"),
    path("sources/<slug:slug>/update/", SourceUpdateView.as_view(), name="source-update"),
    path("sources/<slug:slug>/delete/", SourceDeleteView.as_view(), name="source-delete"),
    path("source/<uuid:source_id>/", article_list, name="article_list"),
    path("articles/", AllArticlesView.as_view(), name="all_articles"),
    path("article/<uuid:article_id>/", article_detail, name="article_detail"),
    path("article/<uuid:article_id>/mark_relevance/", mark_relevance, name="mark_relevance"),
    path(
        "article/<uuid:article_id>/add_training_data/", add_training_data, name="add_training_data"
    ),
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("topics/create/", TopicCreateView.as_view(), name="topic-create"),
    path("topics/<slug:slug>/update/", TopicUpdateView.as_view(), name="topic-update"),
    path("topics/<slug:slug>/delete/", TopicDeleteView.as_view(), name="topic-delete"),
    path("modelconfigs/", ModelConfigListView.as_view(), name="modelconfig-list"),
    path("modelconfigs/create/", ModelConfigCreateView.as_view(), name="modelconfig-create"),
    path("modelconfigs/<slug:slug>/", ModelConfigDetailView.as_view(), name="modelconfig-detail"),
    path(
        "modelconfigs/<slug:slug>/update/",
        ModelConfigUpdateView.as_view(),
        name="modelconfig-update",
    ),
    path(
        "modelconfigs/<slug:slug>/delete/",
        ModelConfigDeleteView.as_view(),
        name="modelconfig-delete",
    ),
    path("admin/", admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
