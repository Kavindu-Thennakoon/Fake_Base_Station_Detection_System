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
    CellLocation,
    SuspiciousNeighbor,
    NeighborAnomalyDetail,
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


@api_view(["GET"])
def geographic_heatmap(request):
    """
    GET /api/analytics/geographic/
    Returns cell locations with anomaly counts and risk levels for map visualization.
    Optional ?run_id= to filter by specific detection run.
    """
    run_id = request.query_params.get("run_id")

    locations = CellLocation.objects.all()
    if not locations.exists():
        return Response([])

    anomaly_qs = Anomaly.objects.all()
    suspicious_qs = SuspiciousNeighbor.objects.all()
    if run_id:
        anomaly_qs = anomaly_qs.filter(run__run_id=run_id)
        suspicious_qs = suspicious_qs.filter(run__run_id=run_id)

    serving_anomaly_counts = dict(
        anomaly_qs
        .values_list("serving_cell_id")
        .annotate(count=Count("id"))
        .values_list("serving_cell_id", "count")
    )

    neighbor_scores = dict(
        suspicious_qs
        .values("neighbor_id")
        .annotate(total_score=Sum("sum_score"), total_occ=Sum("occurrence_count"))
        .values_list("neighbor_id", "total_score")
    )

    result = []
    for loc in locations:
        cid = loc.global_cell_id
        anomaly_count = serving_anomaly_counts.get(cid, 0)
        suspicion_score = neighbor_scores.get(cid, 0) or 0

        if suspicion_score >= 50 or anomaly_count >= 30:
            risk = "critical"
        elif suspicion_score >= 20 or anomaly_count >= 15:
            risk = "high"
        elif suspicion_score >= 5 or anomaly_count >= 5:
            risk = "medium"
        elif anomaly_count > 0 or suspicion_score > 0:
            risk = "low"
        else:
            risk = "normal"

        result.append({
            "cell_id": cid,
            "cell_name": loc.cell_name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "technology": loc.technology,
            "band": loc.band,
            "anomaly_count": anomaly_count,
            "suspicion_score": round(suspicion_score, 2),
            "risk_level": risk,
        })

    return Response(result)


@api_view(["GET"])
def cell_anomaly_map(request):
    """
    GET /api/analytics/cell-anomaly-map/?run_id=...
    Returns individual anomaly events with locations for detailed map markers.
    """
    run_id = request.query_params.get("run_id")
    if not run_id:
        latest = DetectionRun.objects.filter(status="completed").first()
        if not latest:
            return Response([])
        run_id = latest.run_id

    anomalies = (
        Anomaly.objects
        .filter(run__run_id=run_id)
        .select_related("run")[:200]
    )

    loc_map = {
        loc.global_cell_id: loc
        for loc in CellLocation.objects.all()
    }

    result = []
    for a in anomalies:
        loc = loc_map.get(a.serving_cell_id)
        if not loc:
            continue
        result.append({
            "anomaly_id": a.id,
            "serving_cell_id": a.serving_cell_id,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "datetime": a.datetime_raw.isoformat() if a.datetime_raw else None,
            "avg_codisp": round(a.avg_codisp, 4),
            "threshold": round(a.threshold, 4),
            "rrcf_flagged": a.rrcf_flagged,
            "zscore_flagged": a.zscore_flagged,
            "detection_method": a.detection_method,
        })

    return Response(result)