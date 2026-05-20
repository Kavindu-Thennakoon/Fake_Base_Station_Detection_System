import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area,
} from "recharts";
import { BarChart3, TrendingUp } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner";
import { getAnomalyTrends, getCellRiskRanking, getMethodBreakdown } from "../services/api";

export default function Analytics() {
  const [trends, setTrends] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [breakdown, setBreakdown] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [t, r, b] = await Promise.all([
          getAnomalyTrends(),
          getCellRiskRanking(20),
          getMethodBreakdown(),
        ]);
        setTrends(t.data);
        setRanking(r.data);
        setBreakdown(b.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BarChart3 size={24} className="text-[var(--accent-cyan)]" />
          Analytics
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">Deep-dive into detection patterns and risk data</p>
      </div>

      {/* Method Summary Cards */}
      {breakdown && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 text-center">
            <p className="text-xs text-[var(--text-secondary)]">Total</p>
            <p className="text-2xl font-bold text-white">{breakdown.total}</p>
          </div>
          <div className="bg-[var(--bg-card)] border border-blue-500/30 rounded-xl p-4 text-center">
            <p className="text-xs text-[var(--text-secondary)]">RRCF Only</p>
            <p className="text-2xl font-bold text-blue-400">{breakdown.rrcf_only}</p>
          </div>
          <div className="bg-[var(--bg-card)] border border-orange-500/30 rounded-xl p-4 text-center">
            <p className="text-xs text-[var(--text-secondary)]">Z-Score Only</p>
            <p className="text-2xl font-bold text-orange-400">{breakdown.zscore_only}</p>
          </div>
          <div className="bg-[var(--bg-card)] border border-purple-500/30 rounded-xl p-4 text-center">
            <p className="text-xs text-[var(--text-secondary)]">Both Layers</p>
            <p className="text-2xl font-bold text-purple-400">{breakdown.both_layers}</p>
          </div>
        </div>
      )}

      {/* Trends Chart */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp size={18} className="text-[var(--accent-blue)]" />
          Anomaly Trends Over Time
        </h2>
        {trends.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="areaBlue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
              <Area type="monotone" dataKey="rrcf_count" stackId="1" stroke="#3b82f6" fill="url(#areaBlue)" name="RRCF" />
              <Area type="monotone" dataKey="zscore_count" stackId="1" stroke="#f97316" fill="#f9731622" name="Z-Score" />
              <Area type="monotone" dataKey="both_count" stackId="1" stroke="#a855f7" fill="#a855f722" name="Both" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-[var(--text-secondary)] text-sm text-center py-10">No trend data yet.</p>
        )}
      </div>

      {/* Risk Ranking */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
        <h2 className="text-base font-semibold text-white mb-4">Top Suspicious Neighbors (Cross-Run)</h2>
        {ranking.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={ranking} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis dataKey="neighbor_id" type="category" stroke="#64748b" tick={{ fontSize: 10 }} width={110} />
              <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }} />
              <Bar dataKey="total_score" fill="#ef4444" radius={[0, 4, 4, 0]} name="Total Score" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-[var(--text-secondary)] text-sm text-center py-10">No ranking data yet.</p>
        )}
      </div>
    </div>
  );
}