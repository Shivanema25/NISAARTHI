from fastapi import APIRouter
from app.adapters.seeded_loader import load_seeded_services
from app.models.schemas import DataOrigin, EssentialService, ServicesResponse, TrustStatus

router = APIRouter(prefix="/api", tags=["Essential Services"])


@router.get(
    "/services",
    response_model=ServicesResponse,
    summary="Retrieve seeded essential night services in Nagpur",
)
def get_essential_services() -> ServicesResponse:
    """Return seeded 24/7 essential services (trauma centers, pharmacies, police desks) in Nagpur.

    Operating hours represent published schedules (PROBABLE), not live-verified occupancy or staffing.
    """
    raw_services = load_seeded_services()
    services_list = [
        EssentialService(
            id=s["id"],
            name=s["name"],
            service_type=s["service_type"],
            address=s["address"],
            location_desc=s["location_desc"],
            published_hours=s["published_hours"],
            verified_open_now=s.get("verified_open_now"),
            evidence_status=TrustStatus(s.get("evidence_status", "PROBABLE")),
            data_origin=DataOrigin.SEEDED,
            source=s["source"],
            freshness_reason=s["freshness_reason"],
            limitations=s["limitations"],
        )
        for s in raw_services
    ]

    disclaimer = (
        "SEEDED DEMO DATA. Essential services represent published Nagpur directories. "
        "Published operating hours do not prove real-time operational capacity or staffing in Phase 1."
    )

    return ServicesResponse(
        city="Nagpur, Maharashtra, India",
        timezone="Asia/Kolkata",
        services=services_list,
        data_origin=DataOrigin.SEEDED,
        disclaimer=disclaimer,
    )
