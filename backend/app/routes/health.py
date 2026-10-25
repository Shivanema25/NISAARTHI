from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
def get_health():
    """Health check endpoint for Nisaarthi backend.

    Returns a simple JSON health response without external dependencies.
    """
    return {
        "status": "healthy",
        "service": "Nisaarthi Backend",
        "version": "0.1.0",
    }
