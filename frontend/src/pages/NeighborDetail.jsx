import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, ScatterChart, Scatter, ZAxis,
} from "recharts";
import {
  ArrowLeft, Radio, AlertTriangle, Shield, Activity, Brain,
  ChevronDown, ChevronUp, ExternalLink, TrendingUp, Eye,
} from "lucide-react";
import SeverityBadge from "../components/SeverityBadge";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { getNeighborDetail, getAnomalyExplanation, getDetectionRuns } from "../services/api";

export default function NeighborDetail() {
  const { neighborId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState("");
  const [expandedRow, setExpandedRow] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [mrPage, setMrPage] = useState(1);
  const MR_PAGE_SIZE = 20;

  useEffect(() => {
    getDetectionRuns()
      .then(({ data: d }) => setRuns(Array.isArray(d) ? d : d.results || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const params = {};
        if (selectedRun) params.run_id = selectedRun;
        const res = await getNeighborDetail(neighborId, params);
        setData(res.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [neighborId, selectedRun]);

  const toggleExpand = async (anomalyId) => {
    if (expandedRow === anomalyId) {
      setExpandedRow(null);
      setExplanation(null);
      return;
    }
    setExpandedRow(anomalyId);
    setExplainLoading(true);
    try {
      const { data: d } = await getAnomalyExplanation(anomalyId);
      setExplanation(d);
    } catch {
      setExplanation(null);
    } finally {
      setExplainLoading(false);
    }
  };

  if (loading) return <LoadingSpinner text="Loading neighbor analysis..." />;
  if (!data || data.error) return <p className="text-[var(--text-secondary)]">{data?.error || "Not found"}</p>;

  const severityColors = {
    critical: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400" },
    high: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400" },
    medium: { bg: "bg-yellow-500/10", border: "border-yellow-500/30", text: "text-yellow-400" },
    low: { bg: "bg-green-500/10", border: "border-green-500/30", text: "text-green-400" },
  };
  const sc = severityColors[data.severity] || severityColors.low;

  const signalChartData = (data.affected_cells || []).map((c) => ({
    cell: c.serving_cell_id,
    observed_rsrp: c.avg_rsrp,
    baseline_rsrp: c.baseline_stats?.rsrp_mean ?? null,
    observed_rsrq: c.avg_rsrq,
    baseline_rsrq: c.baseline_stats?.rsrq_mean ?? null,
    in_baseline: c.in_baseline,
  }));

  const zScoreData = (data.mr_records || [])
    .filter((r) => r.rsrp_z !== null)
    .map((r, i) => ({
      index: i,
      rsrp_z: r.rsrp_z,
      rsrq_z: r.rsrq_z ?? 0,
      score: r.anomaly_score,
    }));

  const mrRecords = data.mr_records || [];
  const totalMrPages = Math.ceil(mrRecords.length / MR_PAGE_SIZE);
  const pagedRecords = mrRecords.slice((mrPage - 1) * MR_PAGE_SIZE, mrPage * MR_PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/anomalies" className="text-[var(--text-secondary)] hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Radio size={24} className="text-[var(--accent-red)]" />
              Neighbor Cell
            </h1>
            <span className="text-2xl font-mono font-bold text-white">{data.neighbor_id}</span>
            <SeverityBadge severity={data.severity} />
          </div>
          <div className="flex items-center gap-4 mt-1 text-sm text-[var(--text-secondary)]">
            <span>{data.in_any_baseline ? "Known in training baseline" : "Unknown — not in any training baseline"}</span>
            {data.alert && (
              <span className="flex items-center gap-1">
                <AlertTriangle size={14} className="text-[var(--accent-yellow)]" />
                Alert: <StatusBadge status={data.alert.status} />
              </span>
            )}
          </div>
        </div>
        <select
          value={selectedRun}
          onChange={(e) => { setSelectedRun(e.target.value); setMrPage(1); }}
          className="px-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white text-sm focus:outline-none"
        >
          <option value="">All Runs</option>
          {runs.map((r) => (
            <option key={r.run_id} value={r.run_id}>{r.run_id}</option>
          ))}
        </select>
      </div>

      {/* Risk Banner */}
      <div className={`rounded-xl p-5 border ${sc.bg} ${sc.border}`}>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <AlertTriangle size={18} />
            Threat Assessment
          </h2>
          <SeverityBadge severity={data.severity} />
        </div>
        <p className="text-sm text-[var(--text-secondary)]">
          {data.severity === "critical"
            ? "This neighbor cell shows strong indicators of Fake Base Station activity. Multiple serving cells report anomalous signal patterns."
            : data.severity === "high"
            ? "This neighbor cell has significant anomaly indicators. Investigation recommended."
            : data.severity === "medium"
            ? "This neighbor cell has moderate anomaly indicators. May warrant monitoring."
            : "Low anomaly indicators. Likely benign behavior."}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <SummaryCard label="Total Anomaly Score" value={data.total_score >= 1000 ? `${(data.total_score / 1000).toFixed(1)}K` : data.total_score.toFixed(2)} color="var(--accent-red)" />
        <SummaryCard label="Times Detected" value={data.occurrence_count} color="var(--accent-orange)" />
        <SummaryCard label="Affected Cells" value={data.affected_cells_count} color="var(--accent-blue)" />
        <SummaryCard label="Detection Runs" value={data.runs_count} color="var(--accent-purple)" />
        <SummaryCard
          label="Avg RSRP"
          value={data.signal_summary?.rsrp_avg != null ? `${data.signal_summary.rsrp_avg} dBm` : "—"}
          color="var(--accent-cyan)"
        />
      </div>

      {/* Signal Analysis Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RSRP Comparison */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Activity size={18} className="text-[var(--accent-blue)]" />
            RSRP: Observed vs Baseline (per Serving Cell)
          </h2>
          {signalChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={signalChartData} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="cell" stroke="#64748b" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={60} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }}
                  formatter={(v, name) => [`${v?.toFixed(1)} dBm`, name]}
                />
                <Bar dataKey="observed_rsrp" name="Observed RSRP" fill="#ef4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="baseline_rsrp" name="Baseline RSRP" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm text-center py-10">No signal data.</p>
          )}
        </div>

        {/* Z-Score Distribution */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-[var(--accent-orange)]" />
            Z-Score Distribution (RSRP vs RSRQ)
          </h2>
          {zScoreData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="rsrp_z" name="RSRP Z-Score" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis dataKey="rsrq_z" name="RSRQ Z-Score" stroke="#64748b" tick={{ fontSize: 11 }} />
                <ZAxis dataKey="score" range={[20, 200]} name="Score" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }}
                  formatter={(v, name) => [v?.toFixed(2), name]}
                />
                <ReferenceLine x={2} stroke="#eab308" strokeDasharray="5 5" />
                <ReferenceLine y={2} stroke="#eab308" strokeDasharray="5 5" />
                <Scatter data={zScoreData} fill="#ef4444" fillOpacity={0.6} />
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm text-center py-10">No Z-score data available.</p>
          )}
        </div>
      </div>

      {/* Affected Serving Cells Table */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-color)]">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Shield size={18} className="text-[var(--accent-blue)]" />
            Affected Serving Cells ({data.affected_cells?.length || 0})
          </h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Serving Cell</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Detections</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Avg RSRP</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Baseline RSRP</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Avg Z-Score</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">In Baseline</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {(data.affected_cells || []).map((c) => (
              <tr key={c.serving_cell_id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                <td className="px-5 py-3 text-sm font-mono text-white">{c.serving_cell_id}</td>
                <td className="px-5 py-3 text-sm font-semibold text-[var(--accent-red)]">{c.count}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{c.avg_rsrp?.toFixed(1) ?? "—"} dBm</td>
                <td className="px-5 py-3 text-sm text-[var(--accent-blue)]">{c.baseline_stats?.rsrp_mean?.toFixed(1) ?? "—"} dBm</td>
                <td className="px-5 py-3">
                  <span className={`text-sm font-semibold ${(c.avg_rsrp_z ?? 0) > 2 ? "text-[var(--accent-red)]" : "text-[var(--accent-green)]"}`}>
                    {c.avg_rsrp_z?.toFixed(2) ?? "—"}
                  </span>
                </td>
                <td className="px-5 py-3">
                  {c.in_baseline ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400">Known</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 font-semibold">Unknown</span>
                  )}
                </td>
                <td className="px-5 py-3">
                  <Link to={`/cells/${c.serving_cell_id}`} className="text-[var(--accent-blue)] hover:text-blue-300 text-sm flex items-center gap-1">
                    <ExternalLink size={14} /> Profile
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* MR Records Table */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-color)] flex items-center justify-between">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Brain size={18} className="text-[var(--accent-purple)]" />
            Anomaly MR Records ({mrRecords.length})
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">Click a row to expand XAI explanation</p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Row</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Serving Cell</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">CoDisp</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Method</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRP</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRQ</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRP Z</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">RSRQ Z</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Score</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {pagedRecords.map((r) => (
              <MRRow
                key={r.anomaly_id}
                record={r}
                isExpanded={expandedRow === r.anomaly_id}
                onToggle={() => toggleExpand(r.anomaly_id)}
                explanation={expandedRow === r.anomaly_id ? explanation : null}
                explainLoading={expandedRow === r.anomaly_id && explainLoading}
              />
            ))}
            {pagedRecords.length === 0 && (
              <tr><td colSpan={10} className="text-center py-12 text-[var(--text-secondary)]">No MR records.</td></tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalMrPages > 1 && (
          <div className="px-5 py-3 border-t border-[var(--border-color)] flex items-center justify-between">
            <p className="text-xs text-[var(--text-secondary)]">
              Page {mrPage} of {totalMrPages} ({mrRecords.length} records)
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setMrPage((p) => Math.max(1, p - 1))}
                disabled={mrPage <= 1}
                className="px-3 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] text-sm disabled:opacity-30"
              >
                Prev
              </button>
              <button
                onClick={() => setMrPage((p) => Math.min(totalMrPages, p + 1))}
                disabled={mrPage >= totalMrPages}
                className="px-3 py-1 rounded bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-secondary)] text-sm disabled:opacity-30"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Risk Profile / Trend */}
      {data.risk_profile && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Eye size={18} className="text-[var(--accent-cyan)]" />
            Cross-Run Risk Profile
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-[var(--bg-primary)] rounded-lg p-3">
              <p className="text-xs text-[var(--text-secondary)]">Risk Level</p>
              <SeverityBadge severity={data.risk_profile.risk_level} />
            </div>
            <div className="bg-[var(--bg-primary)] rounded-lg p-3">
              <p className="text-xs text-[var(--text-secondary)]">Runs Appeared</p>
              <p className="text-xl font-bold text-white">{data.risk_profile.runs_appeared}</p>
            </div>
            <div className="bg-[var(--bg-primary)] rounded-lg p-3">
              <p className="text-xs text-[var(--text-secondary)]">Total Occurrences</p>
              <p className="text-xl font-bold text-[var(--accent-orange)]">{data.risk_profile.total_occurrences}</p>
            </div>
            <div className="bg-[var(--bg-primary)] rounded-lg p-3">
              <p className="text-xs text-[var(--text-secondary)]">Affected Cells</p>
              <p className="text-xl font-bold text-[var(--accent-blue)]">{data.risk_profile.affected_cells_count}</p>
            </div>
          </div>
          {data.risk_profile.trend && data.risk_profile.trend.length > 1 && (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.risk_profile.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="run_id" stroke="#64748b" tick={{ fontSize: 9 }} angle={-15} textAnchor="end" height={50} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
                <Bar dataKey="occurrences" fill="#f97316" name="Occurrences" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  );
}

function MRRow({ record: r, isExpanded, onToggle, explanation, explainLoading }) {
  const methodCls =
    r.detection_method === "both" ? "bg-purple-500/20 text-purple-400" :
    r.detection_method === "rrcf_only" ? "bg-blue-500/20 text-blue-400" :
    "bg-orange-500/20 text-orange-400";

  return (
    <>
      <tr
        className={`border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors cursor-pointer ${isExpanded ? "bg-[var(--bg-card-hover)]" : ""}`}
        onClick={onToggle}
      >
        <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">#{r.row_index}</td>
        <td className="px-4 py-3 text-sm font-mono text-white">{r.serving_cell_id}</td>
        <td className="px-4 py-3 text-sm font-semibold text-[var(--accent-red)]">{r.avg_codisp?.toFixed(3)}</td>
        <td className="px-4 py-3">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${methodCls}`}>
            {r.detection_method?.replace("_", " ")}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">{r.rsrp?.toFixed(1) ?? "—"}</td>
        <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">{r.rsrq?.toFixed(1) ?? "—"}</td>
        <td className="px-4 py-3">
          <span className={`text-sm font-semibold ${(r.rsrp_z ?? 0) > 2 ? "text-[var(--accent-red)]" : "text-[var(--text-secondary)]"}`}>
            {r.rsrp_z?.toFixed(2) ?? "—"}
          </span>
        </td>
        <td className="px-4 py-3">
          <span className={`text-sm font-semibold ${(r.rsrq_z ?? 0) > 2 ? "text-[var(--accent-red)]" : "text-[var(--text-secondary)]"}`}>
            {r.rsrq_z?.toFixed(2) ?? "—"}
          </span>
        </td>
        <td className="px-4 py-3 text-sm font-bold text-[var(--accent-red)]">{r.anomaly_score?.toFixed(2)}</td>
        <td className="px-4 py-3">
          {isExpanded ? <ChevronUp size={16} className="text-[var(--text-secondary)]" /> : <ChevronDown size={16} className="text-[var(--text-secondary)]" />}
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={10} className="bg-[var(--bg-primary)] border-b border-[var(--border-color)]">
            <div className="p-5">
              {explainLoading ? (
                <div className="flex items-center justify-center py-4">
                  <div className="w-5 h-5 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
                  <span className="ml-2 text-sm text-[var(--text-secondary)]">Loading XAI explanation...</span>
                </div>
              ) : explanation ? (
                <div className="space-y-4">
                  {/* Risk Assessment */}
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={explanation.risk_assessment?.level} />
                    <span className="text-sm text-[var(--text-secondary)]">{explanation.risk_assessment?.summary}</span>
                  </div>

                  {/* RRCF Score */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                      <p className="text-xs text-[var(--text-secondary)]">Avg CoDisp</p>
                      <p className="text-lg font-bold text-[var(--accent-red)]">{explanation.rrcf_explanation?.avg_codisp?.toFixed(4)}</p>
                    </div>
                    <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                      <p className="text-xs text-[var(--text-secondary)]">Threshold</p>
                      <p className="text-lg font-bold text-[var(--accent-yellow)]">{explanation.rrcf_explanation?.threshold?.toFixed(4)}</p>
                    </div>
                    <div className="bg-[var(--bg-secondary)] rounded-lg p-3">
                      <p className="text-xs text-[var(--text-secondary)]">Over By</p>
                      <p className="text-lg font-bold text-white">{explanation.rrcf_explanation?.over_threshold_by?.toFixed(4)}</p>
                    </div>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] italic">{explanation.rrcf_explanation?.interpretation}</p>

                  {/* All Neighbors in this MR */}
                  <div>
                    <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-2">All Neighbors in this MR Record</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {(explanation.neighbor_breakdown || []).map((n, i) => (
                        <div key={i} className={`rounded-lg p-3 border ${n.is_abnormal ? "bg-red-500/5 border-red-500/20" : "bg-[var(--bg-secondary)] border-[var(--border-color)]"}`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-mono text-white">{n.neighbor_id}</span>
                            {n.is_abnormal ? (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 font-semibold">ABNORMAL</span>
                            ) : (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400">Normal</span>
                            )}
                          </div>
                          <div className="text-xs text-[var(--text-secondary)] space-y-0.5">
                            <p>RSRP: {n.rsrp?.toFixed(1) ?? "—"} dBm (Z: {n.rsrp_z?.toFixed(2) ?? "—"})</p>
                            <p>RSRQ: {n.rsrq?.toFixed(1) ?? "—"} dB (Z: {n.rsrq_z?.toFixed(2) ?? "—"})</p>
                            <p className="font-semibold" style={{ color: n.is_abnormal ? "#ef4444" : "#3b82f6" }}>
                              Score: {n.anomaly_score?.toFixed(4)}
                            </p>
                          </div>
                          {n.is_abnormal && n.reason && (
                            <p className="text-[10px] text-[var(--accent-red)] mt-1">{n.reason}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">Could not load explanation.</p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function SummaryCard({ label, value, color }) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4">
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="text-2xl font-bold mt-1" style={{ color }}>{value}</p>
    </div>
  );
}
