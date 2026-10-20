import { useEffect, useRef } from "react";
import { BrainCircuit, Check, ChevronRight, CircleAlert, GitBranch, Play, Truck, X, Zap } from "lucide-react";

const OPTIONS = [
  { id: "surge", name: "Sudden Demand Surge", meta: "+42% fuel consumption · focus location", icon: Zap },
  { id: "blocked", name: "Primary Route Blocked", meta: "Best corridor into focus location closed", icon: GitBranch },
  { id: "weather", name: "Severe Weather", meta: "+6h transit time · all exposed routes", icon: CircleAlert },
  { id: "vehicle", name: "Vehicle Failure", meta: "Vehicle 04 offline · fleet capacity loss", icon: Truck },
];

export function ScenarioView({ scenario, setScenario, run, sim, approve, running, demoWaiting }) {
  const rec = sim?.recommendation;
  const approveRef = useRef();
  useEffect(() => { if (demoWaiting) approveRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }); }, [demoWaiting]);
  return (
    <section className="scenario-page">
      <div className="scenario-intro"><span className="eyebrow">SIMULATION LAB / WHAT-IF ENGINE</span><h2>Stress the twin.<br /><em>See what changes.</em></h2><p>Inject a disruption into the synthetic network, then compare the recommended response before any human decision is made.</p></div>
      <div className="scenario-layout">
        <div className="scenario-list">
          <div className="subhead">SCENARIO LIBRARY <span>04 AVAILABLE</span></div>
          {OPTIONS.map(o => (
            <button data-testid={`scenario-${o.id}-button`} className={scenario === o.id ? "scenario-card selected" : "scenario-card"} key={o.id} onClick={() => setScenario(o.id)}>
              <span className="scenario-icon"><o.icon size={17} /></span><span><b>{o.name}</b><small>{o.meta}</small></span><ChevronRight size={16} />
            </button>
          ))}
          <button data-testid="run-scenario-button" className="primary-btn run-btn" onClick={run} disabled={running}><Play size={15} fill="currentColor" /> {running ? "Propagating…" : "Activate scenario"}</button>
        </div>
        <div className="simulation-result">
          {!sim ? (
            <div className="empty-sim"><div className="orbit"><GitBranch size={24} /></div><h3>Ready to simulate</h3><p>Select a scenario to propagate its effects across inventory, routes, risk, and recommendations.</p></div>
          ) : (
            <>
              <div className="result-head"><div><span className="eyebrow">SCENARIO COMPLETE · {sim.focus.name.toUpperCase()}</span><h2>{sim.scenario.name}</h2></div><span className="status-pill critical">PROPAGATED</span></div>
              <div className="compare-grid">
                <div data-testid="impact-before" className="compare before"><span>BEFORE INTERVENTION</span><strong>{sim.before.stockout_probability}%</strong><small>Stockout probability · 7 days</small><b>{sim.before.risk} RISK</b><i>{sim.before.delivery_delay} · {sim.before.stock_days} days cover</i></div>
                <ChevronRight className="compare-arrow" />
                <div data-testid="impact-after" className="compare after"><span>AFTER RECOMMENDATION</span><strong>{sim.after.stockout_probability}%</strong><small>Stockout probability · 7 days</small><b>{sim.after.risk} RISK</b><i>ETA {sim.after.delivery_delay} · {sim.after.stock_days} days cover</i></div>
              </div>
              <div className="recommendation-card" data-testid="recommendation-card">
                <div className="rec-top"><BrainCircuit size={18} /><span>EXPLAINABLE RECOMMENDATION · {rec.id}</span><span className="approval-required">APPROVAL REQUIRED</span></div>
                <h3 data-testid="recommendation-action">{rec.action}</h3>
                <p>{rec.reason}</p>
                <div className="data-used">{rec.data_used.map(d => <span key={d} className="chip">{d}</span>)}</div>
                <div className="rec-facts"><span><b>BENEFIT</b>{rec.benefit}</span><span><b>ETA</b>{rec.eta || "—"}</span><span><b>VEHICLES</b>{rec.vehicles?.length ? rec.vehicles.map(v => v.name).join(", ") : "None available"}</span><span><b>ALTERNATIVE</b>{rec.alternative}</span></div>
                {sim.ranking?.candidates?.length > 0 && (
                  <div className="mini-rank">{sim.ranking.candidates.map(c => <span key={c.rank} className="mini-rank-row"><i style={{ background: c.color }} /><b>#{c.rank}</b> {c.path_names.map(n => n.split(" ·")[0]).join(" → ")} <em>{c.eta} · score {c.score}</em></span>)}</div>
                )}
                <div className="decision-row">
                  <button ref={approveRef} data-testid="approve-recommendation-button" className={demoWaiting ? "approve-btn pulse-target" : "approve-btn"} onClick={() => approve("APPROVE")}><Check size={15} /> Approve in simulation</button>
                  <button data-testid="reject-recommendation-button" className="reject-btn" onClick={() => approve("REJECT")}><X size={15} /> Reject</button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
