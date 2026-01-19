"""
Main API Router
Combines all endpoint routers
"""

from fastapi import APIRouter

from app.api.endpoints import events, lookup, alerts, health, auth, feedback, downloads

# Create main router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(lookup.router)
api_router.include_router(alerts.router)
api_router.include_router(feedback.router)  # STEP-8: Feedback & audit sync
api_router.include_router(downloads.router)  # Downloads (proxy executable, artifacts)

__all__ = ["api_router"]
