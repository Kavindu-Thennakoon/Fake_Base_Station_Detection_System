import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { useEffect } from "react";

const RISK_COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
  normal: "#22c55e",
};

const RISK_RADIUS = {
  critical: 14,
  high: 11,
  medium: 9,
  low: 7,
  normal: 6,
};

function FitBounds({ cells }) {
  const map = useMap();
  useEffect(() => {
    if (cells.length === 0) return;
    const lats = cells.map((c) => c.latitude);
    const lons = cells.map((c) => c.longitude);
    map.fitBounds(
      [
        [Math.min(...lats) - 0.01, Math.min(...lons) - 0.01],
        [Math.max(...lats) + 0.01, Math.max(...lons) + 0.01],
      ],
      { padding: [30, 30] }
    );
  }, [cells, map]);
  return null;
}

export default function MapView({ cells, onCellClick }) {
  return (
    <MapContainer
      center={[6.9, 79.88]}
      zoom={12}
      className="w-full h-full rounded-xl"
      style={{ minHeight: "500px", background: "#0f172a" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <FitBounds cells={cells} />
      {cells.map((cell) => (
        <CircleMarker
          key={cell.cell_id}
          center={[cell.latitude, cell.longitude]}
          radius={RISK_RADIUS[cell.risk_level] || 6}
          pathOptions={{
            color: RISK_COLORS[cell.risk_level] || "#22c55e",
            fillColor: RISK_COLORS[cell.risk_level] || "#22c55e",
            fillOpacity: 0.7,
            weight: 2,
          }}
          eventHandlers={{
            click: () => onCellClick?.(cell),
          }}
        >
          <Popup>
            <div className="text-xs space-y-1 min-w-[200px]">
              <p className="font-bold text-sm">{cell.cell_name || cell.cell_id}</p>
              <p>
                <span className="text-gray-500">Cell ID:</span> {cell.cell_id}
              </p>
              <p>
                <span className="text-gray-500">Technology:</span> {cell.technology}
                {cell.band && ` — ${cell.band}`}
              </p>
              <p>
                <span className="text-gray-500">Anomalies:</span>{" "}
                <span className="font-semibold">{cell.anomaly_count}</span>
              </p>
              <p>
                <span className="text-gray-500">Suspicion Score:</span>{" "}
                <span className="font-semibold">{cell.suspicion_score}</span>
              </p>
              <p>
                <span className="text-gray-500">Risk:</span>{" "}
                <span
                  className="font-bold uppercase"
                  style={{ color: RISK_COLORS[cell.risk_level] }}
                >
                  {cell.risk_level}
                </span>
              </p>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
