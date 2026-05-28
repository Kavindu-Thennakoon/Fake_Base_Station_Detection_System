from django.urls import path
from analytics.views import (
    dashboard_stats,
    anomaly_trends,
    cell_risk_ranking,
    detection_method_breakdown,
    recent_activity,
    geographic_heatmap,
    cell_anomaly_map,
    powerbi_anomalies,
    powerbi_alerts,
    powerbi_cell_risk,
    powerbi_geographic,
)

urlpatterns = [
    path("dashboard/", dashboard_stats, name="dashboard-stats"),
    path("trends/", anomaly_trends, name="anomaly-trends"),
    path("cell-risk/", cell_risk_ranking, name="cell-risk-ranking"),
    path("method-breakdown/", detection_method_breakdown, name="method-breakdown"),
    path("recent-activity/", recent_activity, name="recent-activity"),
    path("geographic/", geographic_heatmap, name="geographic-heatmap"),
    path("cell-anomaly-map/", cell_anomaly_map, name="cell-anomaly-map"),
    # PowerBI data export endpoints
    path("powerbi/anomalies/", powerbi_anomalies, name="powerbi-anomalies"),
    path("powerbi/alerts/", powerbi_alerts, name="powerbi-alerts"),
    path("powerbi/cell-risk/", powerbi_cell_risk, name="powerbi-cell-risk"),
    path("powerbi/geographic/", powerbi_geographic, name="powerbi-geographic"),
]
