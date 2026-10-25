from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.plan import router as plan_router
from app.routes.services import router as services_router
from app.routes.status import router as status_router

app = FastAPI(
    title="Nisaarthi API",
    description="Backend API for Nisaarthi - Problem Statement 1.1: The City That Sleeps While You Work",
    version="0.1.0",
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(health_router)
app.include_router(plan_router)
app.include_router(services_router)
app.include_router(status_router)
