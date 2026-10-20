import { useEffect, useState, useCallback } from "react";
import { SlidersHorizontal, ShieldCheck } from "lucide-react";
import { axios, API, apiError } from "../../lib/api";

const KEYS = [["inventory", "Inventory cover", "100 − inventory %"], ["transport", "Transport reliability", "mean risk of connected routes"], ["weather", "Weather exposure", "location exposure index"], ["demand", "Demand trend", "forecast demand pressure"]];

export function AdminWeights({ notify, onChanged }) {
  const [weights, setWeights] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { axios.get(`${API}/admin/weights`).then(r => setWeights(Object.fromEntries(Object.entries(r.data).map(([k, v]) => [k, Math.round(v * 100)])))).catch(e => notify(apiError(e), true)); }, [notify]);
  const total = weights ? Object.values(weights).reduce((a, b) => a + b, 0) : 0;
  const save = async () => {
    setSaving(true);
    try { await axios.put(`${API}/admin/weights`, Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, v / 100]))); onChanged(); notify("Risk weights updated — twin recalculated"); } catch (e) { notify(apiError(e), true); }
    setSaving(false);
  };
  if (!weights) return null;
  return (
    <div className="admin-section panel pad" data-testid="weights-panel" style={{ maxWidth: 620 }}>
      <div className="subhead"><span><SlidersHorizontal size={12} /> TRANSPARENT RISK SCORE</span><span data-testid="weights-total" style={{ color: total === 100 ? "#4bd38a" : "#ff5c57" }}>TOTAL {total}%</span></div>
      <p className="hint">Location risk = Σ weight × factor. Status thresholds: CRITICAL ≥ 70, WARNING ≥ 45. Changing weights immediately re-scores every node on the map.</p>
      {KEYS.map(([k, label, desc]) => (
        <div className="slider-row" key={k}>
          <div><span>{label} <small className="hint">· {desc}</small></span><b data-testid={`weight-${k}-value`}>{weights[k]}%</b></div>
          <input data-testid={`weight-${k}-slider`} type="range" min="0" max="100" step="5" value={weights[k]} onChange={e => setWeights({ ...weights, [k]: Number(e.target.value) })} />
        </div>
      ))}
      <button className="primary-btn" data-testid="save-weights-button" onClick={save} disabled={saving || total !== 100}><ShieldCheck size={14} /> {total !== 100 ? "Weights must total 100%" : saving ? "Saving…" : "Save weights"}</button>
    </div>
  );
}

export function AdminAudit({ notify }) {
  const [rows, setRows] = useState([]);
  const load = useCallback(() => axios.get(`${API}/audit`).then(r => setRows(r.data)).catch(e => notify(apiError(e), true)), [notify]);
  useEffect(() => { load(); }, [load]);
  return (
    <div className="admin-section table-panel" data-testid="audit-table">
      <div className="table-head" style={{ gridTemplateColumns: "1.4fr 1fr .8fr 2fr 1fr 1.2fr" }}><span>TIME</span><span>RECOMMENDATION</span><span>DECISION</span><span>ACTION</span><span>IMPACT</span><span>USER</span></div>
      {rows.map(r => (
        <div className="table-row" key={r.id} style={{ gridTemplateColumns: "1.4fr 1fr .8fr 2fr 1fr 1.2fr" }} data-testid={`audit-row-${r.id}`}>
          <span>{new Date(r.timestamp).toLocaleString()}</span><span>{r.recommendation_id}</span><span className={`status-pill ${r.decision === "REJECT" ? "critical" : "normal"}`}>{r.decision}</span><span>{r.action || `${r.quantity} units`}</span>
          <span>{r.before?.stockout_probability != null ? `${r.before.stockout_probability}% → ${r.decision === "REJECT" ? r.before.stockout_probability : r.after?.stockout_probability}%` : "—"}</span><span>{r.user}</span>
        </div>
      ))}
      {!rows.length && <div className="table-row"><span>No decisions recorded yet</span></div>}
    </div>
  );
}
