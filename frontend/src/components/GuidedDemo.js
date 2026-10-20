import { SkipForward, X, Hand } from "lucide-react";
import { DEMO_STEPS } from "../hooks/useGuidedDemo";

export function GuidedDemoBar({ demo, data, sim }) {
  if (!demo.active) return null;
  const s = DEMO_STEPS[demo.step];
  return (
    <div className="demo-bar" data-testid="guided-demo-bar">
      <div className="demo-steps">{DEMO_STEPS.map((x, i) => <i key={x.id} className={i < demo.step ? "done" : i === demo.step ? "current" : ""} />)}</div>
      <div className="demo-body">
        <span className="eyebrow" data-testid="guided-demo-title">{s.title} · STEP {demo.step + 1}/{DEMO_STEPS.length}</span>
        <p data-testid="guided-demo-caption">{s.caption({ data, sim })}</p>
        {!s.wait && <div className="demo-timer" key={demo.step} style={{ animationDuration: `${s.ms}ms` }} />}
        {s.wait && <div className="demo-wait"><Hand size={13} /> Waiting for human approval</div>}
      </div>
      <div className="demo-actions">
        <button className="outline-btn" data-testid="guided-demo-skip" onClick={demo.next}><SkipForward size={13} /> Skip</button>
        <button className="icon-btn" data-testid="guided-demo-exit" onClick={demo.exit}><X size={14} /></button>
      </div>
    </div>
  );
}
