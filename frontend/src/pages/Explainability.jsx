import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getNeighborDetail } from '../api/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts';

export default function Explainability() {
  const { id } = useParams();
  const [details, setDetails] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    getNeighborDetail(id).then(r => {
      const d = r.data.neighbor_details || [];
      setDetails(d);
      if (d.length > 0) setSelected(d[0].neighbor_id);
    });
  }, [id]);

  // Group by neighbor
  const grouped = {};
  details.forEach(d => {
    if (!grouped[d.neighbor_id]) grouped[d.neighbor_id] = [];
    grouped[d.neighbor_id].push(d);
  });

  const neighborIds = Object.keys(grouped);
  const selectedData = selected ? (grouped[selected] || []) : [];

  // Chart: z-score breakdown
  const chartData = selectedData.slice(0, 30).map((d, i) => ({
    name: `MR-${i + 1}`,
    rsrp_z: Number(d.rsrp_z) || 0,
    rsrq_z: Number(d.rsrq_z) || 0,
    score:  Number(d.anomaly_score) || 0,
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">🧠 Explainability — Run #{id}</h1>
      <p className="text-gray-400 text-sm mb-6">
        Understand <strong>WHY</strong> each neighbor was flagged as suspicious
      </p>

      {details.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center">
          <p className="text-gray-500 text-lg">No neighbor anomalies to explain ✅</p>
          <p className="text-gray-600 text-sm mt-2">All neighbors behaved within normal thresholds</p>
        </div>
      ) : (
        <div className="grid grid-cols-12 gap-4">

          {/* ── Left: Neighbor List ── */}
          <div className="col-span-3 bg-gray-900 border border-gray-800 rounded-xl p-4 max-h-[600px] overflow-y-auto">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">
              Suspicious Neighbors ({neighborIds.length})
            </h3>
            {neighborIds.map(nid => (
              <button key={nid}
                onClick={() => setSelected(nid)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition
                  ${selected === nid
                    ? 'bg-red-600/20 text-red-400 border border-red-800'
                    : 'text-gray-400 hover:bg-gray-800'}`}>
                🗼 {nid}
                <span className="ml-2 text-xs text-gray-500">
                  ({grouped[nid].length} hits)
                </span>
              </button>
            ))}
          </div>

          {/* ── Right: Detail Panel ── */}
          <div className="col-span-9 space-y-4">

            {/* ── Z-Score Chart ── */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">
                📊 Z-Score Breakdown — Neighbor {selected}
              </h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#9ca3af' }} />
                  <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }} />
                  <Legend />
                  <Bar dataKey="rsrp_z" name="RSRP Z-Score" fill="#ef4444" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="rsrq_z" name="RSRQ Z-Score" fill="#f59e0b" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* ── Detail Table ── */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">📋 Raw Measurements</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-800">
                      <th className="text-left py-2">Serving Cell</th>
                      <th className="text-left py-2">RSRP</th>
                      <th className="text-left py-2">RSRQ</th>
                      <th className="text-left py-2">RSRP Z</th>
                      <th className="text-left py-2">RSRQ Z</th>
                      <th className="text-left py-2">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedData.slice(0, 50).map((d, i) => (
                      <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="py-2 font-mono">{d.serving_cell_id}</td>
                        <td className="py-2">{d.rsrp ?? '—'}</td>
                        <td className="py-2">{d.rsrq ?? '—'}</td>
                        <td className="py-2 text-red-400">{Number(d.rsrp_z).toFixed(2)}</td>
                        <td className="py-2 text-yellow-400">{Number(d.rsrq_z).toFixed(2)}</td>
                        <td className="py-2">
                          <span className={`px-2 py-1 rounded text-xs font-bold
                            ${Number(d.anomaly_score) > 4
                              ? 'bg-red-900/40 text-red-400'
                              : 'bg-yellow-900/40 text-yellow-400'}`}>
                            {Number(d.anomaly_score).toFixed(2)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}