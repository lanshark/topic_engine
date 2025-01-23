from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from core.views import AllArticlesView
from sources.views import article_detail, article_list, mark_relevance, source_list
from topics.views import TopicListView, add_training_data

urlpatterns = [
    path("", source_list, name="source_list"),
    path("source/<uuid:source_id>/", article_list, name="article_list"),
    path("articles/", AllArticlesView.as_view(), name="all_articles"),
    path("article/<uuid:article_id>/", article_detail, name="article_detail"),
    path("article/<uuid:article_id>/mark_relevance/", mark_relevance, name="mark_relevance"),
    path(
        "article/<uuid:article_id>/add_training_data/", add_training_data, name="add_training_data"
    ),
    path("topics/", TopicListView.as_view(), name="topic-list"),
    path("admin/", admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
