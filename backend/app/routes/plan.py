from fastapi import APIRouter, HTTPException, status
from app.engine.route_evaluator import plan_journey
from app.models.schemas import DataOrigin, JourneyPlanResponse, JourneyRequest

router = APIRouter(prefix="/api", tags=["Journey Planning"])


@router.post(
    "/plan",
    response_model=JourneyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Plan a nocturnal journey deterministically using seeded Nagpur data",
)
def post_journey_plan(request: JourneyRequest) -> JourneyPlanResponse:
    """Accept a validated journey request and return deterministically evaluated route options.

    Calculates:
    - Available window and midnight-crossing day offsets.
    - Walking, waiting, transport, transfer durations and arrival clock time.
    - Hard feasibility constraints (deadline feasibility, transport operational availability, road closures).
    - Evidence trust levels evaluated via the Data Trust Engine.
    - Explainable decision reasons and nocturnal warnings.
    """
    try:
        available_time, deadline_day_offset, ranked_routes = plan_journey(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Journey planning error: {str(e)}",
        )

    if not ranked_routes:
        disclaimer = (
            f"No seeded demonstration routes connect '{request.origin}' to '{request.destination}' in the Nagpur "
            "demonstration model. Supported corridors from Sitabuldi Interchange: Dharampeth Extension, "
            "Khapri / MIHAN, Airport South & MIHAN, Hingna Industrial Area."
        )
    else:
        disclaimer = (
            "SEEDED DEMO DATA — NOT LIVE NAVIGATION. All calculations are performed deterministically "
            "using Nagpur demonstration datasets. Live OSRM routing, GTFS transit tracking, and Open-Meteo "
            "weather telemetry are not connected in Phase 1."
        )


    return JourneyPlanResponse(
        status="success",
        city="Nagpur, Maharashtra, India",
        timezone="Asia/Kolkata",
        request_echo=request,
        available_time_minutes=available_time,
        deadline_day_offset=deadline_day_offset,
        route_options=ranked_routes,
        limitations_disclaimer=disclaimer,
        data_origin=DataOrigin.SEEDED,
    )
