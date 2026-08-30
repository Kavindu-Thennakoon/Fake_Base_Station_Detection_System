import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Radio, Filter, ChevronLeft, ChevronRight, Search, AlertTriangle, ExternalLink } from "lucide-react";
import SeverityBadge from "../components/SeverityBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { getSuspiciousNeighbors, getDetectionRuns } from "../services/api";

const SEVERITIES = [
  { value: "", label: "All Severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export default function Anomalies() {
  const [neighbors, setNeighbors] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const [selectedRun, setSelectedRun] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [searchInput, setSearchInput] = useState("");

  useEffect(() => {
    getDetectionRuns()
      .then(({ data }) => setRuns(Array.isArray(data) ? data : data.results || []))
      .catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 50 };
      if (selectedRun) params.run_id = selectedRun;
      if (selectedSeverity) params.severity = selectedSeverity;
      if (searchTerm) params.search = searchTerm;
      const res = await getSuspiciousNeighbors(params);
      setTotal(res.data.count || 0);
      setNeighbors(res.data.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, selectedRun, selectedSeverity, searchTerm]);

  useEffect(() => { load(); }, [load]);

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchTerm(searchInput);
    setPage(1);
  };

  const stats = {
    total,
    critical: neighbors.filter((n) => n.severity === "critical").length,
    high: neighbors.filter((n) => n.severity === "high").length,
    affectedCells: new Set(neighbors.flatMap((n) => n.affected_serving_cells || [])).size,
  };

  const totalPages = Math.ceil(total / 50);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Radio size={24} className="text-[var(--accent-red)]" />
          Detected Abnormal Neighbors
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">
          Suspicious neighbor cells ranked by anomaly score — potential Fake Base Stations
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniStat label="Total Suspicious" value={stats.total} color="var(--accent-red)" />
        <MiniStat label="Critical" value={stats.critical} color="#ef4444" />
        <MiniStat label="High" value={stats.high} color="var(--accent-orange)" />
        <MiniStat label="Affected Cells (page)" value={stats.affectedCells} color="var(--accent-blue)" />
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

        {SEVERITIES.map((s) => (
          <button
            key={s.value}
            onClick={() => { setSelectedSeverity(s.value); setPage(1); }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              selectedSeverity === s.value
                ? "bg-[var(--accent-blue)] text-white"
                : "bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white"
            }`}
          >
            {s.label}
          </button>
        ))}

        <form onSubmit={handleSearch} className="flex items-center gap-2 ml-auto">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search neighbor ID..."
              className="pl-8 pr-3 py-1.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] w-48"
            />
          </div>
          <button type="submit" className="px-3 py-1.5 rounded-lg bg-[var(--accent-blue)] text-white text-xs font-medium">
            Search
          </button>
        </form>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Neighbor ID</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Anomaly Score</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Occurrences</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Affected Cells</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Severity</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Run</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {neighbors.length > 0 ? (
                neighbors.map((n) => (
                  <tr key={n.id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                    <td className="px-5 py-3 text-sm font-mono font-semibold text-white">{n.neighbor_id}</td>
                    <td className="px-5 py-3 text-sm font-semibold text-[var(--accent-red)]">
                      {n.sum_score >= 1000000
                        ? `${(n.sum_score / 1000000).toFixed(2)}M`
                        : n.sum_score >= 1000
                        ? `${(n.sum_score / 1000).toFixed(1)}K`
                        : n.sum_score.toFixed(2)}
                    </td>
                    <td className="px-5 py-3 text-sm text-white font-medium">{n.occurrence_count}</td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-white font-medium">{n.affected_cells_count}</span>
                        <span className="text-xs text-[var(--text-secondary)]">
                          {n.affected_cells_count === 1 ? "cell" : "cells"}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <SeverityBadge severity={n.severity} />
                    </td>
                    <td className="px-5 py-3 text-xs text-[var(--text-secondary)] font-mono">{n.run_id?.split("_").slice(-2).join("_")}</td>
                    <td className="px-5 py-3">
                      <Link
                        to={`/neighbors/${n.neighbor_id}`}
                        className="flex items-center gap-1 text-[var(--accent-purple)] hover:text-purple-300 text-sm font-medium"
                      >
                        <ExternalLink size={14} /> Details
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="text-center py-16 text-[var(--text-secondary)]">
                    <AlertTriangle size={40} className="mx-auto mb-3 opacity-30" />
                    <p>No suspicious neighbors match current filters.</p>
                  </td>
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
      <p className="text-2xl font-bold text-white mt-1">{typeof value === "number" ? value.toLocaleString() : value}</p>
      <div className="mt-2 h-1 rounded-full bg-[var(--bg-secondary)]">
        <div className="h-full rounded-full" style={{ background: color, width: "60%" }} />
      </div>
    </div>
  );
}
