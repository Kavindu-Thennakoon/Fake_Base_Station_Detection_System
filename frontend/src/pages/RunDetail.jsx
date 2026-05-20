import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { ArrowLeft, Shield, AlertTriangle, Clock, Radio } from "lucide-react";
import StatCard from "../components/StatCard";
import SeverityBadge from "../components/SeverityBadge";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import {
  getRunSummary,
  getRunAnomalies,
  getRunSuspiciousNeighbors,
} from "../services/api";

const PIE_COLORS = ["#3b82f6", "#f97316", "#a855f7"];

export default function RunDetail() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [suspicious, setSuspicious] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, a, sn] = await Promise.all([
          getRunSummary(id),
          getRunAnomalies(id),
          getRunSuspiciousNeighbors(id),
        ]);
        setSummary(s.data);
        setAnomalies(a.data.results || a.data);
        setSuspicious(sn.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <LoadingSpinner />;
  if (!summary) return <p className="text-[var(--text-secondary)]">Run not found.</p>;

  const pieData = [
    { name: "RRCF Only", value: summary.rrcf_only },
    { name: "Z-Score Only", value: summary.zscore_only },
    { name: "Both Layers", value: summary.both_layers },
  ].filter((d) => d.value > 0);

  const topSuspicious = suspicious.slice(0, 10);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/detection" className="text-[var(--text-secondary)] hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white">{summary.run_id}</h1>
          <div className="flex items-center gap-3 mt-1">
            <StatusBadge status={summary.status} />
            {summary.duration_seconds && (
              <span className="text-xs text-[var(--text-secondary)]">
                Duration: {summary.duration_seconds.toFixed(2)}s
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Shield} label="Total Anomalies" value={summary.total_anomalies} color="red" />
        <StatCard icon={AlertTriangle} label="Alerts Generated" value={summary.alerts_generated} color="yellow" />
        <StatCard icon={Radio} label="Suspicious Neighbors" value={summary.suspicious_neighbors} color="orange" />
        <StatCard icon={Clock} label="Detected Windows" value={summary.detected_windows} color="purple" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4">Detection Method Breakdown</h2>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={4} dataKey="value">
                {pieData.map((_, i) => (<Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4">Top Suspicious Neighbors</h2>
          {topSuspicious.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={topSuspicious} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis dataKey="neighbor_id" type="category" stroke="#64748b" tick={{ fontSize: 10 }} width={100} />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
                <Bar dataKey="sum_score" fill="#ef4444" radius={[0, 4, 4, 0]} name="Anomaly Score" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm text-center py-10">No suspicious neighbors.</p>
          )}
        </div>
      </div>

      {/* Anomalies Table */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-color)]">
          <h2 className="text-base font-semibold text-white">Anomalies ({anomalies.length})</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">ID</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Cell ID</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">CoDisp</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Threshold</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Method</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Time</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {anomalies.slice(0, 20).map((a) => (
              <tr key={a.id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                <td className="px-5 py-3 text-sm text-white">#{a.id}</td>
                <td className="px-5 py-3 text-sm font-mono text-white">{a.serving_cell_id}</td>
                <td className="px-5 py-3 text-sm text-[var(--accent-red)] font-semibold">{a.avg_codisp?.toFixed(3)}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{a.threshold?.toFixed(3)}</td>
                <td className="px-5 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    a.detection_method === "both" ? "bg-purple-500/20 text-purple-400" :
                    a.detection_method === "rrcf_only" ? "bg-blue-500/20 text-blue-400" :
                    "bg-orange-500/20 text-orange-400"
                  }`}>
                    {a.detection_method?.replace("_", " ")}
                  </span>
                </td>
                <td className="px-5 py-3 text-xs text-[var(--text-secondary)]">
                  {a.datetime_raw ? new Date(a.datetime_raw).toLocaleString() : "—"}
                </td>
                <td className="px-5 py-3">
                  <Link to={`/anomalies/${a.id}`} className="text-[var(--accent-blue)] hover:text-blue-300 text-sm">
                    Explain →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}