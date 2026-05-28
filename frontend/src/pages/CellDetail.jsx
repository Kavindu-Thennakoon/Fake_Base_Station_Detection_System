import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Radio,
  ArrowLeft,
  Activity,
  Layers,
  Signal,
  ChevronRight,
} from "lucide-react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import LoadingSpinner from "../components/LoadingSpinner";
import { getCellModel, getCellProfile, getAnomalies } from "../services/api";

export default function CellDetail() {
  const { cellId } = useParams();
  const [model, setModel] = useState(null);
  const [profile, setProfile] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [m, p, a] = await Promise.all([
          getCellModel(cellId),
          getCellProfile(cellId).catch(() => ({ data: {} })),
          getAnomalies({ cell_id: cellId }),
        ]);
        setModel(m.data);
        setProfile(p.data);
        setAnomalies(a.data.results || a.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [cellId]);

  if (loading) return <LoadingSpinner />;

  const neighbors = model?.neighbor_stats || {};
  const neighborOrder = model?.neighbor_order || [];

  const radarData = neighborOrder.slice(0, 12).map((nid) => {
    const s = neighbors[nid] || {};
    return {
      neighbor: nid.split("_").pop(),
      rsrp: Math.abs(s.rsrp_mean || 0),
      rsrq: Math.abs(s.rsrq_mean || 0),
    };
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/cells"
          className="p-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-white transition"
        >
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Radio size={24} className="text-[var(--accent-green)]" />
            Cell {cellId}
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Trained model profile and anomaly history
          </p>
        </div>
      </div>

      {/* Baseline Stats */}
      {model && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <MiniStat label="Neighbors (K)" value={model.K} icon={Layers} />
          <MiniStat
            label="Mean CoDisp"
            value={model.mean_codisp?.toFixed(4)}
            icon={Activity}
          />
          <MiniStat
            label="Std CoDisp"
            value={model.std_codisp?.toFixed(4)}
            icon={Activity}
          />
          <MiniStat
            label="Training Rows"
            value={model.training_rows?.toLocaleString()}
            icon={Layers}
          />
          <MiniStat label="Trees" value={model.num_trees} icon={Layers} />
          <MiniStat label="Tree Size" value={model.tree_size} icon={Layers} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <Signal size={18} className="text-[var(--accent-blue)]" />
            Neighbor Signal Profile
          </h2>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis
                  dataKey="neighbor"
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                />
                <PolarRadiusAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                <Radar
                  name="|RSRP| (dBm)"
                  dataKey="rsrp"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.2}
                />
                <Radar
                  name="|RSRQ| (dB)"
                  dataKey="rsrq"
                  stroke="#22c55e"
                  fill="#22c55e"
                  fillOpacity={0.15}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    color: "#f1f5f9",
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-[var(--text-secondary)] text-sm py-10 text-center">
              No neighbor stats available.
            </p>
          )}
        </div>

        {/* Neighbor List */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
          <h2 className="text-base font-semibold text-white mb-4">
            Neighbor Baselines ({neighborOrder.length})
          </h2>
          <div className="space-y-1 max-h-[340px] overflow-y-auto">
            {neighborOrder.map((nid) => {
              const s = neighbors[nid] || {};
              return (
                <div
                  key={nid}
                  className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[var(--bg-card-hover)] transition"
                >
                  <span className="text-sm font-mono text-white">{nid}</span>
                  <div className="flex gap-4 text-xs text-[var(--text-secondary)]">
                    <span>
                      RSRP:{" "}
                      <span className="text-[var(--accent-blue)]">
                        {s.rsrp_mean?.toFixed(1) || "—"}
                      </span>{" "}
                      ±{s.rsrp_std?.toFixed(1) || "—"}
                    </span>
                    <span>
                      RSRQ:{" "}
                      <span className="text-[var(--accent-green)]">
                        {s.rsrq_mean?.toFixed(1) || "—"}
                      </span>{" "}
                      ±{s.rsrq_std?.toFixed(1) || "—"}
                    </span>
                  </div>
                </div>
              );
            })}
            {neighborOrder.length === 0 && (
              <p className="text-[var(--text-secondary)] text-sm text-center py-6">
                No neighbors in model.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Anomaly History */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white">
            Anomaly History ({anomalies.length})
          </h2>
        </div>
        {anomalies.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-color)]">
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] uppercase">
                    ID
                  </th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] uppercase">
                    CoDisp
                  </th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] uppercase">
                    Threshold
                  </th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] uppercase">
                    Method
                  </th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] uppercase">
                    Time
                  </th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {anomalies.slice(0, 20).map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-[var(--border-color)] hover:bg-[var(--bg-card-hover)] transition"
                  >
                    <td className="px-4 py-2 text-sm text-white">#{a.id}</td>
                    <td className="px-4 py-2 text-sm font-semibold text-[var(--accent-red)]">
                      {a.avg_codisp?.toFixed(3)}
                    </td>
                    <td className="px-4 py-2 text-sm text-[var(--text-secondary)]">
                      {a.threshold?.toFixed(3)}
                    </td>
                    <td className="px-4 py-2">
                      <MethodBadge method={a.detection_method} />
                    </td>
                    <td className="px-4 py-2 text-xs text-[var(--text-secondary)]">
                      {a.datetime_raw
                        ? new Date(a.datetime_raw).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-4 py-2">
                      <Link
                        to={`/anomalies/${a.id}`}
                        className="text-[var(--accent-purple)] hover:text-purple-300"
                      >
                        <ChevronRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-[var(--text-secondary)] text-sm text-center py-6">
            No anomalies detected for this cell.
          </p>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value, icon: Icon }) {
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className="text-[var(--text-secondary)]" />
        <span className="text-xs text-[var(--text-secondary)]">{label}</span>
      </div>
      <p className="text-lg font-bold text-white">{value}</p>
    </div>
  );
}

function MethodBadge({ method }) {
  const cls =
    method === "both"
      ? "bg-purple-500/20 text-purple-400"
      : method === "rrcf_only"
      ? "bg-blue-500/20 text-blue-400"
      : "bg-orange-500/20 text-orange-400";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {method?.replace("_", " ")}
    </span>
  );
}
