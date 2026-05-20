from django.urls import path, include
from rest_framework.routers import DefaultRouter
from alerts.views import AlertViewSet

router = DefaultRouter()
router.register(r"", AlertViewSet, basename="alerts")

urlpatterns = [
    path("", include(router.urls)),
]