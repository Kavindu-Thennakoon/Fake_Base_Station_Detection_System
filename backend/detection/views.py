import os
import csv
from collections import defaultdict

from django.conf import settings
from django.db.models import Avg, Count, Sum, Max, Min, F
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

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
from detection.serializers import (
    DetectionRunSerializer,
    DetectionRunCreateSerializer,
    TrainingRunSerializer,
    TrainingRunCreateSerializer,
    CellModelSerializer,
    AnomalySerializer,
    AnomalyDetailSerializer,
    SuspiciousNeighborSerializer,
    DetectedWindowSerializer,
    AbnormalNeighborSerializer,
    CSVUploadSerializer,
)
from detection.services.ml_bridge import MLBridge
from detection.services.explainability import ExplainabilityService
from alerts.models import Alert


class StandardResultsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500


# ===================================================================
# DETECTION RUNS
# ===================================================================
class DetectionRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:    GET  /api/detection/runs/
    read:    GET  /api/detection/runs/{id}/
    trigger: POST /api/detection/runs/trigger/
    + custom actions: anomalies, suspicious-neighbors, windows, summary
    """

    queryset = DetectionRun.objects.all()
    serializer_class = DetectionRunSerializer
    pagination_class = StandardResultsPagination

    @action(detail=False, methods=["post"], url_path="trigger")
    def trigger(self, request):
        """
        POST /api/detection/runs/trigger/
        Body: { "check_file": "/path/to/data.csv", ... }

        Triggers detect_rrcf_v4.py, parses results, generates alerts.
        """
        ser = DetectionRunCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        bridge = MLBridge()
        run = bridge.run_detection(
            check_file=ser.validated_data["check_file"],
            threshold_mult=ser.validated_data.get("threshold_mult", 1.0),
            z_threshold=ser.validated_data.get("z_threshold", 2.0),
            min_anomaly_score=ser.validated_data.get(
                "min_anomaly_score", 4.0
            ),
            n_jobs=ser.validated_data.get("n_jobs", -1),
        )
        return Response(
            DetectionRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="anomalies")
    def anomalies(self, request, pk=None):
        """
        GET /api/detection/runs/{id}/anomalies/
        Optional query params: ?cell_id=12345&method=rrcf_only
        """
        run = self.get_object()
        qs = run.anomalies.all()

        # Optional filters
        cell_id = request.query_params.get("cell_id")
        method = request.query_params.get("method")
        if cell_id:
            qs = qs.filter(serving_cell_id=cell_id)
        if method == "rrcf_only":
            qs = qs.filter(rrcf_flagged=True, zscore_flagged=False)
        elif method == "zscore_only":
            qs = qs.filter(rrcf_flagged=False, zscore_flagged=True)
        elif method == "both":
            qs = qs.filter(rrcf_flagged=True, zscore_flagged=True)

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                AnomalySerializer(page, many=True).data
            )
        return Response(AnomalySerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="suspicious-neighbors")
    def suspicious_neighbors(self, request, pk=None):
        """GET /api/detection/runs/{id}/suspicious-neighbors/"""
        run = self.get_object()
        qs = run.suspicious_neighbors.all()
        return Response(
            SuspiciousNeighborSerializer(qs, many=True).data
        )

    @action(detail=True, methods=["get"], url_path="windows")
    def windows(self, request, pk=None):
        """GET /api/detection/runs/{id}/windows/"""
        run = self.get_object()
        qs = run.detected_windows.all()
        return Response(
            DetectedWindowSerializer(qs, many=True).data
        )

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """
        GET /api/detection/runs/{id}/summary/
        Quick overview stats for a single run — used by dashboard cards.
        """
        run = self.get_object()
        anomalies_qs = run.anomalies.all()

        rrcf_only = anomalies_qs.filter(
            rrcf_flagged=True, zscore_flagged=False
        ).count()
        zscore_only = anomalies_qs.filter(
            rrcf_flagged=False, zscore_flagged=True
        ).count()
        both = anomalies_qs.filter(
            rrcf_flagged=True, zscore_flagged=True
        ).count()

        return Response({
            "run_id": run.run_id,
            "status": run.status,
            "total_anomalies": run.total_anomalies,
            "rrcf_only": rrcf_only,
            "zscore_only": zscore_only,
            "both_layers": both,
            "suspicious_neighbors": run.suspicious_neighbors.count(),
            "detected_windows": run.detected_windows.count(),
            "abnormal_neighbors": run.abnormal_neighbors.count(),
            "alerts_generated": run.alerts.count(),
            "duration_seconds": run.duration_seconds,
            "parameters": {
                "threshold_mult": run.threshold_mult,
                "z_threshold": run.z_threshold,
                "min_anomaly_score": run.min_anomaly_score,
            },
        })


# ===================================================================
# TRAINING RUNS
# ===================================================================
class TrainingRunViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:    GET  /api/detection/training/
    read:    GET  /api/detection/training/{id}/
    trigger: POST /api/detection/training/trigger/
    """

    queryset = TrainingRun.objects.all()
    serializer_class = TrainingRunSerializer
    pagination_class = StandardResultsPagination

    @action(detail=False, methods=["post"], url_path="trigger")
    def trigger(self, request):
        """
        POST /api/detection/training/trigger/
        Body: { "train_file": "/path/to/train.csv", ... }

        Triggers train_rrcf_gpu_mp_v4.py, syncs models to DB.
        """
        ser = TrainingRunCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        bridge = MLBridge()
        run = bridge.run_training(
            train_file=ser.validated_data["train_file"],
            model_dir=ser.validated_data.get("model_dir") or None,
            num_trees=ser.validated_data.get("num_trees", 150),
            tree_size=ser.validated_data.get("tree_size", 1024),
            min_samples=ser.validated_data.get("min_samples", 50),
            n_jobs=ser.validated_data.get("n_jobs", 4),
        )
        return Response(
            TrainingRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )


# ===================================================================
# CELL MODELS
# ===================================================================
class CellModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:    GET /api/detection/cells/
    read:    GET /api/detection/cells/{serving_cell_id}/
    profile: GET /api/detection/cells/{serving_cell_id}/profile/
    """

    queryset = CellModel.objects.all()
    serializer_class = CellModelSerializer
    pagination_class = StandardResultsPagination
    lookup_field = "serving_cell_id"

    @action(detail=True, methods=["get"], url_path="profile")
    def profile(self, request, serving_cell_id=None):
        """
        GET /api/detection/cells/{serving_cell_id}/profile/
        Returns XAI cell profile from ExplainabilityService.
        """
        svc = ExplainabilityService()
        result = svc.get_cell_profile(serving_cell_id)
        return Response(result)


# ===================================================================
# ANOMALIES
# ===================================================================
class AnomalyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:    GET /api/detection/anomalies/?run_id=...&cell_id=...
    read:    GET /api/detection/anomalies/{id}/  (with neighbor details)
    explain: GET /api/detection/anomalies/{id}/explain/  (XAI)
    """

    serializer_class = AnomalySerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        qs = Anomaly.objects.all()
        run_id = self.request.query_params.get("run_id")
        cell_id = self.request.query_params.get("cell_id")
        if run_id:
            qs = qs.filter(run__run_id=run_id)
        if cell_id:
            qs = qs.filter(serving_cell_id=cell_id)
        return qs

    def get_serializer_class(self):
        """Use detail serializer (with neighbor breakdown) for retrieve."""
        if self.action == "retrieve":
            return AnomalyDetailSerializer
        return AnomalySerializer

    @action(detail=True, methods=["get"], url_path="explain")
    def explain(self, request, pk=None):
        """
        GET /api/detection/anomalies/{id}/explain/
        Returns full XAI explanation from ExplainabilityService.
        """
        svc = ExplainabilityService()
        result = svc.get_anomaly_explanation(pk)
        return Response(result)


# ===================================================================
# MODEL STATUS (standalone view)
# ===================================================================
@api_view(["GET"])
def model_status(request):
    """
    GET /api/detection/model-status/
    Check trained model health — loads combined_meta.pkl.
    """
    bridge = MLBridge()
    result = bridge.get_model_status()
    return Response(result)


@api_view(["GET"])
def neighbor_risk_profile(request, neighbor_id):
    """
    GET /api/detection/neighbors/{neighbor_id}/risk-profile/
    Returns cross-run risk profile for a specific neighbor cell.
    """
    svc = ExplainabilityService()
    result = svc.get_neighbor_risk_profile(neighbor_id)
    return Response(result)


@api_view(["GET"])
def suspicious_neighbors_list(request):
    """
    GET /api/detection/suspicious-neighbors/?run_id=...&severity=...&search=...&page=1&page_size=50
    Paginated list of suspicious neighbors with severity classification.
    """
    run_id = request.query_params.get("run_id")
    severity = request.query_params.get("severity")
    search = request.query_params.get("search", "").strip()

    qs = SuspiciousNeighbor.objects.select_related("run").all().order_by("-sum_score")
    if run_id:
        qs = qs.filter(run__run_id=run_id)
    if search:
        qs = qs.filter(neighbor_id__icontains=search)

    if severity:
        from django.db.models import Q, Case, When, CharField
        if severity == "critical":
            qs = qs.filter(Q(sum_score__gte=50) | Q(occurrence_count__gte=100))
        elif severity == "high":
            qs = qs.filter(
                Q(sum_score__gte=20, sum_score__lt=50, occurrence_count__lt=100) |
                Q(occurrence_count__gte=50, occurrence_count__lt=100, sum_score__lt=50)
            )
        elif severity == "medium":
            qs = qs.filter(
                Q(sum_score__gte=10, sum_score__lt=20, occurrence_count__lt=50) |
                Q(occurrence_count__gte=20, occurrence_count__lt=50, sum_score__lt=10)
            )
        elif severity == "low":
            qs = qs.filter(sum_score__lt=10, occurrence_count__lt=20)

    total = qs.count()

    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 50))
    start = (page - 1) * page_size
    end = start + page_size

    results = []
    for sn in qs[start:end]:
        s = sn.sum_score
        if s >= 50 or sn.occurrence_count >= 100:
            sev = "critical"
        elif s >= 20 or sn.occurrence_count >= 50:
            sev = "high"
        elif s >= 10 or sn.occurrence_count >= 20:
            sev = "medium"
        else:
            sev = "low"

        results.append({
            "id": sn.id,
            "neighbor_id": sn.neighbor_id,
            "sum_score": round(sn.sum_score, 4),
            "occurrence_count": sn.occurrence_count,
            "affected_serving_cells": sn.affected_serving_cells,
            "affected_cells_count": len(sn.affected_serving_cells) if sn.affected_serving_cells else 0,
            "severity": sev,
            "run_id": sn.run.run_id,
            "run_pk": sn.run.pk,
        })

    return Response({
        "count": total,
        "page": page,
        "page_size": page_size,
        "results": results,
    })


@api_view(["GET"])
def neighbor_detail(request, neighbor_id):
    """
    GET /api/detection/neighbors/{neighbor_id}/detail/?run_id=...
    Full detail page data for a single suspicious neighbor.
    """
    run_id = request.query_params.get("run_id")

    details_qs = NeighborAnomalyDetail.objects.filter(
        neighbor_id=str(neighbor_id)
    ).select_related("anomaly", "anomaly__run")

    if run_id:
        details_qs = details_qs.filter(anomaly__run__run_id=run_id)

    if not details_qs.exists():
        return Response(
            {"error": f"No records for neighbor {neighbor_id}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    total_score = 0
    total_count = details_qs.count()
    serving_cells_map = defaultdict(lambda: {
        "count": 0, "rsrp_sum": 0, "rsrq_sum": 0,
        "rsrp_z_sum": 0, "rsrq_z_sum": 0,
        "rsrp_values": [], "rsrq_values": [],
        "rsrp_z_values": [], "rsrq_z_values": [],
        "score_sum": 0, "in_baseline": False,
    })
    runs_seen = set()
    mr_records = []

    for d in details_qs.order_by("-anomaly_score")[:500]:
        total_score += d.anomaly_score
        runs_seen.add(d.anomaly.run.run_id)
        cell = serving_cells_map[d.serving_cell_id]
        cell["count"] += 1
        cell["score_sum"] += d.anomaly_score
        if d.rsrp is not None:
            cell["rsrp_sum"] += d.rsrp
            cell["rsrp_values"].append(d.rsrp)
        if d.rsrq is not None:
            cell["rsrq_sum"] += d.rsrq
            cell["rsrq_values"].append(d.rsrq)
        if d.rsrp_z is not None:
            cell["rsrp_z_sum"] += d.rsrp_z
            cell["rsrp_z_values"].append(d.rsrp_z)
        if d.rsrq_z is not None:
            cell["rsrq_z_sum"] += d.rsrq_z
            cell["rsrq_z_values"].append(d.rsrq_z)

        mr_records.append({
            "anomaly_id": d.anomaly.id,
            "row_index": d.anomaly.row_index,
            "serving_cell_id": d.serving_cell_id,
            "avg_codisp": round(d.anomaly.avg_codisp, 4),
            "threshold": round(d.anomaly.threshold, 4),
            "rrcf_flagged": d.anomaly.rrcf_flagged,
            "zscore_flagged": d.anomaly.zscore_flagged,
            "detection_method": d.anomaly.detection_method,
            "datetime_raw": d.anomaly.datetime_raw.isoformat() if d.anomaly.datetime_raw else None,
            "rsrp": d.rsrp,
            "rsrq": d.rsrq,
            "rsrp_z": round(d.rsrp_z, 4) if d.rsrp_z is not None else None,
            "rsrq_z": round(d.rsrq_z, 4) if d.rsrq_z is not None else None,
            "anomaly_score": round(d.anomaly_score, 4),
        })

    affected_cells = []
    for cell_id, data in serving_cells_map.items():
        n = data["count"]
        try:
            cm = CellModel.objects.get(serving_cell_id=cell_id)
            in_baseline = str(neighbor_id) in (cm.neighbor_order or [])
            baseline_stats = (cm.neighbor_stats or {}).get(str(neighbor_id))
        except CellModel.DoesNotExist:
            in_baseline = False
            baseline_stats = None

        affected_cells.append({
            "serving_cell_id": cell_id,
            "count": n,
            "avg_rsrp": round(data["rsrp_sum"] / len(data["rsrp_values"]), 2) if data["rsrp_values"] else None,
            "avg_rsrq": round(data["rsrq_sum"] / len(data["rsrq_values"]), 2) if data["rsrq_values"] else None,
            "avg_rsrp_z": round(data["rsrp_z_sum"] / len(data["rsrp_z_values"]), 2) if data["rsrp_z_values"] else None,
            "avg_rsrq_z": round(data["rsrq_z_sum"] / len(data["rsrq_z_values"]), 2) if data["rsrq_z_values"] else None,
            "avg_score": round(data["score_sum"] / n, 4),
            "in_baseline": in_baseline,
            "baseline_stats": baseline_stats,
        })
    affected_cells.sort(key=lambda x: x["count"], reverse=True)

    if total_score >= 50 or total_count >= 100:
        severity = "critical"
    elif total_score >= 20 or total_count >= 50:
        severity = "high"
    elif total_score >= 10 or total_count >= 20:
        severity = "medium"
    else:
        severity = "low"

    in_any_baseline = any(c["in_baseline"] for c in affected_cells)

    alert = Alert.objects.filter(neighbor_id=str(neighbor_id)).order_by("-created_at").first()
    alert_info = None
    if alert:
        alert_info = {
            "id": alert.id,
            "severity": alert.severity,
            "status": alert.status,
            "created_at": alert.created_at.isoformat(),
        }

    svc = ExplainabilityService()
    risk_profile = svc.get_neighbor_risk_profile(neighbor_id)

    rsrp_all = []
    rsrq_all = []
    rsrp_z_all = []
    rsrq_z_all = []
    for data in serving_cells_map.values():
        rsrp_all.extend(data["rsrp_values"])
        rsrq_all.extend(data["rsrq_values"])
        rsrp_z_all.extend(data["rsrp_z_values"])
        rsrq_z_all.extend(data["rsrq_z_values"])

    signal_summary = {
        "rsrp_min": round(min(rsrp_all), 2) if rsrp_all else None,
        "rsrp_max": round(max(rsrp_all), 2) if rsrp_all else None,
        "rsrp_avg": round(sum(rsrp_all) / len(rsrp_all), 2) if rsrp_all else None,
        "rsrq_min": round(min(rsrq_all), 2) if rsrq_all else None,
        "rsrq_max": round(max(rsrq_all), 2) if rsrq_all else None,
        "rsrq_avg": round(sum(rsrq_all) / len(rsrq_all), 2) if rsrq_all else None,
        "rsrp_z_avg": round(sum(rsrp_z_all) / len(rsrp_z_all), 2) if rsrp_z_all else None,
        "rsrq_z_avg": round(sum(rsrq_z_all) / len(rsrq_z_all), 2) if rsrq_z_all else None,
    }

    return Response({
        "neighbor_id": str(neighbor_id),
        "total_score": round(total_score, 4),
        "occurrence_count": total_count,
        "affected_cells_count": len(affected_cells),
        "runs_count": len(runs_seen),
        "severity": severity,
        "in_any_baseline": in_any_baseline,
        "signal_summary": signal_summary,
        "affected_cells": affected_cells,
        "mr_records": mr_records,
        "alert": alert_info,
        "risk_profile": risk_profile if "error" not in risk_profile else None,
    })


HEADER_SCHEMAS = [
    {
        "name": "normalized",
        "required": {"serving_cell_id", "nbr_cell_1_id", "nbr_cell_1_rsrp"},
    },
    {
        "name": "raw_dataset",
        "required": {"enodebid", "cellid", "eutrancellid1", "avg_dlrsrp_d1"},
    },
]


def _validate_csv_headers(header_set):
    for schema in HEADER_SCHEMAS:
        if schema["required"].issubset(header_set):
            return True, schema["name"], []
    all_options = " OR ".join(
        ", ".join(sorted(s["required"])) for s in HEADER_SCHEMAS
    )
    return False, None, [f"Need one of: {all_options}"]


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_csv(request):
    """
    POST /api/detection/upload/
    Upload a CSV file for detection or training.
    Validates CSV headers against known schemas (normalized or raw dataset format).
    """
    ser = CSVUploadSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    uploaded = ser.validated_data["file"]

    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    dest_path = os.path.join(upload_dir, uploaded.name)
    counter = 1
    base, ext = os.path.splitext(uploaded.name)
    while os.path.exists(dest_path):
        dest_path = os.path.join(upload_dir, f"{base}_{counter}{ext}")
        counter += 1

    with open(dest_path, "wb") as f:
        for chunk in uploaded.chunks():
            f.write(chunk)

    row_count = 0
    headers = []
    try:
        with open(dest_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = [h.strip().lower() for h in next(reader, [])]
            for _ in reader:
                row_count += 1
    except Exception:
        pass

    header_set = set(headers)
    is_valid, schema_name, messages = _validate_csv_headers(header_set)

    return Response({
        "file_path": dest_path,
        "file_name": os.path.basename(dest_path),
        "row_count": row_count,
        "headers": headers,
        "headers_valid": is_valid,
        "schema_detected": schema_name or "unknown",
        "missing_headers": messages,
    }, status=status.HTTP_201_CREATED)