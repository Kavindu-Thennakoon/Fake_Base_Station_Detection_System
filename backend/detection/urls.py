from django.urls import path, include
from rest_framework.routers import DefaultRouter

from detection.views import (
    DetectionRunViewSet,
    TrainingRunViewSet,
    CellModelViewSet,
    AnomalyViewSet,
    model_status,
    neighbor_risk_profile,
)

router = DefaultRouter()
router.register(r"runs", DetectionRunViewSet, basename="detection-runs")
router.register(r"training", TrainingRunViewSet, basename="training-runs")
router.register(r"cells", CellModelViewSet, basename="cell-models")
router.register(r"anomalies", AnomalyViewSet, basename="anomalies")

urlpatterns = [
    path("", include(router.urls)),
    path("model-status/", model_status, name="model-status"),
    path(
        "neighbors/<str:neighbor_id>/risk-profile/",
        neighbor_risk_profile,
        name="neighbor-risk-profile",
    ),
]