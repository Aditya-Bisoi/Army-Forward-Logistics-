import { fmt } from "../lib/api";

export function InventoryView({ locations }) {
  return (
    <section className="data-page">
      <span className="eyebrow">INVENTORY ENGINE / LIVE CALCULATIONS</span><h2>Resource availability</h2>
      <p className="page-lede">Stock cover is derived from current fuel stock divided by the active model's 7-day forecast. Reorder point = 7 days of predicted demand.</p>
      <div className="table-panel" data-testid="inventory-table">
        <div className="table-head"><span>LOCATION</span><span>STOCK / CAPACITY</span><span>STOCK COVER</span><span>REORDER POINT</span><span>RISK</span></div>
        {locations.map(l => (
          <div className="table-row" key={l.id} data-testid={`inventory-row-${l.id}`}>
            <b>{l.name}</b>
            <span>{fmt(l.stock_units)} <small>/ {fmt(l.capacity)} L</small></span>
            <span><b style={{ color: l.stock_days < 7 ? "#ff5c57" : "#4bd38a" }}>{l.stock_days} days</b><small> · {l.daily_demand} L/day</small></span>
            <span>{fmt(l.reorder_point)} L {l.stock_units < l.reorder_point && <small style={{ color: "#ffb547" }}>· below</small>}</span>
            <span className={`status-pill ${l.status.toLowerCase()}`}>{l.status}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
