from django.db import models
from django.contrib.auth.models import User


class Alert(models.Model):
    """Security alert generated when suspicious FBS activity is detected."""

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("new", "New"),
        ("acknowledged", "Acknowledged"),
        ("investigating", "Investigating"),
        ("resolved", "Resolved"),
        ("false_positive", "False Positive"),
    ]

    run = models.ForeignKey(
        "detection.DetectionRun",
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    neighbor_id = models.CharField(max_length=50, db_index=True)
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="medium"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="new"
    )

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")

    affected_cells_count = models.IntegerField(default=0)
    window_count = models.IntegerField(default=0)
    peak_anomaly_score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_alerts",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title} - {self.status}"


class AlertHistory(models.Model):
    """Audit trail for alert status changes."""

    alert = models.ForeignKey(
        Alert, on_delete=models.CASCADE, related_name="history"
    )
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Alert histories"

    def __str__(self):
        return f"Alert #{self.alert_id}: {self.old_status} -> {self.new_status}"