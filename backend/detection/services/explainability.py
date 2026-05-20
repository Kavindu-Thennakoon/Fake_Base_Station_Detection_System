"""
Explainability Service - Provides human-readable explanations for
anomaly detections in the FBS Detection System.

Three levels of explanation:
    1. Per-Anomaly:  WHY was this specific MR row flagged?
    2. Per-Cell:     What is the trained baseline for this serving cell?
    3. Per-Neighbor: How suspicious is this neighbor across ALL runs?
"""

import logging
from django.db.models import Sum, Count

from detection.models import (
    Anomaly,
    NeighborAnomalyDetail,
    CellModel,
    SuspiciousNeighbor,
)

logger = logging.getLogger(__name__)


class ExplainabilityService:
    """Generate explainable insights for FBS anomaly detections."""

    def get_anomaly_explanation(self, anomaly_id):
        try:
            anomaly = Anomaly.objects.get(id=anomaly_id)
        except Anomaly.DoesNotExist:
            return {"error": "Anomaly {} not found".format(anomaly_id)}

        neighbor_details = NeighborAnomalyDetail.objects.filter(anomaly=anomaly)
        neighbor_breakdown = []

        for nd in neighbor_details:
            is_abnormal = nd.anomaly_score >= anomaly.run.min_anomaly_score
            rsrp_z_val = None
            if nd.rsrp_z is not None:
                rsrp_z_val = round(nd.rsrp_z, 4)
            rsrq_z_val = None
            if nd.rsrq_z is not None:
                rsrq_z_val = round(nd.rsrq_z, 4)
            neighbor_breakdown.append({
                "neighbor_id": nd.neighbor_id,
                "anomaly_score": round(nd.anomaly_score, 4),
                "rsrp": nd.rsrp,
                "rsrq": nd.rsrq,
                "rsrp_z": rsrp_z_val,
                "rsrq_z": rsrq_z_val,
                "is_abnormal": is_abnormal,
                "reason": self._neighbor_reason(nd, anomaly.run.min_anomaly_score),
            })

        rrcf_over = anomaly.avg_codisp - anomaly.threshold

        if anomaly.rrcf_flagged:
            rrcf_text = "RRCF score ({:.3f}) exceeds threshold ({:.3f}) -- unusual neighbor COMBINATION detected.".format(anomaly.avg_codisp, anomaly.threshold)
        else:
            rrcf_text = "RRCF score ({:.3f}) is below threshold ({:.3f}) -- neighbor combination is normal.".format(anomaly.avg_codisp, anomaly.threshold)

        over_val = 0
        if rrcf_over > 0:
            over_val = round(rrcf_over, 4)

        rrcf_explanation = {
            "avg_codisp": round(anomaly.avg_codisp, 4),
            "threshold": round(anomaly.threshold, 4),
            "over_threshold_by": over_val,
            "is_flagged": anomaly.rrcf_flagged,
            "interpretation": rrcf_text,
        }

        detection_methods = []
        if anomaly.rrcf_flagged:
            detection_methods.append({
                "layer": "Layer 1 -- RRCF",
                "description": "Detects unusual neighbor COMBINATIONS. An unknown or rare cell ID appeared in this MR neighbor list.",
            })
        if anomaly.zscore_flagged:
            detection_methods.append({
                "layer": "Layer 2 -- Z-Score",
                "description": "Detects abnormal signal VALUES for known neighbors. RSRP/RSRQ measurements deviate significantly from training baseline.",
            })

        risk_level = self._assess_risk(anomaly, neighbor_breakdown)

        dt_str = None
        if anomaly.datetime_raw:
            dt_str = anomaly.datetime_raw.isoformat()

        return {
            "anomaly_id": anomaly.id,
            "serving_cell_id": anomaly.serving_cell_id,
            "row_index": anomaly.row_index,
            "datetime_raw": dt_str,
            "detection_methods": detection_methods,
            "rrcf_explanation": rrcf_explanation,
            "zscore_flagged": anomaly.zscore_flagged,
            "neighbor_breakdown": sorted(neighbor_breakdown, key=lambda x: x["anomaly_score"], reverse=True),
            "risk_assessment": risk_level,
        }

    def get_cell_profile(self, serving_cell_id):
        try:
            cell = CellModel.objects.get(serving_cell_id=str(serving_cell_id))
        except CellModel.DoesNotExist:
            return {"error": "No trained model for cell {}".format(serving_cell_id)}

        total_anomalies = Anomaly.objects.filter(serving_cell_id=str(serving_cell_id)).count()

        last_trained_str = None
        if cell.last_trained:
            last_trained_str = cell.last_trained.isoformat()

        return {
            "serving_cell_id": cell.serving_cell_id,
            "K": cell.K,
            "neighbor_count": cell.K,
            "mean_codisp": round(cell.mean_codisp, 4),
            "std_codisp": round(cell.std_codisp, 4),
            "threshold_at_1x": round(cell.mean_codisp + cell.std_codisp, 4),
            "threshold_at_2x": round(cell.mean_codisp + 2 * cell.std_codisp, 4),
            "training_rows": cell.training_rows,
            "neighbor_order": cell.neighbor_order,
            "num_trees": cell.num_trees,
            "tree_size": cell.tree_size,
            "last_trained": last_trained_str,
            "total_anomalies_detected": total_anomalies,
            "health_status": self._cell_health(total_anomalies),
        }

    def get_neighbor_risk_profile(self, neighbor_id):
        records = SuspiciousNeighbor.objects.filter(neighbor_id=str(neighbor_id))

        if not records.exists():
            return {"error": "No records for neighbor {}".format(neighbor_id)}

        agg = records.aggregate(
            total_score=Sum("sum_score"),
            total_occurrences=Sum("occurrence_count"),
            runs_appeared=Count("run", distinct=True),
        )

        all_cells = set()
        for rec in records:
            if rec.affected_serving_cells:
                all_cells.update(rec.affected_serving_cells)

        trend = []
        for rec in records.order_by("run__started_at"):
            trend.append({
                "run_id": rec.run.run_id,
                "date": rec.run.started_at.isoformat(),
                "score": round(rec.sum_score, 4),
                "occurrences": rec.occurrence_count,
            })

        total_score = agg["total_score"] or 0

        return {
            "neighbor_id": str(neighbor_id),
            "total_score": round(total_score, 4),
            "total_occurrences": agg["total_occurrences"] or 0,
            "runs_appeared": agg["runs_appeared"] or 0,
            "affected_serving_cells": sorted(all_cells),
            "affected_cells_count": len(all_cells),
            "trend": trend,
            "risk_level": self._neighbor_risk_level(total_score, len(all_cells)),
        }

    def _neighbor_reason(self, nd, min_score):
        reasons = []
        if nd.rsrp_z is not None and abs(nd.rsrp_z) > 2.0:
            reasons.append("RSRP={} dBm is {:.1f} std devs from training mean".format(nd.rsrp, abs(nd.rsrp_z)))
        if nd.rsrq_z is not None and abs(nd.rsrq_z) > 2.0:
            reasons.append("RSRQ={} dB is {:.1f} std devs from training mean".format(nd.rsrq, abs(nd.rsrq_z)))
        if nd.anomaly_score >= min_score:
            reasons.append("Combined score {:.2f} exceeds threshold {}".format(nd.anomaly_score, min_score))
        if reasons:
            return "; ".join(reasons)
        return "Within normal range"

    def _assess_risk(self, anomaly, neighbor_breakdown):
        abnormal_count = sum(1 for n in neighbor_breakdown if n["is_abnormal"])
        max_score = max((n["anomaly_score"] for n in neighbor_breakdown), default=0)

        if anomaly.rrcf_flagged and anomaly.zscore_flagged and abnormal_count >= 2:
            level = "critical"
            summary = "Both RRCF and Z-Score layers triggered with multiple abnormal neighbors. High confidence of FBS activity."
        elif anomaly.rrcf_flagged and anomaly.zscore_flagged:
            level = "high"
            summary = "Both detection layers triggered. Likely suspicious activity."
        elif abnormal_count >= 2:
            level = "high"
            summary = "{} neighbors show abnormal signal patterns.".format(abnormal_count)
        elif anomaly.rrcf_flagged or anomaly.zscore_flagged:
            level = "medium"
            summary = "Single detection layer triggered. May warrant investigation."
        else:
            level = "low"
            summary = "Low anomaly indicators. Likely benign."

        return {
            "level": level,
            "abnormal_neighbors": abnormal_count,
            "max_neighbor_score": round(max_score, 4),
            "summary": summary,
        }

    @staticmethod
    def _cell_health(total_anomalies):
        if total_anomalies == 0:
            return "healthy"
        elif total_anomalies < 10:
            return "warning"
        else:
            return "critical"

    @staticmethod
    def _neighbor_risk_level(total_score, affected_cells_count):
        if total_score >= 100 or affected_cells_count >= 5:
            return "critical"
        elif total_score >= 30:
            return "high"
        elif total_score >= 10:
            return "medium"
        else:
            return "low"
