"""API route definitions and setup."""

from fastapi import FastAPI

from app.api import ingestion, detection_routes, alerts_endpoints, observability


def setup_routes(app: FastAPI) -> None:
    """Register all API routes."""
    
    # Ingestion routes
    app.include_router(
        ingestion.router,
        prefix="/api/v1/ingest",
        tags=["Ingestion"],
    )
    
    # Detection routes
    app.include_router(
        detection_routes.router,
        prefix="/api/v1/detection",
        tags=["Detection"],
    )
    
    # Alert/Decision routes
    app.include_router(
        alerts_endpoints.router,
        prefix="/api/v1/alerts",
        tags=["Alerts"],
    )
    
    # Observability routes
    app.include_router(
        observability.router,
        prefix="/api/v1/observability",
        tags=["Observability"],
    )
