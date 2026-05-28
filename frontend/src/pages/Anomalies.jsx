import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Shield, Brain, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner";
import { getAnomalies, getDetectionRuns } from "../services/api";

const METHODS = [
  { value: "", label: "All Methods" },
  { value: "both", label: "Both Layers" },
  { value: "rrcf_only", label: "RRCF Only" },
  { value: "zscore_only", label: "Z-Score Only" },
];

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const [selectedRun, setSelectedRun] = useState("");
  const [selectedCell, setSelectedCell] = useState("");
  const [selectedMethod, setSelectedMethod] = useState("");

  useEffect(() => {
    getDetectionRuns()
      .then(({ data }) => setRuns(Array.isArray(data) ? data : data.results || []))
      .catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page };
      if (selectedRun) params.run_id = selectedRun;
      if (selectedCell) params.cell_id = selectedCell;
      const res = await getAnomalies(params);
      const items = res.data.results || res.data;
      setTotal(res.data.count || items.length);
      setAnomalies(items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, selectedRun, selectedCell]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered =
    selectedMethod
      ? anomalies.filter((a) => a.detection_method === selectedMethod)
      : anomalies;

  const stats = {
    total: total,
    rrcf: anomalies.filter((a) => a.rrcf_flagged).length,
    zscore: anomalies.filter((a) => a.zscore_flagged).length,
    both: anomalies.filter((a) => a.rrcf_flagged && a.zscore_flagged).length,
  };

  const cellIds = [...new Set(anomalies.map((a) => a.serving_cell_id))].sort();
  const totalPages = Math.ceil(total / 50);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Shield size={24} className="text-[var(--accent-red)]" />
          Anomalies
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">
          All detected anomalies across detection runs
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniStat label="Total (this page)" value={stats.total} color="var(--accent-red)" />
        <MiniStat label="RRCF Flagged" value={stats.rrcf} color="var(--accent-blue)" />
        <MiniStat label="Z-Score Flagged" value={stats.zscore} color="var(--accent-orange)" />
        <MiniStat label="Both Layers" value={stats.both} color="var(--accent-purple)" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Filter size={16} className="text-[var(--text-secondary)]" />
        <select
          value={selectedRun}
          onChange={(e) => { setSelectedRun(e.target.value); setPage(1); }}
          className="px-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]"
        >
          <option value="">All Runs</option>
          {runs.map((r) => (
            <option key={r.run_id} value={r.run_id}>{r.run_id}</option>
          ))}
        </select>
        <select
          value={selectedCell}
          onChange={(e) => { setSelectedCell(e.target.value); setPage(1); }}
          className="px-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]"
        >
          <option value="">All Cells</option>
          {cellIds.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        {METHODS.map((m) => (
          <button
            key={m.value}
            onClick={() => setSelectedMethod(m.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              selectedMethod === m.value
                ? "bg-[var(--accent-blue)] text-white"
                : "bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">ID</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Cell ID</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">CoDisp Score</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Threshold</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Method</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Time</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map((a) => (
                  <tr key={a.id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                    <td className="px-5 py-3 text-sm text-white">#{a.id}</td>
                    <td className="px-5 py-3 text-sm font-mono text-white">{a.serving_cell_id}</td>
                    <td className="px-5 py-3 text-sm font-semibold text-[var(--accent-red)]">{a.avg_codisp?.toFixed(3)}</td>
                    <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{a.threshold?.toFixed(3)}</td>
                    <td className="px-5 py-3">
                      <MethodBadge method={a.detection_method} />
                    </td>
                    <td className="px-5 py-3 text-xs text-[var(--text-secondary)]">
                      {a.datetime_raw ? new Date(a.datetime_raw).toLocaleString() : "—"}
                    </td>
                    <td className="px-5 py-3">
                      <Link to={`/anomalies/${a.id}`} className="flex items-center gap-1 text-[var(--accent-purple)] hover:text-purple-300 text-sm">
                        <Brain size={14} /> Explain
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-[var(--text-secondary)]">No anomalies match current filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-[var(--text-secondary)]">
            Page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm disabled:opacity-30 transition"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm disabled:opacity-30 transition"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4">
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      <div className="mt-2 h-1 rounded-full bg-[var(--bg-secondary)]">
        <div className="h-full rounded-full" style={{ background: color, width: "60%" }} />
      </div>
    </div>
  );
}

function MethodBadge({ method }) {
  const cls =
    method === "both"
      ? "bg-purple-500/20 text-purple-400"
      : method === "rrcf_only"
      ? "bg-blue-500/20 text-blue-400"
      : "bg-orange-500/20 text-orange-400";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {method?.replace("_", " ")}
    </span>
  );
}
