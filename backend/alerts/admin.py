from django.contrib import admin
from alerts.models import Alert, AlertHistory


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        "id", "severity", "status", "neighbor_id", "title",
        "affected_cells_count", "peak_anomaly_score", "created_at",
    ]
    list_filter = ["severity", "status"]
    search_fields = ["neighbor_id", "title"]
    raw_id_fields = ["run", "resolved_by"]


@admin.register(AlertHistory)
class AlertHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "alert", "old_status", "new_status",
        "changed_by", "created_at",
    ]
    list_filter = ["new_status"]
    raw_id_fields = ["alert", "changed_by"]