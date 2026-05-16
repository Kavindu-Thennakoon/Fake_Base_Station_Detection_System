from django.db import models


class DetectionRun(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    input_filename = models.CharField(max_length=255)
    output_dir = models.TextField()
    total_rows = models.IntegerField(default=0)
    total_anomalies = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default="success")  # success/error
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Run {self.id} - {self.created_at}"

