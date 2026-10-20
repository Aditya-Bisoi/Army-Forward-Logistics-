import { useState } from "react";
import { X } from "lucide-react";

export const FIELDS = {
  locations: [
    ["id", "ID (optional)", "text"], ["name", "Name", "text"], ["type", "Type", "select", ["DEPOT", "HUB", "FORWARD"]], ["lat", "Latitude", "number"], ["lng", "Longitude", "number"], ["troops", "Personnel", "number"], ["capacity", "Capacity (L)", "number"], ["inventory", "Inventory %", "number"],
    ["weather_exposure", "Weather exposure 0-100", "number"], ["demand_trend", "Demand trend 0-100", "number"], ["fuel_base", "Baseline fuel demand L/day", "number"],
  ],
  routes: [
    ["id", "ID (optional)", "text"], ["name", "Name (e.g. Route G / Pass Name)", "text"], ["source", "Source", "location"], ["destination", "Destination", "location"], ["distance", "Distance (km)", "number"], ["hours", "Transit hours", "number"], ["status", "Status", "select", ["AVAILABLE", "BLOCKED", "DEGRADED"]],
    ["reliability", "Reliability %", "number"], ["risk", "Risk %", "number"], ["capacity", "Capacity (L per convoy)", "number"], ["weather_exposed", "Weather exposed", "checkbox"],
  ],
  vehicles: [["id", "ID (optional)", "text"], ["name", "Name", "text"], ["type", "Type", "select", ["Fuel Tanker", "Cargo Truck", "Light Utility"]], ["capacity", "Capacity (L)", "number"], ["status", "Status", "select", ["AVAILABLE", "IN_TRANSIT", "MAINTENANCE"]], ["base", "Base location", "location"]],
};

const DEFAULTS = {
  locations: { type: "FORWARD", lat: 34.3, lng: 77.7, troops: 300, capacity: 3000, inventory: 60, weather_exposure: 40, demand_trend: 40, fuel_base: 150 },
  routes: { status: "AVAILABLE", distance: 25, hours: 6, reliability: 85, risk: 25, capacity: 2000, weather_exposed: false },
  vehicles: { type: "Cargo Truck", capacity: 800, status: "AVAILABLE" },
};

export function EntityForm({ entity, item, locations, onSave, onClose, saving }) {
  const [form, setForm] = useState(item || { ...DEFAULTS[entity], source: locations[0]?.id, destination: locations[1]?.id, base: locations[0]?.id });
  const [error, setError] = useState("");
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = async e => {
    e.preventDefault(); setError("");
    const payload = Object.fromEntries(FIELDS[entity].map(([k, , type]) => [k, type === "number" ? Number(form[k]) : form[k]]).filter(([k, v]) => !(k === "id" && !v)));
    try { await onSave(payload); } catch (err) { setError(err); }
  };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal" data-testid="entity-form" onClick={e => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-head"><h3>{item ? "Edit" : "Add"} {entity.slice(0, -1)}</h3><button type="button" className="icon-btn" data-testid="entity-form-close" onClick={onClose}><X size={15} /></button></div>
        <div className="form-grid">
          {FIELDS[entity].map(([k, label, type, options]) => (
            <label className="field" key={k}>{label}
              {type === "select" && <select data-testid={`field-${k}`} value={form[k] ?? ""} onChange={e => set(k, e.target.value)}>{options.map(o => <option key={o}>{o}</option>)}</select>}
              {type === "location" && <select data-testid={`field-${k}`} value={form[k] ?? ""} onChange={e => set(k, e.target.value)}>{locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select>}
              {type === "checkbox" && <span className="check-row"><input data-testid={`field-${k}`} type="checkbox" checked={!!form[k]} onChange={e => set(k, e.target.checked)} /> Exposed to weather delays</span>}
              {(type === "text" || type === "number") && <input data-testid={`field-${k}`} type={type} step="any" value={form[k] ?? ""} disabled={k === "id" && !!item} onChange={e => set(k, e.target.value)} required={k !== "id"} />}
            </label>
          ))}
        </div>
        {error && <div className="error-text" data-testid="entity-form-error">{error}</div>}
        <div className="decision-row"><button className="approve-btn" type="submit" data-testid="entity-form-submit" disabled={saving}>{saving ? "Saving…" : "Save"}</button><button type="button" className="reject-btn" onClick={onClose}>Cancel</button></div>
      </form>
    </div>
  );
}
