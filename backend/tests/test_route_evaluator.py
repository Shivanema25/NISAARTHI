"""Automated tests for the deterministic route evaluator, boarding-time checks, and operational feasibility."""

from app.engine.route_evaluator import plan_journey
from app.models.schemas import JourneyRequest


def test_normal_journey_meets_deadline_and_is_operationally_feasible():
    """Normal journey (02:15 -> 03:00) has 45m available; top candidate is fully feasible."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="02:15",
        deadline="03:00",
        demo_scenario="normal",
    )
    available_time, deadline_day_offset, ranked_routes = plan_journey(req)

    assert available_time == 45
    assert deadline_day_offset == 0
    assert len(ranked_routes) > 0

    top_route = ranked_routes[0]
    assert top_route.deadline_feasible is True
    assert top_route.transport_available is True
    assert len(top_route.closure_constraints) == 0
    assert top_route.operational_feasibility is True
    assert top_route.feasibility_status == "OPERATIONALLY_FEASIBLE"
    assert top_route.total_duration <= available_time
    assert top_route.arrival_day_offset == 0
    assert any("Deadline feasible" in r for r in top_route.reasons)


def test_impossible_deadline_never_marked_feasible():
    """When deadline allows only 10 minutes (02:15 -> 02:25), routes are marked DEADLINE_EXCEEDED."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="02:15",
        deadline="02:25",
        demo_scenario="impossible_deadline",
    )
    available_time, _, ranked_routes = plan_journey(req)
    assert available_time == 10

    for route in ranked_routes:
        assert route.deadline_feasible is False
        assert route.operational_feasibility is False
        assert route.feasibility_status == "DEADLINE_EXCEEDED"
        assert any("Deadline INFEASIBLE" in r for r in route.reasons)


def test_transport_unavailable_at_boarding_time():
    """Metro route at 02:15 has boarding time 02:24, outside service window (06:00-22:30).

    Even with generous deadline (03:30), route must be operationally infeasible.
    """
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Khapri / MIHAN",
        departure_time="02:15",
        deadline="03:30",
        demo_scenario="transport_unavailable",
    )
    _, _, ranked_routes = plan_journey(req)

    metro_route = next((r for r in ranked_routes if r.route_id == "route_metro_orange_line"), None)
    assert metro_route is not None
    assert metro_route.deadline_feasible is True  # 33m duration <= 75m window
    assert metro_route.transport_available is False  # Offline at boarding
    assert metro_route.operational_feasibility is False  # Overall infeasible
    assert metro_route.feasibility_status == "TRANSPORT_UNAVAILABLE"
    assert any("Transport UNAVAILABLE" in r for r in metro_route.reasons)

    # Check that the metro leg explicitly recorded boarding time and offline status
    metro_leg = next((l for l in metro_route.legs if l.mode == "metro"), None)
    assert metro_leg is not None
    assert metro_leg.scheduled_boarding_time == "02:24"  # 02:15 + 5m walk + 4m wait
    assert metro_leg.transport_available_at_boarding is False


def test_transport_active_at_departure_but_unavailable_at_boarding():
    """A journey starting at 22:25 before Metro closing (22:30), but boarding occurs at 22:34."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Khapri / MIHAN",
        departure_time="22:25",
        deadline="23:30",
    )
    _, _, ranked_routes = plan_journey(req)
    metro_route = next((r for r in ranked_routes if r.route_id == "route_metro_orange_line"), None)
    assert metro_route is not None
    assert metro_route.transport_available is False
    assert metro_route.operational_feasibility is False
    assert metro_route.feasibility_status == "TRANSPORT_UNAVAILABLE"

    metro_leg = next((l for l in metro_route.legs if l.mode == "metro"), None)
    assert metro_leg is not None
    assert metro_leg.scheduled_boarding_time == "22:34"  # 22:25 + 9m
    assert metro_leg.transport_available_at_boarding is False


def test_transport_active_at_actual_boarding():
    """Aapli night bus operates 23:00-05:00; boarding at 02:26 is active."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="02:15",
        deadline="03:00",
    )
    _, _, ranked_routes = plan_journey(req)
    bus_route = next((r for r in ranked_routes if r.route_id == "route_aapli_night_feeder"), None)
    assert bus_route is not None
    assert bus_route.transport_available is True

    bus_leg = next((l for l in bus_route.legs if l.mode == "bus"), None)
    assert bus_leg is not None
    assert bus_leg.scheduled_boarding_time == "02:26"  # 02:15 + 6m walk + 5m wait
    assert bus_leg.transport_available_at_boarding is True


def test_known_closure_constraint_applied():
    """Wardha Road candidate traversing Ajni maintenance closure is marked CLOSURE_CONSTRAINED."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Airport South & MIHAN",
        departure_time="02:15",
        deadline="03:30",
        demo_scenario="closure",
    )
    _, _, ranked_routes = plan_journey(req)

    wardha_route = next((r for r in ranked_routes if r.route_id == "route_wardha_road_express"), None)
    assert wardha_route is not None
    assert wardha_route.deadline_feasible is True  # 35m <= 75m
    assert len(wardha_route.closure_constraints) > 0
    assert wardha_route.operational_feasibility is False
    assert wardha_route.feasibility_status == "CLOSURE_CONSTRAINED"
    assert any("Route CONSTRAINED" in r for r in wardha_route.reasons)


def test_unknown_safety_evidence_lowers_confidence_without_safety_claim():
    """Sector with missing safety telemetry lowers confidence and warns without claiming safety."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Hingna Industrial Area",
        departure_time="02:15",
        deadline="04:00",
    )
    _, _, ranked_routes = plan_journey(req)

    hingna_route = next((r for r in ranked_routes if r.route_id == "route_cross_city_slow"), None)
    assert hingna_route is not None
    assert "LOW" in hingna_route.confidence_indicator
    assert any("Absence of incident reports does NOT imply safety" in w for w in hingna_route.warnings)
    for r in hingna_route.reasons:
        assert "route is safe" not in r.lower()


def test_total_duration_formula_and_legs_consistency():
    """For every route: total_duration == walking + waiting + transport + transfer == sum(leg durations)."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="02:15",
        deadline="03:00",
    )
    _, _, ranked_routes = plan_journey(req)

    for route in ranked_routes:
        expected_total = (
            route.walking_time
            + route.waiting_time
            + route.transport_time
            + route.transfer_time
        )
        assert route.total_duration == expected_total
        assert sum(leg.duration_minutes for leg in route.legs) == route.total_duration


def test_endpoint_matching_filters_candidates():
    """Requesting Sitabuldi to Dharampeth returns ONLY candidates connecting those endpoints."""
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="02:15",
        deadline="03:00",
    )
    _, _, ranked_routes = plan_journey(req)
    assert len(ranked_routes) == 2
    for r in ranked_routes:
        assert r.origin == "Sitabuldi Interchange"
        assert r.destination == "Dharampeth Extension"


def test_journey_with_transfer_calculates_chronological_boarding_at_second_transit_leg():
    """A journey with transfers calculates second transit boarding time after prior walk, transit, and transfer legs."""
    from app.engine.route_evaluator import evaluate_candidate_route

    transfer_candidate = {
        "route_id": "route_multi_leg_transfer",
        "route_name": "Multi-Leg Feeder + Metro Transfer",
        "origin": "Sitabuldi Interchange",
        "destination": "Khapri / MIHAN",
        "walking_time": 5,
        "waiting_time": 0,
        "transport_time": 30,
        "transfer_time": 10,
        "legs": [
            {
                "mode": "walk",
                "instruction": "Walk to Bus Bay",
                "duration_minutes": 5,
            },
            {
                "mode": "bus",
                "instruction": "Board Feeder Bus",
                "duration_minutes": 15,
                "transit_line": "Feeder Bus F-1",
                "transit_operating_hours": "06:00-23:00",
            },
            {
                "mode": "transfer",
                "instruction": "Transfer walk and platform concourse crossing",
                "duration_minutes": 10,
            },
            {
                "mode": "metro",
                "instruction": "Board Connecting Metro",
                "duration_minutes": 15,
                "transit_line": "Metro Line",
                "transit_operating_hours": "06:00-22:30",
            },
        ],
        "transit_mode": "metro",
        "affected_corridors": [],
        "evidence_items": [],
    }

    # Case A: Departure 22:05 -> Leg 2 boards at 22:10 (active), Leg 4 boards at 22:35 (closed at 22:30)
    req_late = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Khapri / MIHAN",
        departure_time="22:05",
        deadline="23:30",
    )
    res_late = evaluate_candidate_route(transfer_candidate, req_late, available_time_minutes=85, incidents=[])
    assert res_late.deadline_feasible is True  # 45m <= 85m
    assert res_late.transport_available is False
    assert res_late.operational_feasibility is False
    assert res_late.feasibility_status == "TRANSPORT_UNAVAILABLE"
    # Verify leg 4 boarding time is 22:35
    leg4 = res_late.legs[3]
    assert leg4.scheduled_boarding_time == "22:35"
    assert leg4.transport_available_at_boarding is False

    # Case B: Departure 08:00 -> Leg 2 boards at 08:05, Leg 4 boards at 08:30 (both active)
    req_day = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Khapri / MIHAN",
        departure_time="08:00",
        deadline="09:30",
    )
    res_day = evaluate_candidate_route(transfer_candidate, req_day, available_time_minutes=90, incidents=[])
    assert res_day.deadline_feasible is True
    assert res_day.transport_available is True
    assert res_day.operational_feasibility is True
    assert res_day.feasibility_status == "OPERATIONALLY_FEASIBLE"
    assert res_day.legs[3].scheduled_boarding_time == "08:30"
    assert res_day.legs[3].transport_available_at_boarding is True


def test_operating_window_crossing_midnight_at_actual_boarding():
    """A nocturnal service operating 23:00-05:00 is active when boarding at 00:10 and inactive at 05:05."""
    from app.engine.route_evaluator import evaluate_candidate_route

    overnight_transit_candidate = {
        "route_id": "route_overnight_bus",
        "route_name": "Overnight Service",
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "walking_time": 20,
        "waiting_time": 0,
        "transport_time": 15,
        "transfer_time": 0,
        "legs": [
            {
                "mode": "walk",
                "instruction": "Walk to bus stop",
                "duration_minutes": 20,
            },
            {
                "mode": "bus",
                "instruction": "Board Night Bus",
                "duration_minutes": 15,
                "transit_line": "Night Bus N-1",
                "transit_operating_hours": "23:00-05:00",
            },
        ],
        "transit_mode": "bus",
        "affected_corridors": [],
        "evidence_items": [],
    }

    # Departure 23:50 + 20m walk = boarding at 00:10 (active)
    req_active = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="23:50",
        deadline="01:00",
    )
    res_active = evaluate_candidate_route(overnight_transit_candidate, req_active, available_time_minutes=70, incidents=[])
    assert res_active.legs[1].scheduled_boarding_time == "00:10"
    assert res_active.legs[1].transport_available_at_boarding is True
    assert res_active.transport_available is True

    # Departure 04:45 + 20m walk = boarding at 05:05 (offline, window closed at 05:00)
    req_offline = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Dharampeth Extension",
        departure_time="04:45",
        deadline="06:00",
    )
    res_offline = evaluate_candidate_route(overnight_transit_candidate, req_offline, available_time_minutes=75, incidents=[])
    assert res_offline.legs[1].scheduled_boarding_time == "05:05"
    assert res_offline.legs[1].transport_available_at_boarding is False
    assert res_offline.transport_available is False
    assert res_offline.feasibility_status == "TRANSPORT_UNAVAILABLE"


def test_four_quadrant_operational_feasibility_rules():
    """Exhaustively verify all four operational feasibility classifications derived from hard constraints."""
    # 1. Feasible: meets deadline, transport active, no closures
    req_feasible = JourneyRequest(demo_scenario="normal")
    _, _, routes_f = plan_journey(req_feasible)
    top_f = routes_f[0]
    assert top_f.deadline_feasible is True
    assert top_f.transport_available is True
    assert len(top_f.closure_constraints) == 0
    assert top_f.operational_feasibility is True
    assert top_f.feasibility_status == "OPERATIONALLY_FEASIBLE"

    # 2. Transport unavailable: meets deadline, but transit is offline at boarding
    req_trans_unavail = JourneyRequest(demo_scenario="transport_unavailable")
    _, _, routes_tu = plan_journey(req_trans_unavail)
    metro_tu = next(r for r in routes_tu if r.route_id == "route_metro_orange_line")
    assert metro_tu.deadline_feasible is True
    assert metro_tu.transport_available is False
    assert metro_tu.operational_feasibility is False
    assert metro_tu.feasibility_status == "TRANSPORT_UNAVAILABLE"

    # 3. Closure constrained: meets deadline, but intersects active corridor closure
    req_closure = JourneyRequest(demo_scenario="closure")
    _, _, routes_cl = plan_journey(req_closure)
    wardha_cl = next(r for r in routes_cl if r.route_id == "route_wardha_road_express")
    assert wardha_cl.deadline_feasible is True
    assert len(wardha_cl.closure_constraints) > 0
    assert wardha_cl.operational_feasibility is False
    assert wardha_cl.feasibility_status == "CLOSURE_CONSTRAINED"

    # 4. Deadline exceeded: cannot meet deadline
    req_deadline = JourneyRequest(demo_scenario="impossible_deadline")
    _, _, routes_de = plan_journey(req_deadline)
    for r in routes_de:
        assert r.deadline_feasible is False
        assert r.operational_feasibility is False
        assert r.feasibility_status == "DEADLINE_EXCEEDED"


def test_closure_timing_depart_before_closure_reaches_during_closure():
    """Route departs at 22:50 before closure begins (23:00), but reaches corridor at 23:05 -> CLOSURE_CONSTRAINED."""
    from app.engine.route_evaluator import evaluate_candidate_route

    candidate = {
        "route_id": "route_closure_timing_test",
        "route_name": "Ajni Flyover Corridor Test",
        "origin": "Sitabuldi Interchange",
        "destination": "Airport South & MIHAN",
        "walking_time": 15,
        "waiting_time": 0,
        "transport_time": 20,
        "transfer_time": 0,
        "legs": [
            {
                "mode": "walk",
                "instruction": "Walk to Rahate Colony",
                "duration_minutes": 15,
            },
            {
                "mode": "bus",
                "instruction": "Board Bus traversing Ajni Flyover",
                "duration_minutes": 20,
                "corridor": "Ajni Square / Wardha Road Flyover",
                "transit_line": "Express",
                "transit_operating_hours": "20:00-06:00",
            },
        ],
        "affected_corridors": ["Ajni Square / Wardha Road Flyover"],
        "evidence_items": [],
    }

    incidents = [
        {
            "id": "inc-test-01",
            "title": "Ajni Flyover Maintenance",
            "affected_corridor": "Ajni Square / Wardha Road Flyover",
            "active_hours": "23:00-05:00",
        }
    ]

    # Departure at 22:50. Leg 2 (corridor) reached at 22:50 + 15m = 23:05 (inside 23:00-05:00)
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Airport South & MIHAN",
        departure_time="22:50",
        deadline="23:59",
    )
    res = evaluate_candidate_route(candidate, req, available_time_minutes=69, incidents=incidents)
    assert res.deadline_feasible is True
    assert len(res.closure_constraints) > 0
    assert res.operational_feasibility is False
    assert res.feasibility_status == "CLOSURE_CONSTRAINED"
    assert any("23:05" in r and "23:00-05:00" in r for r in res.reasons)


def test_closure_timing_depart_during_closure_reaches_after_closure():
    """Route departs at 04:45 during closure (23:00-05:00), but reaches corridor at 05:05 -> NOT blocked."""
    from app.engine.route_evaluator import evaluate_candidate_route

    candidate = {
        "route_id": "route_closure_timing_cleared_test",
        "route_name": "Ajni Flyover Post-Closure Test",
        "origin": "Sitabuldi Interchange",
        "destination": "Airport South & MIHAN",
        "walking_time": 20,
        "waiting_time": 0,
        "transport_time": 20,
        "transfer_time": 0,
        "legs": [
            {
                "mode": "walk",
                "instruction": "Walk to Rahate Colony Stop",
                "duration_minutes": 20,
            },
            {
                "mode": "bus",
                "instruction": "Board Bus traversing Ajni Flyover",
                "duration_minutes": 20,
                "corridor": "Ajni Square / Wardha Road Flyover",
                "transit_line": "Express",
                "transit_operating_hours": "00:00-23:59",
            },
        ],
        "affected_corridors": ["Ajni Square / Wardha Road Flyover"],
        "evidence_items": [],
    }

    incidents = [
        {
            "id": "inc-test-01",
            "title": "Ajni Flyover Maintenance",
            "affected_corridor": "Ajni Square / Wardha Road Flyover",
            "active_hours": "23:00-05:00",
        }
    ]

    # Departure at 04:45. Leg 2 reached at 04:45 + 20m = 05:05 (outside 23:00-05:00)
    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Airport South & MIHAN",
        departure_time="04:45",
        deadline="06:00",
    )
    res = evaluate_candidate_route(candidate, req, available_time_minutes=75, incidents=incidents)
    assert res.deadline_feasible is True
    assert len(res.closure_constraints) == 0
    assert res.operational_feasibility is True
    assert res.feasibility_status == "OPERATIONALLY_FEASIBLE"
    assert any("outside closure window 23:00-05:00" in r for r in res.reasons)


def test_closure_timing_active_at_actual_corridor_entry():
    """Route departs at 02:15, enters corridor at 02:26 during active closure -> CLOSURE_CONSTRAINED."""
    from app.engine.route_evaluator import evaluate_candidate_route

    candidate = {
        "route_id": "route_wardha_road_express",
        "route_name": "Wardha Road Express Shuttle",
        "origin": "Sitabuldi Interchange",
        "destination": "Airport South & MIHAN",
        "walking_time": 10,
        "waiting_time": 5,
        "transport_time": 20,
        "transfer_time": 0,
        "legs": [
            {"mode": "walk", "duration_minutes": 6},
            {"mode": "wait", "duration_minutes": 5},
            {
                "mode": "bus",
                "duration_minutes": 20,
                "corridor": "Ajni Square / Wardha Road Flyover",
                "transit_line": "Wardha Road Express",
                "transit_operating_hours": "22:00-05:00",
            },
            {"mode": "walk", "duration_minutes": 4},
        ],
        "affected_corridors": ["Ajni Square / Wardha Road Flyover"],
        "evidence_items": [],
    }

    incidents = [
        {
            "id": "inc-test-01",
            "title": "Ajni Flyover Maintenance",
            "affected_corridor": "Ajni Square / Wardha Road Flyover",
            "active_hours": "23:00-05:00",
        }
    ]

    req = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Airport South & MIHAN",
        departure_time="02:15",
        deadline="03:30",
    )
    res = evaluate_candidate_route(candidate, req, available_time_minutes=75, incidents=incidents)
    assert len(res.closure_constraints) > 0
    assert res.operational_feasibility is False
    assert res.feasibility_status == "CLOSURE_CONSTRAINED"
    assert any("02:26" in r for r in res.reasons)


def test_closure_window_crossing_midnight():
    """Corridor entry crossing midnight into +1 day is correctly evaluated against overnight window."""
    from app.engine.route_evaluator import evaluate_candidate_route

    candidate = {
        "route_id": "route_overnight_corridor",
        "route_name": "Overnight Flyover Transit",
        "origin": "Sitabuldi Interchange",
        "destination": "Airport South & MIHAN",
        "walking_time": 15,
        "waiting_time": 0,
        "transport_time": 20,
        "transfer_time": 0,
        "legs": [
            {"mode": "walk", "duration_minutes": 15},
            {
                "mode": "bus",
                "duration_minutes": 20,
                "corridor": "Wardha Road Flyover",
                "transit_line": "Express",
                "transit_operating_hours": "22:00-06:00",
            },
        ],
        "affected_corridors": ["Wardha Road Flyover"],
        "evidence_items": [],
    }

    incidents = [
        {
            "id": "inc-overnight",
            "title": "Night Flyover Closure",
            "affected_corridor": "Wardha Road Flyover",
            "active_hours": "23:00-05:00",
        }
    ]

    # Departure at 23:55. Corridor entry at 23:55 + 15m = 00:10 (inside 23:00-05:00 overnight window)
    req_inside = JourneyRequest(
        origin="Sitabuldi Interchange",
        destination="Airport South & MIHAN",
        departure_time="23:55",
        deadline="01:00",
    )
    res_inside = evaluate_candidate_route(candidate, req_inside, available_time_minutes=65, incidents=incidents)
    assert len(res_inside.closure_constraints) > 0
    assert res_inside.operational_feasibility is False
    assert any("00:10" in r and "23:00-05:00" in r for r in res_inside.reasons)


def test_evidence_freshness_metadata_distinguishes_age_from_threshold():
    """Verify that observed_age_minutes and freshness_limit threshold are separate fields."""
    req = JourneyRequest(demo_scenario="normal")
    _, _, routes = plan_journey(req)
    bus_route = next(r for r in routes if r.route_id == "route_aapli_night_feeder")
    assert len(bus_route.evidence) > 0
    sched_ev = next(e for e in bus_route.evidence if e.fact_type == "transit_schedule")
    # For static seeded data, observed_age_minutes is None (unmeasured/static)
    assert sched_ev.observed_age_minutes is None
    # freshness_limit is the configured source threshold (1440m for published_schedule)
    assert sched_ev.freshness_limit == "1440m threshold"
    assert "1440m threshold" != str(sched_ev.observed_age_minutes)


def test_freshness_threshold_displayed_when_age_is_zero():
    """When an evidence item has age 0 minutes, freshness_limit is still a valid threshold string."""
    from app.engine.route_evaluator import evaluate_candidate_route

    candidate = {
        "route_id": "route_zero_age_test",
        "route_name": "Zero Age Route",
        "origin": "Sitabuldi Interchange",
        "destination": "Dharampeth Extension",
        "walking_time": 10,
        "waiting_time": 0,
        "transport_time": 15,
        "transfer_time": 0,
        "legs": [],
        "evidence_items": [
            {
                "subject": "Direct Sensor Lighting",
                "fact_type": "lighting_observation",
                "value": "Well-lit corridor",
                "source": "direct_sensor",
                "data_age_minutes": 0,
                "is_direct_evidence": True,
            }
        ],
    }
    req = JourneyRequest(demo_scenario="normal")
    res = evaluate_candidate_route(candidate, req, available_time_minutes=45, incidents=[])

    ev = res.evidence[0]
    assert ev.observed_age_minutes == 0
    assert ev.freshness_limit == "30m threshold"
    assert ev.freshness_limit != "0m limit"
