import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { ArrowLeft, Brain, AlertTriangle, Shield, Activity } from "lucide-react";
import SeverityBadge from "../components/SeverityBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { getAnomalyExplanation } from "../services/api";

export default function AnomalyExplain() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await getAnomalyExplanation(id);
        setData(res.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <LoadingSpinner text="Generating explanation..." />;
  if (!data || data.error) return <p className="text-[var(--text-secondary)]">{data?.error || "Not found"}</p>;

  const neighborChart = (data.neighbor_breakdown || []).map((n) => ({
    name: n.neighbor_id,
    score: n.anomaly_score,
    abnormal: n.is_abnormal,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/anomalies" className="text-[var(--text-secondary)] hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Brain size={24} className="text-[var(--accent-purple)]" />
            Anomaly Explanation #{data.anomaly_id}
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Cell: <span className="font-mono text-white">{data.serving_cell_id}</span> | Row: {data.row_index}
          </p>
        </div>
      </div>

      {/* Risk Assessment Banner */}
      <div className={`rounded-xl p-5 border ${
        data.risk_assessment?.level === "critical" ? "bg-red-500/10 border-red-500/30" :
        data.risk_assessment?.level === "high" ? "bg-orange-500/10 border-orange-500/30" :
        data.risk_assessment?.level === "medium" ? "bg-yellow-500/10 border-yellow-500/30" :
        "bg-green-500/10 border-green-500/30"
      }`}>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <AlertTriangle size={18} />
            Risk Assessment
          </h2>
          <SeverityBadge severity={data.risk_assessment?.level} />
        </div>
        <p className="text-sm text-[var(--text-secondary)]">{data.risk_assessment?.summary}</p>
        <div className="flex gap-6 mt-3 text-xs text-[var(--text-secondary)]">
          <span>Abnormal Neighbors: <span className="text-white font-semibold">{data.risk_assessment?.abnormal_neighbors}</span></span>
          <span>Max Score: <span className="text-[var(--accent-red)] font-semibold">{data.risk_assessment?.max_neighbor_score?.toFixed(4)}</span></span>
        </div>
      </div>

      {/* Detection Methods */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.detection_methods?.map((m, i) => (
          <div key={i} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <Shield size={16} className="text-[var(--accent-blue)]" />
              {m.layer}
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">{m.description}</p>
          </div>
        ))}
      </div>

      {/* RRCF Explanation */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
          <Activity size={18} className="text-[var(--accent-blue)]" />
          RRCF Score Analysis
        </h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-[var(--bg-primary)] rounded-lg p-3">
            <p className="text-xs text-[var(--text-secondary)]">Avg CoDisp</p>
            <p className="text-xl font-bold text-[var(--accent-red)]">{data.rrcf_explanation?.avg_codisp?.toFixed(4)}</p>
          </div>
          <div className="bg-[var(--bg-primary)] rounded-lg p-3">
            <p className="text-xs text-[var(--text-secondary)]">Threshold</p>
            <p className="text-xl font-bold text-[var(--accent-yellow)]">{data.rrcf_explanation?.threshold?.toFixed(4)}</p>
          </div>
          <div className="bg-[var(--bg-primary)] rounded-lg p-3">
            <p className="text-xs text-[var(--text-secondary)]">Over By</p>
            <p className="text-xl font-bold text-white">{data.rrcf_explanation?.over_threshold_by?.toFixed(4)}</p>
          </div>
        </div>
        <p className="text-sm text-[var(--text-secondary)] italic">{data.rrcf_explanation?.interpretation}</p>
      </div>

      {/* Neighbor Breakdown Chart */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-4">Neighbor Anomaly Scores</h2>
        {neighborChart.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={neighborChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={60} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
              <ReferenceLine y={4.0} stroke="#eab308" strokeDasharray="5 5" label={{ value: "Threshold", fill: "#eab308", fontSize: 11 }} />
              <Bar dataKey="score" name="Anomaly Score" radius={[4, 4, 0, 0]}>
                {neighborChart.map((entry, i) => (
                  <Cell key={i} fill={entry.abnormal ? "#ef4444" : "#3b82f6"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-[var(--text-secondary)] text-sm text-center py-10">No neighbor data.</p>
        )}
      </div>

      {/* Neighbor Details Table */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-color)]">
          <h2 className="text-base font-semibold text-white">Neighbor Details</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Neighbor ID</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Score</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRP (dBm)</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRQ (dB)</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRP Z</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRQ Z</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Status</th>
            </tr>
          </thead>
          <tbody>
            {(data.neighbor_breakdown || []).map((n, i) => (
              <tr key={i} className={`border-b border-[var(--border-color)] ${n.is_abnormal ? "bg-red-500/5" : ""}`}>
                <td className="px-5 py-3 text-sm font-mono text-white">{n.neighbor_id}</td>
                <td className="px-5 py-3 text-sm font-semibold" style={{ color: n.is_abnormal ? "#ef4444" : "#3b82f6" }}>{n.anomaly_score?.toFixed(4)}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{n.rsrp?.toFixed(1) ?? "—"}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{n.rsrq?.toFixed(1) ?? "—"}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{n.rsrp_z?.toFixed(2) ?? "—"}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{n.rsrq_z?.toFixed(2) ?? "—"}</td>
                <td className="px-5 py-3">
                  {n.is_abnormal ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 font-semibold">ABNORMAL</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">Normal</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {/* Reason strings */}
        {(data.neighbor_breakdown || []).filter(n => n.is_abnormal).length > 0 && (
          <div className="px-5 py-4 border-t border-[var(--border-color)]">
            <h3 className="text-sm font-semibold text-white mb-2">Abnormal Neighbor Reasons</h3>
            {data.neighbor_breakdown.filter(n => n.is_abnormal).map((n, i) => (
              <p key={i} className="text-xs text-[var(--text-secondary)] mb-1">
                <span className="font-mono text-[var(--accent-red)]">{n.neighbor_id}</span>: {n.reason}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}