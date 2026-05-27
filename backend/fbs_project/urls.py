"""
FBS Project — Main URL Configuration

API Routes:
    /admin/                    → Django admin
    /api/detection/            → Detection runs, anomalies, cells, training
    /api/alerts/               → Alert management
    /api/analytics/            → Dashboard stats, trends, rankings
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/detection/", include("detection.urls")),
    path("api/alerts/", include("alerts.urls")),
    path("api/analytics/", include("analytics.urls")),
]