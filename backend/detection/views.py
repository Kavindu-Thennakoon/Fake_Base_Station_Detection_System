from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from detection.models import (
    DetectionRun,
    TrainingRun,
    CellModel,
    Anomaly,
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
)
from detection.services.ml_bridge import MLBridge
from detection.services.explainability import ExplainabilityService


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