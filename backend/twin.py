from db import db

SEED_LOCATIONS = [
    {"id": "dep-a", "name": "Depot A · Leh Logistics Base", "type": "DEPOT", "lat": 34.1526, "lng": 77.5771, "troops": 0, "capacity": 24000, "inventory": 92, "weather_exposure": 20, "demand_trend": 25, "fuel_base": 520},
    {"id": "hub-n", "name": "Distribution Hub North", "type": "HUB", "lat": 34.2058, "lng": 77.5142, "troops": 420, "capacity": 12000, "inventory": 74, "weather_exposure": 35, "demand_trend": 40, "fuel_base": 700},
    {"id": "forward-b", "name": "Forward Location B", "type": "FORWARD", "lat": 34.3394, "lng": 77.6853, "troops": 860, "capacity": 4800, "inventory": 28, "weather_exposure": 70, "demand_trend": 90, "fuel_base": 250},
    {"id": "forward-c", "name": "Forward Location C", "type": "FORWARD", "lat": 34.4163, "lng": 77.7771, "troops": 540, "capacity": 3600, "inventory": 46, "weather_exposure": 65, "demand_trend": 55, "fuel_base": 260},
    {"id": "forward-d", "name": "Forward Location D", "type": "FORWARD", "lat": 34.1129, "lng": 77.8901, "troops": 330, "capacity": 2200, "inventory": 68, "weather_exposure": 30, "demand_trend": 30, "fuel_base": 200},
]
SEED_ROUTES = [
    {"id": "route-a", "source": "dep-a", "destination": "hub-n", "name": "Route A / Srinagar Axis", "distance": 22, "hours": 4.2, "status": "AVAILABLE", "reliability": 94, "risk": 12, "capacity": 6000, "weather_exposed": False},
    {"id": "route-b", "source": "hub-n", "destination": "forward-b", "name": "Route B / North Pass", "distance": 31, "hours": 7.8, "status": "BLOCKED", "reliability": 61, "risk": 89, "capacity": 2500, "weather_exposed": True},
    {"id": "route-c", "source": "dep-a", "destination": "forward-b", "name": "Route C / Alternate Ridge", "distance": 48, "hours": 10.6, "status": "AVAILABLE", "reliability": 86, "risk": 28, "capacity": 1800, "weather_exposed": True},
    {"id": "route-d", "source": "hub-n", "destination": "forward-c", "name": "Route D / Valley Spur", "distance": 27, "hours": 6.4, "status": "AVAILABLE", "reliability": 78, "risk": 44, "capacity": 2200, "weather_exposed": True},
    {"id": "route-e", "source": "dep-a", "destination": "forward-d", "name": "Route E / South Link", "distance": 35, "hours": 8.1, "status": "AVAILABLE", "reliability": 91, "risk": 18, "capacity": 2600, "weather_exposed": False},
    {"id": "route-f", "source": "forward-c", "destination": "forward-b", "name": "Route F / Ridge Track", "distance": 19, "hours": 5.9, "status": "AVAILABLE", "reliability": 70, "risk": 52, "capacity": 900, "weather_exposed": True},
]
SEED_VEHICLES = [
    {"id": "VH-01", "name": "Vehicle 01", "type": "Fuel Tanker", "capacity": 1200, "status": "AVAILABLE", "base": "dep-a"},
    {"id": "VH-02", "name": "Vehicle 02", "type": "Fuel Tanker", "capacity": 1200, "status": "AVAILABLE", "base": "dep-a"},
    {"id": "VH-03", "name": "Vehicle 03", "type": "Cargo Truck", "capacity": 800, "status": "IN_TRANSIT", "base": "hub-n"},
    {"id": "VH-04", "name": "Vehicle 04", "type": "Fuel Tanker", "capacity": 1000, "status": "AVAILABLE", "base": "dep-a"},
    {"id": "VH-05", "name": "Vehicle 05", "type": "Cargo Truck", "capacity": 800, "status": "AVAILABLE", "base": "dep-a"},
    {"id": "VH-06", "name": "Vehicle 06", "type": "Cargo Truck", "capacity": 800, "status": "MAINTENANCE", "base": "dep-a"},
    {"id": "VH-07", "name": "Vehicle 07", "type": "Cargo Truck", "capacity": 800, "status": "IN_TRANSIT", "base": "dep-a"},
    {"id": "VH-08", "name": "Vehicle 08", "type": "Light Utility", "capacity": 300, "status": "AVAILABLE", "base": "hub-n"},
    {"id": "VH-09", "name": "Vehicle 09", "type": "Light Utility", "capacity": 300, "status": "AVAILABLE", "base": "hub-n"},
    {"id": "VH-10", "name": "Vehicle 10", "type": "Fuel Tanker", "capacity": 1200, "status": "AVAILABLE", "base": "hub-n"},
    {"id": "VH-11", "name": "Vehicle 11", "type": "Light Utility", "capacity": 300, "status": "AVAILABLE", "base": "forward-c"},
    {"id": "VH-12", "name": "Vehicle 12", "type": "Cargo Truck", "capacity": 800, "status": "AVAILABLE", "base": "dep-a"},
]
DEFAULT_WEIGHTS = {"id": "risk_weights", "inventory": 0.35, "transport": 0.25, "weather": 0.15, "demand": 0.25}
SCENARIOS = [
    {"id": "normal", "name": "Normal Operations", "severity": "BASELINE", "description": "All corridors keep their current status and demand follows the seasonal baseline."},
    {"id": "surge", "name": "Sudden Demand Surge", "severity": "HIGH", "description": "Fuel demand rises 42% at the most critical forward location."},
    {"id": "blocked", "name": "Primary Route Blocked", "severity": "CRITICAL", "description": "The primary corridor to the focus location becomes unavailable due to a simulated road closure."},
    {"id": "weather", "name": "Severe Weather", "severity": "HIGH", "description": "Snow and low visibility add 6 hours to every weather-exposed route."},
    {"id": "vehicle", "name": "Vehicle Failure", "severity": "MEDIUM", "description": "Vehicle 04 is removed from the available fleet."},
]
MISSIONS = [
    {"id": "MSN-042", "origin": "Depot A", "destination": "Forward Location C", "resource": "Rations", "quantity": 840, "vehicle": "Vehicle 07", "eta": "04h 20m", "status": "IN TRANSIT"},
    {"id": "MSN-041", "origin": "Distribution Hub North", "destination": "Forward Location D", "resource": "Medical", "quantity": 180, "vehicle": "Vehicle 03", "eta": "01h 50m", "status": "LOADING"},
]


async def seed_twin():
    if await db.locations.count_documents({}) == 0: await db.locations.insert_many([dict(x) for x in SEED_LOCATIONS])
    if await db.routes.count_documents({}) == 0: await db.routes.insert_many([dict(x) for x in SEED_ROUTES])
    if await db.vehicles.count_documents({}) == 0: await db.vehicles.insert_many([dict(x) for x in SEED_VEHICLES])
    if not await db.settings.find_one({"id": "risk_weights"}): await db.settings.insert_one(dict(DEFAULT_WEIGHTS))


def status_for(risk): return "CRITICAL" if risk >= 70 else "WARNING" if risk >= 45 else "NORMAL"


def enrich_locations(locations, routes, weights):
    out = []
    for loc in locations:
        incoming = [r["risk"] for r in routes if loc["id"] in (r["source"], r["destination"])]
        transport = sum(incoming) / len(incoming) if incoming else 10
        factors = {"inventory": 100 - loc["inventory"], "transport": transport, "weather": loc["weather_exposure"], "demand": loc["demand_trend"]}
        risk = round(sum(weights[k] * factors[k] for k in factors))
        out.append({**loc, "risk": risk, "status": status_for(risk), "factors": {k: round(v) for k, v in factors.items()}})
    return out


async def load_twin():
    locations = await db.locations.find({}, {"_id": 0}).to_list(500)
    routes = await db.routes.find({}, {"_id": 0}).to_list(500)
    vehicles = await db.vehicles.find({}, {"_id": 0}).to_list(500)
    weights = await db.settings.find_one({"id": "risk_weights"}, {"_id": 0, "id": 0}) or {k: v for k, v in DEFAULT_WEIGHTS.items() if k != "id"}
    return {"locations": enrich_locations(locations, routes, weights), "routes": routes, "vehicles": vehicles, "weights": weights}
