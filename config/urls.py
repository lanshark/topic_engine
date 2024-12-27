"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views import AllArticlesView
from sources.views import source_list, article_list, article_detail, mark_relevance
from topics.views import add_training_data

urlpatterns = [
    path('', source_list, name='source_list'),
    path('source/<uuid:source_id>/', article_list, name='article_list'),
    path('articles/', AllArticlesView.as_view(), name='all_articles'),
    path('article/<uuid:article_id>/', article_detail, name='article_detail'),
    path('article/<uuid:article_id>/mark_relevance/', mark_relevance, name='mark_relevance'),
    path('article/<uuid:article_id>/add_training_data/', add_training_data, name='add_training_data'),
    path('admin/', admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)