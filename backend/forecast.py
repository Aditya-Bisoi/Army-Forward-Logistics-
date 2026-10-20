import io, pickle, zlib, asyncio, math
import numpy as np, pandas as pd
from bson import Binary
from datetime import datetime, timezone, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from db import db

RESOURCES = ["Fuel", "Rations", "Medical", "Spares"]
FEATURES = ["lag1", "lag7", "roll7", "roll14", "roll28", "dow", "resource_idx"]
PARAMS = {"n_estimators": 80, "max_depth": 8, "random_state": 42}
_cache = {}


def today(): return datetime.now(timezone.utc).date()
def now_iso(): return datetime.now(timezone.utc).isoformat()


def base_level(loc, resource):
    troops = loc.get("troops", 0)
    if resource == "Fuel": return loc.get("fuel_base") or max(50, troops * 0.4)
    if loc["type"] == "DEPOT": return {"Rations": 900, "Medical": 140, "Spares": 120}[resource]
    return {"Rations": troops * 1.1, "Medical": troops * 0.18, "Spares": troops * 0.12}[resource]


def generate_history(locations, days=180, seed=42):
    rng = np.random.default_rng(seed); end = today() - timedelta(days=1); rows = []
    for loc in locations:
        for res in RESOURCES:
            base = base_level(loc, res)
            for i in range(days):
                d = end - timedelta(days=days - 1 - i)
                season = 1 + 0.08 * math.sin(2 * math.pi * i / 30)
                weekly = 1 + (0.06 if d.weekday() in (0, 1) else -0.04 if d.weekday() == 6 else 0)
                trend = 1 + 0.12 * (i / days) * (loc.get("demand_trend", 30) / 100)
                surge = 1 + 0.42 * min(1, (i - (days - 12)) / 10) if (loc.get("demand_trend", 0) >= 85 and res == "Fuel" and i >= days - 12) else 1
                q = base * season * weekly * trend * surge * (1 + rng.normal(0, 0.05))
                rows.append({"date": d.isoformat(), "location_id": loc["id"], "resource": res, "quantity": round(float(max(0, q)), 1), "source": "synthetic"})
    return rows


def frame(rows):
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"]); df = df.sort_values(["location_id", "resource", "date"])
    g = df.groupby(["location_id", "resource"])["quantity"]
    df["lag1"] = g.shift(1); df["lag7"] = g.shift(7)
    for n in (7, 14, 28): df[f"roll{n}"] = g.transform(lambda s, n=n: s.shift(1).rolling(n).mean())
    df["dow"] = df["date"].dt.dayofweek; df["resource_idx"] = df["resource"].map(RESOURCES.index)
    return df.dropna()


def train_model(rows, version, notes):
    df = frame(rows)
    if len(df) < 60: raise ValueError("Not enough history to train (need at least 60 feature rows)")
    cutoff = df["date"].max() - pd.Timedelta(days=21)
    tr, te = df[df["date"] <= cutoff], df[df["date"] > cutoff]
    model = RandomForestRegressor(**PARAMS, n_jobs=-1).fit(tr[FEATURES], tr["quantity"])
    pred = model.predict(te[FEATURES])
    mae = mean_absolute_error(te["quantity"], pred); rmse = math.sqrt(mean_squared_error(te["quantity"], pred))
    mape = float(np.mean(np.abs(te["quantity"] - pred) / np.maximum(te["quantity"], 1)) * 100)
    return {"version": version, "trained_at": now_iso(), "mae": round(mae, 2), "rmse": round(rmse, 2), "mape": round(mape, 2), "n_train": int(len(tr)), "n_test": int(len(te)), "series": int(df.groupby(["location_id", "resource"]).ngroups),
            "features": FEATURES, "params": PARAMS, "importance": {f: round(float(v), 3) for f, v in zip(FEATURES, model.feature_importances_)}, "notes": notes, "active": True, "algorithm": "RandomForestRegressor", "blob": Binary(zlib.compress(pickle.dumps(model)))}


def predict_future(model, history, resource, horizon, start):
    q = [r["quantity"] for r in history]; out = []
    for h in range(horizon):
        d = start + timedelta(days=h)
        x = np.array([[q[-1], q[-7], np.mean(q[-7:]), np.mean(q[-14:]), np.mean(q[-28:]), d.weekday(), RESOURCES.index(resource)]])
        p = round(float(model.predict(x)[0]), 1); out.append(p); q.append(p)
    return out


def fitted_recent(model, history, n=7):
    df = frame(history)
    if df.empty: return [r["quantity"] for r in history[-n:]]
    tail = df.tail(n)
    return [round(float(v), 1) for v in model.predict(tail[FEATURES])]


async def ensure_history(locations):
    if await db.consumption_history.count_documents({}) == 0:
        await db.consumption_history.insert_many(generate_history(locations))
        await db.consumption_history.create_index([("location_id", 1), ("resource", 1), ("date", 1)])


async def regenerate_history(locations):
    await db.consumption_history.delete_many({})
    rows = generate_history(locations); await db.consumption_history.insert_many(rows)
    _cache.clear()
    return len(rows)


async def next_version(): return f"rf-demand-0.{await db.model_versions.count_documents({}) + 1}"


async def train_and_store(notes="Manual retrain"):
    rows = await db.consumption_history.find({}, {"_id": 0}).to_list(200000)
    doc = await asyncio.to_thread(train_model, rows, await next_version(), notes)
    await db.model_versions.update_many({}, {"$set": {"active": False}})
    await db.model_versions.insert_one(doc)
    return {k: v for k, v in doc.items() if k not in ("blob", "_id")}


async def ensure_model():
    if await db.model_versions.count_documents({}) == 0: await train_and_store("Baseline model trained at startup on synthetic history")


async def list_models(): return await db.model_versions.find({}, {"_id": 0, "blob": 0}).sort("trained_at", -1).to_list(50)
async def active_meta(): return await db.model_versions.find_one({"active": True}, {"_id": 0, "blob": 0})


async def activate(version):
    doc = await db.model_versions.find_one({"version": version})
    if not doc: return None
    await db.model_versions.update_many({}, {"$set": {"active": False}})
    await db.model_versions.update_one({"version": version}, {"$set": {"active": True}})
    return version


async def active_model():
    doc = await db.model_versions.find_one({"active": True}, {"version": 1, "blob": 1})
    if not doc: return None, None
    if doc["version"] not in _cache: _cache[doc["version"]] = pickle.loads(zlib.decompress(doc["blob"]))
    return _cache[doc["version"]], doc["version"]


async def series(location_id, resource, days=90):
    rows = await db.consumption_history.find({"location_id": location_id, "resource": resource}, {"_id": 0}).sort("date", 1).to_list(5000)
    return rows[-days:]


def label(d): return d.strftime("%d %b")


async def forecast_for(location_id, resource="Fuel", horizon=7, demand_factor=1.0):
    model, version = await active_model(); meta = await active_meta() or {}
    history = await series(location_id, resource)
    start = today()
    if not history: return {"location_id": location_id, "resource": resource, "labels": [], "actual": [], "fitted": [], "predicted": [], "daily_demand": 0, "model": None}
    actual = [r["quantity"] for r in history[-7:]]
    if model and len(history) >= 29:
        predicted = predict_future(model, history, resource, horizon, start); fitted = fitted_recent(model, history)
    else:
        naive = round(float(np.mean(actual)), 1); predicted = [naive] * horizon; fitted = actual
    predicted = [round(p * demand_factor, 1) for p in predicted]
    past_labels = [label(datetime.fromisoformat(r["date"])) for r in history[-7:]]
    future_labels = [label(start + timedelta(days=h)) for h in range(horizon)]
    return {"location_id": location_id, "resource": resource, "labels": past_labels + future_labels, "actual": actual, "fitted": fitted, "predicted": predicted, "horizon": f"{horizon} days", "daily_demand": round(float(np.mean(predicted)), 1),
            "model": version or "naive-mean", "algorithm": meta.get("algorithm", "Random Forest baseline"), "mae": meta.get("mae"), "rmse": meta.get("rmse"), "mape": meta.get("mape"), "trend_pct": round((np.mean(predicted) / max(np.mean(actual), 1) - 1) * 100, 1)}


async def ingest_csv(content: bytes):
    df = pd.read_csv(io.BytesIO(content))
    required = {"date", "location_id", "resource", "quantity"}
    if not required <= set(df.columns): raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce"); df = df.dropna(subset=["date", "quantity"])
    df["resource"] = df["resource"].astype(str).str.strip().str.title()
    bad = sorted(set(df["resource"]) - set(RESOURCES))
    if bad: raise ValueError(f"Unknown resources: {', '.join(bad)}. Allowed: {', '.join(RESOURCES)}")
    known = {l["id"] for l in await db.locations.find({}, {"_id": 0, "id": 1}).to_list(500)}
    bad_loc = sorted(set(df["location_id"].astype(str)) - known)
    if bad_loc: raise ValueError(f"Unknown location ids: {', '.join(bad_loc)}")
    pairs = df[["location_id", "resource"]].drop_duplicates().values.tolist()
    for loc, res in pairs: await db.consumption_history.delete_many({"location_id": loc, "resource": res})
    rows = [{"date": r.date.date().isoformat(), "location_id": str(r.location_id), "resource": r.resource, "quantity": round(float(r.quantity), 1), "source": "upload"} for r in df.itertuples()]
    await db.consumption_history.insert_many(rows)
    return {"rows": len(rows), "series_replaced": len(pairs), "date_range": [df["date"].min().date().isoformat(), df["date"].max().date().isoformat()]}


async def history_summary():
    pipeline = [{"$group": {"_id": {"l": "$location_id", "r": "$resource", "s": "$source"}, "rows": {"$sum": 1}, "start": {"$min": "$date"}, "end": {"$max": "$date"}}}]
    rows = await db.consumption_history.aggregate(pipeline).to_list(500)
    return sorted([{"location_id": r["_id"]["l"], "resource": r["_id"]["r"], "source": r["_id"]["s"], "rows": r["rows"], "start": r["start"], "end": r["end"]} for r in rows], key=lambda x: (x["location_id"], x["resource"]))
