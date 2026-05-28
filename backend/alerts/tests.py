from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from detection.models import DetectionRun, Anomaly, SuspiciousNeighbor
from alerts.models import Alert, AlertHistory


class AlertModelTest(TestCase):
    def setUp(self):
        self.run = DetectionRun.objects.create(run_id="alert_run", input_file="t.csv")

    def test_create_alert(self):
        alert = Alert.objects.create(
            run=self.run, neighbor_id="n1", severity="high",
            title="Test alert", description="Desc",
            affected_cells_count=3, peak_anomaly_score=25.5,
        )
        self.assertEqual(alert.status, "new")
        self.assertEqual(alert.severity, "high")

    def test_alert_str(self):
        alert = Alert.objects.create(
            run=self.run, neighbor_id="n2", severity="critical",
            title="Critical", description="Desc",
        )
        self.assertIn("critical", str(alert).lower())


class AlertAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("alertuser", password="pass1234")
        resp = self.client.post("/api/accounts/login/", {
            "username": "alertuser", "password": "pass1234",
        })
        self.token = resp.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

        self.run = DetectionRun.objects.create(run_id="api_alert_run", input_file="t.csv")
        self.alert = Alert.objects.create(
            run=self.run, neighbor_id="suspicious_1", severity="high",
            title="Test alert", description="Suspicious cell detected",
            affected_cells_count=5, peak_anomaly_score=30.0,
        )

    def test_list_alerts(self):
        resp = self.client.get("/api/alerts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_alert(self):
        resp = self.client.get(f"/api/alerts/{self.alert.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["severity"], "high")

    def test_acknowledge_alert(self):
        resp = self.client.post(f"/api/alerts/{self.alert.id}/acknowledge/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "acknowledged")
        self.assertEqual(AlertHistory.objects.filter(alert=self.alert).count(), 1)

    def test_resolve_alert(self):
        self.alert.status = "acknowledged"
        self.alert.save()
        resp = self.client.post(f"/api/alerts/{self.alert.id}/resolve/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "resolved")
        self.assertIsNotNone(self.alert.resolved_at)

    def test_false_positive(self):
        resp = self.client.post(f"/api/alerts/{self.alert.id}/false-positive/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "false_positive")

    def test_filter_by_status(self):
        resp = self.client.get("/api/alerts/?status=new")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data.get("results", resp.data)
        for a in data:
            self.assertEqual(a["status"], "new")

    def test_audit_trail_created(self):
        self.client.post(f"/api/alerts/{self.alert.id}/acknowledge/")
        self.client.post(f"/api/alerts/{self.alert.id}/resolve/")
        history = AlertHistory.objects.filter(alert=self.alert).order_by("created_at")
        self.assertEqual(history.count(), 2)
        self.assertEqual(history[0].new_status, "acknowledged")
        self.assertEqual(history[1].new_status, "resolved")

    def test_alert_includes_history(self):
        self.client.post(f"/api/alerts/{self.alert.id}/acknowledge/")
        resp = self.client.get(f"/api/alerts/{self.alert.id}/")
        self.assertIn("history", resp.data)
        self.assertTrue(len(resp.data["history"]) >= 1)
