import { useEffect, useState, useCallback, useRef } from "react";
import { BrainCircuit, Upload, RefreshCw, CheckCircle2, Database } from "lucide-react";
import { axios, API, apiError } from "../../lib/api";

export function AdminModel({ notify, onChanged }) {
  const [versions, setVersions] = useState([]);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState("");
  const [notes, setNotes] = useState("Retrain after data update");
  const fileRef = useRef();

  const load = useCallback(async () => {
    const [v, h] = await Promise.all([axios.get(`${API}/admin/model/versions`), axios.get(`${API}/admin/model/history`)]);
    setVersions(v.data); setHistory(h.data);
  }, []);
  useEffect(() => { load().catch(e => notify(apiError(e), true)); }, [load, notify]);

  const run = async (key, fn, message) => {
    setBusy(key);
    try { const r = await fn(); await load(); onChanged(); notify(message(r.data)); } catch (e) { notify(apiError(e), true); }
    setBusy("");
  };
  const train = () => run("train", () => axios.post(`${API}/admin/model/train`, { notes }), d => `Trained ${d.version} · MAE ${d.mae} · RMSE ${d.rmse}`);
  const activate = v => run(v, () => axios.post(`${API}/admin/model/versions/${v}/activate`), () => `${v} is now the active model`);
  const regenerate = () => run("regen", () => axios.post(`${API}/admin/model/history/regenerate`), d => `Regenerated ${d.history_rows} synthetic rows`);
  const upload = e => {
    const file = e.target.files[0]; if (!file) return;
    const body = new FormData(); body.append("file", file);
    run("upload", () => axios.post(`${API}/admin/model/history/upload`, body), d => `Ingested ${d.rows} rows across ${d.series_replaced} series (${d.date_range[0]} → ${d.date_range[1]}). Retrain to use them.`);
    e.target.value = "";
  };
  const active = versions.find(v => v.active);

  return (
    <div className="admin-section model-grid">
      <div className="panel pad" data-testid="active-model-panel">
        <div className="subhead"><span><BrainCircuit size={12} /> ACTIVE MODEL</span><span>{active?.algorithm}</span></div>
        {active ? (
          <>
            <h3 className="big-mono" data-testid="active-model-version">{active.version}</h3>
            <div className="metric-row"><span><b>{active.mae}</b>MAE</span><span><b>{active.rmse}</b>RMSE</span><span><b>{active.mape}%</b>MAPE</span><span><b>{active.n_train}</b>train rows</span><span><b>{active.n_test}</b>test rows</span><span><b>{active.series}</b>series</span></div>
            <div className="subhead" style={{ marginTop: 18 }}>FEATURE IMPORTANCE</div>
            {Object.entries(active.importance).sort((a, b) => b[1] - a[1]).map(([f, v]) => <div className="factor" key={f}><span>{f}</span><b>{(v * 100).toFixed(1)}%</b><i><em style={{ width: `${v * 100}%`, background: "#62b4ff" }} /></i></div>)}
            <small className="hint">Hold-out: last 21 days of every series · params {JSON.stringify(active.params)}</small>
          </>
        ) : <p className="hint">No model trained yet.</p>}
        <label className="field" style={{ marginTop: 18 }}>Training notes<input data-testid="train-notes-input" value={notes} onChange={e => setNotes(e.target.value)} /></label>
        <button className="primary-btn" data-testid="retrain-button" onClick={train} disabled={!!busy}><RefreshCw size={14} className={busy === "train" ? "spin" : ""} /> {busy === "train" ? "Training…" : "Retrain model"}</button>
      </div>
      <div className="panel pad" data-testid="model-versions-panel">
        <div className="subhead">MODEL VERSIONS <span>{versions.length} STORED</span></div>
        {versions.map(v => (
          <div className="version-row" key={v.version} data-testid={`version-${v.version}`}>
            <div><b>{v.version}</b><small>{new Date(v.trained_at).toLocaleString()} · MAE {v.mae} · RMSE {v.rmse}</small><small>{v.notes}</small></div>
            {v.active ? <span className="status-pill normal"><CheckCircle2 size={10} /> ACTIVE</span> : <button className="outline-btn" data-testid={`activate-${v.version}`} onClick={() => activate(v.version)} disabled={!!busy}>Activate</button>}
          </div>
        ))}
      </div>
      <div className="panel pad" data-testid="training-data-panel">
        <div className="subhead"><span><Database size={12} /> TRAINING DATA</span><span>{history.reduce((a, h) => a + h.rows, 0)} ROWS</span></div>
        <p className="hint">Upload a CSV with columns <code>date,location_id,resource,quantity</code>. Resources: Fuel, Rations, Medical, Spares. Uploaded series replace synthetic ones for the same location/resource.</p>
        <div className="toolbar-actions">
          <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={upload} data-testid="csv-file-input" />
          <button className="outline-btn" data-testid="upload-csv-button" onClick={() => fileRef.current.click()} disabled={!!busy}><Upload size={13} /> {busy === "upload" ? "Uploading…" : "Upload CSV"}</button>
          <button className="outline-btn" data-testid="regenerate-history-button" onClick={regenerate} disabled={!!busy}><RefreshCw size={13} /> Regenerate synthetic</button>
        </div>
        <div className="table-panel" style={{ marginTop: 14 }}>
          <div className="table-head" style={{ gridTemplateColumns: "1.3fr 1fr 1fr .6fr 1.4fr" }}><span>LOCATION</span><span>RESOURCE</span><span>SOURCE</span><span>ROWS</span><span>RANGE</span></div>
          {history.map(h => <div className="table-row" key={`${h.location_id}-${h.resource}-${h.source}`} style={{ gridTemplateColumns: "1.3fr 1fr 1fr .6fr 1.4fr" }}><span>{h.location_id}</span><span>{h.resource}</span><span className={`status-pill ${h.source === "upload" ? "warning" : "normal"}`}>{h.source}</span><span>{h.rows}</span><span>{h.start} → {h.end}</span></div>)}
        </div>
      </div>
    </div>
  );
}
