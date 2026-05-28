import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Play, RefreshCw, Search, ChevronRight } from "lucide-react";
import StatusBadge from "../components/StatusBadge";
import LoadingSpinner from "../components/LoadingSpinner";
import FileUpload from "../components/FileUpload";
import { getDetectionRuns, triggerDetection } from "../services/api";

export default function DetectionRuns() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    check_file: "",
    threshold_mult: 1.0,
    z_threshold: 2.0,
    min_anomaly_score: 4.0,
  });

  const load = async () => {
    setLoading(true);
    try {
      const res = await getDetectionRuns();
      setRuns(res.data.results || res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleTrigger = async () => {
    if (!formData.check_file) return;
    setTriggering(true);
    try {
      await triggerDetection(formData);
      setShowModal(false);
      setFormData({ check_file: "", threshold_mult: 1.0, z_threshold: 2.0, min_anomaly_score: 4.0 });
      await load();
    } catch (e) {
      console.error(e);
      alert("Detection failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Detection Runs</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">
            Manage and monitor FBS detection pipeline executions
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={load}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-card-hover)] transition-colors text-sm"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-blue)] text-white hover:bg-blue-600 transition-colors text-sm font-medium shadow-lg shadow-blue-500/20"
          >
            <Play size={16} />
            New Detection
          </button>
        </div>
      </div>

      {/* Runs Table */}
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Run ID</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Anomalies</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Alerts</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Duration</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">Started</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {runs.length > 0 ? (
                runs.map((run) => (
                  <tr key={run.id} className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition-colors">
                    <td className="px-5 py-4">
                      <span className="text-sm font-mono font-medium text-white">{run.run_id}</span>
                    </td>
                    <td className="px-5 py-4"><StatusBadge status={run.status} /></td>
                    <td className="px-5 py-4 text-sm font-semibold text-[var(--accent-red)]">{run.anomaly_count}</td>
                    <td className="px-5 py-4 text-sm font-semibold text-[var(--accent-yellow)]">{run.alert_count}</td>
                    <td className="px-5 py-4 text-sm text-[var(--text-secondary)]">
                      {run.duration_seconds ? `${run.duration_seconds.toFixed(2)}s` : "—"}
                    </td>
                    <td className="px-5 py-4 text-sm text-[var(--text-secondary)]">
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-4">
                      <Link
                        to={`/detection/${run.id}`}
                        className="text-[var(--accent-blue)] hover:text-blue-300 transition-colors"
                      >
                        <ChevronRight size={18} />
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-[var(--text-secondary)]">
                    No detection runs yet. Click "New Detection" to start.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Trigger Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-lg font-bold text-white mb-4">Trigger Detection Run</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-[var(--text-secondary)] block mb-1.5">MR Data File *</label>
                <FileUpload
                  accentColor="var(--accent-blue)"
                  onUploaded={(data) =>
                    setFormData({ ...formData, check_file: data?.file_path || "" })
                  }
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Threshold Mult</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.threshold_mult}
                    onChange={(e) => setFormData({ ...formData, threshold_mult: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-blue)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Z Threshold</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.z_threshold}
                    onChange={(e) => setFormData({ ...formData, z_threshold: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-blue)]"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Min Score</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.min_anomaly_score}
                    onChange={(e) => setFormData({ ...formData, min_anomaly_score: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)] text-white text-sm focus:outline-none focus:border-[var(--accent-blue)]"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleTrigger}
                disabled={triggering || !formData.check_file}
                className="flex-1 px-4 py-2 rounded-lg bg-[var(--accent-blue)] text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
              >
                {triggering ? "Running..." : "Start Detection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}