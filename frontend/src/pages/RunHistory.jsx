import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAllRuns } from '../api/api';

export default function RunHistory() {
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    getAllRuns().then(r => setRuns(r.data.runs || []));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">📜 Detection History</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        {runs.length === 0 ? (
          <p className="text-gray-500">No detection runs yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-3">ID</th>
                <th className="text-left py-3">File</th>
                <th className="text-left py-3">Anomalies</th>
                <th className="text-left py-3">Status</th>
                <th className="text-left py-3">Date</th>
                <th className="text-left py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
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
                  <td className="py-3 text-green-400">● {run.status}</td>
                  <td className="py-3 text-gray-400">{new Date(run.created_at).toLocaleString()}</td>
                  <td className="py-3 space-x-2">
                    <Link to={`/runs/${run.id}`} className="text-blue-400 hover:text-blue-300 text-xs">
                      Details
                    </Link>
                    <Link to={`/runs/${run.id}/explain`} className="text-purple-400 hover:text-purple-300 text-xs">
                      Explain
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