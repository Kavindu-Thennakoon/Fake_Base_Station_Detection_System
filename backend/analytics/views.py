"""
Analytics API - Aggregated data endpoints for React dashboard and PowerBI.
Supports Research Proposal Objective 4: interactive forensic dashboards.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate

from detection.models import (
    DetectionRun,
    Anomaly,
    CellModel,
    SuspiciousNeighbor,
)
from alerts.models import Alert


@api_view(["GET"])
def dashboard_stats(request):
    """GET /api/analytics/dashboard/ — overview stats for main dashboard."""
    active_alerts = Alert.objects.filter(
        status__in=["new", "acknowledged", "investigating"]
    ).count()

    latest_run = DetectionRun.objects.filter(status="completed").first()

    return Response({
        "total_detection_runs": DetectionRun.objects.count(),
        "completed_runs": DetectionRun.objects.filter(
            status="completed"
        ).count(),
        "total_anomalies": Anomaly.objects.count(),
        "active_alerts": active_alerts,
        "total_cells_trained": CellModel.objects.count(),
        "latest_run": {
            "run_id": latest_run.run_id,
            "status": latest_run.status,
            "total_anomalies": latest_run.total_anomalies,
            "started_at": latest_run.started_at.isoformat(),
            "completed_at": (
                latest_run.completed_at.isoformat()
                if latest_run.completed_at
                else None
            ),
        } if latest_run else None,
    })


@api_view(["GET"])
def anomaly_trends(request):
    """GET /api/analytics/trends/ — time-series anomaly data by date."""
    trends = (
        Anomaly.objects
        .filter(datetime_raw__isnull=False)
        .annotate(date=TruncDate("datetime_raw"))
        .values("date")
        .annotate(
            total=Count("id"),
            rrcf_count=Count("id", filter=Q(rrcf_flagged=True)),
            zscore_count=Count("id", filter=Q(zscore_flagged=True)),
            both_count=Count(
                "id",
                filter=Q(rrcf_flagged=True, zscore_flagged=True),
            ),
            avg_codisp=Avg("avg_codisp"),
        )
        .order_by("date")
    )

    return Response(list(trends))


@api_view(["GET"])
def cell_risk_ranking(request):
    """GET /api/analytics/cell-risk/?top=20 — top N suspicious neighbors."""
    top_n = int(request.query_params.get("top", 20))

    ranking = (
        SuspiciousNeighbor.objects
        .values("neighbor_id")
        .annotate(
            total_score=Sum("sum_score"),
            total_occurrences=Sum("occurrence_count"),
            runs_appeared=Count("run", distinct=True),
        )
        .order_by("-total_score")[:top_n]
    )

    return Response(list(ranking))


@api_view(["GET"])
def detection_method_breakdown(request):
    """
    GET /api/analytics/method-breakdown/?run_id=...
    Pie chart data: anomalies by detection method.
    """
    qs = Anomaly.objects.all()

    run_id = request.query_params.get("run_id")
    if run_id:
        qs = qs.filter(run__run_id=run_id)

    rrcf_only = qs.filter(
        rrcf_flagged=True, zscore_flagged=False
    ).count()
    zscore_only = qs.filter(
        rrcf_flagged=False, zscore_flagged=True
    ).count()
    both = qs.filter(
        rrcf_flagged=True, zscore_flagged=True
    ).count()

    return Response({
        "rrcf_only": rrcf_only,
        "zscore_only": zscore_only,
        "both_layers": both,
        "total": rrcf_only + zscore_only + both,
    })


@api_view(["GET"])
def recent_activity(request):
    """GET /api/analytics/recent-activity/ — last 10 detection runs."""
    runs = DetectionRun.objects.all()[:10]

    data = []
    for run in runs:
        data.append({
            "run_id": run.run_id,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "completed_at": (
                run.completed_at.isoformat()
                if run.completed_at
                else None
            ),
            "total_anomalies": run.total_anomalies,
            "alerts_generated": run.alerts.count(),
            "duration_seconds": run.duration_seconds,
        })

    return Response(data)