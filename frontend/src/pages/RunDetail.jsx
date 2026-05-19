import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AlertTriangle, Search } from 'lucide-react';
import { getRunSummary, getRunAnomalies, getNeighborRanked } from '../api/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function RunDetail() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [ranked, setRanked] = useState([]);

  useEffect(() => {
    getRunSummary(id).then(r => setSummary(r.data));
    getRunAnomalies(id).then(r => setAnomalies(r.data.anomalies || []));
    getNeighborRanked(id).then(r => setRanked(r.data.ranked_neighbors || []));
  }, [id]);

  const topRanked = ranked.slice(0, 15);

  return (
    <div>
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">
          🔍 Run #{id} — Detection Results
        </h1>
        <Link to={`/runs/${id}/explain`}
          className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition">
          <Search size={16} /> Explainability View
        </Link>
      </div>

      {/* ── Summary ── */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-400 uppercase">File</p>
            <p className="text-lg font-semibold mt-1">{summary.input_filename}</p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-400 uppercase">Anomalies Found</p>
            <p className={`text-3xl font-bold mt-1
              ${summary.total_anomalies > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {summary.total_anomalies}
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-400 uppercase">Status</p>
            <p className="text-lg font-semibold mt-1 text-green-400">{summary.status}</p>
          </div>
        </div>
      )}

      {/* ── Top Suspicious Neighbors Chart ── */}
      {topRanked.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">
            📊 Top Suspicious Neighbors (by Score)
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topRanked}>
              <XAxis dataKey="neighbor_id" tick={{ fill: '#9ca3af', fontSize: 11 }} angle={-45} textAnchor="end" height={80} />
              <YAxis tick={{ fill: '#9ca3af' }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }}
                labelStyle={{ color: '#f9fafb' }} />
              <Bar dataKey="sum_score" radius={[4, 4, 0, 0]}>
                {topRanked.map((_, i) => (
                  <Cell key={i} fill={i < 3 ? '#ef4444' : i < 7 ? '#f59e0b' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Anomaly Table ── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle size={18} className="text-red-400" />
          Anomalous Records
        </h2>

        {anomalies.length === 0 ? (
          <p className="text-gray-500">No anomalies detected in this run ✅</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-3">Serving Cell</th>
                  <th className="text-left py-3">Timestamp</th>
                  <th className="text-left py-3">CoDisp Score</th>
                  <th className="text-left py-3">Threshold</th>
                  <th className="text-left py-3">RRCF Flag</th>
                  <th className="text-left py-3">Z-Score Flag</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((row, i) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 font-mono">{row.serving_cell_id}</td>
                    <td className="py-2 text-gray-400">{row.datetime_raw}</td>
                    <td className="py-2 text-yellow-400">{Number(row.avg_codisp).toFixed(3)}</td>
                    <td className="py-2 text-gray-400">{Number(row.threshold).toFixed(3)}</td>
                    <td className="py-2">
                      {row.rrcf_flagged === 'True' || row.rrcf_flagged === true
                        ? <span className="text-red-400 font-bold">⚠ YES</span>
                        : <span className="text-green-500">No</span>}
                    </td>
                    <td className="py-2">
                      {row.zscore_flagged === 'True' || row.zscore_flagged === true
                        ? <span className="text-red-400 font-bold">⚠ YES</span>
                        : <span className="text-green-500">No</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}