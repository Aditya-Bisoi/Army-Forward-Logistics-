import { useEffect, useState, useCallback } from "react";
import { Route, Truck, AlertTriangle } from "lucide-react";
import { axios, API, apiError } from "../lib/api";
import { NetworkMap } from "./NetworkMap";

const SLIDERS = [["time", "Transit time"], ["risk", "Route risk"], ["capacity", "Capacity fit"]];

export function OptimizerView({ data, notify }) {
  const [source, setSource] = useState(data.recommendation?.source ? data.locations.find(l => l.name === data.recommendation.source)?.id : data.locations[0]?.id);
  const [destination, setDestination] = useState(data.focus?.id || data.locations[2]?.id);
  const [quantity, setQuantity] = useState(data.recommendation?.quantity || 1200);
  const [weights, setWeights] = useState({ time: 40, risk: 40, capacity: 20 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const rank = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.post(`${API}/optimizer/rank`, { source, destination, quantity: Number(quantity), weights: { time: weights.time / 100, risk: weights.risk / 100, capacity: weights.capacity / 100 } });
      setResult(r.data);
    } catch (e) { notify(apiError(e), true); }
    setLoading(false);
  }, [source, destination, quantity, weights, notify]);

  useEffect(() => { const t = setTimeout(rank, 250); return () => clearTimeout(t); }, [rank]);

  return (
    <section className="opt-page" data-testid="optimizer-page">
      <div className="opt-head"><span className="eyebrow">ROUTE OPTIMIZER / MULTI-CRITERIA RANKING</span><h2>Rank every open corridor.<br /><em>Balance time, risk, capacity.</em></h2></div>
      <div className="opt-layout">
        <aside className="opt-controls panel">
          <div className="subhead">MISSION PARAMETERS</div>
          <label className="field">Source<select data-testid="opt-source-select" value={source} onChange={e => setSource(e.target.value)}>{data.locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
          <label className="field">Destination<select data-testid="opt-destination-select" value={destination} onChange={e => setDestination(e.target.value)}>{data.locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
          <label className="field">Quantity (L)<input data-testid="opt-quantity-input" type="number" min="50" step="50" value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
          <div className="subhead" style={{ marginTop: 22 }}>SCORING WEIGHTS <span>{weights.time + weights.risk + weights.capacity}%</span></div>
          {SLIDERS.map(([k, label]) => (
            <div className="slider-row" key={k}>
              <div><span>{label}</span><b data-testid={`opt-weight-${k}-value`}>{weights[k]}%</b></div>
              <input data-testid={`opt-weight-${k}-slider`} type="range" min="0" max="100" value={weights[k]} onChange={e => setWeights({ ...weights, [k]: Number(e.target.value) })} />
            </div>
          ))}
          <p className="hint">Score = 100 − (w₁·time + w₂·risk + w₃·capacity shortfall). Weights are normalised; paths enumerated with K-shortest simple paths over open corridors.</p>
          {result && (
            <div className="fleet-box" data-testid="opt-fleet">
              <div className="subhead"><span><Truck size={12} /> VEHICLE ALLOCATION</span><span style={{ color: result.capacity_ok ? "#4bd38a" : "#ff5c57" }}>{result.capacity_ok ? "SUFFICIENT" : "SHORTFALL"}</span></div>
              {result.vehicles.length ? result.vehicles.map(v => <span key={v.id} className="chip">{v.name} · {v.type} · {v.capacity} L</span>) : <span className="chip">No available vehicles</span>}
            </div>
          )}
        </aside>
        <div className="opt-main">
          <NetworkMap locations={data.locations} routes={data.routes} topRoutes={result?.candidates || []} label="CORRIDOR RANKING" height={380} />
          <div className="rank-list" data-testid="rank-list">
            {loading && !result && <div className="empty-sim" style={{ padding: 30 }}>Ranking corridors…</div>}
            {result && !result.candidates.length && <div className="empty-sim" style={{ padding: 30 }}><AlertTriangle size={20} /><p>{result.message}</p></div>}
            {result?.candidates.map(c => (
              <div className="rank-card" key={c.rank} data-testid={`rank-card-${c.rank}`} style={{ "--rank": c.color }}>
                <div className="rank-badge"><b>#{c.rank}</b><span>{c.label}</span></div>
                <div className="rank-body">
                  <h3><Route size={15} /> {c.path_names.map(n => n.split(" ·")[0]).join(" → ")}</h3>
                  <small>{c.legs.map(l => l.name).join(" + ")}</small>
                  <div className="rank-metrics">
                    <span><b>{c.eta}</b>ETA</span><span><b>{c.distance} km</b>distance</span><span><b style={{ color: c.max_risk >= 60 ? "#ff5c57" : c.max_risk >= 40 ? "#ffb547" : "#4bd38a" }}>{c.max_risk}%</b>peak risk</span><span><b>{c.min_capacity}</b>min capacity</span><span><b style={{ color: c.shortfall_pct ? "#ff5c57" : "#4bd38a" }}>{c.shortfall_pct}%</b>shortfall</span>
                  </div>
                  <div className="penalty-bar" title="Penalty breakdown">
                    <i style={{ width: `${c.breakdown.time}%`, background: "#62b4ff" }} /><i style={{ width: `${c.breakdown.risk}%`, background: "#ff5c57" }} /><i style={{ width: `${c.breakdown.capacity}%`, background: "#ffb547" }} />
                  </div>
                  <small className="penalty-legend">penalty · time {c.breakdown.time} · risk {c.breakdown.risk} · capacity {c.breakdown.capacity}</small>
                </div>
                <div className="rank-score"><strong data-testid={`rank-score-${c.rank}`}>{c.score}</strong><small>SCORE</small></div>
              </div>
            ))}
            {result && <small className="hint">{result.evaluated} candidate paths evaluated · {result.algorithm}</small>}
          </div>
        </div>
      </div>
    </section>
  );
}
