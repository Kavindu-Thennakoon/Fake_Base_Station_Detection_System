import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Shield, Brain } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner";
import { getAnomalies } from "../services/api";

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await getAnomalies();
        setAnomalies(res.data.results || res.data);
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
          <Shield size={24} className="text-[var(--accent-red)]" />
          Anomalies
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">All detected anomalies across runs</p>
      </div>

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
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {anomalies.length > 0 ? anomalies.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                <td className="px-5 py-3 text-sm text-white">#{a.id}</td>
                <td className="px-5 py-3 text-sm font-mono text-white">{a.serving_cell_id}</td>
                <td className="px-5 py-3 text-sm font-semibold text-[var(--accent-red)]">{a.avg_codisp?.toFixed(3)}</td>
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
                  <Link to={`/anomalies/${a.id}`} className="flex items-center gap-1 text-[var(--accent-purple)] hover:text-purple-300 text-sm">
                    <Brain size={14} /> Explain
                  </Link>
                </td>
              </tr>
            )) : (
              <tr><td colSpan={7} className="text-center py-12 text-[var(--text-secondary)]">No anomalies detected yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}