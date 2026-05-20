import { useState, useEffect } from "react";
import { Radio, Activity } from "lucide-react";
import StatCard from "../components/StatCard";
import LoadingSpinner from "../components/LoadingSpinner";
import { getCellModels, getModelStatus } from "../services/api";

export default function CellModels() {
  const [cells, setCells] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [c, s] = await Promise.all([getCellModels(), getModelStatus()]);
        setCells(c.data.results || c.data);
        setStatus(s.data);
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
          <Radio size={24} className="text-[var(--accent-green)]" />
          Cell Models
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">Trained RRCF models per serving cell</p>
      </div>

      {/* Model Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={Radio} label="Model Status" value={status?.status?.toUpperCase() || "UNKNOWN"} color="green" />
        <StatCard icon={Activity} label="Total Cells" value={status?.total_cells || 0} color="blue" />
        <StatCard icon={Activity} label="Model Size" value={status?.model_size_mb ? status.model_size_mb + " MB" : "N/A"} color="purple" />
      </div>

      {/* Cell Table */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Cell ID</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">K (Neighbors)</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Mean CoDisp</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Std CoDisp</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Training Rows</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Trees</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Last Trained</th>
            </tr>
          </thead>
          <tbody>
            {cells.length > 0 ? cells.map((c) => (
              <tr key={c.serving_cell_id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                <td className="px-5 py-3 text-sm font-mono font-medium text-white">{c.serving_cell_id}</td>
                <td className="px-5 py-3 text-sm text-white">{c.K}</td>
                <td className="px-5 py-3 text-sm text-[var(--accent-blue)]">{c.mean_codisp?.toFixed(4)}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{c.std_codisp?.toFixed(4)}</td>
                <td className="px-5 py-3 text-sm text-white">{c.training_rows?.toLocaleString()}</td>
                <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{c.num_trees}</td>
                <td className="px-5 py-3 text-xs text-[var(--text-secondary)]">{c.last_trained ? new Date(c.last_trained).toLocaleString() : "—"}</td>
              </tr>
            )) : (
              <tr><td colSpan={7} className="text-center py-12 text-[var(--text-secondary)]">No trained models. Run training first.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}