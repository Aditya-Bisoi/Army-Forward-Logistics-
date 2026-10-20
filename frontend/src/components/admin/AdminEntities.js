import { useEffect, useState, useCallback } from "react";
import { Pencil, Plus, Trash2, RotateCcw } from "lucide-react";
import { axios, API, apiError } from "../../lib/api";
import { EntityForm } from "./EntityForm";

const COLUMNS = {
  locations: [["name", "Name"], ["type", "Type"], ["inventory", "Inv %"], ["capacity", "Capacity"], ["troops", "Personnel"], ["weather_exposure", "Weather"], ["demand_trend", "Demand"]],
  routes: [["name", "Name"], ["source", "From"], ["destination", "To"], ["hours", "Hours"], ["risk", "Risk"], ["capacity", "Capacity"], ["status", "Status"]],
  vehicles: [["name", "Name"], ["type", "Type"], ["capacity", "Capacity"], ["base", "Base"], ["status", "Status"]],
};

export function AdminEntities({ notify, onChanged }) {
  const [entity, setEntity] = useState("locations");
  const [rows, setRows] = useState([]);
  const [locations, setLocations] = useState([]);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [r, l] = await Promise.all([axios.get(`${API}/admin/${entity}`), axios.get(`${API}/admin/locations`)]);
    setRows(r.data); setLocations(l.data);
  }, [entity]);
  useEffect(() => { load().catch(e => notify(apiError(e), true)); }, [load, notify]);

  const save = async payload => {
    setSaving(true);
    try {
      if (editing?.id) await axios.put(`${API}/admin/${entity}/${editing.id}`, payload); else await axios.post(`${API}/admin/${entity}`, payload);
      setEditing(null); await load(); onChanged(); notify(`${entity.slice(0, -1)} saved`);
    } catch (e) { setSaving(false); throw apiError(e); }
    setSaving(false);
  };
  const remove = async row => {
    if (!window.confirm(`Delete ${row.name}? Linked records will be removed too.`)) return;
    try { await axios.delete(`${API}/admin/${entity}/${row.id}`); await load(); onChanged(); notify(`${row.name} deleted`); } catch (e) { notify(apiError(e), true); }
  };
  const reset = async () => {
    if (!window.confirm("Reset the digital twin to the seeded synthetic dataset? Custom entities and uploaded history will be discarded.")) return;
    try { await axios.post(`${API}/admin/twin/reset`); await load(); onChanged(); notify("Digital twin reset to seed data"); } catch (e) { notify(apiError(e), true); }
  };

  return (
    <div className="admin-section">
      <div className="admin-toolbar">
        <div className="pill-tabs">{Object.keys(COLUMNS).map(k => <button key={k} data-testid={`entity-tab-${k}`} className={entity === k ? "active" : ""} onClick={() => setEntity(k)}>{k} <b>{k === entity ? rows.length : ""}</b></button>)}</div>
        <div className="toolbar-actions"><button className="outline-btn" data-testid="reset-twin-button" onClick={reset}><RotateCcw size={13} /> Reset to seed</button><button className="primary-btn" data-testid="add-entity-button" onClick={() => setEditing({})}><Plus size={14} /> Add {entity.slice(0, -1)}</button></div>
      </div>
      <div className="table-panel admin-table" data-testid={`admin-table-${entity}`}>
        <div className="table-head" style={{ gridTemplateColumns: `repeat(${COLUMNS[entity].length}, 1fr) 90px` }}>{COLUMNS[entity].map(([k, label]) => <span key={k}>{label.toUpperCase()}</span>)}<span>ACTIONS</span></div>
        {rows.map(row => (
          <div className="table-row" key={row.id} data-testid={`admin-row-${row.id}`} style={{ gridTemplateColumns: `repeat(${COLUMNS[entity].length}, 1fr) 90px` }}>
            {COLUMNS[entity].map(([k]) => <span key={k}>{k === "status" ? <span className={`status-pill ${row[k] === "BLOCKED" || row[k] === "MAINTENANCE" ? "critical" : row[k] === "AVAILABLE" ? "normal" : "warning"}`}>{row[k]}</span> : String(row[k] ?? "")}</span>)}
            <span className="row-actions"><button className="icon-btn" data-testid={`edit-${row.id}`} onClick={() => setEditing(row)}><Pencil size={13} /></button><button className="icon-btn danger" data-testid={`delete-${row.id}`} onClick={() => remove(row)}><Trash2 size={13} /></button></span>
          </div>
        ))}
        {!rows.length && <div className="table-row"><span>No records</span></div>}
      </div>
      {editing && <EntityForm entity={entity} item={editing.id ? editing : null} locations={locations} onSave={save} onClose={() => setEditing(null)} saving={saving} />}
    </div>
  );
}
