from django.db import models
from django.utils import timezone


class DetectionRun(models.Model):
    """Each execution of the detect_rrcf_v4.py pipeline."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    run_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    input_file = models.CharField(max_length=500)
    total_rows_scanned = models.IntegerField(default=0)
    total_anomalies = models.IntegerField(default=0)
    total_cells_scanned = models.IntegerField(default=0)

    # Detection parameters (matching detect_rrcf_v4.py CLI args)
    threshold_mult = models.FloatField(default=1.0)
    z_threshold = models.FloatField(default=2.0)
    min_anomaly_score = models.FloatField(default=4.0)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Output
    output_dir = models.CharField(max_length=500, blank=True, default="")
    error_log = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.run_id} [{self.status}] - {self.total_anomalies} anomalies"

    @property
    def duration_seconds(self):
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class TrainingRun(models.Model):
    """Each execution of the train_rrcf_gpu_mp_v4.py pipeline."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    run_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    train_file = models.CharField(max_length=500)
    model_dir = models.CharField(max_length=500, blank=True, default="")

    # Training parameters (matching train_rrcf_gpu_mp_v4.py CLI args)
    num_trees = models.IntegerField(default=150)
    tree_size = models.IntegerField(default=1024)
    min_samples = models.IntegerField(default=50)

    total_cells_trained = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Train {self.run_id} [{self.status}] - {self.total_cells_trained} cells"


class CellModel(models.Model):
    """
    Metadata about a trained per-cell RRCF model.
    Mirrors the contents of each .pkl file in v4_model/cell_meta/.
    Fields map directly to combined_meta.pkl structure.
    """

    serving_cell_id = models.CharField(max_length=50, unique=True, db_index=True)
    K = models.IntegerField(help_text="Number of unique neighbors = len(neighbor_order)")
    mean_codisp = models.FloatField(help_text="Baseline mean CoDisp score from training")
    std_codisp = models.FloatField(help_text="Baseline std CoDisp score from training")
    training_rows = models.IntegerField(default=0, help_text="Number of MR rows used for training")
    neighbor_order = models.JSONField(
        default=list,
        help_text="Ordered list of ALL unique neighbor cell IDs (defines feature columns)",
    )
    neighbor_stats = models.JSONField(
        default=dict,
        help_text="Per-neighbor RSRP/RSRQ mean/std statistics for Z-score computation",
    )
    num_trees = models.IntegerField(default=150, help_text="Number of RRCF trees")
    tree_size = models.IntegerField(default=1024, help_text="Max data points per tree")
    last_trained = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["serving_cell_id"]

    def __str__(self):
        return f"Cell {self.serving_cell_id} (K={self.K}, rows={self.training_rows})"


class Anomaly(models.Model):
    """
    Single anomalous MR record from anomalies.csv.
    Columns: serving_cell_id, row_index, datetime_raw,
             avg_codisp, threshold, rrcf_flagged, zscore_flagged
    """

    run = models.ForeignKey(
        DetectionRun, on_delete=models.CASCADE, related_name="anomalies"
    )
    serving_cell_id = models.CharField(max_length=50, db_index=True)
    row_index = models.IntegerField()
    datetime_raw = models.DateTimeField(null=True, blank=True)

    # RRCF scoring
    avg_codisp = models.FloatField(
        help_text="Average CoDisp score across 150 RRCF trees"
    )
    threshold = models.FloatField(
        help_text="mean_codisp + threshold_mult * std_codisp"
    )

    # Detection flags — OR logic: flagged if EITHER layer triggers
    rrcf_flagged = models.BooleanField(
        default=False,
        help_text="Layer 1: avg_codisp > threshold",
    )
    zscore_flagged = models.BooleanField(
        default=False,
        help_text="Layer 2: any neighbor combined Z-score > min_anomaly_score",
    )

    class Meta:
        ordering = ["-avg_codisp"]
        indexes = [
            models.Index(fields=["run", "serving_cell_id"]),
        ]

    def __str__(self):
        flags = []
        if self.rrcf_flagged:
            flags.append("RRCF")
        if self.zscore_flagged:
            flags.append("Z-Score")
        return (
            f"Anomaly row={self.row_index} "
            f"cell={self.serving_cell_id} [{'+'.join(flags)}]"
        )

    @property
    def detection_method(self):
        """Which detection layer(s) triggered this anomaly."""
        if self.rrcf_flagged and self.zscore_flagged:
            return "both"
        elif self.rrcf_flagged:
            return "rrcf_only"
        elif self.zscore_flagged:
            return "zscore_only"
        return "unknown"


class NeighborAnomalyDetail(models.Model):
    """
    Per-neighbor detail from neighbor_anomaly_details.csv.
    Columns: serving_cell_id, neighbor_id, anomaly_score,
             rsrp, rsrq, rsrp_z, rsrq_z
    """

    anomaly = models.ForeignKey(
        Anomaly, on_delete=models.CASCADE, related_name="neighbor_details"
    )
    serving_cell_id = models.CharField(max_length=50)
    neighbor_id = models.CharField(max_length=50, db_index=True)
    anomaly_score = models.FloatField(
        help_text="Combined Z-score: sqrt(rsrp_z^2 + rsrq_z^2)"
    )
    rsrp = models.FloatField(
        null=True, blank=True, help_text="Observed RSRP in dBm (-140 to -44)"
    )
    rsrq = models.FloatField(
        null=True, blank=True, help_text="Observed RSRQ in dB (-20 to -3)"
    )
    rsrp_z = models.FloatField(
        null=True, blank=True, help_text="RSRP Z-score vs training mean"
    )
    rsrq_z = models.FloatField(
        null=True, blank=True, help_text="RSRQ Z-score vs training mean"
    )

    class Meta:
        ordering = ["-anomaly_score"]

    def __str__(self):
        return f"Neighbor {self.neighbor_id} score={self.anomaly_score:.2f}"


class SuspiciousNeighbor(models.Model):
    """
    Aggregated suspicion ranking from neighbor_ranked.csv.
    Start investigation here — shows most suspicious neighbor cell IDs.
    """

    run = models.ForeignKey(
        DetectionRun, on_delete=models.CASCADE, related_name="suspicious_neighbors"
    )
    neighbor_id = models.CharField(max_length=50, db_index=True)
    sum_score = models.FloatField(help_text="Total cumulative anomaly score")
    occurrence_count = models.IntegerField(
        default=0, help_text="Number of times this neighbor was flagged"
    )
    affected_serving_cells = models.JSONField(
        default=list, help_text="List of serving cells where this neighbor appeared"
    )

    class Meta:
        ordering = ["-sum_score"]

    def __str__(self):
        return (
            f"Suspicious {self.neighbor_id} "
            f"score={self.sum_score:.2f} ({self.occurrence_count}x)"
        )


class DetectedWindow(models.Model):
    """
    Time windows where anomaly clusters occurred (detected_windows.csv).
    A neighbor must appear as anomalous >=10 times within any 30-minute window.
    """

    run = models.ForeignKey(
        DetectionRun, on_delete=models.CASCADE, related_name="detected_windows"
    )
    serving_cell_id = models.CharField(max_length=50)
    neighbor_id = models.CharField(max_length=50)
    window_start = models.DateTimeField(null=True, blank=True)
    window_end = models.DateTimeField(null=True, blank=True)
    event_count = models.IntegerField(
        default=0, help_text="Anomaly events in this window"
    )

    class Meta:
        ordering = ["-event_count"]

    def __str__(self):
        return f"Window {self.neighbor_id} ({self.event_count} events)"


class CellLocation(models.Model):
    """Geographic location of a cell tower for map visualization."""

    TECHNOLOGY_CHOICES = [
        ("LTE", "LTE"),
        ("5G-NR", "5G NR"),
        ("3G", "3G"),
    ]

    global_cell_id = models.CharField(max_length=50, unique=True, db_index=True)
    cell_name = models.CharField(max_length=200, blank=True, default="")
    latitude = models.FloatField()
    longitude = models.FloatField()
    technology = models.CharField(max_length=10, choices=TECHNOLOGY_CHOICES, default="LTE")
    band = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        ordering = ["global_cell_id"]

    def __str__(self):
        return f"{self.global_cell_id} ({self.latitude:.4f}, {self.longitude:.4f})"


class AbnormalNeighbor(models.Model):
    """
    Window-filtered summary from abnormal_neighbors.csv.
    Only persistent anomalies survive the filter (>=10 events in 30 min).
    """

    run = models.ForeignKey(
        DetectionRun, on_delete=models.CASCADE, related_name="abnormal_neighbors"
    )
    serving_cell_id = models.CharField(max_length=50)
    neighbor_id = models.CharField(max_length=50, db_index=True)
    event_count = models.IntegerField(
        default=0, help_text="Total anomaly events for this neighbor"
    )
    window_count = models.IntegerField(
        default=0, help_text="Number of 30-min windows where this neighbor triggered"
    )

    class Meta:
        ordering = ["-event_count"]

    def __str__(self):
        return (
            f"Abnormal {self.neighbor_id} "
            f"({self.event_count} events, {self.window_count} windows)"
        )
