"""Deterministic Route Evaluator for Nisaarthi.

Applies explicit, testable rules to evaluate journey candidates:
- Computes leg durations and total journey duration (walking + waiting + transport + transfer).
- Evaluates deadline feasibility using elapsed time arithmetic across midnight.
- Calculates chronological boarding time for each transit leg and checks operating windows.
- Matches candidate routes strictly to requested origin and destination endpoints.
- Identifies active seeded closures and corridor constraints.
- Evaluates evidence items via the Data Trust Engine.
- Separates time-only feasibility from overall operational feasibility.
- Produces deterministic, explainable ranking and nocturnal warnings.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.adapters.seeded_loader import (
    load_seeded_incidents,
    load_seeded_routes,
)
from app.engine.time_utils import (
    calculate_arrival,
    calculate_available_time,
    is_time_within_window,
    minutes_to_time_str,
    parse_time_to_minutes,
)
from app.models.schemas import (
    DataOrigin,
    FactEvidence,
    JourneyLeg,
    JourneyRequest,
    RouteOption,
    TrustStatus,
)
from app.trust.engine import evaluate_trust, get_source_freshness_threshold

TRANSIT_MODES = {"bus", "metro", "transit", "train"}


def evaluate_candidate_route(
    candidate: Dict[str, Any],
    request: JourneyRequest,
    available_time_minutes: int,
    incidents: List[Dict[str, Any]],
) -> RouteOption:
    """Evaluate a single route candidate against journey parameters, boarding times, and seeded constraints."""
    origin = candidate["origin"]
    destination = candidate["destination"]

    walking_time = candidate.get("walking_time", 0)
    waiting_time = candidate.get("waiting_time", 0)
    transport_time = candidate.get("transport_time", 0)
    transfer_time = candidate.get("transfer_time", 0)

    # Deterministic duration calculation
    total_duration = walking_time + waiting_time + transport_time + transfer_time

    # Calculate arrival clock time and day offset
    estimated_arrival, arrival_day_offset = calculate_arrival(
        request.departure_time, total_duration
    )

    reasons: List[str] = []
    warnings: List[str] = []
    closure_constraints: List[str] = []

    # 1. Deadline Feasibility Check (Time-only)
    deadline_feasible = total_duration <= available_time_minutes
    if deadline_feasible:
        margin = available_time_minutes - total_duration
        day_text = "same day" if arrival_day_offset == 0 else "next calendar day (+1)"
        reasons.append(
            f"Deadline feasible: Journey duration ({total_duration}m) meets available window "
            f"({available_time_minutes}m) with a {margin}m buffer. Arrives at {estimated_arrival} ({day_text})."
        )
    else:
        overdue_minutes = total_duration - available_time_minutes
        reasons.append(
            f"Deadline INFEASIBLE: Journey duration ({total_duration}m) exceeds available window "
            f"({available_time_minutes}m) by {overdue_minutes} minutes. Cannot meet {request.deadline} deadline."
        )

    # 2. Chronological Leg Boarding Time and Transport Operational Availability Check
    dep_mins = parse_time_to_minutes(request.departure_time)
    current_offset_mins = 0
    transport_available = True
    journey_legs: List[JourneyLeg] = []

    raw_legs = candidate.get("legs", [])
    for leg_data in raw_legs:
        leg_mode = leg_data.get("mode", "walk").lower()
        leg_duration = leg_data.get("duration_minutes", 0)
        leg_transit_line = leg_data.get("transit_line")
        leg_operating_hours = leg_data.get("transit_operating_hours")
        leg_constraints = list(leg_data.get("constraints", []))

        boarding_time_str: Optional[str] = None
        leg_transport_available: Optional[bool] = None

        if leg_mode in TRANSIT_MODES and leg_operating_hours:
            # Boarding time is departure time + cumulative minutes elapsed before this leg
            boarding_total_mins = dep_mins + current_offset_mins
            boarding_time_str = minutes_to_time_str(boarding_total_mins)

            in_service = is_time_within_window(boarding_time_str, leg_operating_hours)
            leg_transport_available = in_service

            if not in_service:
                transport_available = False
                reasons.append(
                    f"Transport UNAVAILABLE: {leg_transit_line or 'Transit'} operates during {leg_operating_hours}. "
                    f"At scheduled boarding time {boarding_time_str}, the service is offline."
                )
                warnings.append(
                    f"Required transit leg '{leg_transit_line}' is inactive at boarding time {boarding_time_str}."
                )
            else:
                reasons.append(
                    f"Transport available: {leg_transit_line or 'Transit'} operates within {leg_operating_hours} "
                    f"at scheduled boarding time {boarding_time_str}."
                )

        leg_corridor = leg_data.get("corridor") or leg_data.get("affected_corridor")
        journey_legs.append(
            JourneyLeg(
                mode=leg_data.get("mode", "transit"),
                instruction=leg_data.get("instruction", ""),
                from_name=leg_data.get("from_name", origin),
                to_name=leg_data.get("to_name", destination),
                duration_minutes=leg_duration,
                distance_meters=leg_data.get("distance_meters"),
                transit_line=leg_transit_line,
                transit_operating_hours=leg_operating_hours,
                corridor=leg_corridor,
                scheduled_boarding_time=boarding_time_str,
                transport_available_at_boarding=leg_transport_available,
                constraints=leg_constraints,
            )
        )
        current_offset_mins += leg_duration

    # 3. Active Seeded Closure Constraints (Evaluated chronologically at corridor encounter time)
    affected_corridors = candidate.get("affected_corridors", [])
    corridor_entry_offsets = candidate.get("corridor_entry_offsets", {})

    for incident in incidents:
        inc_corridor = incident.get("affected_corridor", "")
        inc_hours = incident.get("active_hours", "")
        inc_title = incident.get("title", "Active Incident")

        # Check if corridor matches top-level affected_corridors or any individual leg corridor
        corridor_match = any(
            inc_corridor.lower() in c.lower() or c.lower() in inc_corridor.lower()
            for c in affected_corridors
        ) or any(
            leg.corridor and (
                inc_corridor.lower() in leg.corridor.lower() or leg.corridor.lower() in inc_corridor.lower()
            )
            for leg in journey_legs
        )

        if not corridor_match:
            continue

        # Determine chronological corridor encounter timing
        encounter_offset_mins: Optional[int] = None

        # Check documented explicit entry offset on candidate if provided
        for c_key, c_offset in corridor_entry_offsets.items():
            if inc_corridor.lower() in c_key.lower() or c_key.lower() in inc_corridor.lower():
                encounter_offset_mins = int(c_offset)
                break

        # If not explicitly defined, search journey legs chronologically
        if encounter_offset_mins is None:
            accum_offset = 0
            for leg_data in raw_legs:
                l_c = leg_data.get("corridor") or leg_data.get("affected_corridor")
                l_inst = leg_data.get("instruction", "")
                l_constr = " ".join(leg_data.get("constraints", []))

                if (
                    (l_c and (inc_corridor.lower() in l_c.lower() or l_c.lower() in inc_corridor.lower()))
                    or inc_corridor.lower() in l_inst.lower()
                    or inc_corridor.lower() in l_constr.lower()
                ):
                    encounter_offset_mins = accum_offset
                    break
                accum_offset += leg_data.get("duration_minutes", 0)

        # Evaluate closure window at actual corridor encounter time
        if encounter_offset_mins is not None:
            encounter_total_mins = dep_mins + encounter_offset_mins
            encounter_time_str = minutes_to_time_str(encounter_total_mins)

            if is_time_within_window(encounter_time_str, inc_hours):
                closure_constraints.append(f"{inc_title} ({inc_hours})")
                reasons.append(
                    f"Route CONSTRAINED: Path reaches {inc_title} at estimated entry time {encounter_time_str} "
                    f"(+{encounter_offset_mins}m from departure), during active closure window {inc_hours}."
                )
                warnings.append(
                    f"Road closure active on corridor '{inc_corridor}' at estimated encounter time {encounter_time_str}."
                )
            else:
                reasons.append(
                    f"Corridor accessible: Reaches {inc_title} at {encounter_time_str} "
                    f"(+{encounter_offset_mins}m from departure), outside closure window {inc_hours}."
                )
        else:
            # Report limitation honestly when encounter timing is unavailable
            warnings.append(
                f"Exact corridor encounter timing unavailable in seeded model for '{inc_corridor}'. "
                f"Evaluated conservatively against departure time {request.departure_time}."
            )
            if is_time_within_window(request.departure_time, inc_hours):
                closure_constraints.append(f"{inc_title} ({inc_hours})")
                reasons.append(
                    f"Route CONSTRAINED: Path intersects {inc_title}. Exact corridor encounter timing unavailable in seeded model; "
                    f"evaluated conservatively at departure {request.departure_time} (active window {inc_hours})."
                )

    # 4. Overall Operational Feasibility Determination (Separated from Time-only Feasibility)
    operational_feasibility = (
        deadline_feasible
        and transport_available
        and len(closure_constraints) == 0
    )

    if not deadline_feasible:
        feasibility_status = "DEADLINE_EXCEEDED"
    elif not transport_available:
        feasibility_status = "TRANSPORT_UNAVAILABLE"
    elif len(closure_constraints) > 0:
        feasibility_status = "CLOSURE_CONSTRAINED"
    else:
        feasibility_status = "OPERATIONALLY_FEASIBLE"

    # 5. Evaluate Evidence using Data Trust Engine
    evidence_items: List[FactEvidence] = []
    has_unknown_safety = False
    has_probable_schedule = False

    raw_evidence = candidate.get("evidence_items", [])
    for item in raw_evidence:
        src = item.get("source")
        age = item.get("data_age_minutes")
        is_direct = item.get("is_direct_evidence")
        is_safety = bool(item.get("is_safety_evidence")) or "safety" in item.get("fact_type", "").lower()

        status, reason = evaluate_trust(
            source_type=src,
            data_age_minutes=age,
            is_direct_evidence=is_direct,
            is_safety_evidence=is_safety,
            data_origin=DataOrigin.SEEDED,
        )

        if is_safety and status == TrustStatus.UNKNOWN:
            has_unknown_safety = True
        if status == TrustStatus.PROBABLE:
            has_probable_schedule = True

        # Correct freshness metadata: separate observed age from configured threshold
        thresh = get_source_freshness_threshold(src)
        freshness_limit_str = f"{thresh}m threshold" if thresh is not None else None
        observed_age = age if (age is not None and age >= 0) else None

        evidence_items.append(
            FactEvidence(
                subject=item.get("subject", "Route Fact"),
                fact_type=item.get("fact_type", "observation"),
                value=item.get("value", "Seeded Value"),
                status=status,
                source=src or "demonstration_seed",
                observed_age_minutes=observed_age,
                retrieval_timestamp=None,  # Static seeded data carries no fabricated live timestamp
                freshness_limit=freshness_limit_str,
                reason=reason,
                data_origin=DataOrigin.SEEDED,
            )
        )

    # 6. Uncertainty Assessment & Scenario-Scoped Confidence Labels
    if has_unknown_safety or candidate.get("route_id") == "route_cross_city_slow":
        confidence_indicator = "LOW (Missing Nocturnal Safety Telemetry)"
        warnings.append(
            "Safety observations unavailable for this sector. Absence of incident reports does NOT imply safety."
        )
        reasons.append("Safety evidence is UNKNOWN: Do not assume unmonitored sectors are safe.")
    elif not transport_available or closure_constraints:
        confidence_indicator = "LOW (Operational Constraints Active)"
    else:
        confidence_indicator = "SCENARIO_DEMO (Seeded Demonstration Model)"

    # Base disclaimer warning
    warnings.append("Seeded demonstration dataset for Nagpur. Live telemetry not connected in Phase 1.")

    return RouteOption(
        route_id=candidate.get("route_id", "route_unknown"),
        route_name=candidate.get("route_name", "Demonstration Route"),
        origin=origin,
        destination=destination,
        legs=journey_legs,
        walking_time=walking_time,
        waiting_time=waiting_time,
        transport_time=transport_time,
        transfer_time=transfer_time,
        total_duration=total_duration,
        estimated_arrival=estimated_arrival,
        arrival_day_offset=arrival_day_offset,
        deadline_feasible=deadline_feasible,
        transport_available=transport_available,
        closure_constraints=closure_constraints,
        operational_feasibility=operational_feasibility,
        feasibility_status=feasibility_status,
        evidence=evidence_items,
        reasons=reasons,
        confidence_indicator=confidence_indicator,
        data_origin=DataOrigin.SIMULATED,
        warnings=warnings,
    )


def plan_journey(request: JourneyRequest) -> Tuple[int, int, List[RouteOption]]:
    """Deterministically plan and rank route alternatives for a validated journey request.

    Filters candidates strictly matching requested origin and destination endpoints.
    Applies scenario-specific configurations when a demo_scenario is requested.

    Returns:
        (available_time_minutes, deadline_day_offset, ranked_route_options)
    """
    available_time_minutes, deadline_day_offset = calculate_available_time(
        request.departure_time, request.deadline
    )

    all_routes = load_seeded_routes()
    incidents = load_seeded_incidents()

    # 1. Endpoint Matching: Filter candidates whose origin and destination match the request
    matched_candidates = [
        r
        for r in all_routes
        if r.get("origin", "").strip().lower() == request.origin.strip().lower()
        and r.get("destination", "").strip().lower() == request.destination.strip().lower()
    ]

    # 2. Scenario-Specific Filtering (when demo_scenario is specified)
    scenario = request.demo_scenario
    if scenario == "transport_unavailable":
        # Target candidates requiring transit to demonstrate boarding-time unavailability
        candidates = [r for r in matched_candidates if r.get("transit_mode") in TRANSIT_MODES] or matched_candidates
    elif scenario == "closure":
        # Target candidates affected by corridor closure to demonstrate active constraint
        candidates = [r for r in matched_candidates if len(r.get("affected_corridors", [])) > 0] or matched_candidates
    else:
        candidates = matched_candidates

    evaluated_routes: List[RouteOption] = []
    for candidate in candidates:
        evaluated = evaluate_candidate_route(
            candidate=candidate,
            request=request,
            available_time_minutes=available_time_minutes,
            incidents=incidents,
        )
        evaluated_routes.append(evaluated)

    # 3. Deterministic Ranking Rules:
    # 1. Fully operationally feasible candidates (operational_feasibility is True) ranked first.
    # 2. Among feasible candidates: sorted by deadline buffer margin descending, then total duration ascending.
    # 3. Infeasible candidates ranked below:
    #    - Priority 1: Deadline-feasible but operational blocker (transport unavailable / closure)
    #    - Priority 2: Deadline-infeasible (cannot arrive on time)
    #    - Sorted by total duration ascending
    def ranking_key(r: RouteOption) -> Tuple[int, int, int]:
        if r.operational_feasibility:
            margin = available_time_minutes - r.total_duration
            return (0, -margin, r.total_duration)
        elif r.deadline_feasible:
            # Feasible on time, but blocked operationally (transit offline or closure)
            return (1, 0, r.total_duration)
        else:
            # Cannot meet deadline
            return (2, 0, r.total_duration)

    ranked_routes = sorted(evaluated_routes, key=ranking_key)
    return available_time_minutes, deadline_day_offset, ranked_routes
