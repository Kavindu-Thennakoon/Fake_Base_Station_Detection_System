import { useState, useEffect } from "react";
import { MapPin, AlertTriangle, Radio, ShieldAlert, Filter } from "lucide-react";
import MapView from "../components/MapView";
import { getGeographicHeatmap, getDetectionRuns } from "../services/api";

const SEVERITY_FILTERS = ["all", "critical", "high", "medium", "low", "normal"];

const RISK_COLORS = {
  critical: "var(--accent-red)",
  high: "var(--accent-orange)",
  medium: "var(--accent-yellow)",
  low: "var(--accent-blue)",
  normal: "var(--accent-green)",
};

export default function MapPage() {
  const [cells, setCells] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selectedCell, setSelectedCell] = useState(null);

  useEffect(() => {
    getDetectionRuns()
      .then(({ data }) => setRuns(Array.isArray(data) ? data : data.results || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    getGeographicHeatmap(selectedRun || undefined)
      .then(({ data }) => setCells(data))
      .catch(() => setCells([]))
      .finally(() => setLoading(false));
  }, [selectedRun]);

  const filteredCells =
    severityFilter === "all"
      ? cells
      : cells.filter((c) => c.risk_level === severityFilter);

  const stats = {
    total: cells.length,
    critical: cells.filter((c) => c.risk_level === "critical").length,
    high: cells.filter((c) => c.risk_level === "high").length,
    anomalous: cells.filter((c) => c.anomaly_count > 0).length,
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <MapPin size={24} className="text-[var(--accent-blue)]" />
            Geographic Map
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Cell tower locations and anomaly risk visualization
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedRun}
            onChange={(e) => setSelectedRun(e.target.value)}
            className="px-3 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)]"
          >
            <option value="">All Runs</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          icon={Radio}
          label="Total Cells"
          value={stats.total}
          color="var(--accent-blue)"
        />
        <StatCard
          icon={ShieldAlert}
          label="Critical Risk"
          value={stats.critical}
          color="var(--accent-red)"
        />
        <StatCard
          icon={AlertTriangle}
          label="High Risk"
          value={stats.high}
          color="var(--accent-orange)"
        />
        <StatCard
          icon={MapPin}
          label="With Anomalies"
          value={stats.anomalous}
          color="var(--accent-yellow)"
        />
      </div>

      {/* Severity Filter */}
      <div className="flex items-center gap-2">
        <Filter size={16} className="text-[var(--text-secondary)]" />
        <span className="text-sm text-[var(--text-secondary)]">Filter:</span>
        {SEVERITY_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setSeverityFilter(f)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all capitalize ${
              severityFilter === f
                ? "bg-[var(--accent-blue)] text-white"
                : "bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
            }`}
          >
            {f}
            {f !== "all" && (
              <span className="ml-1 opacity-70">
                ({cells.filter((c) => c.risk_level === f).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Map + Detail Panel */}
      <div className="flex gap-4" style={{ height: "calc(100vh - 320px)" }}>
        <div className="flex-1 rounded-xl overflow-hidden border border-[var(--border-color)]">
          {loading ? (
            <div className="flex items-center justify-center h-full bg-[var(--bg-card)]">
              <div className="w-8 h-8 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <MapView cells={filteredCells} onCellClick={setSelectedCell} />
          )}
        </div>

        {/* Side Panel */}
        <div className="w-80 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 overflow-y-auto">
          {selectedCell ? (
            <CellDetail cell={selectedCell} />
          ) : (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-white">Cell Towers</h3>
              <p className="text-xs text-[var(--text-secondary)]">
                Click a marker on the map to view details, or browse below.
              </p>
              <div className="space-y-2 mt-3">
                {filteredCells
                  .sort((a, b) => {
                    const order = { critical: 0, high: 1, medium: 2, low: 3, normal: 4 };
                    return (order[a.risk_level] ?? 5) - (order[b.risk_level] ?? 5);
                  })
                  .map((cell) => (
                    <button
                      key={cell.cell_id}
                      onClick={() => setSelectedCell(cell)}
                      className="w-full text-left px-3 py-2 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card-hover)] transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white truncate">
                          {cell.cell_name || cell.cell_id}
                        </span>
                        <span
                          className="text-xs font-bold uppercase"
                          style={{ color: RISK_COLORS[cell.risk_level] }}
                        >
                          {cell.risk_level}
                        </span>
                      </div>
                      <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                        {cell.cell_id} — {cell.anomaly_count} anomalies
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl">
        <span className="text-xs text-[var(--text-secondary)] font-medium">Legend:</span>
        {Object.entries(RISK_COLORS).map(([level, color]) => (
          <span key={level} className="flex items-center gap-1.5 text-xs capitalize">
            <span
              className="w-3 h-3 rounded-full"
              style={{ background: color }}
            />
            <span className="text-[var(--text-secondary)]">{level}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-[var(--text-secondary)]">{label}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ background: `${color}20` }}
        >
          <Icon size={20} style={{ color }} />
        </div>
      </div>
    </div>
  );
}

function CellDetail({ cell }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-white">{cell.cell_name || cell.cell_id}</h3>
        <p className="text-xs text-[var(--text-secondary)] mt-1">Cell ID: {cell.cell_id}</p>
      </div>

      <div
        className="px-3 py-2 rounded-lg text-sm font-bold uppercase text-center"
        style={{
          color: RISK_COLORS[cell.risk_level],
          background: `${RISK_COLORS[cell.risk_level]}15`,
          border: `1px solid ${RISK_COLORS[cell.risk_level]}40`,
        }}
      >
        {cell.risk_level} Risk
      </div>

      <div className="space-y-2">
        <DetailRow label="Technology" value={cell.technology} />
        {cell.band && <DetailRow label="Band" value={cell.band} />}
        <DetailRow
          label="Coordinates"
          value={`${cell.latitude.toFixed(4)}, ${cell.longitude.toFixed(4)}`}
        />
        <DetailRow label="Anomaly Count" value={cell.anomaly_count} />
        <DetailRow label="Suspicion Score" value={cell.suspicion_score} />
      </div>

      {cell.cell_id.startsWith("99999") || cell.cell_id.startsWith("88888") ? (
        <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
          This cell ID does not match any known operator. It may be a Fake Base Station
          (IMSI Catcher).
        </div>
      ) : null}
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-[var(--border-color)]">
      <span className="text-xs text-[var(--text-secondary)]">{label}</span>
      <span className="text-sm text-white font-medium">{value}</span>
    </div>
  );
}
