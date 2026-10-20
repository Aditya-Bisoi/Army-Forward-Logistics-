import { useCallback, useEffect, useRef, useState } from "react";

export const DEMO_STEPS = [
  { id: "observe", tab: "overview", title: "01 · OBSERVE", ms: 7000, caption: ({ data }) => `${data.focus.name} is ${data.locations.find(l => l.id === data.focus.id)?.status}: ${data.focus.stock_days} days of fuel cover, ${data.kpis.route_disruptions} corridor blocked, ${data.kpis.predicted_shortages} shortages predicted.` },
  { id: "predict", tab: "overview", title: "02 · PREDICT", ms: 6500, caption: ({ data }) => `Random Forest ${data.forecast.model} forecasts ${data.forecast.trend_pct > 0 ? "+" : ""}${data.forecast.trend_pct}% fuel demand change over 7 days · hold-out MAE ${data.forecast.mae}.` },
  { id: "inject", tab: "scenarios", title: "03 · SIMULATE", ms: 3500, action: "select", caption: () => "Injecting 'Primary Route Blocked' into the digital twin — the best corridor into the focus location closes." },
  { id: "propagate", tab: "scenarios", title: "04 · PROPAGATE", ms: 5000, action: "run", caption: () => "Recalculating inventory, demand forecast, route availability, risk, vehicle allocation and the resupply plan." },
  { id: "explain", tab: "scenarios", title: "05 · EXPLAIN", ms: 9000, caption: ({ sim }) => sim ? `Before intervention: ${sim.before.stockout_probability}% stockout probability. Recommended: ${sim.recommendation.action} (ETA ${sim.recommendation.eta || "—"}).` : "Waiting for simulation…" },
  { id: "decide", tab: "scenarios", title: "06 · HUMAN DECISION", wait: true, caption: () => "The AI only recommends. Click Approve in simulation to continue — nothing moves without a human decision." },
  { id: "impact", tab: "scenarios", title: "07 · IMPACT", ms: 8000, caption: ({ sim }) => sim ? `Stockout probability ${sim.before.stockout_probability}% → ${sim.after.stockout_probability}% · stock cover ${sim.before.stock_days} → ${sim.after.stock_days} days. Decision recorded in the audit trail.` : "" },
  { id: "optimize", tab: "optimizer", title: "08 · OPTIMIZE", ms: 9000, caption: () => "Top-3 corridors ranked by transit time, route risk and capacity fit — tune the weights live and the map re-ranks." },
];

export function useGuidedDemo({ setTab, setScenario, runScenario }) {
  const [step, setStep] = useState(null);
  const [startedAt, setStartedAt] = useState(0);
  const actions = useRef({ setTab, setScenario, runScenario });
  actions.current = { setTab, setScenario, runScenario };

  const next = useCallback(() => setStep(s => (s === null ? null : s + 1 >= DEMO_STEPS.length ? null : s + 1)), []);
  const exit = useCallback(() => setStep(null), []);
  const start = useCallback(() => { setStep(0); }, []);

  useEffect(() => {
    if (step === null) return;
    const s = DEMO_STEPS[step];
    actions.current.setTab(s.tab);
    if (s.action === "select") actions.current.setScenario("blocked");
    if (s.action === "run") actions.current.runScenario("blocked");
    setStartedAt(Date.now());
    if (s.wait) return;
    const t = setTimeout(next, s.ms);
    return () => clearTimeout(t);
  }, [step, next]);

  const onApproved = useCallback(() => { if (step !== null && DEMO_STEPS[step].wait) next(); }, [step, next]);
  return { step, active: step !== null, start, next, exit, onApproved, startedAt, waiting: step !== null && !!DEMO_STEPS[step].wait };
}
