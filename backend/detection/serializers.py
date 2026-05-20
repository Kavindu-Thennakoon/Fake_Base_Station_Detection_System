from rest_framework import serializers
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


class CellModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CellModel
        fields = "__all__"


class DetectionRunSerializer(serializers.ModelSerializer):
    """Serializer for listing/retrieving detection runs with computed counts."""

    anomaly_count = serializers.SerializerMethodField()
    alert_count = serializers.SerializerMethodField()
    duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = DetectionRun
        fields = "__all__"

    def get_anomaly_count(self, obj):
        return obj.anomalies.count()

    def get_alert_count(self, obj):
        return obj.alerts.count()


class DetectionRunCreateSerializer(serializers.Serializer):
    """Serializer for triggering a new detection run via POST."""

    check_file = serializers.CharField(
        help_text="Path to MR CSV file to scan"
    )
    threshold_mult = serializers.FloatField(default=1.0, required=False)
    z_threshold = serializers.FloatField(default=2.0, required=False)
    min_anomaly_score = serializers.FloatField(default=4.0, required=False)
    n_jobs = serializers.IntegerField(default=-1, required=False)


class TrainingRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingRun
        fields = "__all__"


class TrainingRunCreateSerializer(serializers.Serializer):
    """Serializer for triggering a new training run via POST."""

    train_file = serializers.CharField(
        help_text="Path to training MR CSV file"
    )
    model_dir = serializers.CharField(required=False, allow_blank=True)
    num_trees = serializers.IntegerField(default=150, required=False)
    tree_size = serializers.IntegerField(default=1024, required=False)
    min_samples = serializers.IntegerField(default=50, required=False)
    n_jobs = serializers.IntegerField(default=4, required=False)


class NeighborAnomalyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = NeighborAnomalyDetail
        fields = [
            "id",
            "serving_cell_id",
            "neighbor_id",
            "anomaly_score",
            "rsrp",
            "rsrq",
            "rsrp_z",
            "rsrq_z",
        ]


class AnomalySerializer(serializers.ModelSerializer):
    """List serializer — lightweight, no nested neighbor details."""

    detection_method = serializers.ReadOnlyField()

    class Meta:
        model = Anomaly
        fields = [
            "id",
            "run",
            "serving_cell_id",
            "row_index",
            "datetime_raw",
            "avg_codisp",
            "threshold",
            "rrcf_flagged",
            "zscore_flagged",
            "detection_method",
        ]


class AnomalyDetailSerializer(serializers.ModelSerializer):
    """Detail serializer — includes nested neighbor breakdown."""

    neighbor_details = NeighborAnomalyDetailSerializer(
        many=True, read_only=True
    )
    detection_method = serializers.ReadOnlyField()

    class Meta:
        model = Anomaly
        fields = [
            "id",
            "run",
            "serving_cell_id",
            "row_index",
            "datetime_raw",
            "avg_codisp",
            "threshold",
            "rrcf_flagged",
            "zscore_flagged",
            "detection_method",
            "neighbor_details",
        ]


class SuspiciousNeighborSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspiciousNeighbor
        fields = "__all__"


class DetectedWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectedWindow
        fields = "__all__"


class AbnormalNeighborSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbnormalNeighbor
        fields = "__all__"