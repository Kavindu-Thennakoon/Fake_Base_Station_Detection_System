from django.contrib import admin
from detection.models import (
    DetectionRun,
    TrainingRun,
    CellModel,
    Anomaly,
    NeighborAnomalyDetail,
    SuspiciousNeighbor,
    DetectedWindow,
    AbnormalNeighbor,
)


@admin.register(DetectionRun)
class DetectionRunAdmin(admin.ModelAdmin):
    list_display = [
        "run_id", "status", "total_anomalies",
        "total_cells_scanned", "started_at", "completed_at",
    ]
    list_filter = ["status"]
    search_fields = ["run_id"]
    readonly_fields = ["started_at"]


@admin.register(TrainingRun)
class TrainingRunAdmin(admin.ModelAdmin):
    list_display = [
        "run_id", "status", "total_cells_trained",
        "num_trees", "tree_size", "started_at",
    ]
    list_filter = ["status"]
    search_fields = ["run_id"]


@admin.register(CellModel)
class CellModelAdmin(admin.ModelAdmin):
    list_display = [
        "serving_cell_id", "K", "mean_codisp",
        "std_codisp", "training_rows", "last_trained",
    ]
    search_fields = ["serving_cell_id"]
    list_filter = ["num_trees"]


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = [
        "id", "run", "serving_cell_id", "row_index",
        "avg_codisp", "rrcf_flagged", "zscore_flagged",
    ]
    list_filter = ["rrcf_flagged", "zscore_flagged"]
    search_fields = ["serving_cell_id"]
    raw_id_fields = ["run"]


@admin.register(NeighborAnomalyDetail)
class NeighborAnomalyDetailAdmin(admin.ModelAdmin):
    list_display = [
        "id", "anomaly", "neighbor_id",
        "anomaly_score", "rsrp", "rsrq",
    ]
    search_fields = ["neighbor_id", "serving_cell_id"]
    raw_id_fields = ["anomaly"]


@admin.register(SuspiciousNeighbor)
class SuspiciousNeighborAdmin(admin.ModelAdmin):
    list_display = [
        "run", "neighbor_id", "sum_score", "occurrence_count",
    ]
    search_fields = ["neighbor_id"]
    list_filter = ["run"]


@admin.register(DetectedWindow)
class DetectedWindowAdmin(admin.ModelAdmin):
    list_display = [
        "run", "serving_cell_id", "neighbor_id",
        "event_count", "window_start", "window_end",
    ]
    search_fields = ["neighbor_id", "serving_cell_id"]


@admin.register(AbnormalNeighbor)
class AbnormalNeighborAdmin(admin.ModelAdmin):
    list_display = [
        "run", "serving_cell_id", "neighbor_id",
        "event_count", "window_count",
    ]
    search_fields = ["neighbor_id"]