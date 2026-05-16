from django.shortcuts import render
from django.shortcuts import get_object_or_404

import os
import pandas as pd
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import DetectionRun
from fbs_service.detection_service import run_detection


@api_view(["POST"])
def run_detection_api(request):
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"status": "error", "message": "No file uploaded"}, status=400)

    # 1) Save upload
    upload_path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)
    full_upload_path = os.path.join(settings.MEDIA_ROOT, upload_path)

    # 2) Run detection (use settings paths)
    result = run_detection(
        model_dir=str(settings.FBS_MODEL_DIR),
        input_file=str(full_upload_path),
        cell_details_file=str(settings.FBS_CELL_DETAILS),
        n_jobs=4
    )

    # 3) Persist run
    run = DetectionRun.objects.create(
        input_filename=uploaded_file.name,
        output_dir=result.get("output_dir", ""),
        total_anomalies=result.get("total_anomalies", 0) if result.get("status") == "success" else 0,
        status=result.get("status", "error"),
        error_message=result.get("message", "")
    )

    # 4) Return lightweight JSON (don’t dump huge arrays to UI)
    return Response({
        "status": result.get("status"),
        "run_id": run.id,
        "total_anomalies": result.get("total_anomalies", 0),
    })
    

def _load_csv_as_records(path):
    if not path or not os.path.exists(path):
        return []
    try:
        df = pd.read_csv(path)
        if df.empty:
            return []
        return df.to_dict(orient="records")
    except:
        return []

@api_view(["GET"])
def get_run_summary(request, run_id):
    run = get_object_or_404(DetectionRun, id=run_id)
    return Response({
        "run_id": run.id,
        "created_at": run.created_at,
        "input_filename": run.input_filename,
        "status": run.status,
        "total_anomalies": run.total_anomalies,
    })

@api_view(["GET"])
def get_run_anomalies(request, run_id):
    run = get_object_or_404(DetectionRun, id=run_id)
    anomalies_path = os.path.join(run.output_dir, "anomalies.csv")
    return Response({"run_id": run.id, "anomalies": _load_csv_as_records(anomalies_path)})

@api_view(["GET"])
def get_run_neighbor_details(request, run_id):
    run = get_object_or_404(DetectionRun, id=run_id)
    details_path = os.path.join(run.output_dir, "neighbor_anomaly_details.csv")
    return Response({"run_id": run.id, "neighbor_details": _load_csv_as_records(details_path)})

@api_view(["GET"])
def get_run_neighbor_ranked(request, run_id):
    run = get_object_or_404(DetectionRun, id=run_id)
    ranked_path = os.path.join(run.output_dir, "neighbor_ranked.csv")
    return Response({"run_id": run.id, "ranked_neighbors": _load_csv_as_records(ranked_path)})


@api_view(["GET"])
def get_all_runs(request):
    runs = DetectionRun.objects.all().order_by('-created_at')
    data = [{
        "id": r.id,
        "input_filename": r.input_filename,
        "total_anomalies": r.total_anomalies,
        "status": r.status,
        "created_at": r.created_at.isoformat(),
    } for r in runs]
    return Response({"runs": data})