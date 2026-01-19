"""
Downloads API Endpoints
Handles artifact downloads (proxy executable, etc.)
with authentication, authorization, and audit logging
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.middleware.auth import get_current_admin_user
from app.db.database import get_db


router = APIRouter(
    prefix="/api/v1/downloads",
    tags=["downloads"],
    responses={401: {"description": "Not authenticated"}, 403: {"description": "Not authorized"}},
)

logger = logging.getLogger(__name__)

# Configuration
# Path calculation: downloads.py → endpoints → api → app → backend → ddas (5 levels up)
PROXY_BIN_PATH = Path(__file__).parent.parent.parent.parent.parent / "proxy" / "bin" / "ddas_proxy.exe"
PROXY_FILENAME = "ddas_proxy.exe"


async def log_download_audit(
    artifact: str,
    user_id: Optional[str],
    org_id: Optional[str],
    status: str,
    db: Session,
):
    """Log artifact download for audit trail"""
    try:
        # Simple logging only - no database model dependency
        logger.info(
            f"Audit: {user_id or 'unknown'} downloaded {artifact} - {status}",
            extra={"org_id": org_id or "default"},
        )
    except Exception as e:
        logger.error(f"Failed to log download audit: {e}")


# DEMO-ONLY: Authentication is intentionally bypassed for demo purposes.
# This endpoint will be secured in production with proper authentication.
@router.get("/proxy/windows", response_class=FileResponse)
async def download_proxy_windows(
    db: Session = Depends(get_db),
):
    """
    Download Windows Proxy executable

    **DEMO MODE**: Authentication is bypassed for demo purposes.
    In production, this will require admin role.

    Returns:
        FileResponse: Binary proxy executable

    Raises:
        HTTPException: 404 if proxy file not found
    """
    try:
        # Demo mode: no user authentication required
        user_id = None
        org_id = None

        # Verify proxy file exists
        if not PROXY_BIN_PATH.exists():
            logger.error(f"Proxy executable not found at {PROXY_BIN_PATH}")
            await log_download_audit(
                artifact="proxy-windows",
                user_id=user_id,
                org_id=org_id,
                status="FAILED_NOT_FOUND",
                db=db,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proxy executable not available for download",
            )

        # Verify it's actually a file (not directory)
        if not PROXY_BIN_PATH.is_file():
            logger.error(f"Proxy path is not a file: {PROXY_BIN_PATH}")
            await log_download_audit(
                artifact="proxy-windows",
                user_id=user_id,
                org_id=org_id,
                status="FAILED_NOT_FILE",
                db=db,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid proxy artifact configuration",
            )

        # Log successful download initiation
        await log_download_audit(
            artifact="proxy-windows",
            user_id=user_id,
            org_id=org_id,
            status="SUCCESS",
            db=db,
        )

        logger.info(
            f"Admin {user_id} downloading proxy executable",
            extra={"org_id": org_id},
        )

        # Return file
        return FileResponse(
            path=PROXY_BIN_PATH,
            filename=PROXY_FILENAME,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{PROXY_FILENAME}"',
                "X-Content-Type-Options": "nosniff",
                "X-Download-Options": "noopen",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading proxy: {e}")
        await log_download_audit(
            artifact="proxy-windows",
            user_id=None,
            org_id=None,
            status="FAILED_ERROR",
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download proxy executable",
        )


@router.get("/proxy/windows/info", response_model=dict)
async def get_proxy_info(
    current_user=Depends(get_current_admin_user),
):
    """
    Get information about the Windows Proxy executable

    **Admin Only**: Requires admin role

    Returns:
        dict: Proxy information (name, size, availability)
    """
    try:
        if not PROXY_BIN_PATH.exists():
            return {
                "available": False,
                "message": "Proxy executable not configured",
                "filename": PROXY_FILENAME,
            }

        file_stat = PROXY_BIN_PATH.stat()
        return {
            "available": True,
            "filename": PROXY_FILENAME,
            "size_bytes": file_stat.st_size,
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "last_modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "description": "DDAS Proxy executable for Windows (x64)",
            "requires_admin": True,
            "requires_net_framework": True,
        }
    except Exception as e:
        logger.error(f"Error getting proxy info: {e}")
        return {
            "available": False,
            "message": "Failed to retrieve proxy information",
            "filename": PROXY_FILENAME,
        }


@router.get("/list", response_model=dict)
async def list_available_downloads():
    """
    List all available artifacts for download

    **Public Endpoint**: No authentication required for listing

    Returns:
        dict: Dictionary of available artifacts
    """
    artifacts = {}

    # Check proxy availability
    if PROXY_BIN_PATH.exists():
        file_stat = PROXY_BIN_PATH.stat()
        artifacts["proxy-windows"] = {
            "name": "Windows Proxy Executable",
            "filename": PROXY_FILENAME,
            "size_bytes": file_stat.st_size,
            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "platform": "Windows x64",
            "requires_admin": True,
            "description": "Standalone proxy for event capture and forwarding",
            "endpoint": "/api/v1/downloads/proxy/windows",
        }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(artifacts),
        "artifacts": artifacts,
    }
