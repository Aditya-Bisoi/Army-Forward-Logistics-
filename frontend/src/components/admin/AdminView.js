import { useState } from "react";
import { Database, BrainCircuit, SlidersHorizontal, ShieldCheck } from "lucide-react";
import { AdminEntities } from "./AdminEntities";
import { AdminModel } from "./AdminModel";
import { AdminWeights, AdminAudit } from "./AdminPanels";

const TABS = [["entities", "Data entities", Database], ["model", "Forecast model", BrainCircuit], ["weights", "Risk weights", SlidersHorizontal], ["audit", "Audit trail", ShieldCheck]];

export function AdminView({ notify, onChanged, summary }) {
  const [tab, setTab] = useState("entities");
  return (
    <section className="data-page" data-testid="admin-page">
      <span className="eyebrow">ADMIN CONSOLE / CONFIGURATION</span><h2>System configuration</h2>
      <p className="page-lede">Manage digital twin inputs, retrain the forecasting model, tune transparent risk weights, and review every human decision.</p>
      <div className="admin-stats">
        {summary && [["locations", summary.entities.locations], ["routes", summary.entities.routes], ["vehicles", summary.entities.vehicles], ["model", summary.model?.version || "—"], ["decisions", summary.decisions], ["history rows", summary.history_rows]].map(([k, v]) => <div key={k} data-testid={`admin-stat-${k.replace(" ", "-")}`}><small>{k.toUpperCase()}</small><b>{v}</b></div>)}
      </div>
      <div className="admin-tabs">{TABS.map(([id, label, I]) => <button key={id} data-testid={`admin-tab-${id}`} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><I size={14} /> {label}</button>)}</div>
      {tab === "entities" && <AdminEntities notify={notify} onChanged={onChanged} />}
      {tab === "model" && <AdminModel notify={notify} onChanged={onChanged} />}
      {tab === "weights" && <AdminWeights notify={notify} onChanged={onChanged} />}
      {tab === "audit" && <AdminAudit notify={notify} />}
    </section>
  );
}
