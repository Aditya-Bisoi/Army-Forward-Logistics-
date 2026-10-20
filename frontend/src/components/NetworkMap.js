import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Layers3 } from "lucide-react";
import { colors } from "../lib/api";

const iconFor = (status, type) => L.divIcon({ className: "map-marker", html: `<span style="--marker:${colors[status] || colors[type]}"><i></i></span>`, iconSize: [28, 28], iconAnchor: [14, 14] });

function FitBounds({ locations }) {
  const map = useMap();
  const key = locations.map(l => l.id).join(",");
  useEffect(() => {
    if (locations.length > 1) map.fitBounds(locations.map(l => [l.lat, l.lng]), { padding: [40, 40] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, map]);
  return null;
}

export function NetworkMap({ locations, routes, topRoutes = [], setSelected, label = "LIVE DIGITAL TWIN", height }) {
  const coords = Object.fromEntries(locations.map(x => [x.id, [x.lat, x.lng]]));
  return (
    <div className="map-frame" style={height ? { height } : undefined}>
      <MapContainer center={[34.27, 77.67]} zoom={10} scrollWheelZoom={false} zoomControl={false}>
        <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <FitBounds locations={locations} />
        {routes.filter(r => coords[r.source] && coords[r.destination]).map(r => (
          <Polyline key={r.id} positions={[coords[r.source], coords[r.destination]]} pathOptions={{ color: r.status === "BLOCKED" ? "#ff5c57" : "#8fa49a", weight: r.status === "BLOCKED" ? 3 : 2, dashArray: r.status === "BLOCKED" ? "6 8" : undefined, opacity: 0.75 }}>
            <Popup><b>{r.name}</b><br />{r.status} · {r.hours}h · {r.risk}% risk<br />Capacity {r.capacity} units</Popup>
          </Polyline>
        ))}
        {[...topRoutes].reverse().map(c => (
          <Polyline key={`top-${c.rank}`} positions={c.coords} pathOptions={{ color: c.color, weight: 7 - c.rank, opacity: 0.95 }}>
            <Popup><b>#{c.rank} {c.label}</b><br />{c.path_names.join(" → ")}<br />Score {c.score} · ETA {c.eta}</Popup>
          </Polyline>
        ))}
        {locations.map(l => (
          <Marker key={l.id} position={[l.lat, l.lng]} icon={iconFor(l.status, l.type)} eventHandlers={{ click: () => setSelected?.(l) }}>
            <Popup><b>{l.name}</b><br />{l.type} · {l.risk}% risk<br />{l.inventory}% inventory</Popup>
          </Marker>
        ))}
      </MapContainer>
      <div className="map-legend">
        <span><i className="dot green" /> Normal</span><span><i className="dot amber" /> Warning</span><span><i className="dot red" /> Critical</span>
        {topRoutes.length > 0 && <span><i className="dot" style={{ background: "#f3c969" }} /> Top corridor</span>}
      </div>
      <div className="map-label"><Layers3 size={14} /> {label} <b>·</b> SYNTHETIC DATA</div>
    </div>
  );
}
