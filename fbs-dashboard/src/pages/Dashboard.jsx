import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, Server, Clock } from 'lucide-react';
import StatCard from '../components/StatCard';
import { getAllRuns } from '../api/api';

export default function Dashboard() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAllRuns()
      .then(res => setRuns(res.data.runs || []))
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, []);

  const totalRuns = runs.length;
  const totalAnomalies = runs.reduce((s, r) => s + (r.total_anomalies || 0), 0);
  const latestRun = runs.length > 0 ? runs[0] : null;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        🛡️ Fake Base Station Detection Dashboard
      </h1>

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard title="Total Runs"      value={totalRuns}      icon={Activity}       color="blue" />
        <StatCard title="Total Anomalies"  value={totalAnomalies} icon={AlertTriangle}  color="red" />
        <StatCard title="Cells Monitored"  value="798"            icon={Server}         color="green" />
        <StatCard title="Detection Model"  value="RRCF v4"        icon={Clock}          color="yellow" />
      </div>

      {/* ── Recent Runs ── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Detection Runs</h2>
          <Link to="/upload" className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg text-sm transition">
            + New Detection
          </Link>
        </div>

        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : runs.length === 0 ? (
          <p className="text-gray-500">No runs yet. Upload MR data to start.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-3">Run ID</th>
                <th className="text-left py-3">File</th>
                <th className="text-left py-3">Anomalies</th>
                <th className="text-left py-3">Status</th>
                <th className="text-left py-3">Date</th>
                <th className="text-left py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {runs.slice(0, 10).map(run => (
                <tr key={run.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-3 font-mono">#{run.id}</td>
                  <td className="py-3">{run.input_filename}</td>
                  <td className="py-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold
                      ${run.total_anomalies > 0
                        ? 'bg-red-900/40 text-red-400'
                        : 'bg-green-900/40 text-green-400'}`}>
                      {run.total_anomalies}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className="text-green-400">● {run.status}</span>
                  </td>
                  <td className="py-3 text-gray-400">{new Date(run.created_at).toLocaleString()}</td>
                  <td className="py-3">
                    <Link to={`/runs/${run.id}`}
                      className="text-blue-400 hover:text-blue-300 text-xs">
                      View Details →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}