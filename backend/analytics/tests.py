from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from detection.models import (
    DetectionRun, CellModel, Anomaly, SuspiciousNeighbor, CellLocation,
)
from alerts.models import Alert


class AnalyticsTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.run = DetectionRun.objects.create(
            run_id="analytics_run", input_file="t.csv", status="completed",
            total_anomalies=5, total_cells_scanned=3,
        )
        now = timezone.now()
        for i in range(5):
            Anomaly.objects.create(
                run=self.run, serving_cell_id=f"cell_{i % 3}",
                row_index=i, datetime_raw=now - timezone.timedelta(hours=i),
                avg_codisp=10.0 + i, threshold=8.0,
                rrcf_flagged=True, zscore_flagged=(i % 2 == 0),
            )
        SuspiciousNeighbor.objects.create(
            run=self.run, neighbor_id="susp_1",
            sum_score=50.0, occurrence_count=20,
            affected_serving_cells=["cell_0", "cell_1"],
        )
        Alert.objects.create(
            run=self.run, neighbor_id="susp_1", severity="high",
            title="Test alert", description="Desc",
            affected_cells_count=2, peak_anomaly_score=50.0,
        )
        CellModel.objects.create(
            serving_cell_id="cell_0", K=5,
            mean_codisp=4.0, std_codisp=1.5, training_rows=1000,
        )
        CellLocation.objects.create(
            global_cell_id="cell_0", cell_name="Test Site",
            latitude=6.93, longitude=79.85,
        )


class DashboardStatsTest(AnalyticsTestBase):
    def test_dashboard_stats(self):
        resp = self.client.get("/api/analytics/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_detection_runs"], 1)
        self.assertEqual(resp.data["total_anomalies"], 5)
        self.assertIsNotNone(resp.data["latest_run"])


class AnomalyTrendsTest(AnalyticsTestBase):
    def test_trends(self):
        resp = self.client.get("/api/analytics/trends/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)


class CellRiskTest(AnalyticsTestBase):
    def test_cell_risk_ranking(self):
        resp = self.client.get("/api/analytics/cell-risk/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) >= 1)
        self.assertEqual(resp.data[0]["neighbor_id"], "susp_1")


class MethodBreakdownTest(AnalyticsTestBase):
    def test_breakdown(self):
        resp = self.client.get("/api/analytics/method-breakdown/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("rrcf_only", resp.data)
        self.assertEqual(resp.data["total"], 5)


class GeographicTest(AnalyticsTestBase):
    def test_geographic_heatmap(self):
        resp = self.client.get("/api/analytics/geographic/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) >= 1)
        self.assertIn("latitude", resp.data[0])


class PowerBIAnomaliesTest(AnalyticsTestBase):
    def test_json(self):
        resp = self.client.get("/api/analytics/powerbi/anomalies/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_csv(self):
        resp = self.client.get("/api/analytics/powerbi/anomalies/?output=csv")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn("anomaly_id", resp.content.decode())


class PowerBIAlertsTest(AnalyticsTestBase):
    def test_json(self):
        resp = self.client.get("/api/analytics/powerbi/alerts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) >= 1)

    def test_csv(self):
        resp = self.client.get("/api/analytics/powerbi/alerts/?output=csv")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("severity", resp.content.decode())


class PowerBICellRiskTest(AnalyticsTestBase):
    def test_json(self):
        resp = self.client.get("/api/analytics/powerbi/cell-risk/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) >= 1)
        self.assertIn("risk_category", resp.data[0])


class PowerBIGeographicTest(AnalyticsTestBase):
    def test_json(self):
        resp = self.client.get("/api/analytics/powerbi/geographic/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_csv(self):
        resp = self.client.get("/api/analytics/powerbi/geographic/?output=csv")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("latitude", resp.content.decode())
