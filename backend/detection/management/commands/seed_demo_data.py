import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from detection.models import (
    DetectionRun,
    TrainingRun,
    CellModel,
    Anomaly,
    NeighborAnomalyDetail,
    SuspiciousNeighbor,
    DetectedWindow,
    AbnormalNeighbor,
)
from alerts.models import Alert, AlertHistory


SERVING_CELLS = [
    "41301_12845", "41301_12846", "41301_12847",
    "41301_33901", "41301_33902", "41301_44510",
    "41301_44511", "41301_55620", "41301_55621",
    "41301_66730", "41301_77801", "41301_77802",
]

LEGIT_NEIGHBORS = [
    "41301_12900", "41301_12901", "41301_12902",
    "41301_33950", "41301_33951", "41301_44560",
    "41301_44561", "41301_55670", "41301_55671",
    "41301_66780", "41301_66781", "41301_77850",
]

FBS_CELLS = ["99999_00001", "99999_00002", "88888_00003"]


class Command(BaseCommand):
    help = "Seed the database with realistic demo data for multiple runs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing data first"
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data ...")
            AlertHistory.objects.all().delete()
            Alert.objects.all().delete()
            AbnormalNeighbor.objects.all().delete()
            DetectedWindow.objects.all().delete()
            SuspiciousNeighbor.objects.all().delete()
            NeighborAnomalyDetail.objects.all().delete()
            Anomaly.objects.all().delete()
            DetectionRun.objects.all().delete()
            TrainingRun.objects.all().delete()

        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@fbs.local", "is_staff": True, "is_superuser": True},
        )
        if admin_user.check_password("admin"):
            pass
        else:
            admin_user.set_password("admin123")
            admin_user.save()
        profile = admin_user.profile
        profile.role = "admin"
        profile.organization = "Dialog Axiata PLC"
        profile.save()

        self._seed_cell_models()
        self._seed_training_run()

        now = timezone.now()
        run_offsets = [
            ("run_20260520_091500", timedelta(days=7), 35, True),
            ("run_20260522_143000", timedelta(days=5), 48, True),
            ("run_20260524_081200", timedelta(days=3), 22, False),
            ("run_20260526_100000", timedelta(days=1), 55, True),
        ]

        for run_id, offset, num_anomalies, has_fbs in run_offsets:
            base_time = now - offset
            run = self._create_detection_run(run_id, base_time, num_anomalies)
            self._create_anomalies(run, base_time, num_anomalies, has_fbs)
            self._create_suspicious_neighbors(run)
            if has_fbs:
                self._create_windows_and_abnormals(run)
            self._create_alerts(run)

        self._resolve_some_alerts(admin_user)

        total_anomalies = Anomaly.objects.count()
        total_alerts = Alert.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Seeded: 4 detection runs, {total_anomalies} anomalies, "
            f"{total_alerts} alerts, {CellModel.objects.count()} cell models"
        ))

    def _seed_cell_models(self):
        for cell_id in SERVING_CELLS:
            K = random.randint(5, 12)
            neighbors = random.sample(LEGIT_NEIGHBORS, min(K, len(LEGIT_NEIGHBORS)))
            neighbor_stats = {}
            for nbr in neighbors:
                neighbor_stats[nbr] = {
                    "rsrp_mean": round(random.uniform(-95, -70), 2),
                    "rsrp_std": round(random.uniform(3.0, 8.0), 2),
                    "rsrq_mean": round(random.uniform(-14, -6), 2),
                    "rsrq_std": round(random.uniform(1.5, 4.0), 2),
                }
            CellModel.objects.update_or_create(
                serving_cell_id=cell_id,
                defaults={
                    "K": K,
                    "mean_codisp": round(random.uniform(3.0, 8.0), 4),
                    "std_codisp": round(random.uniform(1.0, 3.0), 4),
                    "training_rows": random.randint(5000, 50000),
                    "neighbor_order": neighbors,
                    "neighbor_stats": neighbor_stats,
                    "num_trees": 150,
                    "tree_size": 1024,
                },
            )

    def _seed_training_run(self):
        TrainingRun.objects.update_or_create(
            run_id="train_20260515_120000",
            defaults={
                "status": "completed",
                "train_file": "train_70_filtered.csv",
                "model_dir": "v4_model",
                "num_trees": 150,
                "tree_size": 1024,
                "min_samples": 50,
                "total_cells_trained": len(SERVING_CELLS),
                "completed_at": timezone.now() - timedelta(days=12),
            },
        )

    def _create_detection_run(self, run_id, base_time, num_anomalies):
        run, _ = DetectionRun.objects.update_or_create(
            run_id=run_id,
            defaults={
                "status": "completed",
                "input_file": "detect_30_filtered.csv",
                "total_rows_scanned": random.randint(100000, 350000),
                "total_anomalies": num_anomalies,
                "total_cells_scanned": len(SERVING_CELLS),
                "threshold_mult": 1.0,
                "z_threshold": 2.0,
                "min_anomaly_score": 4.0,
                "started_at": base_time,
                "completed_at": base_time + timedelta(minutes=random.randint(8, 25)),
                "output_dir": "DEMO_SEED",
            },
        )
        return run

    def _create_anomalies(self, run, base_time, count, has_fbs):
        Anomaly.objects.filter(run=run).delete()
        NeighborAnomalyDetail.objects.filter(anomaly__run=run).delete()

        anomaly_objs = []
        for i in range(count):
            cell = random.choice(SERVING_CELLS)
            dt = base_time + timedelta(minutes=random.randint(0, 180))
            roll = random.random()
            if roll < 0.55:
                rrcf_flag, zscore_flag = True, True
            elif roll < 0.80:
                rrcf_flag, zscore_flag = True, False
            else:
                rrcf_flag, zscore_flag = False, True

            mean_c = random.uniform(3.0, 8.0)
            std_c = random.uniform(1.0, 3.0)
            threshold = mean_c + 1.0 * std_c
            avg_codisp = (
                threshold + random.uniform(0.5, 12.0)
                if rrcf_flag
                else threshold - random.uniform(0.1, 1.0)
            )
            anomaly_objs.append(Anomaly(
                run=run,
                serving_cell_id=cell,
                row_index=random.randint(1000, 500000),
                datetime_raw=dt,
                avg_codisp=round(avg_codisp, 4),
                threshold=round(threshold, 4),
                rrcf_flagged=rrcf_flag,
                zscore_flagged=zscore_flag,
            ))
        Anomaly.objects.bulk_create(anomaly_objs)

        detail_objs = []
        for anomaly in Anomaly.objects.filter(run=run):
            for _ in range(random.randint(1, 3)):
                nbr = random.choice(LEGIT_NEIGHBORS)
                rsrp_z = random.uniform(-1.5, 1.5)
                rsrq_z = random.uniform(-1.5, 1.5)
                detail_objs.append(NeighborAnomalyDetail(
                    anomaly=anomaly,
                    serving_cell_id=anomaly.serving_cell_id,
                    neighbor_id=nbr,
                    anomaly_score=round((rsrp_z**2 + rsrq_z**2)**0.5, 4),
                    rsrp=round(random.uniform(-95, -75), 1),
                    rsrq=round(random.uniform(-12, -6), 1),
                    rsrp_z=round(rsrp_z, 4),
                    rsrq_z=round(rsrq_z, 4),
                ))
            if has_fbs and anomaly.zscore_flagged:
                fbs = random.choice(FBS_CELLS)
                rsrp_z = random.uniform(4.0, 8.0)
                rsrq_z = random.uniform(3.5, 7.0)
                detail_objs.append(NeighborAnomalyDetail(
                    anomaly=anomaly,
                    serving_cell_id=anomaly.serving_cell_id,
                    neighbor_id=fbs,
                    anomaly_score=round((rsrp_z**2 + rsrq_z**2)**0.5, 4),
                    rsrp=round(random.uniform(-55, -44), 1),
                    rsrq=round(random.uniform(-5, -3), 1),
                    rsrp_z=round(rsrp_z, 4),
                    rsrq_z=round(rsrq_z, 4),
                ))
        NeighborAnomalyDetail.objects.bulk_create(detail_objs, batch_size=1000)

    def _create_suspicious_neighbors(self, run):
        SuspiciousNeighbor.objects.filter(run=run).delete()
        details = NeighborAnomalyDetail.objects.filter(anomaly__run=run)
        agg = {}
        for d in details:
            if d.neighbor_id not in agg:
                agg[d.neighbor_id] = {"score": 0, "count": 0, "cells": set()}
            agg[d.neighbor_id]["score"] += d.anomaly_score
            agg[d.neighbor_id]["count"] += 1
            agg[d.neighbor_id]["cells"].add(d.serving_cell_id)

        for nbr_id, data in agg.items():
            SuspiciousNeighbor.objects.create(
                run=run,
                neighbor_id=nbr_id,
                sum_score=round(data["score"], 4),
                occurrence_count=data["count"],
                affected_serving_cells=sorted(data["cells"]),
            )

    def _create_windows_and_abnormals(self, run):
        DetectedWindow.objects.filter(run=run).delete()
        AbnormalNeighbor.objects.filter(run=run).delete()

        for fbs in FBS_CELLS:
            fbs_details = NeighborAnomalyDetail.objects.filter(
                anomaly__run=run, neighbor_id=fbs
            ).select_related("anomaly")
            if fbs_details.count() < 3:
                continue
            times = sorted([
                d.anomaly.datetime_raw for d in fbs_details if d.anomaly.datetime_raw
            ])
            if not times:
                continue
            affected_cells = set(d.serving_cell_id for d in fbs_details)
            for cell in list(affected_cells)[:4]:
                DetectedWindow.objects.create(
                    run=run,
                    serving_cell_id=cell,
                    neighbor_id=fbs,
                    window_start=times[0],
                    window_end=times[-1],
                    event_count=fbs_details.filter(serving_cell_id=cell).count(),
                )
                AbnormalNeighbor.objects.create(
                    run=run,
                    serving_cell_id=cell,
                    neighbor_id=fbs,
                    event_count=fbs_details.filter(serving_cell_id=cell).count(),
                    window_count=1,
                )

    def _create_alerts(self, run):
        Alert.objects.filter(run=run).delete()
        for sn in SuspiciousNeighbor.objects.filter(run=run).order_by("-sum_score"):
            if sn.sum_score >= 50 or sn.occurrence_count >= 100:
                severity = "critical"
            elif sn.sum_score >= 20 or sn.occurrence_count >= 50:
                severity = "high"
            elif sn.sum_score >= 10 or sn.occurrence_count >= 20:
                severity = "medium"
            else:
                severity = "low"

            affected = len(sn.affected_serving_cells) if sn.affected_serving_cells else 0
            Alert.objects.create(
                run=run,
                neighbor_id=sn.neighbor_id,
                severity=severity,
                title=f"Suspicious neighbor cell {sn.neighbor_id} detected",
                description=(
                    f"Cell ID {sn.neighbor_id} flagged {sn.occurrence_count} time(s) "
                    f"with cumulative anomaly score {sn.sum_score:.2f}. "
                    f"Affected serving cells: {affected}."
                ),
                affected_cells_count=affected,
                peak_anomaly_score=sn.sum_score,
            )

    def _resolve_some_alerts(self, user):
        old_alerts = Alert.objects.filter(
            run__run_id__in=["run_20260520_091500", "run_20260522_143000"]
        )
        for i, alert in enumerate(old_alerts):
            if i % 3 == 0:
                alert.status = "resolved"
                alert.resolved_at = timezone.now() - timedelta(hours=random.randint(1, 48))
                alert.resolved_by = user
                alert.save()
                AlertHistory.objects.create(
                    alert=alert, changed_by=user,
                    old_status="new", new_status="acknowledged",
                    comment="Investigating anomaly pattern.",
                )
                AlertHistory.objects.create(
                    alert=alert, changed_by=user,
                    old_status="acknowledged", new_status="resolved",
                    comment="Confirmed as legitimate new cell tower deployment.",
                )
            elif i % 3 == 1:
                alert.status = "acknowledged"
                alert.save()
                AlertHistory.objects.create(
                    alert=alert, changed_by=user,
                    old_status="new", new_status="acknowledged",
                    comment="Under investigation.",
                )
