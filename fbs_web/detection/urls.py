from django.urls import path

from .views import (
    run_detection_api,
    get_run_summary,
    get_run_anomalies,
    get_run_neighbor_details,
    get_run_neighbor_ranked
)


urlpatterns = [
    
path("run-detection/", run_detection_api),
    path("runs/<int:run_id>/", get_run_summary),
    path("runs/<int:run_id>/anomalies/", get_run_anomalies),
    path("runs/<int:run_id>/neighbor-details/", get_run_neighbor_details),
    path("runs/<int:run_id>/neighbor-ranked/", get_run_neighbor_ranked),

]