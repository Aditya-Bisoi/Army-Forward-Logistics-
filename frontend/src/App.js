import { useCallback, useEffect, useState } from "react";
import { Bell, Check, ChevronRight, CircleAlert, Database, Gauge, GitBranch, LogOut, Menu, PlayCircle, Route, ShieldCheck, SlidersHorizontal, X } from "lucide-react";
import "@/App.css";
import { axios, API, TOKEN_KEY, saveSession, clearSession, apiError, colors } from "./lib/api";
import { NetworkMap } from "./components/NetworkMap";
import { ForecastPanel } from "./components/ForecastPanel";
import { ScenarioView } from "./components/ScenarioView";
import { InventoryView } from "./components/InventoryView";
import { OptimizerView } from "./components/OptimizerView";
import { AdminView } from "./components/admin/AdminView";
import { GuidedDemoBar } from "./components/GuidedDemo";
import { useGuidedDemo } from "./hooks/useGuidedDemo";

const NAV = [{ id: "overview", label: "Control tower", icon: Gauge }, { id: "scenarios", label: "Scenarios", icon: GitBranch }, { id: "optimizer", label: "Route optimizer", icon: Route }, { id: "inventory", label: "Inventory engine", icon: Database }, { id: "admin", label: "Admin console", icon: SlidersHorizontal }];
const KPIS = [["locations", "LOCATIONS", "#62b4ff", "monitored"], ["critical_locations", "CRITICAL LOCATIONS", "#ff5c57", "risk ≥ 70"], ["active_missions", "ACTIVE MISSIONS", "#f3c969", "in motion"], ["inventory_availability", "INVENTORY AVAILABILITY", "#4bd38a", "network mean", "%"], ["predicted_shortages", "PREDICTED SHORTAGES", "#ffb547", "next 7 days"], ["route_disruptions", "ROUTE DISRUPTIONS", "#ff5c57", "corridors blocked"]];
const FACTOR_LABELS = { inventory: "Inventory cover", transport: "Route reliability", weather: "Weather exposure", demand: "Demand trend" };

function Login({ onLogin }) {
  const [email, setEmail] = useState("admin@forwardlogistics.demo"), [password, setPassword] = useState("ControlTower2026!"), [error, setError] = useState("");
  const submit = async e => { e.preventDefault(); try { const { data } = await axios.post(`${API}/auth/login`, { email, password }); saveSession(data); onLogin(data); } catch (err) { setError(apiError(err)); } };
  return (
    <main className="login-shell">
      <div className="login-art"><div className="radar-grid" /><span className="eyebrow">SIH 2026 · PS26251</span><h1>Predictive<br /><em>Forward Logistics</em></h1><p>Decision support for the last mile of readiness.</p><div className="signal"><span className="pulse" />Synthetic twin online · Mongo-persisted digital twin · Random Forest forecasting</div></div>
      <form className="login-panel" onSubmit={submit}>
        <div className="brand-mark"><ShieldCheck size={18} /> CONTROL TOWER</div><h2>Mission access</h2><p className="muted">Sign in to the synthetic logistics environment.</p>
        <label>Email address<input data-testid="login-email-input" value={email} onChange={e => setEmail(e.target.value)} /></label>
        <label>Password<input data-testid="login-password-input" type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
        {error && <div data-testid="login-error" className="error-text">{error}</div>}
        <button data-testid="login-submit-button" className="primary-btn" type="submit">Enter control tower <ChevronRight size={16} /></button>
        <small>Demo environment · Human approval required for all recommendations</small>
      </form>
    </main>
  );
}

function Sparkline({ points, color }) {
  const max = Math.max(...points), min = Math.min(...points);
  const path = points.map((p, i) => `${(i * 100 / (points.length - 1)).toFixed(1)},${90 - (p - min) / (max - min || 1) * 70}`).join(" ");
  return <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="spark"><polyline points={path} fill="none" stroke={color} strokeWidth="2.5" /></svg>;
}

function Inspector({ selected, onClose }) {
  return (
    <aside className="inspector">
      <div className="section-head compact"><div><span className="eyebrow">TWIN INSPECTOR</span><h2>{selected?.name || "Select a node"}</h2></div><button data-testid="close-inspector-button" className="icon-btn" onClick={onClose}><X size={16} /></button></div>
      {selected && <>
        <div className="node-title"><span data-testid="selected-node-status" className={`status-pill ${selected.status.toLowerCase()}`}>{selected.status}</span><span className="node-type">{selected.type} · {selected.troops || "—"} PERSONNEL</span></div>
        <div className="inspector-grid">
          <div><small>INVENTORY</small><b data-testid="selected-node-inventory">{selected.inventory}%</b><div className="progress"><i style={{ width: `${selected.inventory}%`, background: colors[selected.status] }} /></div></div>
          <div><small>RISK SCORE</small><b data-testid="selected-node-risk" style={{ color: colors[selected.status] }}>{selected.risk}<em>/100</em></b><div className="progress"><i style={{ width: `${selected.risk}%`, background: colors[selected.status] }} /></div></div>
          <div><small>STOCK COVER</small><b>{selected.stock_days}<em> days</em></b></div>
          <div><small>FORECAST DEMAND</small><b>{selected.daily_demand}<em> L/day</em></b></div>
        </div>
        <div className="factor-list">
          <div className="subhead">RISK CONTRIBUTORS <span>WEIGHTED · TRANSPARENT</span></div>
          {Object.entries(selected.factors).map(([k, v]) => <div className="factor" key={k}><span>{FACTOR_LABELS[k]}</span><b>{v >= 60 ? "High" : v >= 35 ? "Medium" : "Low"} · {v}</b><i><em style={{ width: `${v}%` }} /></i></div>)}
        </div>
      </>}
    </aside>
  );
}

function Overview({ data, selected, setSelected, onOpenScenarios }) {
  const rec = data.recommendation;
  return <>
    <section className="question-strip">
      <div><span>01 · OBSERVE</span><b>What is happening?</b><small>Network health & live posture</small></div>
      <div><span>02 · PREDICT</span><b>What will happen?</b><small>Demand & shortage windows</small></div>
      <div><span>03 · EXPLAIN</span><b>Why will it happen?</b><small>Factors behind every score</small></div>
      <div className="question-active" role="button" onClick={onOpenScenarios} data-testid="question-act"><span>04 · ACT</span><b>What should we do?</b><small>Human-approved response plans</small><ChevronRight size={20} /></div>
    </section>
    <section className="kpi-grid">
      {KPIS.map(([key, label, color, delta, suffix]) => <div data-testid={`kpi-${key}`} className="kpi" key={key}><div className="kpi-top"><span>{label}</span><i style={{ background: color }} /></div><strong>{String(data.kpis[key]).padStart(2, "0")}{suffix || ""}</strong><small style={{ color }}>{delta}</small><Sparkline points={key === "inventory_availability" ? [55, 58, 57, 65, 63, 70, data.kpis[key]] : key === "critical_locations" ? [1, 1, 1, 0, 0, 1, data.kpis[key]] : [45, 47, 43, 52, 54, 57, 60]} color={color} /></div>)}
    </section>
    <section className="workspace">
      <div className="map-column">
        <div className="section-head"><div><span className="eyebrow">DIGITAL TWIN / GEOSPATIAL VIEW</span><h2>Forward network posture</h2></div><div className="map-tools"><span className="map-mode"><i /> TOP-{data.top_routes.length} CORRIDORS · {data.focus.name.toUpperCase()}</span></div></div>
        <NetworkMap locations={data.locations} routes={data.routes} topRoutes={data.top_routes} setSelected={setSelected} />
        <div className="map-foot"><span><b className="mono">{String(data.locations.length).padStart(2, "0")}</b> nodes monitored</span><span><b className="mono">{String(data.routes.filter(r => r.status !== "BLOCKED").length).padStart(2, "0")}</b> corridors open</span><span><b className="mono">{String(data.kpis.vehicles_available).padStart(2, "0")}</b> vehicles available</span></div>
      </div>
      <Inspector selected={selected} onClose={() => setSelected(null)} />
    </section>
    <section className="lower-grid">
      <ForecastPanel forecast={data.forecast} focus={data.focus} />
      <div className="alert-panel panel">
        <div className="section-head"><div><span className="eyebrow">PRIORITY QUEUE</span><h2>Attention required</h2></div><span className="queue-count">{String(data.alerts.length).padStart(2, "0")} OPEN</span></div>
        {data.alerts.map(a => <div data-testid={`alert-${a.id}`} className="alert-row" key={a.id} title={a.reason}><span className={`alert-icon ${a.severity.toLowerCase()}`}><CircleAlert size={15} /></span><div><b>{a.title}</b><small>{a.location} · {a.reason}</small></div><ChevronRight size={15} /></div>)}
      </div>
    </section>
    <section className="rec-strip" data-testid="dashboard-recommendation" onClick={onOpenScenarios} role="button">
      <div><span className="eyebrow">LIVE RECOMMENDATION · {rec.id} · {rec.priority}</span><b>{rec.action}</b><small>{rec.benefit} · {rec.risk}</small></div>
      <span className="approval-required">APPROVAL REQUIRED</span><ChevronRight size={18} />
    </section>
  </>;
}

export default function App() {
  const [user, setUser] = useState(null), [authChecked, setAuthChecked] = useState(false), [data, setData] = useState(null), [summary, setSummary] = useState(null);
  const [selected, setSelected] = useState(null), [tab, setTab] = useState("overview"), [scenario, setScenario] = useState("surge"), [sim, setSim] = useState(null), [running, setRunning] = useState(false), [toast, setToast] = useState(null);
  const notify = useCallback((text, error = false) => { setToast({ text, error }); setTimeout(() => setToast(null), 4000); }, []);

  const loadDashboard = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/dashboard`); setData(r.data);
      setSelected(prev => r.data.locations.find(l => l.id === (prev?.id || r.data.focus.id)) || null);
      if (r.data.user.role === "admin") axios.get(`${API}/admin/summary`).then(s => setSummary(s.data)).catch(() => {});
    } catch (e) { if (e?.response?.status === 401) { clearSession(); setUser(null); } else notify("Control tower data could not be loaded", true); }
  }, [notify]);

  useEffect(() => { if (!localStorage.getItem(TOKEN_KEY)) { setAuthChecked(true); return; } axios.get(`${API}/auth/me`).then(r => setUser(r.data)).catch(() => clearSession()).finally(() => setAuthChecked(true)); }, []);
  useEffect(() => { if (!user) { setData(null); setSim(null); setTab("overview"); return; } loadDashboard(); }, [user, loadDashboard]);

  const runScenario = useCallback(async id => {
    setRunning(true);
    try { const r = await axios.post(`${API}/simulation/disruption`, { scenario_id: id || scenario, severity: "HIGH", duration_hours: 24 }); setSim(r.data); notify("Scenario propagated across the digital twin"); } catch (e) { notify(apiError(e), true); }
    setRunning(false);
  }, [scenario, notify]);
  const demo = useGuidedDemo({ setTab, setScenario, runScenario });
  const approve = async decision => {
    if (!sim) return;
    try {
      await axios.post(`${API}/recommendations/${sim.recommendation.id}/decision`, { decision, recommendation: sim.recommendation, scenario_id: sim.scenario.id, before: sim.before, after: sim.after });
      notify(decision === "APPROVE" ? "Recommendation approved in simulation · logged to audit trail" : "Recommendation rejected · logged to audit trail");
      if (decision === "APPROVE") demo.onApproved();
    } catch (e) { notify(apiError(e), true); }
  };
  const logout = async () => { try { await axios.post(`${API}/auth/logout`); } catch {} clearSession(); setUser(null); };

  if (!authChecked) return <div className="loading">RESTORING SESSION<span className="loading-bar" /></div>;
  if (!user) return <Login onLogin={setUser} />;
  if (!data) return <div className="loading">INITIALIZING DIGITAL TWIN<span className="loading-bar" /></div>;
  const title = tab === "overview" ? "Logistics Intelligence Control Tower" : NAV.find(x => x.id === tab)?.label;

  return (
    <div className={demo.active ? "app-shell demo-active" : "app-shell"}>
      <aside className="sidebar">
        <div className="side-brand"><div className="crest"><ShieldCheck size={18} /></div><div><strong>FORWARD<br />LOGISTICS</strong><small>INTELLIGENCE OS</small></div></div>
        <div className="side-status"><span className="pulse" /> SYSTEM NOMINAL <b>v2.0.0</b></div>
        <nav>{NAV.map(n => <button data-testid={`nav-${n.id}-button`} key={n.id} className={tab === n.id ? "active" : ""} onClick={() => setTab(n.id)}><n.icon size={17} />{n.label}{n.id === "overview" && <span className="nav-count">{String(data.alerts.length).padStart(2, "0")}</span>}</button>)}</nav>
        <div className="side-bottom">
          <div className="user-chip"><div className="avatar">OA</div><div><b>Operations Admin</b><small>{user.role} access</small></div></div>
          <button data-testid="logout-button" className="logout" onClick={logout}><LogOut size={15} /> Exit session</button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="mobile-menu"><Menu size={18} /></div>
          <div><span className="eyebrow">NORTH SECTOR / SYNTHETIC OPERATIONS</span><h1>{title}</h1></div>
          <div className="top-actions">
            <button data-testid="guided-demo-button" className="demo-btn" onClick={demo.active ? demo.exit : demo.start}><PlayCircle size={15} /> {demo.active ? "Stop demo" : "Guided demo"}</button>
            <span className="live-badge"><i /> LIVE TWIN</span>
            <button data-testid="alerts-button" className="icon-btn" onClick={() => setTab("overview")}><Bell size={17} /><i className="notif" /></button>
            <span className="top-date">{new Date(data.last_updated).toUTCString().slice(5, 16).toUpperCase()}<br /><b>{new Date(data.last_updated).toUTCString().slice(17, 25)} UTC</b></span>
          </div>
        </header>
        {tab === "overview" && <Overview data={data} selected={selected} setSelected={setSelected} onOpenScenarios={() => setTab("scenarios")} />}
        {tab === "scenarios" && <ScenarioView scenario={scenario} setScenario={setScenario} run={() => runScenario()} sim={sim} approve={approve} running={running} demoWaiting={demo.waiting} />}
        {tab === "optimizer" && <OptimizerView data={data} notify={notify} />}
        {tab === "inventory" && <InventoryView locations={data.locations} />}
        {tab === "admin" && (user.role === "admin" ? <AdminView notify={notify} onChanged={loadDashboard} summary={summary} /> : <section className="data-page"><h2>Admin role required</h2></section>)}
      </main>
      <GuidedDemoBar demo={demo} data={data} sim={sim} />
      {toast && <div data-testid="toast-message" className={toast.error ? "toast toast-error" : "toast"}>{toast.error ? <CircleAlert size={16} /> : <Check size={16} />}{toast.text}</div>}
    </div>
  );
}
