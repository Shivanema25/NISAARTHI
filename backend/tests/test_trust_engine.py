"""Automated unit tests for the Data Trust Engine."""

import pytest
from app.models.schemas import DataOrigin, TrustStatus
from app.trust.config import DEFAULT_TRUST_THRESHOLDS, TrustThresholds
from app.trust.engine import evaluate_trust


def test_recent_credible_direct_evidence_is_known():
    """Recent live direct sensor evidence within its freshness threshold is KNOWN."""
    status, reason = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=15,
        thresholds=DEFAULT_TRUST_THRESHOLDS,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.KNOWN
    assert "15m old <= 30m threshold" in reason


def test_unrecognized_source_with_recent_age_is_unknown():
    """An unrecognized evidence source must NOT become KNOWN even if age is recent."""
    status, reason = evaluate_trust(
        source_type="random_unverified_blog",
        data_age_minutes=2,
        thresholds=DEFAULT_TRUST_THRESHOLDS,
    )
    assert status == TrustStatus.UNKNOWN
    assert "Unrecognized evidence source" in reason


def test_published_schedule_is_probable():
    """Credible published static timetable without live confirmation is PROBABLE."""
    status, reason = evaluate_trust(
        source_type="published_schedule",
        data_age_minutes=120,
        thresholds=DEFAULT_TRUST_THRESHOLDS,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.PROBABLE
    assert "without live transit telemetry" in reason


def test_stale_evidence_becomes_outdated():
    """Direct evidence exceeding the freshness limit is OUTDATED."""
    status, reason = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=45,
        thresholds=DEFAULT_TRUST_THRESHOLDS,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.OUTDATED
    assert "Direct evidence expired" in reason


def test_missing_evidence_becomes_unknown():
    """Missing or empty source metadata yields UNKNOWN."""
    status, reason = evaluate_trust(source_type=None, data_age_minutes=10)
    assert status == TrustStatus.UNKNOWN
    assert "Missing evidence source metadata" in reason

    status_empty, _ = evaluate_trust(source_type="   ", data_age_minutes=10)
    assert status_empty == TrustStatus.UNKNOWN


def test_missing_age_for_published_schedule_remains_probable():
    """Published timetable with unknown age is PROBABLE (static published data)."""
    status, reason = evaluate_trust(
        source_type="published_schedule",
        data_age_minutes=None,
        data_origin=DataOrigin.SEEDED,
    )
    assert status == TrustStatus.PROBABLE
    assert "Published static timetable" in reason


def test_missing_age_for_direct_evidence_is_unknown():
    """Direct evidence without age/timestamp cannot establish freshness and becomes UNKNOWN."""
    status, reason = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=None,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.UNKNOWN
    assert "Direct evidence lacks verified observation timestamp" in reason


def test_seeded_direct_fact_without_genuine_timestamp_is_unknown():
    """A direct fact defined in a seeded demo dataset carries no live timestamp and yields UNKNOWN."""
    status, reason = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=None,
        data_origin=DataOrigin.SEEDED,
    )
    assert status == TrustStatus.UNKNOWN
    assert "lacks genuine live observation timestamp in seeded dataset" in reason


def test_unverified_incident_evidence_is_probable_with_scenario_caveat():
    """A seeded incident advisory is PROBABLE within the demo scenario and discloses unverified status."""
    status, reason = evaluate_trust(
        source_type="traffic_police_bulletin",
        data_age_minutes=None,
        data_origin=DataOrigin.SEEDED,
    )
    assert status == TrustStatus.PROBABLE
    assert "Seeded demonstration scenario constraint" in reason
    assert "unverified against live real-world road operations" in reason


def test_freshness_threshold_boundary_conditions():
    """Test exact boundary: age == threshold is valid, age == threshold + 1 is OUTDATED."""
    custom_thresholds = TrustThresholds(
        direct_evidence_max_age_minutes=20,
        published_schedule_max_age_minutes=600,
        incident_report_max_age_minutes=45,
    )

    # Exactly at threshold -> KNOWN
    status_at_boundary, _ = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=20,
        thresholds=custom_thresholds,
        data_origin=DataOrigin.LIVE,
    )
    assert status_at_boundary == TrustStatus.KNOWN

    # 1 minute past threshold -> OUTDATED
    status_past_boundary, _ = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=21,
        thresholds=custom_thresholds,
        data_origin=DataOrigin.LIVE,
    )
    assert status_past_boundary == TrustStatus.OUTDATED


def test_negative_age_handling():
    """Negative data age is invalid and returns UNKNOWN with an explanation."""
    status, reason = evaluate_trust(source_type="direct_sensor", data_age_minutes=-5)
    assert status == TrustStatus.UNKNOWN
    assert "Invalid negative evidence age" in reason


def test_invalid_threshold_configuration():
    """Invalid zero or negative threshold raises validation error or returns UNKNOWN."""
    with pytest.raises(ValueError, match="strictly positive"):
        TrustThresholds(direct_evidence_max_age_minutes=0)

    with pytest.raises(ValueError, match="strictly positive"):
        TrustThresholds(published_schedule_max_age_minutes=-10)


def test_unknown_safety_evidence_never_claims_safe():
    """Missing or proxy safety evidence must return UNKNOWN, never a safety claim."""
    status, reason = evaluate_trust(
        source_type="missing_report",
        data_age_minutes=None,
        is_safety_evidence=True,
    )
    assert status == TrustStatus.UNKNOWN
    assert "Absence of incident reports does NOT imply safety" in reason


def test_pure_function_deterministic_reproducibility():
    """Identical inputs must produce identical outputs every single time."""
    result1 = evaluate_trust("direct_sensor", 15, data_origin=DataOrigin.LIVE)
    result2 = evaluate_trust("direct_sensor", 15, data_origin=DataOrigin.LIVE)
    assert result1 == result2
    assert result1[0] == TrustStatus.KNOWN


def test_unrecognized_source_with_direct_flag_still_unknown():
    """An unrecognized source must NOT become KNOWN even if caller sets is_direct_evidence=True."""
    status, reason = evaluate_trust(
        source_type="unregistered_diy_telemetry_probe",
        data_age_minutes=3,
        is_direct_evidence=True,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.UNKNOWN
    assert "Unrecognized evidence source" in reason


def test_fresh_published_schedule_never_becomes_known():
    """Published schedules without live confirmation must NOT establish actual current operation (never KNOWN)."""
    status, reason = evaluate_trust(
        source_type="published_schedule",
        data_age_minutes=10,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.PROBABLE
    assert status != TrustStatus.KNOWN
    assert "without live transit telemetry" in reason


def test_outdated_published_schedule_becomes_outdated():
    """Published schedule exceeding the 1440m threshold becomes OUTDATED."""
    status, reason = evaluate_trust(
        source_type="published_schedule",
        data_age_minutes=1500,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.OUTDATED
    assert "Published schedule is outdated" in reason


def test_cached_direct_evidence_is_known_with_cached_provenance_disclosure():
    """Cached direct evidence within freshness threshold is KNOWN without claiming to be live."""
    status, reason = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=15,
        data_origin=DataOrigin.CACHED,
    )
    assert status == TrustStatus.KNOWN
    assert "cached direct evidence" in reason
    assert "record is cached, not live" in reason
    assert "live direct telemetry" not in reason


def test_cached_direct_evidence_expired_becomes_outdated():
    """Cached direct evidence exceeding freshness threshold is OUTDATED."""
    status, reason = evaluate_trust(
        source_type="direct_sensor",
        data_age_minutes=45,
        data_origin=DataOrigin.CACHED,
    )
    assert status == TrustStatus.OUTDATED
    assert "Direct evidence expired" in reason
    assert "Provenance: CACHED" in reason


def test_cached_published_schedule_remains_probable_never_known():
    """Cached published schedule is PROBABLE, never KNOWN."""
    status, reason = evaluate_trust(
        source_type="published_schedule",
        data_age_minutes=120,
        data_origin=DataOrigin.CACHED,
    )
    assert status == TrustStatus.PROBABLE
    assert status != TrustStatus.KNOWN
    assert "cached source" in reason


def test_unrecognized_source_with_cached_provenance_is_unknown():
    """Unrecognized source remains UNKNOWN under CACHED provenance."""
    status, reason = evaluate_trust(
        source_type="random_unofficial_feed",
        data_age_minutes=5,
        data_origin=DataOrigin.CACHED,
    )
    assert status == TrustStatus.UNKNOWN
    assert "Unrecognized evidence source" in reason


def test_missing_safety_evidence_with_live_provenance_remains_unknown():
    """Missing safety evidence with LIVE provenance still returns UNKNOWN and never claims safety."""
    status, reason = evaluate_trust(
        source_type="missing_report",
        data_age_minutes=5,
        is_safety_evidence=True,
        data_origin=DataOrigin.LIVE,
    )
    assert status == TrustStatus.UNKNOWN
    assert "Absence of incident reports does NOT imply safety" in reason


def test_get_source_freshness_threshold_helper():
    """Verify centralized freshness threshold retrieval for all recognized source categories."""
    from app.trust.engine import get_source_freshness_threshold

    assert get_source_freshness_threshold("direct_sensor") == 30
    assert get_source_freshness_threshold("live_telemetry") == 30
    assert get_source_freshness_threshold("published_schedule") == 1440
    assert get_source_freshness_threshold("static_timetable") == 1440
    assert get_source_freshness_threshold("traffic_police_bulletin") == 60
    assert get_source_freshness_threshold("incident_notice") == 60
    assert get_source_freshness_threshold("unrecognized_source_xyz") is None
    assert get_source_freshness_threshold(None) is None
    assert get_source_freshness_threshold("") is None
