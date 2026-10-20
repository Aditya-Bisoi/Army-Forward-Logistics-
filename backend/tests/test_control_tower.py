"""Backend regression tests for Predictive Forward Logistics Digital Twin.

Covers the new DB-driven contract (iteration 4):
- auth, dashboard contract, forecast, optimizer rank, simulation disruption,
  recommendation decisions, admin CRUD/weights/model, cascade delete and reset.
"""
import io
import os
import time

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
EMAIL = "admin@forwardlogistics.demo"
PASSWORD = "ControlTower2026!"
SEED_LOCATIONS = {"dep-a", "hub-n", "forward-b", "forward-c", "forward-d"}
SEED_ROUTES = {"route-a", "route-b", "route-c", "route-d", "route-e", "route-f"}
SEED_VEHICLES = {f"VH-{i:02d}" for i in range(1, 13)}


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ---------- auth ----------

class TestAuth:
    def test_login_me_logout(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200 and me.json()["email"] == EMAIL
        out = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert out.status_code == 200
        assert s.get(f"{BASE_URL}/api/auth/me", timeout=15).status_code == 401

    def test_unauthenticated_rejected(self):
        for path in ("/api/dashboard", "/api/admin/summary", "/api/admin/locations"):
            r = requests.get(f"{BASE_URL}{path}", timeout=15)
            assert r.status_code == 401, (path, r.status_code)

    def test_bearer_header(self, token):
        r = requests.get(f"{BASE_URL}/api/auth/me",
                         headers={"Authorization": f"Bearer {token}"}, timeout=15)
        assert r.status_code == 200


# ---------- dashboard ----------

class TestDashboard:
    def test_contract(self, client):
        r = client.get(f"{BASE_URL}/api/dashboard", timeout=20)
        assert r.status_code == 200
        b = r.json()
        for k in ("kpis", "locations", "routes", "vehicles", "weights",
                  "alerts", "recommendation", "forecast", "focus",
                  "top_routes", "baseline", "model"):
            assert k in b, f"missing key: {k}"
        assert len(b["locations"]) == 5
        assert len(b["routes"]) == 6
        for loc in b["locations"]:
            for fld in ("risk", "status", "factors", "stock_units", "stock_days",
                        "daily_demand", "reorder_point"):
                assert fld in loc, f"loc missing {fld}: {loc.get('id')}"
            assert set(loc["factors"].keys()) == {"inventory", "transport", "weather", "demand"}
        rec = b["recommendation"]
        assert rec["id"].startswith("REC-")
        assert "action" in rec and rec["action"]
        assert isinstance(rec.get("data_used"), list) and len(rec["data_used"]) > 0
        fc = b["forecast"]
        assert len(fc["labels"]) == 14
        assert len(fc["actual"]) == 7
        assert len(fc["fitted"]) == 7
        assert len(fc["predicted"]) == 7
        assert fc["model"].startswith("rf-demand-")
        assert isinstance(fc["mae"], (int, float))
        assert isinstance(fc["rmse"], (int, float))
        assert isinstance(b["top_routes"], list) and len(b["top_routes"]) >= 1
        for c in b["top_routes"]:
            assert "rank" in c and "color" in c and "coords" in c and "score" in c and "eta" in c


# ---------- forecast ----------

class TestForecast:
    def test_forecast_ok(self, client):
        r = client.get(f"{BASE_URL}/api/forecast",
                       params={"location_id": "forward-b", "resource": "Fuel", "horizon": 7}, timeout=15)
        assert r.status_code == 200
        b = r.json()
        assert len(b["predicted"]) == 7

    def test_unknown_resource_404(self, client):
        r = client.get(f"{BASE_URL}/api/forecast",
                       params={"location_id": "forward-b", "resource": "Toilets", "horizon": 7}, timeout=15)
        assert r.status_code == 404


# ---------- optimizer ----------

class TestOptimizer:
    def test_rank_ok(self, client):
        r = client.post(f"{BASE_URL}/api/optimizer/rank",
                        json={"source": "dep-a", "destination": "forward-b",
                              "quantity": 1300,
                              "weights": {"time": 0.4, "risk": 0.4, "capacity": 0.2}}, timeout=20)
        assert r.status_code == 200, r.text
        b = r.json()
        assert len(b["candidates"]) >= 1
        for i, c in enumerate(b["candidates"]):
            assert c["rank"] == i + 1
            assert "breakdown" in c
        scores = [c["score"] for c in b["candidates"]]
        assert scores == sorted(scores, reverse=True)
        assert "vehicles" in b and "capacity_ok" in b

    def test_rank_weights_affect_score(self, client):
        p1 = client.post(f"{BASE_URL}/api/optimizer/rank",
                         json={"source": "dep-a", "destination": "forward-b",
                               "quantity": 1300,
                               "weights": {"time": 0.9, "risk": 0.05, "capacity": 0.05}}, timeout=20).json()
        p2 = client.post(f"{BASE_URL}/api/optimizer/rank",
                         json={"source": "dep-a", "destination": "forward-b",
                               "quantity": 1300,
                               "weights": {"time": 0.05, "risk": 0.9, "capacity": 0.05}}, timeout=20).json()
        s1 = [c["score"] for c in p1["candidates"]]
        s2 = [c["score"] for c in p2["candidates"]]
        assert s1 != s2

    def test_same_src_dst_400(self, client):
        r = client.post(f"{BASE_URL}/api/optimizer/rank",
                        json={"source": "dep-a", "destination": "dep-a", "quantity": 500}, timeout=15)
        assert r.status_code == 400

    def test_unknown_location_404(self, client):
        r = client.post(f"{BASE_URL}/api/optimizer/rank",
                        json={"source": "nope", "destination": "forward-b", "quantity": 500}, timeout=15)
        assert r.status_code == 404

    def test_bad_quantity_400(self, client):
        r = client.post(f"{BASE_URL}/api/optimizer/rank",
                        json={"source": "dep-a", "destination": "forward-b", "quantity": 0}, timeout=15)
        assert r.status_code == 400


# ---------- scenarios / disruption ----------

@pytest.mark.parametrize("sid", ["normal", "surge", "blocked", "weather", "vehicle"])
def test_disruption_scenarios(client, sid):
    r = client.post(f"{BASE_URL}/api/simulation/disruption",
                    json={"scenario_id": sid}, timeout=25)
    assert r.status_code == 200, (sid, r.text)
    b = r.json()
    for k in ("before", "after", "recommendation", "ranking", "overrides"):
        assert k in b
    for side in ("before", "after"):
        for fld in ("stockout_probability", "risk", "delivery_delay", "stock_days"):
            assert fld in b[side]
    if sid == "blocked":
        assert len(b["overrides"]["blocked"]) >= 1
        assert b["after"]["stockout_probability"] < b["before"]["stockout_probability"]
    if sid == "surge":
        assert b["after"]["stockout_probability"] < b["before"]["stockout_probability"]
    if sid == "weather":
        assert b["overrides"]["extra_hours"]
    if sid == "vehicle":
        assert "VH-04" in b["overrides"]["exclude_vehicles"]


def test_disruption_invalid_404(client):
    r = client.post(f"{BASE_URL}/api/simulation/disruption",
                    json={"scenario_id": "nope"}, timeout=15)
    assert r.status_code == 404


# ---------- recommendation decisions ----------

class TestDecisions:
    def _make_sim(self, client):
        r = client.post(f"{BASE_URL}/api/simulation/disruption",
                        json={"scenario_id": "blocked"}, timeout=25).json()
        return r

    def test_approve(self, client):
        sim = self._make_sim(client)
        rec = sim["recommendation"]
        r = client.post(f"{BASE_URL}/api/recommendations/{rec['id']}/decision",
                        json={"decision": "APPROVE", "recommendation": rec,
                              "scenario_id": "blocked",
                              "before": sim["before"], "after": sim["after"]}, timeout=15)
        assert r.status_code == 200
        b = r.json()
        assert b["audit"]["decision"] == "APPROVE"
        assert b["impact"]["inventory_stabilized"] is True
        assert b["impact"]["stockout_probability"] == sim["after"]["stockout_probability"]

    def test_reject(self, client):
        sim = self._make_sim(client)
        rec = sim["recommendation"]
        r = client.post(f"{BASE_URL}/api/recommendations/{rec['id']}/decision",
                        json={"decision": "REJECT", "recommendation": rec,
                              "scenario_id": "blocked",
                              "before": sim["before"], "after": sim["after"]}, timeout=15)
        assert r.status_code == 200
        assert r.json()["impact"]["inventory_stabilized"] is False

    def test_invalid_decision(self, client):
        r = client.post(f"{BASE_URL}/api/recommendations/REC-X/decision",
                        json={"decision": "NOPE"}, timeout=15)
        assert r.status_code == 400

    def test_audit_newest_first(self, client):
        r = client.get(f"{BASE_URL}/api/audit", timeout=15)
        assert r.status_code == 200
        audit = r.json()
        assert len(audit) >= 1
        ts = [a["timestamp"] for a in audit]
        assert ts == sorted(ts, reverse=True)


# ---------- admin CRUD ----------

class TestAdminCRUD:
    def test_list_entities(self, client):
        for ent in ("locations", "routes", "vehicles"):
            r = client.get(f"{BASE_URL}/api/admin/{ent}", timeout=15)
            assert r.status_code == 200

    def test_vehicle_crud_and_cleanup(self, client):
        # CREATE
        payload = {"name": "TEST QA Tanker", "type": "Fuel Tanker",
                   "capacity": 900, "status": "AVAILABLE", "base": "dep-a"}
        r = client.post(f"{BASE_URL}/api/admin/vehicles", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        vid = r.json()["id"]
        # GET verify
        got = client.get(f"{BASE_URL}/api/admin/vehicles", timeout=15).json()
        assert any(v["id"] == vid and v["capacity"] == 900 for v in got)
        # UPDATE
        payload2 = {**payload, "capacity": 1500}
        r = client.put(f"{BASE_URL}/api/admin/vehicles/{vid}", json=payload2, timeout=15)
        assert r.status_code == 200 and r.json()["capacity"] == 1500
        got = client.get(f"{BASE_URL}/api/admin/vehicles", timeout=15).json()
        assert any(v["id"] == vid and v["capacity"] == 1500 for v in got)
        # DUPLICATE id -> 409
        dup = client.post(f"{BASE_URL}/api/admin/vehicles",
                          json={**payload, "id": vid}, timeout=15)
        assert dup.status_code == 409
        # PUT unknown -> 404
        notf = client.put(f"{BASE_URL}/api/admin/vehicles/VH-does-not-exist",
                          json=payload, timeout=15)
        assert notf.status_code == 404
        # DELETE
        r = client.delete(f"{BASE_URL}/api/admin/vehicles/{vid}", timeout=15)
        assert r.status_code == 200

    def test_route_validation(self, client):
        # unknown source
        r = client.post(f"{BASE_URL}/api/admin/routes",
                        json={"source": "nope", "destination": "forward-b",
                              "name": "Test Bad", "distance": 10, "hours": 2}, timeout=15)
        assert r.status_code == 422
        # same src/dst
        r = client.post(f"{BASE_URL}/api/admin/routes",
                        json={"source": "dep-a", "destination": "dep-a",
                              "name": "Test Same", "distance": 10, "hours": 2}, timeout=15)
        assert r.status_code == 422

    def test_location_inventory_out_of_range(self, client):
        r = client.post(f"{BASE_URL}/api/admin/locations",
                        json={"name": "TEST Bad", "type": "FORWARD",
                              "lat": 34.0, "lng": 77.0, "troops": 100,
                              "capacity": 1000, "inventory": 120}, timeout=15)
        assert r.status_code == 422

    def test_location_cascade_delete(self, client):
        # Create a disposable location + a route + a vehicle referencing it, then delete location.
        loc_payload = {"id": "TEST-LOC-CAS", "name": "TEST Cascade",
                       "type": "FORWARD", "lat": 34.5, "lng": 77.5,
                       "troops": 50, "capacity": 2000, "inventory": 40,
                       "weather_exposure": 30, "demand_trend": 30, "fuel_base": 200}
        assert client.post(f"{BASE_URL}/api/admin/locations", json=loc_payload, timeout=15).status_code == 200
        route_payload = {"id": "TEST-ROUTE-CAS", "source": "dep-a",
                         "destination": "TEST-LOC-CAS", "name": "Test / Cascade",
                         "distance": 20, "hours": 4}
        assert client.post(f"{BASE_URL}/api/admin/routes", json=route_payload, timeout=15).status_code == 200
        veh_payload = {"id": "TEST-VH-CAS", "name": "TEST VH Cascade",
                       "type": "Cargo Truck", "capacity": 500, "base": "TEST-LOC-CAS"}
        assert client.post(f"{BASE_URL}/api/admin/vehicles", json=veh_payload, timeout=15).status_code == 200
        # delete the location
        r = client.delete(f"{BASE_URL}/api/admin/locations/TEST-LOC-CAS", timeout=15)
        assert r.status_code == 200
        cascade = r.json().get("cascade", {})
        assert cascade.get("routes", 0) >= 1
        assert cascade.get("vehicles", 0) >= 1
        # verify dependents gone
        routes = client.get(f"{BASE_URL}/api/admin/routes", timeout=15).json()
        assert not any(r["id"] == "TEST-ROUTE-CAS" for r in routes)
        vehicles = client.get(f"{BASE_URL}/api/admin/vehicles", timeout=15).json()
        assert not any(v["id"] == "TEST-VH-CAS" for v in vehicles)


# ---------- admin weights ----------

class TestAdminWeights:
    def test_weights_sum_mismatch(self, client):
        r = client.put(f"{BASE_URL}/api/admin/weights",
                       json={"inventory": 0.5, "transport": 0.5,
                             "weather": 0.5, "demand": 0.5}, timeout=15)
        assert r.status_code == 422

    def test_weights_change_affects_dashboard(self, client):
        base = client.get(f"{BASE_URL}/api/dashboard", timeout=20).json()
        risks_before = {l["id"]: l["risk"] for l in base["locations"]}
        # Push weights so that transport dominates
        r = client.put(f"{BASE_URL}/api/admin/weights",
                       json={"inventory": 0.1, "transport": 0.7,
                             "weather": 0.1, "demand": 0.1}, timeout=15)
        assert r.status_code == 200
        after = client.get(f"{BASE_URL}/api/dashboard", timeout=20).json()
        risks_after = {l["id"]: l["risk"] for l in after["locations"]}
        assert risks_before != risks_after
        # Restore defaults
        r = client.put(f"{BASE_URL}/api/admin/weights",
                       json={"inventory": 0.35, "transport": 0.25,
                             "weather": 0.15, "demand": 0.25}, timeout=15)
        assert r.status_code == 200


# ---------- admin model ----------

class TestAdminModel:
    def test_versions_and_active(self, client):
        r = client.get(f"{BASE_URL}/api/admin/model/versions", timeout=15)
        assert r.status_code == 200
        versions = r.json()
        assert len(versions) >= 1
        active = [v for v in versions if v.get("active")]
        assert len(active) == 1

    def test_train_and_activate(self, client):
        before = client.get(f"{BASE_URL}/api/admin/model/versions", timeout=15).json()
        old_active = next(v for v in before if v.get("active"))["version"]
        r = client.post(f"{BASE_URL}/api/admin/model/train",
                        json={"notes": "TEST train"}, timeout=60)
        assert r.status_code == 200, r.text
        new_v = r.json()["version"]
        assert new_v.startswith("rf-demand-0.")
        versions = client.get(f"{BASE_URL}/api/admin/model/versions", timeout=15).json()
        assert next(v for v in versions if v["version"] == new_v)["active"] is True
        # activate old again
        r = client.post(f"{BASE_URL}/api/admin/model/versions/{old_active}/activate", timeout=15)
        assert r.status_code == 200 and r.json()["active"] == old_active
        # restore newest trained as active
        client.post(f"{BASE_URL}/api/admin/model/versions/{new_v}/activate", timeout=15)

    def test_activate_unknown_404(self, client):
        r = client.post(f"{BASE_URL}/api/admin/model/versions/nope/activate", timeout=15)
        assert r.status_code == 404

    def test_history_summary(self, client):
        r = client.get(f"{BASE_URL}/api/admin/model/history", timeout=15)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_csv_upload_valid_and_invalid(self, client):
        # valid: 40 rows for forward-d Fuel
        from datetime import date, timedelta
        rows = ["date,location_id,resource,quantity"]
        d = date.today() - timedelta(days=40)
        for i in range(40):
            rows.append(f"{(d + timedelta(days=i)).isoformat()},forward-d,Fuel,{200 + i}")
        content = "\n".join(rows).encode()
        files = {"file": ("hist.csv", content, "text/csv")}
        r = requests.post(f"{BASE_URL}/api/admin/model/history/upload",
                          headers={"Authorization": client.headers["Authorization"]},
                          files=files, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["rows"] == 40 and body["series_replaced"] >= 1
        # invalid: unknown resource
        bad = "date,location_id,resource,quantity\n2026-01-01,forward-d,UFO,10"
        r = requests.post(f"{BASE_URL}/api/admin/model/history/upload",
                          headers={"Authorization": client.headers["Authorization"]},
                          files={"file": ("bad.csv", bad.encode(), "text/csv")}, timeout=15)
        assert r.status_code == 422
        # missing column
        bad2 = "date,resource,quantity\n2026-01-01,Fuel,10"
        r = requests.post(f"{BASE_URL}/api/admin/model/history/upload",
                          headers={"Authorization": client.headers["Authorization"]},
                          files={"file": ("bad2.csv", bad2.encode(), "text/csv")}, timeout=15)
        assert r.status_code == 422
        # Regenerate restores synthetic rows
        r = client.post(f"{BASE_URL}/api/admin/model/history/regenerate", timeout=60)
        assert r.status_code == 200
        assert r.json()["history_rows"] == 3600


# ---------- final cleanup: reset twin ----------

def test_zz_reset_twin(client):
    """Run last — restores seeded state."""
    r = client.post(f"{BASE_URL}/api/admin/twin/reset", timeout=60)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # verify seeded ids back
    locs = {l["id"] for l in client.get(f"{BASE_URL}/api/admin/locations", timeout=15).json()}
    assert SEED_LOCATIONS <= locs
    routes = {r["id"] for r in client.get(f"{BASE_URL}/api/admin/routes", timeout=15).json()}
    assert SEED_ROUTES <= routes
    vehs = {v["id"] for v in client.get(f"{BASE_URL}/api/admin/vehicles", timeout=15).json()}
    assert SEED_VEHICLES <= vehs
