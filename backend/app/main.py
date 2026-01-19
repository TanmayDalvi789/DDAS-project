"""
DDAS Backend FastAPI Application
Detection and Analysis System REST API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime

from app.config import settings
from app.api.router import api_router
from app.api.schemas import ErrorResponse, ValidationErrorResponse
from app.middleware.auth import APIKeyMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DDAS Detection API",
    description="Detection and Analysis System REST API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# API Key Authentication Middleware
app.add_middleware(APIKeyMiddleware)

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    # Format field errors
    field_errors = {}
    for error in exc.errors():
        field_name = ".".join(str(loc) for loc in error["loc"][1:])
        if field_name not in field_errors:
            field_errors[field_name] = []
        field_errors[field_name].append(error["msg"])
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "status_code": 422,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": field_errors,
        }
    )


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting DDAS Detection API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Initialize database tables
    try:
        from app.db.database import init_db
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
    
    logger.info("✓ API initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down DDAS Detection API")


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DDAS Detection API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "endpoints": {
            "health": "/api/v1/health",
            "stats": "/api/v1/stats",
            "events": "/api/v1/events",
            "detection": "/api/v1/detection",
            "alerts": "/api/v1/alerts",
        }
    }


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

app.include_router(api_router)

# ============================================================================
# 404 HANDLER
# ============================================================================

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def not_found(path_name: str):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": f"Endpoint /{path_name} not found",
            "status_code": 404,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# ============================================================================
# LOGGING MIDDLEWARE
# ============================================================================

@app.middleware("http")
async def log_requests(request, call_next):
    """Log HTTP requests."""
    # Skip logging for health checks
    if request.url.path in ["/api/v1/health", "/api/v1/live"]:
        return await call_next(request)
    
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
    return response


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
