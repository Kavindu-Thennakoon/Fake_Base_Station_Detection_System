import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Check, X, Eye, RefreshCw, ChevronDown, ChevronUp, Search, Shield } from "lucide-react";
import SeverityBadge from "../components/SeverityBadge";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { getAlerts, getAlert, acknowledgeAlert, resolveAlert, markFalsePositive } from "../services/api";

const FILTERS = ["all", "new", "acknowledged", "investigating", "resolved", "false_positive"];

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

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
      if (expandedId === id) {
        setExpandedId(null);
        setDetail(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(id);
    setDetailLoading(true);
    try {
      const { data } = await getAlert(id);
      setDetail(data);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const counts = {
    all: alerts.length,
    new: alerts.filter((a) => a.status === "new").length,
    acknowledged: alerts.filter((a) => a.status === "acknowledged").length,
    resolved: alerts.filter((a) => a.status === "resolved").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <AlertTriangle size={24} className="text-[var(--accent-yellow)]" />
            Alerts
          </h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">Monitor and manage security alerts</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm transition-colors">
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard label="Total Alerts" value={counts.all} color="var(--accent-blue)" />
        <SummaryCard label="New" value={counts.new} color="var(--accent-red)" />
        <SummaryCard label="Acknowledged" value={counts.acknowledged} color="var(--accent-yellow)" />
        <SummaryCard label="Resolved" value={counts.resolved} color="var(--accent-green)" />
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map((f) => (
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

      {/* Alert List */}
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-3">
          {alerts.length > 0 ? (
            alerts.map((alert) => (
              <div key={alert.id} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden hover:border-[var(--accent-blue)]/30 transition-colors">
                {/* Alert Header */}
                <div className="p-5">
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
                        <span>Affected: <span className="text-white">{alert.affected_cells_count}</span></span>
                        <span>Score: <span className="text-[var(--accent-red)] font-semibold">{alert.peak_anomaly_score?.toFixed(2)}</span></span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {alert.status === "new" && (
                        <>
                          <ActionBtn icon={Eye} color="blue" title="Acknowledge" onClick={() => handleAction(alert.id, "acknowledge")} />
                          <ActionBtn icon={Check} color="green" title="Resolve" onClick={() => handleAction(alert.id, "resolve")} />
                          <ActionBtn icon={X} color="gray" title="False Positive" onClick={() => handleAction(alert.id, "false_positive")} />
                        </>
                      )}
                      {alert.status === "acknowledged" && (
                        <ActionBtn icon={Check} color="green" title="Resolve" onClick={() => handleAction(alert.id, "resolve")} />
                      )}
                      <button
                        onClick={() => toggleExpand(alert.id)}
                        className="p-2 rounded-lg bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-white transition"
                        title="Details"
                      >
                        {expandedId === alert.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Detail Panel */}
                {expandedId === alert.id && (
                  <div className="border-t border-[var(--border-color)] bg-[var(--bg-primary)] p-5">
                    {detailLoading ? (
                      <div className="flex items-center justify-center py-4">
                        <div className="w-5 h-5 border-2 border-[var(--accent-blue)] border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : detail ? (
                      <div className="space-y-4">
                        <div className="flex items-center gap-3">
                          <Link
                            to={`/neighbors/${alert.neighbor_id}`}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-500/10 text-purple-400 text-xs font-medium hover:bg-purple-500/20 transition"
                          >
                            <Search size={14} /> Investigate Neighbor
                          </Link>
                          <Link
                            to={`/cells/${alert.neighbor_id}`}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-xs font-medium hover:bg-blue-500/20 transition"
                          >
                            <Shield size={14} /> Cell Profile
                          </Link>
                        </div>

                        {/* Alert Details */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <DetailItem label="Alert ID" value={`#${detail.id}`} />
                          <DetailItem label="Run" value={detail.run_detail?.run_id || `Run #${detail.run}`} />
                          <DetailItem label="Created" value={new Date(detail.created_at).toLocaleString()} />
                          <DetailItem label="Resolved" value={detail.resolved_at ? new Date(detail.resolved_at).toLocaleString() : "—"} />
                        </div>

                        {/* Audit History */}
                        {detail.history && detail.history.length > 0 && (
                          <div>
                            <h4 className="text-xs font-semibold text-[var(--text-secondary)] uppercase mb-2">Audit Trail</h4>
                            <div className="space-y-2">
                              {detail.history.map((h, i) => (
                                <div key={i} className="flex items-start gap-3 pl-3 border-l-2 border-[var(--border-color)]">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      <StatusBadge status={h.old_status} />
                                      <span className="text-xs text-[var(--text-secondary)]">&rarr;</span>
                                      <StatusBadge status={h.new_status} />
                                      <span className="text-xs text-[var(--text-secondary)]">
                                        by {h.changed_by_username || "system"} &middot; {new Date(h.created_at).toLocaleString()}
                                      </span>
                                    </div>
                                    {h.comment && (
                                      <p className="text-xs text-[var(--text-secondary)] mt-1 italic">"{h.comment}"</p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)]">Could not load alert details.</p>
                    )}
                  </div>
                )}
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

function ActionBtn({ icon: Icon, color, title, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`p-2 rounded-lg bg-${color}-500/10 text-${color}-400 hover:bg-${color}-500/20 transition-colors`}
      title={title}
    >
      <Icon size={16} />
    </button>
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

function DetailItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="text-sm text-white font-medium">{value}</p>
    </div>
  );
}
