from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone

from alerts.models import Alert, AlertHistory
from alerts.serializers import AlertSerializer, AlertUpdateSerializer


class AlertPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AlertViewSet(viewsets.ModelViewSet):
    """
    list:    GET    /api/alerts/?status=new&severity=critical
    read:    GET    /api/alerts/{id}/
    update:  PATCH  /api/alerts/{id}/
    + actions: acknowledge, resolve, false-positive
    """

    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    pagination_class = AlertPagination

    def get_queryset(self):
        qs = super().get_queryset()

        alert_status = self.request.query_params.get("status")
        if alert_status:
            qs = qs.filter(status=alert_status)

        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)

        neighbor_id = self.request.query_params.get("neighbor_id")
        if neighbor_id:
            qs = qs.filter(neighbor_id=neighbor_id)

        return qs

    def partial_update(self, request, *args, **kwargs):
        """PATCH — update alert status with audit trail."""
        alert = self.get_object()
        ser = AlertUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        old_status = alert.status
        new_status = ser.validated_data["status"]

        # Create audit history record
        AlertHistory.objects.create(
            alert=alert,
            changed_by=(
                request.user if request.user.is_authenticated else None
            ),
            old_status=old_status,
            new_status=new_status,
            comment=ser.validated_data.get("comment", ""),
        )

        # Update alert
        alert.status = new_status
        if ser.validated_data.get("notes"):
            alert.notes = ser.validated_data["notes"]

        if new_status in ("resolved", "false_positive"):
            alert.resolved_at = timezone.now()
            if request.user.is_authenticated:
                alert.resolved_by = request.user

        alert.save()
        return Response(AlertSerializer(alert).data)

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        """POST /api/alerts/{id}/acknowledge/"""
        alert = self.get_object()
        old_status = alert.status

        AlertHistory.objects.create(
            alert=alert,
            changed_by=(
                request.user if request.user.is_authenticated else None
            ),
            old_status=old_status,
            new_status="acknowledged",
            comment=request.data.get("comment", "Acknowledged by operator"),
        )
        alert.status = "acknowledged"
        alert.save()
        return Response(AlertSerializer(alert).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        """POST /api/alerts/{id}/resolve/"""
        alert = self.get_object()
        old_status = alert.status

        AlertHistory.objects.create(
            alert=alert,
            changed_by=(
                request.user if request.user.is_authenticated else None
            ),
            old_status=old_status,
            new_status="resolved",
            comment=request.data.get("comment", "Resolved"),
        )
        alert.status = "resolved"
        alert.resolved_at = timezone.now()
        if request.user.is_authenticated:
            alert.resolved_by = request.user
        alert.save()
        return Response(AlertSerializer(alert).data)

    @action(detail=True, methods=["post"], url_path="false-positive")
    def mark_false_positive(self, request, pk=None):
        """POST /api/alerts/{id}/false-positive/"""
        alert = self.get_object()
        old_status = alert.status

        AlertHistory.objects.create(
            alert=alert,
            changed_by=(
                request.user if request.user.is_authenticated else None
            ),
            old_status=old_status,
            new_status="false_positive",
            comment=request.data.get("comment", "Marked as false positive"),
        )
        alert.status = "false_positive"
        alert.resolved_at = timezone.now()
        if request.user.is_authenticated:
            alert.resolved_by = request.user
        alert.save()
        return Response(AlertSerializer(alert).data)