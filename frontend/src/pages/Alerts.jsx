import { useState, useEffect } from "react";
import { AlertTriangle, Check, X, Eye, RefreshCw } from "lucide-react";
import SeverityBadge from "../components/SeverityBadge";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { getAlerts, acknowledgeAlert, resolveAlert, markFalsePositive } from "../services/api";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    setLoading(true);
    try {
      const params = filter !== "all" ? { status: filter } : {};
      const res = await getAlerts(params);
      setAlerts(res.data.results || res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleAction = async (id, action) => {
    try {
      if (action === "acknowledge") await acknowledgeAlert(id);
      else if (action === "resolve") await resolveAlert(id);
      else if (action === "false_positive") await markFalsePositive(id);
      await load();
    } catch (e) {
      console.error(e);
    }
  };

  const filters = ["all", "new", "acknowledged", "investigating", "resolved", "false_positive"];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">Monitor and manage security alerts</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm transition-colors">
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === f
                ? "bg-[var(--accent-blue)] text-white"
                : "bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white"
            }`}
          >
            {f.replace("_", " ").toUpperCase()}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-3">
          {alerts.length > 0 ? (
            alerts.map((alert) => (
              <div key={alert.id} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5 hover:border-[var(--accent-blue)]/30 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <SeverityBadge severity={alert.severity} />
                      <StatusBadge status={alert.status} />
                      <span className="text-xs text-[var(--text-secondary)]">
                        {new Date(alert.created_at).toLocaleString()}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-white mb-1">{alert.title}</h3>
                    <p className="text-xs text-[var(--text-secondary)] mb-2">{alert.description}</p>
                    <div className="flex gap-4 text-xs text-[var(--text-secondary)]">
                      <span>Cell: <span className="font-mono text-white">{alert.neighbor_id}</span></span>
                      <span>Affected Cells: <span className="text-white">{alert.affected_cells_count}</span></span>
                      <span>Score: <span className="text-[var(--accent-red)] font-semibold">{alert.peak_anomaly_score?.toFixed(2)}</span></span>
                    </div>
                  </div>
                  {/* Action Buttons */}
                  {alert.status === "new" && (
                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleAction(alert.id, "acknowledge")}
                        className="p-2 rounded-lg bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition-colors"
                        title="Acknowledge"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        onClick={() => handleAction(alert.id, "resolve")}
                        className="p-2 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors"
                        title="Resolve"
                      >
                        <Check size={16} />
                      </button>
                      <button
                        onClick={() => handleAction(alert.id, "false_positive")}
                        className="p-2 rounded-lg bg-gray-500/10 text-gray-400 hover:bg-gray-500/20 transition-colors"
                        title="False Positive"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  )}
                  {alert.status === "acknowledged" && (
                    <div className="flex gap-2 ml-4">
                      <button onClick={() => handleAction(alert.id, "resolve")} className="p-2 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors" title="Resolve">
                        <Check size={16} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-16 text-[var(--text-secondary)]">
              <AlertTriangle size={40} className="mx-auto mb-3 opacity-30" />
              <p>No alerts matching this filter.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}