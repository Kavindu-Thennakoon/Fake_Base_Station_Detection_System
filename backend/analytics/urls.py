from django.urls import path
from analytics.views import (
    dashboard_stats,
    anomaly_trends,
    cell_risk_ranking,
    detection_method_breakdown,
    recent_activity,
)

urlpatterns = [
    path("dashboard/", dashboard_stats, name="dashboard-stats"),
    path("trends/", anomaly_trends, name="anomaly-trends"),
    path("cell-risk/", cell_risk_ranking, name="cell-risk-ranking"),
    path("method-breakdown/", detection_method_breakdown, name="method-breakdown"),
    path("recent-activity/", recent_activity, name="recent-activity"),
]