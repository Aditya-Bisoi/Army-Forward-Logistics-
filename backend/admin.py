import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field
from db import db
from auth import admin_user
from twin import load_twin, SCENARIOS, DEFAULT_WEIGHTS, SEED_LOCATIONS, SEED_ROUTES, SEED_VEHICLES
import forecast as fc

router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_user)])


class LocationInput(BaseModel):
    id: Optional[str] = None
    name: str
    type: str = Field(pattern="^(DEPOT|HUB|FORWARD)$")
    lat: float
    lng: float
    troops: int = 0
    capacity: int = Field(gt=0)
    inventory: int = Field(ge=0, le=100)
    weather_exposure: int = Field(ge=0, le=100, default=30)
    demand_trend: int = Field(ge=0, le=100, default=30)
    fuel_base: float = Field(gt=0, default=200)


class RouteInput(BaseModel):
    id: Optional[str] = None
    source: str
    destination: str
    name: str
    distance: float = Field(gt=0)
    hours: float = Field(gt=0)
    status: str = Field(pattern="^(AVAILABLE|BLOCKED|DEGRADED)$", default="AVAILABLE")
    reliability: int = Field(ge=0, le=100, default=85)
    risk: int = Field(ge=0, le=100, default=20)
    capacity: int = Field(gt=0, default=2000)
    weather_exposed: bool = False


class VehicleInput(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    capacity: int = Field(gt=0)
    status: str = Field(pattern="^(AVAILABLE|IN_TRANSIT|MAINTENANCE)$", default="AVAILABLE")
    base: str


class WeightsInput(BaseModel):
    inventory: float = Field(ge=0, le=1)
    transport: float = Field(ge=0, le=1)
    weather: float = Field(ge=0, le=1)
    demand: float = Field(ge=0, le=1)


class TrainInput(BaseModel):
    notes: str = "Manual retrain from admin console"


COLLECTIONS = {"locations": (db.locations, LocationInput, "loc"), "routes": (db.routes, RouteInput, "route"), "vehicles": (db.vehicles, VehicleInput, "VH")}


async def validate_refs(entity, body):
    ids = {l["id"] for l in await db.locations.find({}, {"_id": 0, "id": 1}).to_list(500)}
    refs = [body.source, body.destination] if entity == "routes" else [body.base] if entity == "vehicles" else []
    missing = [r for r in refs if r not in ids]
    if missing: raise HTTPException(422, f"Unknown location id(s): {', '.join(missing)}")
    if entity == "routes" and body.source == body.destination: raise HTTPException(422, "Source and destination must differ")


def get_collection(entity):
    if entity not in COLLECTIONS: raise HTTPException(404, "Unknown entity")
    return COLLECTIONS[entity]


@router.get("/summary")
async def admin_summary():
    twin = await load_twin()
    return {"entities": {"locations": len(twin["locations"]), "routes": len(twin["routes"]), "vehicles": len(twin["vehicles"]), "resources": len(fc.RESOURCES), "scenarios": len(SCENARIOS)}, "model": await fc.active_meta(), "weights": twin["weights"], "decisions": await db.audit_logs.count_documents({}),
            "history_rows": await db.consumption_history.count_documents({})}


@router.get("/{entity}")
async def list_entities(entity: str):
    if entity == "weights": return await db.settings.find_one({"id": "risk_weights"}, {"_id": 0, "id": 0})
    coll, _, _ = get_collection(entity)
    return await coll.find({}, {"_id": 0}).to_list(500)


@router.post("/{entity}")
async def create_entity(entity: str, payload: dict):
    coll, Model, prefix = get_collection(entity)
    try: body = Model(**payload)
    except Exception as e: raise HTTPException(422, str(e))
    await validate_refs(entity, body)
    doc = body.model_dump(); doc["id"] = doc["id"] or f"{prefix}-{uuid.uuid4().hex[:6]}"
    if await coll.find_one({"id": doc["id"]}): raise HTTPException(409, f"{entity[:-1]} id already exists")
    await coll.insert_one(dict(doc)); fc._cache.clear()
    return doc


@router.put("/weights")
async def update_weights(body: WeightsInput):
    total = body.inventory + body.transport + body.weather + body.demand
    if abs(total - 1) > 0.02: raise HTTPException(422, f"Weights must sum to 1.0 (currently {total:.2f})")
    doc = body.model_dump(); await db.settings.update_one({"id": "risk_weights"}, {"$set": doc}, upsert=True)
    return doc


@router.put("/{entity}/{item_id}")
async def update_entity(entity: str, item_id: str, payload: dict):
    coll, Model, _ = get_collection(entity)
    try: body = Model(**{**payload, "id": item_id})
    except Exception as e: raise HTTPException(422, str(e))
    await validate_refs(entity, body)
    doc = body.model_dump()
    result = await coll.update_one({"id": item_id}, {"$set": doc})
    if result.matched_count == 0: raise HTTPException(404, "Not found")
    return doc


@router.delete("/{entity}/{item_id}")
async def delete_entity(entity: str, item_id: str):
    coll, _, _ = get_collection(entity)
    result = await coll.delete_one({"id": item_id})
    if result.deleted_count == 0: raise HTTPException(404, "Not found")
    cascade = {}
    if entity == "locations":
        cascade["routes"] = (await db.routes.delete_many({"$or": [{"source": item_id}, {"destination": item_id}]})).deleted_count
        cascade["vehicles"] = (await db.vehicles.delete_many({"base": item_id})).deleted_count
        cascade["history"] = (await db.consumption_history.delete_many({"location_id": item_id})).deleted_count
    return {"deleted": item_id, "cascade": cascade}


@router.post("/twin/reset")
async def reset_twin():
    await db.locations.delete_many({}); await db.routes.delete_many({}); await db.vehicles.delete_many({})
    await db.locations.insert_many([dict(x) for x in SEED_LOCATIONS]); await db.routes.insert_many([dict(x) for x in SEED_ROUTES]); await db.vehicles.insert_many([dict(x) for x in SEED_VEHICLES])
    await db.settings.update_one({"id": "risk_weights"}, {"$set": {k: v for k, v in DEFAULT_WEIGHTS.items() if k != "id"}}, upsert=True)
    rows = await fc.regenerate_history(SEED_LOCATIONS)
    return {"ok": True, "history_rows": rows}


@router.get("/model/versions")
async def model_versions(): return await fc.list_models()


@router.post("/model/train")
async def train_model(body: TrainInput):
    try: return await fc.train_and_store(body.notes)
    except ValueError as e: raise HTTPException(422, str(e))


@router.post("/model/versions/{version}/activate")
async def activate_model(version: str):
    if not await fc.activate(version): raise HTTPException(404, "Model version not found")
    return {"active": version}


@router.get("/model/history")
async def model_history(): return await fc.history_summary()


@router.post("/model/history/upload")
async def upload_history(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 5_000_000: raise HTTPException(413, "CSV larger than 5 MB")
    try: return await fc.ingest_csv(content)
    except ValueError as e: raise HTTPException(422, str(e))


@router.post("/model/history/regenerate")
async def regenerate_history():
    locations = await db.locations.find({}, {"_id": 0}).to_list(500)
    return {"history_rows": await fc.regenerate_history(locations)}
