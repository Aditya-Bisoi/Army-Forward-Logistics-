RANK_LABELS = ["PRIMARY", "ALTERNATE", "FALLBACK"]
RANK_COLORS = ["#f3c969", "#4bd38a", "#8fa49a"]


def build_graph(routes, blocked, extra_hours):
    graph = {}
    for r in routes:
        if r["status"] == "BLOCKED" or r["id"] in blocked: continue
        leg = {**r, "hours": round(r["hours"] + extra_hours.get(r["id"], 0), 1)}
        graph.setdefault(r["source"], []).append((r["destination"], leg))
        graph.setdefault(r["destination"], []).append((r["source"], leg))
    return graph


def simple_paths(graph, source, destination, limit=50):
    paths, stack = [], [(source, [source], [])]
    while stack and len(paths) < limit:
        node, visited, legs = stack.pop()
        if node == destination:
            paths.append((visited, legs)); continue
        for nxt, leg in graph.get(node, []):
            if nxt not in visited: stack.append((nxt, visited + [nxt], legs + [leg]))
    return paths


def assign_vehicles(vehicles, source, quantity, excluded):
    pool = [v for v in vehicles if v["status"] == "AVAILABLE" and v["id"] not in excluded]
    local = sorted([v for v in pool if v["base"] == source], key=lambda v: -v["capacity"])
    remote = sorted([v for v in pool if v["base"] != source], key=lambda v: -v["capacity"])
    chosen, total = [], 0
    for v in local + remote:
        if total >= quantity: break
        chosen.append({"id": v["id"], "name": v["name"], "type": v["type"], "capacity": v["capacity"], "base": v["base"]}); total += v["capacity"]
    return chosen, total


def rank_paths(twin, source, destination, quantity, weights, overrides=None, k=3):
    overrides = overrides or {}
    blocked, extra_hours, excluded = set(overrides.get("blocked", [])), overrides.get("extra_hours", {}), set(overrides.get("exclude_vehicles", []))
    names = {l["id"]: l["name"] for l in twin["locations"]}
    coords = {l["id"]: [l["lat"], l["lng"]] for l in twin["locations"]}
    graph = build_graph(twin["routes"], blocked, extra_hours)
    total_w = sum(weights.values()) or 1
    w = {key: weights[key] / total_w for key in ("time", "risk", "capacity")}
    vehicles, vehicle_capacity = assign_vehicles(twin["vehicles"], source, quantity, excluded)
    candidates = []
    for nodes, legs in simple_paths(graph, source, destination):
        hours = round(sum(l["hours"] for l in legs), 1)
        max_risk = max(l["risk"] for l in legs)
        avg_risk = round(sum(l["risk"] * l["hours"] for l in legs) / hours, 1)
        min_capacity = min(l["capacity"] for l in legs)
        effective_capacity = min(min_capacity, vehicle_capacity)
        shortfall = max(0, quantity - effective_capacity) / quantity
        candidates.append({"path": nodes, "path_names": [names[n] for n in nodes], "legs": [{"id": l["id"], "name": l["name"], "hours": l["hours"], "risk": l["risk"], "capacity": l["capacity"], "distance": l["distance"]} for l in legs],
                           "coords": [coords[n] for n in nodes], "hours": hours, "distance": sum(l["distance"] for l in legs), "max_risk": max_risk, "avg_risk": avg_risk, "min_capacity": min_capacity, "shortfall_pct": round(shortfall * 100),
                           "reliability": round(min(l["reliability"] for l in legs))})
    if not candidates: return {"candidates": [], "source": source, "destination": destination, "quantity": quantity, "weights": w, "vehicles": vehicles, "message": "No open corridor connects these nodes under the current conditions."}
    max_hours = max(c["hours"] for c in candidates)
    for c in candidates:
        time_norm = c["hours"] / max_hours
        risk_norm = (0.6 * c["max_risk"] + 0.4 * c["avg_risk"]) / 100
        cap_norm = c["shortfall_pct"] / 100
        penalty = w["time"] * time_norm + w["risk"] * risk_norm + w["capacity"] * cap_norm
        c["breakdown"] = {"time": round(w["time"] * time_norm * 100, 1), "risk": round(w["risk"] * risk_norm * 100, 1), "capacity": round(w["capacity"] * cap_norm * 100, 1)}
        c["score"] = round(100 - penalty * 100, 1)
        c["eta"] = f"{int(c['hours'])}h {int(round((c['hours'] % 1) * 60)):02d}m"
    candidates.sort(key=lambda c: -c["score"])
    top = candidates[:k]
    for i, c in enumerate(top):
        c["rank"] = i + 1; c["label"] = RANK_LABELS[i]; c["color"] = RANK_COLORS[i]
    return {"candidates": top, "evaluated": len(candidates), "source": source, "destination": destination, "quantity": quantity, "weights": w, "vehicles": vehicles, "vehicle_capacity": vehicle_capacity, "capacity_ok": vehicle_capacity >= quantity}
