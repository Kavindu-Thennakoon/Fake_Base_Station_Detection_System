from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from detection.models import (
    DetectionRun, TrainingRun, CellModel, Anomaly,
    NeighborAnomalyDetail, SuspiciousNeighbor, CellLocation,
)


class DetectionRunModelTest(TestCase):
    def test_create_run(self):
        run = DetectionRun.objects.create(
            run_id="test_run_001", input_file="test.csv",
            total_rows_scanned=1000, total_anomalies=5,
        )
        self.assertEqual(str(run), "test_run_001 [pending] - 5 anomalies")

    def test_duration_seconds(self):
        now = timezone.now()
        run = DetectionRun.objects.create(
            run_id="test_dur", input_file="t.csv",
            started_at=now, completed_at=now + timezone.timedelta(seconds=120),
        )
        self.assertAlmostEqual(run.duration_seconds, 120.0, places=0)

    def test_ordering(self):
        DetectionRun.objects.create(run_id="older", input_file="a.csv")
        DetectionRun.objects.create(run_id="newer", input_file="b.csv")
        runs = list(DetectionRun.objects.values_list("run_id", flat=True))
        self.assertEqual(runs[0], "newer")


class CellModelTest(TestCase):
    def test_create_cell_model(self):
        cm = CellModel.objects.create(
            serving_cell_id="41301_12345", K=8,
            mean_codisp=5.0, std_codisp=2.0,
            training_rows=10000, neighbor_order=["n1", "n2"],
            neighbor_stats={"n1": {"rsrp_mean": -80}},
        )
        self.assertEqual(cm.K, 8)
        self.assertIn("n1", cm.neighbor_stats)

    def test_unique_serving_cell(self):
        CellModel.objects.create(serving_cell_id="unique1", K=5, mean_codisp=3, std_codisp=1)
        with self.assertRaises(Exception):
            CellModel.objects.create(serving_cell_id="unique1", K=6, mean_codisp=4, std_codisp=2)


class AnomalyModelTest(TestCase):
    def setUp(self):
        self.run = DetectionRun.objects.create(run_id="anom_run", input_file="t.csv")

    def test_detection_method_both(self):
        a = Anomaly.objects.create(
            run=self.run, serving_cell_id="c1", row_index=1,
            avg_codisp=10.0, threshold=5.0,
            rrcf_flagged=True, zscore_flagged=True,
        )
        self.assertEqual(a.detection_method, "both")

    def test_detection_method_rrcf_only(self):
        a = Anomaly.objects.create(
            run=self.run, serving_cell_id="c2", row_index=2,
            avg_codisp=10.0, threshold=5.0,
            rrcf_flagged=True, zscore_flagged=False,
        )
        self.assertEqual(a.detection_method, "rrcf_only")

    def test_detection_method_zscore_only(self):
        a = Anomaly.objects.create(
            run=self.run, serving_cell_id="c3", row_index=3,
            avg_codisp=4.0, threshold=5.0,
            rrcf_flagged=False, zscore_flagged=True,
        )
        self.assertEqual(a.detection_method, "zscore_only")


class CellLocationModelTest(TestCase):
    def test_create_location(self):
        loc = CellLocation.objects.create(
            global_cell_id="41301_99999",
            cell_name="Test Site", latitude=6.93, longitude=79.85,
        )
        self.assertIn("6.9300", str(loc))


class DetectionRunAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.run = DetectionRun.objects.create(
            run_id="api_run_001", input_file="test.csv",
            status="completed", total_anomalies=10, total_cells_scanned=5,
        )

    def test_list_runs(self):
        resp = self.client.get("/api/detection/runs/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_run(self):
        resp = self.client.get(f"/api/detection/runs/{self.run.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["run_id"], "api_run_001")

    def test_model_status_endpoint(self):
        resp = self.client.get("/api/detection/model-status/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("status", resp.data)


class CellModelAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.cm = CellModel.objects.create(
            serving_cell_id="41301_77777", K=6,
            mean_codisp=4.5, std_codisp=1.5,
            training_rows=5000,
            neighbor_order=["n1", "n2", "n3"],
            neighbor_stats={"n1": {"rsrp_mean": -85, "rsrp_std": 5}},
        )

    def test_list_cells(self):
        resp = self.client.get("/api/detection/cells/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_retrieve_cell(self):
        resp = self.client.get(f"/api/detection/cells/{self.cm.serving_cell_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["K"], 6)

    def test_profile_endpoint(self):
        resp = self.client.get(f"/api/detection/cells/{self.cm.serving_cell_id}/profile/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("health_status", resp.data)


class AnomalyAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.run = DetectionRun.objects.create(run_id="anom_api", input_file="t.csv", status="completed")
        self.anomaly = Anomaly.objects.create(
            run=self.run, serving_cell_id="c1", row_index=100,
            avg_codisp=12.5, threshold=8.0,
            rrcf_flagged=True, zscore_flagged=True,
        )
        NeighborAnomalyDetail.objects.create(
            anomaly=self.anomaly, serving_cell_id="c1",
            neighbor_id="n1", anomaly_score=5.5,
            rsrp=-80, rsrq=-8, rsrp_z=3.2, rsrq_z=2.8,
        )

    def test_list_anomalies(self):
        resp = self.client.get("/api/detection/anomalies/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_explain_anomaly(self):
        resp = self.client.get(f"/api/detection/anomalies/{self.anomaly.id}/explain/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("anomaly_id", resp.data)


class CSVUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_upload_csv(self):
        import io
        content = "serving_cell_id,datetime_raw,neighbor_id,rsrp,rsrq\n41301_1,2026-01-01,41301_2,-80,-8\n"
        f = io.BytesIO(content.encode())
        f.name = "test.csv"
        resp = self.client.post("/api/detection/upload/", {"file": f}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["headers_valid"])
        self.assertEqual(resp.data["row_count"], 1)

    def test_upload_non_csv_rejected(self):
        import io
        f = io.BytesIO(b"not a csv")
        f.name = "test.txt"
        resp = self.client.post("/api/detection/upload/", {"file": f}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
