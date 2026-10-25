from pydantic import BaseModel, Field, field_validator


class TrustThresholds(BaseModel):
    """Configurable freshness thresholds in minutes for deterministic trust evaluation."""
    direct_evidence_max_age_minutes: int = Field(30, description="Max freshness limit for direct observations (default 30m)")
    published_schedule_max_age_minutes: int = Field(1440, description="Max freshness limit for static timetables (default 24h)")
    incident_report_max_age_minutes: int = Field(60, description="Max freshness limit for incident/closure notices (default 60m)")

    @field_validator(
        "direct_evidence_max_age_minutes",
        "published_schedule_max_age_minutes",
        "incident_report_max_age_minutes",
    )
    @classmethod
    def validate_positive(cls, v: int, info) -> int:
        if v <= 0:
            raise ValueError(f"Threshold '{info.field_name}' must be a strictly positive integer, got {v}.")
        return v


DEFAULT_TRUST_THRESHOLDS = TrustThresholds()
