import time
import uuid
from typing import Callable, Dict, Any
import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.common.logger import get_logger

logger = get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging request and response information.
    
    Logs basic information about all requests and responses like:
    - Request path, method, client IP
    - Response status code
    - Processing time
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "props": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                }
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "props": {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "processing_time_ms": round(process_time * 1000, 2),
                    }
                }
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception as e:
            # Log unhandled exceptions
            process_time = time.time() - start_time
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "props": {
                        "request_id": request_id,
                        "error": str(e),
                        "processing_time_ms": round(process_time * 1000, 2),
                    }
                },
                exc_info=True
            )
            raise

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for basic rate limiting.
    
    Uses Redis to track request counts per IP address.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        redis_client: Any,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Rate limit key
        rate_limit_key = f"rate_limit:{client_ip}"
        
        # Check if rate limit exceeded
        current_count = await self.redis_client.get(rate_limit_key)
        if current_count and int(current_count) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip}",
                extra={"props": {"client_ip": client_ip}}
            )
            
            return Response(
                content=json.dumps({
                    "detail": "Rate limit exceeded. Please try again later."
                }),
                status_code=429,
                media_type="application/json"
            )
        
        # Increment request count
        pipe = self.redis_client.pipeline()
        pipe.incr(rate_limit_key)
        pipe.expire(rate_limit_key, self.window_seconds)
        await pipe.execute()
        
        # Process the request
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; connect-src 'self'"
        
        return response
