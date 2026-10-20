import math
from datetime import datetime, timezone
from twin import SCENARIOS
from optimizer import rank_paths
from forecast import forecast_for

DEFAULT_OPT_WEIGHTS = {"time": 0.4, "risk": 0.4, "capacity": 0.2}


def now(): return datetime.now(timezone.utc).isoformat()
def clamp(v, lo=4, hi=96): return int(max(lo, min(hi, round(v))))


def stockout_probability(stock, daily_forecast, days):
    whole, frac = int(days), days - int(days)
    cum = sum(daily_forecast[:whole]) + (daily_forecast[min(whole, len(daily_forecast) - 1)] * frac if frac else 0)
    if cum <= 0: return 4
    return clamp(100 / (1 + math.exp(-6 * (cum - stock) / cum)))


def risk_band(p): return "HIGH" if p >= 60 else "MEDIUM" if p >= 30 else "LOW"


def scenario_overrides(scenario_id, twin, focus):
    overrides, factor = {"blocked": [], "extra_hours": {}, "exclude_vehicles": []}, 1.0
    if scenario_id == "surge": factor = 1.42
    if scenario_id == "blocked":
        depot = pick_depot(twin, focus)
        baseline = rank_paths(twin, depot["id"], focus["id"], 1, DEFAULT_OPT_WEIGHTS) if depot else {"candidates": []}
        if baseline["candidates"]: overrides["blocked"].append(baseline["candidates"][0]["legs"][-1]["id"])
    if scenario_id == "weather": overrides["extra_hours"] = {r["id"]: 6 for r in twin["routes"] if r.get("weather_exposed")}
    if scenario_id == "vehicle": overrides["exclude_vehicles"].append("VH-04")
    return overrides, factor


def pick_focus(twin):
    targets = [l for l in twin["locations"] if l["type"] != "DEPOT"] or twin["locations"]
    return max(targets, key=lambda l: l["risk"])


def pick_depot(twin, focus):
    depots = [l for l in twin["locations"] if l["type"] == "DEPOT" and l["id"] != focus["id"]] or [l for l in twin["locations"] if l["id"] != focus["id"]]
    return max(depots, key=lambda l: l["inventory"]) if depots else None


async def plan_resupply(twin, scenario_id="normal", opt_weights=None):
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), SCENARIOS[0])
    focus = pick_focus(twin); depot = pick_depot(twin, focus)
    overrides, factor = scenario_overrides(scenario_id, twin, focus)
    fc = await forecast_for(focus["id"], "Fuel", 7, factor)
    daily = fc["predicted"] or [1]
    stock = round(focus["inventory"] / 100 * focus["capacity"])
    stock_days = round(stock / max(fc["daily_demand"], 1), 1)
    quantity = int(round(fc["daily_demand"] * 4 / 50) * 50) or 400
    before_p = stockout_probability(stock, daily, 7)
    ranking = rank_paths(twin, depot["id"], focus["id"], quantity, opt_weights or DEFAULT_OPT_WEIGHTS, overrides) if depot else {"candidates": []}
    best = ranking["candidates"][0] if ranking["candidates"] else None
    if best:
        days_until = (best["hours"] + 2) / 24
        after_p = clamp(stockout_probability(stock, daily, days_until) + 0.2 * best["max_risk"] + (8 if best["shortfall_pct"] else 0))
        after_delay = best["eta"]
    else:
        after_p, after_delay = before_p, "No corridor"
    primary = sorted([r for r in twin["routes"] if focus["id"] in (r["source"], r["destination"])], key=lambda r: r["hours"])
    before_delay = "No open corridor" if (not primary or all(r["status"] == "BLOCKED" or r["id"] in overrides["blocked"] for r in primary)) else "No dispatch planned"
    rec_id = f"REC-{scenario_id.upper()[:3]}-{focus['id'].split('-')[-1].upper()}"
    recommendation = {"id": rec_id, "priority": "P0" if before_p >= 60 else "P1", "status": "RECOMMENDED", "requires_approval": True, "quantity": quantity, "resource": "Fuel", "source": depot["name"] if depot else None, "destination": focus["name"], "destination_id": focus["id"],
                      "headline": f"Protect {focus['name']} before the fuel shortfall window" if before_p >= 30 else f"Maintain {focus['name']} stock cover",
                      "action": f"Dispatch {quantity:,} L from {depot['name'].split(' ·')[0]} via {' → '.join(l['name'].split(' / ')[1] for l in best['legs'])}" if best else "Hold position — no open corridor; escalate route clearance",
                      "route": " + ".join(l["name"] for l in best["legs"]) if best else None, "eta": best["eta"] if best else None, "vehicles": ranking.get("vehicles", []),
                      "reason": f"{focus['name']} holds {stock:,} L against a forecast of {fc['daily_demand']:.0f} L/day ({stock_days} days of cover). " + (f"Best open corridor scores {best['score']} with {best['max_risk']}% peak route risk and {best['eta']} ETA." if best else "Every corridor into the location is blocked under this scenario."),
                      "data_used": [f"{fc['trend_pct']:+.0f}% forecast demand trend", f"{fc['daily_demand']:.0f} L/day predicted consumption", f"{stock_days} day stock cover", *(f"{r['name']} blocked" for r in twin["routes"] if r["status"] == "BLOCKED" or r["id"] in overrides["blocked"]), *( [f"Best path ETA {best['eta']}"] if best else [])],
                      "benefit": f"Reduce stockout probability from {before_p}% to {after_p}%", "risk": (f"Peak corridor risk {best['max_risk']}% · reliability {best['reliability']}%" if best else "Shortage persists"), "alternative": (f"{ranking['candidates'][1]['label']}: {ranking['candidates'][1]['eta']} ETA, score {ranking['candidates'][1]['score']}" if len(ranking["candidates"]) > 1 else "Hold position and accept projected shortage")}
    return {"scenario": scenario, "focus": {"id": focus["id"], "name": focus["name"], "stock": stock, "stock_days": stock_days, "daily_demand": fc["daily_demand"]}, "forecast": fc, "overrides": overrides, "demand_factor": factor,
            "before": {"stockout_probability": before_p, "risk": risk_band(before_p), "delivery_delay": before_delay, "stock_days": stock_days},
            "after": {"stockout_probability": after_p, "risk": risk_band(after_p), "delivery_delay": after_delay, "stock_days": round((stock + (quantity if best else 0)) / max(fc["daily_demand"], 1), 1)},
            "ranking": ranking, "recommendation": recommendation, "timestamp": now()}
