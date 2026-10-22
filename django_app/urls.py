"""
URL configuration for the Vehicle Damage & Insurance Claim Django project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # django-allauth handles /accounts/google/login/ and callback
    path("accounts/", include("allauth.urls")),
    # Our core app
    path("", include("core.urls", namespace="core")),
]

# Serve media files locally during development
if settings.DEBUG and not settings.AWS_STORAGE_BUCKET_NAME:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
