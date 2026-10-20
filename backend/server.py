from dotenv import load_dotenv
load_dotenv()

import os, uuid, logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import db, client
from auth import router as auth_router, current_user, seed_admin
from admin import router as admin_router
from twin import load_twin, seed_twin, SCENARIOS, MISSIONS
from optimizer import rank_paths
from simulation import plan_resupply, DEFAULT_OPT_WEIGHTS
import forecast as fc

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app = FastAPI(title="Predictive Forward Logistics Digital Twin", version="2.0.0")
api = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO)


class DisruptionInput(BaseModel):
    scenario_id: str
    severity: str = "HIGH"
    duration_hours: int = 24


class ApprovalInput(BaseModel):
    decision: str
    modified_quantity: Optional[int] = None
    recommendation: Optional[dict] = None
    scenario_id: Optional[str] = None
    before: Optional[dict] = None
    after: Optional[dict] = None


class RankInput(BaseModel):
    source: str
    destination: str
    quantity: int = 1200
    weights: dict = DEFAULT_OPT_WEIGHTS
    scenario_id: str = "normal"


def now(): return datetime.now(timezone.utc).isoformat()


def alerts_for(twin, plan, forecasts):
    alerts = []
    for loc in sorted(twin["locations"], key=lambda l: -l["risk"]):
        if loc["status"] == "NORMAL": continue
        f = forecasts[loc["id"]]; stock = loc["inventory"] / 100 * loc["capacity"]; days = round(stock / max(f["daily_demand"], 1), 1)
        alerts.append({"id": f"ALT-{loc['id'].upper()}", "severity": "CRITICAL" if loc["status"] == "CRITICAL" else "HIGH", "title": f"Fuel shortage predicted in {max(1, int(days))} days" if days < 7 else "Risk score elevated", "location": loc["name"], "resource": "Fuel",
                       "reason": f"{f['trend_pct']:+.0f}% demand trend · {days} days cover · risk {loc['risk']}/100", "action": plan["recommendation"]["action"] if loc["id"] == plan["focus"]["id"] else "Review replenishment window"})
    for r in twin["routes"]:
        if r["status"] == "BLOCKED": alerts.append({"id": f"ALT-{r['id'].upper()}", "severity": "HIGH", "title": f"{r['name'].split(' / ')[1]} corridor blocked", "location": r["name"], "resource": "Transport", "reason": f"Route risk {r['risk']}% · reliability {r['reliability']}%", "action": "Optimizer re-routes via alternates"})
    busy = [v for v in twin["vehicles"] if v["status"] != "AVAILABLE"]
    if busy: alerts.append({"id": "ALT-FLEET", "severity": "MEDIUM", "title": f"{len(busy)} vehicles unavailable", "location": "Fleet", "resource": "Vehicles", "reason": ", ".join(v["name"] for v in busy[:3]), "action": "Check maintenance queue"})
    return alerts[:6]


@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    twin = await load_twin()
    forecasts = {l["id"]: await fc.forecast_for(l["id"], "Fuel") for l in twin["locations"]}
    for loc in twin["locations"]:
        f = forecasts[loc["id"]]; loc["stock_units"] = round(loc["inventory"] / 100 * loc["capacity"]); loc["daily_demand"] = f["daily_demand"]
        loc["stock_days"] = round(loc["stock_units"] / max(f["daily_demand"], 1), 1); loc["reorder_point"] = round(f["daily_demand"] * 7); loc["trend_pct"] = f["trend_pct"]
    plan = await plan_resupply(twin)
    kpis = {"locations": len(twin["locations"]), "critical_locations": sum(1 for x in twin["locations"] if x["status"] == "CRITICAL"), "active_missions": len(MISSIONS),
            "inventory_availability": round(sum(l["inventory"] for l in twin["locations"]) / max(len(twin["locations"]), 1)), "predicted_shortages": sum(1 for l in twin["locations"] if l["stock_days"] < 7),
            "route_disruptions": sum(1 for x in twin["routes"] if x["status"] == "BLOCKED"), "vehicles_available": sum(1 for v in twin["vehicles"] if v["status"] == "AVAILABLE")}
    return {"kpis": kpis, "locations": twin["locations"], "routes": twin["routes"], "vehicles": twin["vehicles"], "weights": twin["weights"], "missions": MISSIONS, "alerts": alerts_for(twin, plan, forecasts), "recommendation": plan["recommendation"],
            "forecast": plan["forecast"], "focus": plan["focus"], "top_routes": plan["ranking"].get("candidates", []), "baseline": {"before": plan["before"], "after": plan["after"]}, "model": await fc.active_meta(), "user": user, "last_updated": now()}


@api.get("/forecast")
async def forecast(location_id: str, resource: str = "Fuel", horizon: int = 7, user=Depends(current_user)):
    if resource not in fc.RESOURCES: raise HTTPException(404, "Unknown resource")
    return await fc.forecast_for(location_id, resource, min(max(horizon, 1), 30))


@api.post("/optimizer/rank")
async def optimizer_rank(input: RankInput, user=Depends(current_user)):
    twin = await load_twin(); ids = {l["id"] for l in twin["locations"]}
    if input.source not in ids or input.destination not in ids: raise HTTPException(404, "Unknown location")
    if input.source == input.destination: raise HTTPException(400, "Source and destination must differ")
    if input.quantity <= 0: raise HTTPException(400, "Quantity must be positive")
    from simulation import scenario_overrides
    focus = next(l for l in twin["locations"] if l["id"] == input.destination)
    overrides, _ = scenario_overrides(input.scenario_id, twin, focus)
    weights = {k: float(input.weights.get(k, DEFAULT_OPT_WEIGHTS[k])) for k in DEFAULT_OPT_WEIGHTS}
    return {**rank_paths(twin, input.source, input.destination, input.quantity, weights, overrides), "overrides": overrides, "algorithm": "K-shortest simple paths (Yen-style enumeration) with weighted multi-criteria scoring"}


@api.post("/simulation/disruption")
async def disruption(input: DisruptionInput, user=Depends(current_user)):
    if input.scenario_id not in [x["id"] for x in SCENARIOS]: raise HTTPException(404, "Scenario not found")
    twin = await load_twin()
    plan = await plan_resupply(twin, input.scenario_id)
    return {**plan, "activated": True, "recalculated": ["inventory", "demand forecast", "route availability", "risk assessment", "vehicle allocation", "resupply plan"]}


@api.post("/recommendations/{recommendation_id}/decision")
async def recommendation_decision(recommendation_id: str, input: ApprovalInput, user=Depends(current_user)):
    if input.decision not in ["APPROVE", "MODIFY", "REJECT"]: raise HTTPException(400, "Decision must be APPROVE, MODIFY, or REJECT")
    rec = input.recommendation or {}
    quantity = input.modified_quantity or rec.get("quantity") or 0
    after = input.after or {}; before = input.before or {}
    accepted = input.decision != "REJECT"
    impact = {"stockout_probability": after.get("stockout_probability") if accepted else before.get("stockout_probability"), "risk": after.get("risk") if accepted else before.get("risk"), "inventory_stabilized": accepted, "stock_days": after.get("stock_days") if accepted else before.get("stock_days")}
    audit = {"id": str(uuid.uuid4()), "recommendation_id": recommendation_id, "decision": input.decision, "quantity": quantity, "user": user["email"], "timestamp": now(), "scenario_id": input.scenario_id, "action": rec.get("action"), "destination": rec.get("destination"), "route": rec.get("route"), "before": before, "after": after, "result": "Simulation updated" if accepted else "Recommendation declined"}
    await db.audit_logs.insert_one(dict(audit))
    return {"audit": audit, "impact": impact}


@api.get("/scenarios")
async def scenarios(user=Depends(current_user)): return SCENARIOS
@api.get("/locations")
async def locations(user=Depends(current_user)): return (await load_twin())["locations"]
@api.get("/routes")
async def routes(user=Depends(current_user)): return (await load_twin())["routes"]
@api.get("/vehicles")
async def vehicles(user=Depends(current_user)): return (await load_twin())["vehicles"]
@api.get("/audit")
async def audit(user=Depends(current_user)): return await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
@api.get("/health")
async def health(): return {"status": "ok", "service": "logistics-control-tower"}


app.include_router(auth_router); app.include_router(admin_router); app.include_router(api)
configured_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip() and o.strip() != "*"]
if FRONTEND_URL not in configured_origins: configured_origins.append(FRONTEND_URL)
app.add_middleware(CORSMiddleware, allow_origins=configured_origins, allow_origin_regex=r"https://.*\.emergentagent\.com", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await seed_admin(); await seed_twin()
    await fc.ensure_history(await db.locations.find({}, {"_id": 0}).to_list(500))
    await fc.ensure_model()


@app.on_event("shutdown")
async def shutdown(): client.close()
