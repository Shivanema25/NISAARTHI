"""Data Trust Engine for Nisaarthi.

A pure, deterministic function that evaluates the trust status of evidence
based strictly on explicit inputs: source type, data age in minutes, provenance,
and configurable freshness thresholds.
"""

from typing import Optional, Tuple
from app.models.schemas import DataOrigin, TrustStatus
from app.trust.config import DEFAULT_TRUST_THRESHOLDS, TrustThresholds

RECOGNIZED_DIRECT_SOURCES = {
    "direct_sensor",
    "verified_check",
    "live_telemetry",
    "field_observation",
    "direct_beacon",
}

RECOGNIZED_SCHEDULE_SOURCES = {
    "published_schedule",
    "static_timetable",
    "official_hours",
    "schedule_catalog",
}

RECOGNIZED_INCIDENT_SOURCES = {
    "incident_notice",
    "traffic_police_bulletin",
    "closure_notice",
    "civic_advisory",
}

RECOGNIZED_DEMO_SOURCES = {
    "demonstration_scenario",
    "demonstration_bulletin",
    "demonstration_seed",
    "demo_catalog",
}

MISSING_SAFETY_SOURCES = {
    "none",
    "missing",
    "missing_report",
    "unmonitored",
    "absence_of_reports",
}

ALL_RECOGNIZED_SOURCES = (
    RECOGNIZED_DIRECT_SOURCES
    | RECOGNIZED_SCHEDULE_SOURCES
    | RECOGNIZED_INCIDENT_SOURCES
    | RECOGNIZED_DEMO_SOURCES
    | MISSING_SAFETY_SOURCES
)


def get_source_freshness_threshold(
    source_type: Optional[str],
    thresholds: Optional[TrustThresholds] = None,
) -> Optional[int]:
    """Return the configured maximum freshness threshold in minutes for a recognized source type.

    Returns None if the source is unrecognized, synthetic without freshness, or unconfigured.
    """
    if not source_type or not source_type.strip():
        return None

    if thresholds is None:
        thresholds = DEFAULT_TRUST_THRESHOLDS

    source_norm = source_type.strip().lower()

    if source_norm in RECOGNIZED_DIRECT_SOURCES:
        return thresholds.direct_evidence_max_age_minutes
    if source_norm in RECOGNIZED_SCHEDULE_SOURCES:
        return thresholds.published_schedule_max_age_minutes
    if source_norm in RECOGNIZED_INCIDENT_SOURCES:
        return thresholds.incident_report_max_age_minutes

    return None


def evaluate_trust(
    source_type: Optional[str],
    data_age_minutes: Optional[int],
    thresholds: Optional[TrustThresholds] = None,
    is_direct_evidence: Optional[bool] = None,
    is_safety_evidence: bool = False,
    data_origin: DataOrigin = DataOrigin.SEEDED,
) -> Tuple[TrustStatus, str]:
    """Deterministically evaluate trust status and produce an explainable reason.

    Pure function: No I/O, no system clock, no external calls, no mutable global state.

    Args:
        source_type: Identifier of evidence source category.
        data_age_minutes: Age of evidence in minutes (None if unavailable/static).
        thresholds: Configured freshness limits (defaults to DEFAULT_TRUST_THRESHOLDS).
        is_direct_evidence: Explicit override for direct vs indirect classification.
        is_safety_evidence: If True, missing or unverified sources always yield UNKNOWN.
        data_origin: Provenance of the evidence record (SEEDED, SIMULATED, LIVE, CACHED).

    Returns:
        (TrustStatus, reason_str)
    """
    if thresholds is None:
        thresholds = DEFAULT_TRUST_THRESHOLDS

    # Validate threshold configuration
    if (
        thresholds.direct_evidence_max_age_minutes <= 0
        or thresholds.published_schedule_max_age_minutes <= 0
        or thresholds.incident_report_max_age_minutes <= 0
    ):
        return (
            TrustStatus.UNKNOWN,
            "Invalid freshness threshold configuration: thresholds must be strictly positive.",
        )

    # 1. Missing or empty source metadata
    if not source_type or not source_type.strip():
        if is_safety_evidence:
            return (
                TrustStatus.UNKNOWN,
                "No verified safety observations available. Absence of incident reports does NOT imply safety.",
            )
        return (
            TrustStatus.UNKNOWN,
            "Missing evidence source metadata: source type was not provided.",
        )

    source_norm = source_type.strip().lower()

    # 2. Safety evidence check: missing or proxy sources must never claim safety
    if is_safety_evidence:
        if (
            source_norm in MISSING_SAFETY_SOURCES
            or "missing" in source_norm
            or data_origin == DataOrigin.SEEDED
            or data_age_minutes is None
        ):
            return (
                TrustStatus.UNKNOWN,
                "Missing nocturnal safety telemetry. Absence of incident reports does NOT imply safety.",
            )

    # 3. Invalid negative age
    if data_age_minutes is not None and data_age_minutes < 0:
        return (
            TrustStatus.UNKNOWN,
            f"Invalid negative evidence age ({data_age_minutes} minutes). Time elapsed cannot be negative.",
        )

    # 4. Unrecognized source check: unrecognized sources must never become KNOWN
    if source_norm not in ALL_RECOGNIZED_SOURCES:
        return (
            TrustStatus.UNKNOWN,
            f"Unrecognized evidence source '{source_type}'. Unverified or unclassified sources cannot establish trust.",
        )

    # 5. Seeded demonstration data handling (synthetic scenario scope)
    if data_origin == DataOrigin.SEEDED or source_norm in RECOGNIZED_DEMO_SOURCES:
        if source_norm in RECOGNIZED_SCHEDULE_SOURCES:
            return (
                TrustStatus.PROBABLE,
                "Published static timetable in seeded demonstration dataset. Expected operating hours without live telemetry.",
            )
        if source_norm in (RECOGNIZED_INCIDENT_SOURCES | RECOGNIZED_DEMO_SOURCES):
            return (
                TrustStatus.PROBABLE,
                "Seeded demonstration scenario constraint. Defined for testing; unverified against live real-world road operations.",
            )
        if source_norm in RECOGNIZED_DIRECT_SOURCES or is_direct_evidence is True:
            return (
                TrustStatus.UNKNOWN,
                "Direct evidence lacks genuine live observation timestamp in seeded dataset.",
            )

    # 6. Live / Cached evidence evaluation (real-world telemetry)
    # Direct evidence
    if source_norm in RECOGNIZED_DIRECT_SOURCES:
        if data_age_minutes is None:
            return (
                TrustStatus.UNKNOWN,
                "Direct evidence lacks verified observation timestamp or age metadata.",
            )
        threshold = thresholds.direct_evidence_max_age_minutes
        if data_age_minutes <= threshold:
            if data_origin == DataOrigin.CACHED:
                return (
                    TrustStatus.KNOWN,
                    f"Recent credible cached direct evidence ({data_age_minutes}m old <= {threshold}m threshold). "
                    "Original observation age preserved; record is cached, not live.",
                )
            elif data_origin == DataOrigin.LIVE:
                return (
                    TrustStatus.KNOWN,
                    f"Recent credible live direct telemetry ({data_age_minutes}m old <= {threshold}m threshold).",
                )
            else:
                return (
                    TrustStatus.UNKNOWN,
                    f"Direct evidence carries non-operational provenance '{data_origin}'. Cannot establish real-world trust.",
                )
        return (
            TrustStatus.OUTDATED,
            f"Direct evidence expired ({data_age_minutes}m old > {threshold}m threshold). Provenance: {data_origin.value}.",
        )

    # Published schedule / operating hours
    if source_norm in RECOGNIZED_SCHEDULE_SOURCES:
        if data_age_minutes is None:
            return (
                TrustStatus.PROBABLE,
                "Published static timetable without live real-time confirmation or timestamp.",
            )
        threshold = thresholds.published_schedule_max_age_minutes
        if data_age_minutes <= threshold:
            origin_label = "cached" if data_origin == DataOrigin.CACHED else "live"
            return (
                TrustStatus.PROBABLE,
                f"Credible published schedule from {origin_label} source ({data_age_minutes}m old <= {threshold}m threshold); "
                "expected operating hours without live transit telemetry.",
            )
        return (
            TrustStatus.OUTDATED,
            f"Published schedule is outdated ({data_age_minutes}m old > {threshold}m threshold). Provenance: {data_origin.value}.",
        )

    # Incident / closure notices
    if source_norm in RECOGNIZED_INCIDENT_SOURCES:
        if data_age_minutes is None:
            return (
                TrustStatus.UNKNOWN,
                "Incident advisory lacks retrieval timestamp or age metadata.",
            )
        threshold = thresholds.incident_report_max_age_minutes
        if data_age_minutes <= threshold:
            if data_origin == DataOrigin.CACHED:
                return (
                    TrustStatus.KNOWN,
                    f"Active verified cached incident advisory ({data_age_minutes}m old <= {threshold}m threshold). "
                    "Cached bulletin, not live.",
                )
            elif data_origin == DataOrigin.LIVE:
                return (
                    TrustStatus.KNOWN,
                    f"Active verified live incident advisory ({data_age_minutes}m old <= {threshold}m threshold).",
                )
            else:
                return (
                    TrustStatus.UNKNOWN,
                    f"Incident advisory carries non-operational provenance '{data_origin}'.",
                )
        origin_label = "Cached" if data_origin == DataOrigin.CACHED else "Live"
        return (
            TrustStatus.OUTDATED,
            f"{origin_label} incident advisory expired ({data_age_minutes}m old > {threshold}m threshold).",
        )

    return (
        TrustStatus.UNKNOWN,
        "Evidence cannot be verified with available metadata.",
    )
