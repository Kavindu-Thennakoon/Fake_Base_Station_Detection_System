import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Shield,
  AlertTriangle,
  Radio,
  Activity,
  TrendingUp,
  Clock,
  MapPin,
  Server,
  CheckCircle,
  XCircle,
} from "lucide-react";
import StatCard from "../components/StatCard";
import SeverityBadge from "../components/SeverityBadge";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import MapView from "../components/MapView";
import {
  getDashboardStats,
  getAnomalyTrends,
  getMethodBreakdown,
  getRecentActivity,
  getAlerts,
  getGeographicHeatmap,
  getModelStatus,
} from "../services/api";

const PIE_COLORS = ["#3b82f6", "#f97316", "#a855f7"];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);
  const [breakdown, setBreakdown] = useState(null);
  const [activity, setActivity] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [mapCells, setMapCells] = useState([]);
  const [modelHealth, setModelHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, t, b, a, al, geo, mh] = await Promise.all([
          getDashboardStats(),
          getAnomalyTrends(),
          getMethodBreakdown(),
          getRecentActivity(),
          getAlerts({ status: "new" }),
          getGeographicHeatmap().catch(() => ({ data: [] })),
          getModelStatus().catch(() => ({ data: null })),
        ]);
        setStats(s.data);
        setTrends(t.data);
        setBreakdown(b.data);
        setActivity(a.data);
        setAlerts(al.data.results || al.data);
        setMapCells(geo.data || []);
        setModelHealth(mh.data);
      } catch (e) {
        console.error("Dashboard load error:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner text="Loading dashboard..." />;

  const pieData = breakdown
    ? [
        { name: "RRCF Only", value: breakdown.rrcf_only },
        { name: "Z-Score Only", value: breakdown.zscore_only },
        { name: "Both Layers", value: breakdown.both_layers },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">
            Fake Base Station Detection System — Overview
          </p>
        </div>
        <SystemHealthBadge model={modelHealth} />
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Detection Runs" value={stats?.total_detection_runs || 0} color="blue" sub={`${stats?.completed_runs || 0} completed`} />
        <StatCard icon={Shield} label="Total Anomalies" value={stats?.total_anomalies || 0} color="red" />
        <StatCard icon={AlertTriangle} label="Active Alerts" value={stats?.active_alerts || 0} color="yellow" />
        <StatCard icon={Radio} label="Cells Trained" value={stats?.total_cells_trained || 0} color="green" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Anomaly Trends */}
        <div className="lg:col-span-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-[var(--accent-blue)]" />
            Anomaly Trends
          </h2>
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
                <Area type="monotone" dataKey="total" stroke="#3b82f6" fill="url(#colorTotal)" strokeWidth={2} name="Total Anomalies" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm py-10 text-center">No trend data yet.</p>
          )}
        </div>

        {/* Detection Method Breakdown */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4">Detection Methods</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={4} dataKey="value">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
                <Legend wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm py-10 text-center">No breakdown data yet.</p>
          )}
        </div>
      </div>

      {/* Map Preview + Active Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mini Map */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <MapPin size={18} className="text-[var(--accent-cyan)]" />
              Cell Tower Map
            </h2>
            <Link to="/map" className="text-xs text-[var(--accent-blue)] hover:underline">Full Map &rarr;</Link>
          </div>
          {mapCells.length > 0 ? (
            <div className="h-[260px] rounded-lg overflow-hidden">
              <MapView cells={mapCells} />
            </div>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm py-10 text-center">No cell locations available.</p>
          )}
        </div>

        {/* Active Alerts */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <AlertTriangle size={18} className="text-[var(--accent-yellow)]" />
              Active Alerts
            </h2>
            <Link to="/alerts" className="text-xs text-[var(--accent-blue)] hover:underline">View All &rarr;</Link>
          </div>
          <div className="space-y-3">
            {alerts.length > 0 ? (
              alerts.slice(0, 5).map((alert) => (
                <Link key={alert.id} to={`/neighbors/${alert.neighbor_id}`} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--bg-card-hover)] transition-colors">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{alert.title}</p>
                    <p className="text-xs text-[var(--text-secondary)]">Neighbor: {alert.neighbor_id}</p>
                  </div>
                  <SeverityBadge severity={alert.severity} />
                </Link>
              ))
            ) : (
              <p className="text-[var(--text-secondary)] text-sm text-center py-6">No active alerts</p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Activity + Latest Run */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Clock size={18} className="text-[var(--accent-cyan)]" />
            Recent Detection Runs
          </h2>
          <div className="space-y-3">
            {activity.length > 0 ? (
              activity.slice(0, 5).map((run) => (
                <Link key={run.run_id} to={`/detection/${run.run_id}`} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--bg-card-hover)] transition-colors">
                  <div>
                    <p className="text-sm font-medium text-white">{run.run_id}</p>
                    <p className="text-xs text-[var(--text-secondary)]">{new Date(run.started_at).toLocaleString()}</p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={run.status} />
                    <p className="text-xs text-[var(--text-secondary)] mt-1">{run.total_anomalies} anomalies</p>
                  </div>
                </Link>
              ))
            ) : (
              <p className="text-[var(--text-secondary)] text-sm text-center py-6">No detection runs yet.</p>
            )}
          </div>
        </div>

        {/* Latest Run Summary */}
        {stats?.latest_run && (
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
            <h2 className="text-base font-semibold text-white mb-3">Latest Run Summary</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Run ID</p>
                <p className="text-sm font-medium text-white">{stats.latest_run.run_id}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Status</p>
                <StatusBadge status={stats.latest_run.status} />
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Anomalies</p>
                <p className="text-sm font-bold text-[var(--accent-red)]">{stats.latest_run.total_anomalies}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-secondary)]">Started</p>
                <p className="text-sm text-white">{new Date(stats.latest_run.started_at).toLocaleString()}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SystemHealthBadge({ model }) {
  const isHealthy = model?.status === "loaded" || model?.status === "demo";
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
      isHealthy
        ? "bg-green-500/10 text-green-400 border border-green-500/30"
        : "bg-red-500/10 text-red-400 border border-red-500/30"
    }`}>
      {isHealthy ? <CheckCircle size={14} /> : <XCircle size={14} />}
      <Server size={14} />
      {isHealthy ? "System Healthy" : "System Issue"}
      {model?.total_cells > 0 && (
        <span className="opacity-60">&middot; {model.total_cells} cells</span>
      )}
    </div>
  );
}
