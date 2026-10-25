from fastapi import APIRouter
from app.models.schemas import DataOrigin, PlannerStatusResponse

router = APIRouter(prefix="/api", tags=["Status"])


@router.get(
    "/status",
    response_model=PlannerStatusResponse,
    summary="Get planning engine readiness and data mode status",
)
def get_planner_status() -> PlannerStatusResponse:
    """Return backend status, demonstration city, timezone, and data mode.

    Explicitly confirms that external live providers are not connected in Phase 1.
    """
    return PlannerStatusResponse(
        status="ready",
        project="Nisaarthi",
        problem_statement="1.1 - The City That Sleeps While You Work",
        demo_city="Nagpur, Maharashtra, India",
        timezone="Asia/Kolkata",
        engine_readiness="Deterministic Evaluator Active",
        data_mode="SEEDED_DEMO",
        data_origin=DataOrigin.SEEDED,
        providers_connected=False,
        disclaimer=(
            "Phase 1 operates strictly in SEEDED_DEMO data mode. External APIs (Nebius, Tavily, "
            "Open-Meteo, OSRM) and live databases are not connected."
        ),
    )
