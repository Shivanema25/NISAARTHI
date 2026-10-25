from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

SUPPORTED_ORIGINS = [
    "Sitabuldi Interchange",
]

SUPPORTED_DESTINATIONS = [
    "Dharampeth Extension",
    "Khapri / MIHAN",
    "Airport South & MIHAN",
    "Hingna Industrial Area",
]

SUPPORTED_CORRIDORS = {
    ("Sitabuldi Interchange", "Dharampeth Extension"),
    ("Sitabuldi Interchange", "Khapri / MIHAN"),
    ("Sitabuldi Interchange", "Airport South & MIHAN"),
    ("Sitabuldi Interchange", "Hingna Industrial Area"),
}

ALLOWED_DEMO_SCENARIOS = {
    "normal",
    "overnight_rollover",
    "impossible_deadline",
    "transport_unavailable",
    "closure",
}

DEMO_SCENARIO_CONFIGS: Dict[str, Dict[str, str]] = {
    "normal": {
        "title": "Normal Journey",
        "default_origin": "Sitabuldi Interchange",
        "default_destination": "Dharampeth Extension",
        "default_departure_time": "02:15",
        "default_deadline": "03:00",
        "expected_status": "OPERATIONALLY_FEASIBLE",
        "description": (
            "Sitabuldi to Dharampeth corridor (02:15 -> 03:00). 45-minute window with "
            "Aapli Night Bus Feeder operating 23:00-05:00."
        ),
    },
    "overnight_rollover": {
        "title": "Midnight Rollover",
        "default_origin": "Sitabuldi Interchange",
        "default_destination": "Dharampeth Extension",
        "default_departure_time": "23:40",
        "default_deadline": "00:30",
        "expected_status": "OPERATIONALLY_FEASIBLE",
        "description": (
            "Sitabuldi to Dharampeth corridor crossing midnight (23:40 -> 00:30). "
            "50-minute window into following calendar day (+1)."
        ),
    },
    "impossible_deadline": {
        "title": "Impossible Deadline",
        "default_origin": "Sitabuldi Interchange",
        "default_destination": "Dharampeth Extension",
        "default_departure_time": "02:15",
        "default_deadline": "02:25",
        "expected_status": "DEADLINE_EXCEEDED",
        "description": (
            "Sitabuldi to Dharampeth corridor with strict 10-minute window (02:15 -> 02:25). "
            "All candidate routes exceed deadline."
        ),
    },
    "transport_unavailable": {
        "title": "Transport Unavailable",
        "default_origin": "Sitabuldi Interchange",
        "default_destination": "Khapri / MIHAN",
        "default_departure_time": "02:15",
        "default_deadline": "03:30",
        "expected_status": "TRANSPORT_UNAVAILABLE",
        "description": (
            "Sitabuldi to Khapri corridor via Nagpur Metro Orange Line. "
            "Boarding at 02:24 occurs outside operating hours (06:00-22:30)."
        ),
    },
    "closure": {
        "title": "Road Closure",
        "default_origin": "Sitabuldi Interchange",
        "default_destination": "Airport South & MIHAN",
        "default_departure_time": "02:15",
        "default_deadline": "03:30",
        "expected_status": "CLOSURE_CONSTRAINED",
        "description": (
            "Sitabuldi to Airport South corridor via Wardha Road Express. "
            "Nocturnal Ajni Flyover maintenance closure active during 23:00-05:00."
        ),
    },
}


class DataOrigin(str, Enum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    SEEDED = "SEEDED"
    SIMULATED = "SIMULATED"


class TrustStatus(str, Enum):
    KNOWN = "KNOWN"
    PROBABLE = "PROBABLE"
    OUTDATED = "OUTDATED"
    UNKNOWN = "UNKNOWN"


class FactEvidence(BaseModel):
    subject: str = Field(..., description="Subject or entity of the fact")
    fact_type: str = Field(..., description="Category or metric (e.g., transit_schedule, street_lighting, road_closure)")
    value: Any = Field(..., description="Observed or seeded value")
    status: TrustStatus = Field(..., description="Trust evaluation status")
    source: str = Field(..., description="Source of the evidence (e.g., published_schedule, user_report, demo_seed)")
    observed_age_minutes: Optional[int] = Field(None, ge=0, description="Observed age of evidence in minutes (None if static seeded or unmeasured)")
    retrieval_timestamp: Optional[str] = Field(None, description="Actual retrieval timestamp if available; None for static seeded demo data")
    freshness_limit: Optional[str] = Field(None, description="Configured maximum freshness threshold string (e.g., 30m threshold, 1440m threshold)")
    reason: str = Field(..., description="Deterministic explanation of why this status was assigned")
    data_origin: DataOrigin = Field(DataOrigin.SEEDED, description="Provenance: SEEDED for demonstration data")


class JourneyLeg(BaseModel):
    mode: str = Field(..., description="Transportation mode: walk, wait, bus, metro, auto, transfer")
    instruction: str = Field(..., description="Step instruction")
    from_name: str = Field(..., description="Departure stop or location name")
    to_name: str = Field(..., description="Arrival stop or location name")
    duration_minutes: int = Field(..., ge=0, description="Duration of this leg in minutes")
    distance_meters: Optional[int] = Field(None, ge=0, description="Estimated distance in meters")
    transit_line: Optional[str] = Field(None, description="Name or number of transit line if applicable")
    transit_operating_hours: Optional[str] = Field(None, description="Published operational hours (e.g., 06:00-22:30)")
    corridor: Optional[str] = Field(None, description="Corridor or arterial segment traversed by this leg")
    scheduled_boarding_time: Optional[str] = Field(None, description="Calculated clock time when passenger boards this leg")
    transport_available_at_boarding: Optional[bool] = Field(None, description="Whether transit is in service at boarding time")
    constraints: List[str] = Field(default_factory=list, description="Leg-specific constraints or warnings")


class RouteOption(BaseModel):
    route_id: str = Field(..., description="Unique route candidate identifier")
    route_name: str = Field(..., description="Human-readable route title")
    origin: str = Field(..., description="Origin location")
    destination: str = Field(..., description="Destination location")
    legs: List[JourneyLeg] = Field(..., description="Ordered list of journey legs")
    walking_time: int = Field(..., ge=0, description="Total walking time in minutes")
    waiting_time: int = Field(..., ge=0, description="Expected waiting time in minutes")
    transport_time: int = Field(..., ge=0, description="In-transit time in minutes")
    transfer_time: int = Field(..., ge=0, description="Transfer buffer time in minutes")
    total_duration: int = Field(..., ge=0, description="Sum of walking, waiting, transport, transfer time")
    estimated_arrival: str = Field(..., description="Estimated arrival time in HH:MM format")
    arrival_day_offset: int = Field(..., ge=0, description="0 for same calendar day, 1 for following calendar day")
    deadline_feasible: bool = Field(..., description="Time-only feasibility: whether journey duration <= available window")
    transport_available: bool = Field(..., description="Whether required transit services operate at actual boarding times")
    closure_constraints: List[str] = Field(default_factory=list, description="Active closures or construction constraints")
    operational_feasibility: bool = Field(..., description="Overall hard feasibility: deadline_feasible and transport_available and no closures")
    feasibility_status: str = Field(..., description="Categorized status: OPERATIONALLY_FEASIBLE, TRANSPORT_UNAVAILABLE, CLOSURE_CONSTRAINED, DEADLINE_EXCEEDED")
    evidence: List[FactEvidence] = Field(default_factory=list, description="Evaluated evidence items backing this route")
    reasons: List[str] = Field(..., description="Explainable determination reasons")
    confidence_indicator: str = Field(..., description="Confidence or uncertainty indicator (e.g., SCENARIO_DEMO, LOW)")
    data_origin: DataOrigin = Field(DataOrigin.SIMULATED, description="Derived route calculation provenance")
    warnings: List[str] = Field(default_factory=list, description="Important nocturnal warnings and caveats")


class JourneyRequest(BaseModel):
    origin: Optional[str] = Field(None, min_length=2, max_length=100, description="Starting point in demo city")
    destination: Optional[str] = Field(None, min_length=2, max_length=100, description="End point in demo city")
    departure_time: Optional[str] = Field(None, description="Departure time in HH:MM (24-hour format)")
    deadline: Optional[str] = Field(None, description="Arrival deadline in HH:MM (24-hour format)")
    needs: List[str] = Field(default_factory=list, description="User requirements, e.g. transport, pharmacy, well_lit")
    risk_preference: str = Field("balanced", description="Risk preference (e.g., balanced, cautious)")
    demo_scenario: Optional[str] = Field(None, description="Demonstration scenario preset")

    @model_validator(mode="after")
    def validate_and_populate_scenario(self):
        # 1. If demo_scenario is provided, validate and populate canonical defaults
        if self.demo_scenario is not None:
            norm_scenario = self.demo_scenario.strip().lower()
            if norm_scenario not in ALLOWED_DEMO_SCENARIOS:
                allowed = ", ".join(sorted(ALLOWED_DEMO_SCENARIOS))
                raise ValueError(f"Unsupported demo_scenario '{self.demo_scenario}'. Supported options: {allowed}.")
            self.demo_scenario = norm_scenario
            cfg = DEMO_SCENARIO_CONFIGS[norm_scenario]

            if not self.origin:
                self.origin = cfg["default_origin"]
            if not self.destination:
                self.destination = cfg["default_destination"]
            if not self.departure_time:
                self.departure_time = cfg["default_departure_time"]
            if not self.deadline:
                self.deadline = cfg["default_deadline"]

        # 2. Origin, destination, departure_time, and deadline must be present
        if not self.origin or not self.origin.strip():
            raise ValueError("Origin location is required when demo_scenario is not specified.")
        if not self.destination or not self.destination.strip():
            raise ValueError("Destination location is required when demo_scenario is not specified.")
        if not self.departure_time or not self.departure_time.strip():
            raise ValueError("Departure time is required when demo_scenario is not specified.")
        if not self.deadline or not self.deadline.strip():
            raise ValueError("Deadline is required when demo_scenario is not specified.")

        # 3. Time format validation
        dep_clean = self.departure_time.strip()
        if not TIME_REGEX.match(dep_clean):
            raise ValueError(f"Time '{self.departure_time}' must be in strict 24-hour format HH:MM (00:00 to 23:59).")
        self.departure_time = dep_clean

        dead_clean = self.deadline.strip()
        if not TIME_REGEX.match(dead_clean):
            raise ValueError(f"Time '{self.deadline}' must be in strict 24-hour format HH:MM (00:00 to 23:59).")
        self.deadline = dead_clean

        # 4. Location endpoint validation against supported Nagpur demonstration points
        orig_clean = self.origin.strip()
        matched_origin = next((o for o in SUPPORTED_ORIGINS if o.lower() == orig_clean.lower()), None)
        if not matched_origin:
            supported = ", ".join(SUPPORTED_ORIGINS)
            raise ValueError(f"Unsupported demonstration origin '{orig_clean}'. Supported origins in Nagpur: {supported}.")
        self.origin = matched_origin

        dest_clean = self.destination.strip()
        matched_dest = next((d for d in SUPPORTED_DESTINATIONS if d.lower() == dest_clean.lower()), None)
        if not matched_dest:
            supported = ", ".join(SUPPORTED_DESTINATIONS)
            raise ValueError(f"Unsupported demonstration destination '{dest_clean}'. Supported destinations in Nagpur: {supported}.")
        self.destination = matched_dest

        return self


class JourneyPlanResponse(BaseModel):
    status: str = "success"
    city: str = "Nagpur, Maharashtra, India"
    timezone: str = "Asia/Kolkata"
    request_echo: JourneyRequest
    available_time_minutes: int
    deadline_day_offset: int
    route_options: List[RouteOption]
    limitations_disclaimer: str
    data_origin: DataOrigin = DataOrigin.SEEDED


class EssentialService(BaseModel):
    id: str
    name: str
    service_type: str
    address: str
    location_desc: str
    published_hours: str
    verified_open_now: Optional[bool] = None
    evidence_status: TrustStatus
    data_origin: DataOrigin = DataOrigin.SEEDED
    source: str
    freshness_reason: str
    limitations: str


class ServicesResponse(BaseModel):
    city: str = "Nagpur, Maharashtra, India"
    timezone: str = "Asia/Kolkata"
    services: List[EssentialService]
    data_origin: DataOrigin = DataOrigin.SEEDED
    disclaimer: str


class PlannerStatusResponse(BaseModel):
    status: str = "ready"
    project: str = "Nisaarthi"
    problem_statement: str = "1.1 - The City That Sleeps While You Work"
    demo_city: str = "Nagpur, Maharashtra, India"
    timezone: str = "Asia/Kolkata"
    engine_readiness: str = "Deterministic Evaluator Active"
    data_mode: str = "SEEDED_DEMO"
    data_origin: DataOrigin = DataOrigin.SEEDED
    providers_connected: bool = False
    disclaimer: str
