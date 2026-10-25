"""Automated API integration tests for Phase 1 endpoints and all scenarios."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_post_plan_scenario_normal():
    """POST /api/plan with normal scenario returns 200 and operationally feasible alternatives."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "departure_time": "02:15",
        "deadline": "03:00",
        "needs": ["transport", "pharmacy"],
        "demo_scenario": "normal",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["city"] == "Nagpur, Maharashtra, India"
    assert data["available_time_minutes"] == 45
    assert data["deadline_day_offset"] == 0
    assert len(data["route_options"]) > 0

    top_route = data["route_options"][0]
    assert top_route["deadline_feasible"] is True
    assert top_route["transport_available"] is True
    assert top_route["operational_feasibility"] is True
    assert top_route["feasibility_status"] == "OPERATIONALLY_FEASIBLE"


def test_post_plan_scenario_overnight_rollover():
    """POST /api/plan with overnight departure (23:40 -> 00:30) calculates day offset +1."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "departure_time": "23:40",
        "deadline": "00:30",
        "demo_scenario": "overnight_rollover",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["available_time_minutes"] == 50
    assert data["deadline_day_offset"] == 1

    top_route = data["route_options"][0]
    assert top_route["arrival_day_offset"] == 1
    assert top_route["operational_feasibility"] is True


def test_post_plan_scenario_impossible_deadline():
    """POST /api/plan with impossible deadline flags DEADLINE_EXCEEDED."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "departure_time": "02:15",
        "deadline": "02:25",
        "demo_scenario": "impossible_deadline",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["available_time_minutes"] == 10

    for route in data["route_options"]:
        assert route["deadline_feasible"] is False
        assert route["operational_feasibility"] is False
        assert route["feasibility_status"] == "DEADLINE_EXCEEDED"


def test_post_plan_scenario_transport_unavailable():
    """POST /api/plan with Metro off-hours flags TRANSPORT_UNAVAILABLE."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Khapri / MIHAN",
        "departure_time": "02:15",
        "deadline": "03:30",
        "demo_scenario": "transport_unavailable",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    metro_route = next((r for r in data["route_options"] if r["route_id"] == "route_metro_orange_line"), None)
    assert metro_route is not None
    assert metro_route["transport_available"] is False
    assert metro_route["operational_feasibility"] is False
    assert metro_route["feasibility_status"] == "TRANSPORT_UNAVAILABLE"


def test_post_plan_scenario_closure():
    """POST /api/plan with Ajni Flyover maintenance flags CLOSURE_CONSTRAINED."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Airport South & MIHAN",
        "departure_time": "02:15",
        "deadline": "03:30",
        "demo_scenario": "closure",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()

    wardha_route = next((r for r in data["route_options"] if r["route_id"] == "route_wardha_road_express"), None)
    assert wardha_route is not None
    assert len(wardha_route["closure_constraints"]) > 0
    assert wardha_route["operational_feasibility"] is False
    assert wardha_route["feasibility_status"] == "CLOSURE_CONSTRAINED"


def test_post_plan_unsupported_location_rejected():
    """POST /api/plan with unknown origin/destination returns HTTP 422."""
    payload = {
        "origin": "Mumbai Central",
        "destination": "Dharampeth Extension",
        "departure_time": "02:15",
        "deadline": "03:00",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 422
    assert "Unsupported demonstration origin" in response.text


def test_post_plan_invalid_time_format_rejected():
    """POST /api/plan with malformed time format returns HTTP 422 validation error."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "departure_time": "25:99",
        "deadline": "03:00",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 422


def test_post_plan_unsupported_demo_scenario_rejected():
    """POST /api/plan with unsupported scenario returns HTTP 422."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "departure_time": "02:15",
        "deadline": "03:00",
        "demo_scenario": "unsupported_scenario_xyz",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 422


def test_post_plan_scenario_preset_standalone_normal():
    """POST /api/plan with ONLY demo_scenario='normal' configures inputs and returns OPERATIONALLY_FEASIBLE."""
    response = client.post("/api/plan", json={"demo_scenario": "normal"})
    assert response.status_code == 200
    data = response.json()
    assert data["request_echo"]["origin"] == "Sitabuldi Interchange"
    assert data["request_echo"]["destination"] == "Dharampeth Extension"
    assert data["available_time_minutes"] == 45
    assert len(data["route_options"]) > 0
    top = data["route_options"][0]
    assert top["operational_feasibility"] is True
    assert top["feasibility_status"] == "OPERATIONALLY_FEASIBLE"


def test_post_plan_scenario_preset_standalone_overnight_rollover():
    """POST /api/plan with ONLY demo_scenario='overnight_rollover' evaluates cross-midnight rollover."""
    response = client.post("/api/plan", json={"demo_scenario": "overnight_rollover"})
    assert response.status_code == 200
    data = response.json()
    assert data["available_time_minutes"] == 50
    assert data["deadline_day_offset"] == 1
    top = data["route_options"][0]
    assert top["arrival_day_offset"] == 1
    assert top["operational_feasibility"] is True


def test_post_plan_scenario_preset_standalone_impossible_deadline():
    """POST /api/plan with ONLY demo_scenario='impossible_deadline' evaluates strict 10m window."""
    response = client.post("/api/plan", json={"demo_scenario": "impossible_deadline"})
    assert response.status_code == 200
    data = response.json()
    assert data["available_time_minutes"] == 10
    for r in data["route_options"]:
        assert r["deadline_feasible"] is False
        assert r["feasibility_status"] == "DEADLINE_EXCEEDED"


def test_post_plan_scenario_preset_standalone_transport_unavailable():
    """POST /api/plan with ONLY demo_scenario='transport_unavailable' selects Metro corridor and evaluates off-hours."""
    response = client.post("/api/plan", json={"demo_scenario": "transport_unavailable"})
    assert response.status_code == 200
    data = response.json()
    assert data["request_echo"]["destination"] == "Khapri / MIHAN"
    metro = next(r for r in data["route_options"] if r["route_id"] == "route_metro_orange_line")
    assert metro["transport_available"] is False
    assert metro["feasibility_status"] == "TRANSPORT_UNAVAILABLE"


def test_post_plan_scenario_preset_standalone_closure():
    """POST /api/plan with ONLY demo_scenario='closure' selects Wardha Road corridor and evaluates Ajni Flyover closure."""
    response = client.post("/api/plan", json={"demo_scenario": "closure"})
    assert response.status_code == 200
    data = response.json()
    assert data["request_echo"]["destination"] == "Airport South & MIHAN"
    wardha = next(r for r in data["route_options"] if r["route_id"] == "route_wardha_road_express")
    assert len(wardha["closure_constraints"]) > 0
    assert wardha["feasibility_status"] == "CLOSURE_CONSTRAINED"


def test_post_plan_empty_request_rejected():
    """POST /api/plan with empty body {} returns HTTP 422."""
    response = client.post("/api/plan", json={})
    assert response.status_code == 422


def test_post_plan_missing_deadline_without_scenario_rejected():
    """POST /api/plan without demo_scenario and missing deadline returns HTTP 422."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "departure_time": "02:15",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 422


def test_post_plan_unsupported_destination_rejected():
    """POST /api/plan with unsupported destination returns HTTP 422."""
    payload = {
        "origin": "Sitabuldi Interchange",
        "destination": "Pune Station",
        "departure_time": "02:15",
        "deadline": "03:00",
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 422
    assert "Unsupported demonstration destination" in response.text


def test_get_services_returns_seeded_data():
    """GET /api/services returns seeded Nagpur essential services with correct provenance."""
    response = client.get("/api/services")
    assert response.status_code == 200
    data = response.json()

    assert data["city"] == "Nagpur, Maharashtra, India"
    assert data["data_origin"] == "SEEDED"
    assert len(data["services"]) >= 4

    for s in data["services"]:
        assert s["data_origin"] == "SEEDED"
        assert s["evidence_status"] == "PROBABLE"
        assert "published_hours" in s
        assert "limitations" in s


def test_get_status_reports_correct_data_mode():
    """GET /api/status confirms SEEDED_DEMO mode and no live provider connections."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ready"
    assert data["demo_city"] == "Nagpur, Maharashtra, India"
    assert data["data_mode"] == "SEEDED_DEMO"
    assert data["data_origin"] == "SEEDED"
    assert data["providers_connected"] is False


def test_phase_0_health_check_regression():
    """Verify Phase 0 GET /api/health still functions identically."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Nisaarthi Backend"
