from rest_framework import serializers
from alerts.models import Alert, AlertHistory


class AlertHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = AlertHistory
        fields = [
            "id", "old_status", "new_status", "comment",
            "changed_by", "changed_by_username", "created_at",
        ]

    def get_changed_by_username(self, obj):
        return obj.changed_by.username if obj.changed_by else None


class AlertSerializer(serializers.ModelSerializer):
    history = AlertHistorySerializer(many=True, read_only=True)
    run_id = serializers.CharField(source="run.run_id", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "run", "run_id", "neighbor_id", "severity", "status",
            "title", "description", "affected_cells_count", "window_count",
            "peak_anomaly_score", "created_at", "updated_at", "resolved_at",
            "resolved_by", "notes", "history",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AlertUpdateSerializer(serializers.Serializer):
    """For PATCH status changes with audit trail."""

    status = serializers.ChoiceField(choices=Alert.STATUS_CHOICES)
    comment = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )