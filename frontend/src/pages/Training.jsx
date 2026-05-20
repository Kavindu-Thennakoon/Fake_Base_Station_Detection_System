import { useState, useEffect } from "react";
import { Brain, Play, RefreshCw } from "lucide-react";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import { getTrainingRuns, triggerTraining } from "../services/api";

export default function Training() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    train_file: "",
    num_trees: 150,
    tree_size: 1024,
    min_samples: 50,
  });

  const load = async () => {
    setLoading(true);
    try {
      const res = await getTrainingRuns();
      setRuns(res.data.results || res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleTrigger = async () => {
    if (!formData.train_file) return;
    setTriggering(true);
    try {
      await triggerTraining(formData);
      setShowModal(false);
      setFormData({ train_file: "", num_trees: 150, tree_size: 1024, min_samples: 50 });
      await load();
    } catch (e) {
      console.error(e);
      alert("Training failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Brain size={24} className="text-[var(--accent-purple)]" />
            Training Runs
          </h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">Train RRCF models on MR data</p>
        </div>
        <div className="flex gap-3">
          <button onClick={load} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm transition-colors">
            <RefreshCw size={16} /> Refresh
          </button>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-purple)] text-white hover:bg-purple-600 transition-colors text-sm font-medium shadow-lg shadow-purple-500/20">
            <Play size={16} /> New Training
          </button>
        </div>
      </div>

      {loading ? <LoadingSpinner /> : (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Run ID</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Status</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Cells Trained</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Trees</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Tree Size</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase">Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.length > 0 ? runs.map((r) => (
                <tr key={r.id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                  <td className="px-5 py-4 text-sm font-mono font-medium text-white">{r.run_id}</td>
                  <td className="px-5 py-4"><StatusBadge status={r.status} /></td>
                  <td className="px-5 py-4 text-sm font-semibold text-[var(--accent-green)]">{r.total_cells_trained}</td>
                  <td className="px-5 py-4 text-sm text-[var(--text-secondary)]">{r.num_trees}</td>
                  <td className="px-5 py-4 text-sm text-[var(--text-secondary)]">{r.tree_size}</td>
                  <td className="px-5 py-4 text-sm text-[var(--text-secondary)]">{new Date(r.started_at).toLocaleString()}</td>
                </tr>
              )) : (
                <tr><td colSpan={6} className="text-center py-12 text-[var(--text-secondary)]">No training runs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-lg font-bold text-white mb-4">Trigger Training Run</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-[var(--text-secondary)] block mb-1">Training Data File *</label>
                <input type="text" value={formData.train_file} onChange={(e) => setFormData({ ...formData, train_file: e.target.value })} placeholder="e.g. demo_train.csv" className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-purple)]" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Num Trees</label>
                  <input type="number" value={formData.num_trees} onChange={(e) => setFormData({ ...formData, num_trees: parseInt(e.target.value) })} className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-purple)]" />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Tree Size</label>
                  <input type="number" value={formData.tree_size} onChange={(e) => setFormData({ ...formData, tree_size: parseInt(e.target.value) })} className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-purple)]" />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Min Samples</label>
                  <input type="number" value={formData.min_samples} onChange={(e) => setFormData({ ...formData, min_samples: parseInt(e.target.value) })} className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-purple)]" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="flex-1 px-4 py-2 rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm transition-colors">Cancel</button>
              <button onClick={handleTrigger} disabled={triggering || !formData.train_file} className="flex-1 px-4 py-2 rounded-lg bg-[var(--accent-purple)] text-white text-sm font-medium hover:bg-purple-600 disabled:opacity-50 transition-colors">
                {triggering ? "Training..." : "Start Training"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}