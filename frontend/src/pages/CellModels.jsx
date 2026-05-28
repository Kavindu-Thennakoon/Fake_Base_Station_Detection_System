import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Radio, Activity, ChevronRight } from "lucide-react";
import StatCard from "../components/StatCard";
import LoadingSpinner from "../components/LoadingSpinner";
import { getCellModels, getModelStatus } from "../services/api";

function getHealth(cell) {
  if (!cell.training_rows || cell.training_rows < 100) return { label: "Low Data", color: "text-[var(--accent-yellow)]", bg: "bg-yellow-500/15" };
  if (cell.std_codisp > 5) return { label: "Noisy", color: "text-[var(--accent-orange)]", bg: "bg-orange-500/15" };
  return { label: "Healthy", color: "text-[var(--accent-green)]", bg: "bg-green-500/15" };
}

export default function CellModels() {
  const [cells, setCells] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

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
        <p className="text-[var(--text-secondary)] text-sm mt-1">
          Trained RRCF models per serving cell — click a row for details
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={Radio} label="Model Status" value={status?.status?.toUpperCase() || "UNKNOWN"} color="green" />
        <StatCard icon={Activity} label="Total Cells" value={status?.total_cells || 0} color="blue" />
        <StatCard icon={Activity} label="Model Size" value={status?.model_size_mb ? status.model_size_mb + " MB" : "N/A"} color="purple" />
      </div>

      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Cell ID</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Health</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">K</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Mean CoDisp</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Std CoDisp</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Training Rows</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Trees</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Last Trained</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {cells.length > 0 ? cells.map((c) => {
              const health = getHealth(c);
              return (
                <tr
                  key={c.serving_cell_id}
                  onClick={() => navigate(`/cells/${c.serving_cell_id}`)}
                  className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors cursor-pointer"
                >
                  <td className="px-5 py-3 text-sm font-mono font-medium text-white">{c.serving_cell_id}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${health.bg} ${health.color}`}>
                      {health.label}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-sm text-white">{c.K}</td>
                  <td className="px-5 py-3 text-sm text-[var(--accent-blue)]">{c.mean_codisp?.toFixed(4)}</td>
                  <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{c.std_codisp?.toFixed(4)}</td>
                  <td className="px-5 py-3 text-sm text-white">{c.training_rows?.toLocaleString()}</td>
                  <td className="px-5 py-3 text-sm text-[var(--text-secondary)]">{c.num_trees}</td>
                  <td className="px-5 py-3 text-xs text-[var(--text-secondary)]">{c.last_trained ? new Date(c.last_trained).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3 text-[var(--accent-blue)]"><ChevronRight size={16} /></td>
                </tr>
              );
            }) : (
              <tr><td colSpan={9} className="text-center py-12 text-[var(--text-secondary)]">No trained models. Run training first.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
