import { BrainCircuit } from "lucide-react";

const W = 700, H = 180, PAD = 8;

export function ForecastPanel({ forecast, focus }) {
  const actual = forecast.actual || [], fitted = forecast.fitted || [], predicted = forecast.predicted || [], labels = forecast.labels || [];
  const all = [...actual, ...fitted, ...predicted];
  const max = Math.max(...all, 1) * 1.1, min = Math.max(0, Math.min(...all) * 0.8);
  const n = actual.length + predicted.length;
  const x = i => (i * (W - PAD * 2)) / Math.max(n - 1, 1) + PAD;
  const y = v => H - 20 - ((v - min) / (max - min || 1)) * (H - 30);
  const line = (vals, offset = 0) => vals.map((v, i) => `${x(i + offset).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const bridge = actual.length && predicted.length ? `${x(actual.length - 1)},${y(actual[actual.length - 1])} ${x(actual.length)},${y(predicted[0])}` : "";
  const ticks = [max, (max + min) / 2, min].map(v => Math.round(v));
  const trend = forecast.trend_pct ?? 0;
  return (
    <div className="forecast-panel panel" data-testid="forecast-panel">
      <div className="section-head">
        <div><span className="eyebrow">DEMAND FORECAST / FUEL / {focus?.name?.toUpperCase()}</span><h2>Consumption trajectory</h2></div>
        <div className="metric-badge" data-testid="forecast-trend"><b style={{ color: trend > 10 ? "#ff5c57" : "#4bd38a" }}>{trend > 0 ? "+" : ""}{trend}%</b> {trend > 10 ? "surge detected" : "vs last 7 days"}</div>
      </div>
      <div className="chart-wrap">
        <div className="chart-y">{ticks.map((t, i) => <span key={i}>{t}</span>)}<span>L/day</span></div>
        <div className="chart">
          <div className="grid-lines" />
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            {actual.length > 0 && <line x1={x(actual.length - 0.5)} x2={x(actual.length - 0.5)} y1={0} y2={H - 20} stroke="#3b4a41" strokeDasharray="4 4" />}
            <polyline points={line(fitted)} fill="none" stroke="#e3c372" strokeWidth="2" strokeDasharray="5 5" opacity=".6" />
            <polyline points={line(actual)} fill="none" stroke="#e3c372" strokeWidth="3" />
            <polyline points={`${bridge} ${line(predicted, actual.length)}`} fill="none" stroke="#58b8ff" strokeWidth="3" strokeDasharray="7 6" />
            {predicted.map((v, i) => <circle key={i} cx={x(i + actual.length)} cy={y(v)} r="3" fill="#58b8ff" />)}
          </svg>
          <div className="chart-labels">{labels.filter((_, i) => i % 2 === 0).map(l => <span key={l}>{l.toUpperCase()}</span>)}</div>
        </div>
      </div>
      <div className="chart-legend">
        <span><i className="line actual" /> Actual consumption</span>
        <span><i className="line predicted" /> Forecast · next {predicted.length} days</span>
        <span className="model-note" data-testid="forecast-model-note"><BrainCircuit size={13} /> {forecast.algorithm === "RandomForestRegressor" ? "Random Forest" : forecast.algorithm} · {forecast.model} · MAE {forecast.mae ?? "—"} · RMSE {forecast.rmse ?? "—"}</span>
      </div>
    </div>
  );
}
