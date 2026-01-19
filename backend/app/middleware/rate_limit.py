"""Rate limiting middleware."""

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.security.rate_limiter import ip_rate_limiter, user_rate_limiter, api_key_rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    # Paths that bypass rate limiting
    BYPASS_PATHS = [
        "/health",
        "/api/v1/live",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for bypass paths
        if request.url.path in self.BYPASS_PATHS:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check IP rate limit
        ip_allowed, ip_limit_info = ip_rate_limiter.is_allowed(client_ip)
        
        if not ip_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests from this IP",
                    "rate_limit": ip_limit_info["limit"],
                    "retry_after": ip_limit_info["reset"],
                },
            )
        
        # Try to extract user identifier for user-based rate limiting
        user_id = None
        api_key = request.headers.get("X-API-Key")
        
        if api_key:
            # Check API key rate limit
            key_allowed, key_limit_info = api_key_rate_limiter.is_allowed(api_key)
            
            if not key_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests with this API key",
                        "rate_limit": key_limit_info["limit"],
                        "retry_after": key_limit_info["reset"],
                    },
                )
            user_id = api_key
        else:
            # Try to extract user from JWT (optional)
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Could extract user from token here
                pass
        
        # Check user rate limit if we have a user_id
        if user_id:
            user_allowed, user_limit_info = user_rate_limiter.is_allowed(user_id)
            
            if not user_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Too many requests",
                        "rate_limit": user_limit_info["limit"],
                        "retry_after": user_limit_info["reset"],
                    },
                )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(ip_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(ip_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(ip_limit_info["reset"])
        
        return response
