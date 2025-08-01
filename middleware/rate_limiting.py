#!/usr/bin/env python3
"""
Rate Limiting Middleware - Production API Protection

This module implements comprehensive rate limiting for the Hybrid AI Council API.
It uses Redis as a backend for distributed rate limiting across multiple instances.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from clients.redis_client import get_redis_connection


@dataclass
class RateLimit:
    """Configuration for a specific rate limit."""
    requests: int  # Number of requests allowed
    window_seconds: int  # Time window in seconds
    scope: str  # Scope identifier (e.g., "ip", "user", "endpoint")


@dataclass 
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    requests_made: int
    requests_remaining: int
    reset_time: int
    retry_after: Optional[int] = None


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with multiple strategies.
    
    Features:
    - Per-IP rate limiting
    - Per-endpoint rate limiting  
    - Burst protection
    - Distributed limiting via Redis
    - Custom limits for different endpoint types
    - WebSocket connection limiting
    """
    
    def __init__(
        self, 
        app,
        enabled: bool = True,
        redis_key_prefix: str = "rate_limit",
        default_limits: Optional[List[RateLimit]] = None
    ):
        super().__init__(app)
        self.enabled = enabled
        self.redis_key_prefix = redis_key_prefix
        self.logger = structlog.get_logger("RateLimitingMiddleware")
        
        # Default rate limits if none provided
        self.default_limits = default_limits or [
            RateLimit(requests=100, window_seconds=60, scope="ip_per_minute"),      # 100 req/min per IP
            RateLimit(requests=1000, window_seconds=3600, scope="ip_per_hour"),    # 1000 req/hour per IP  
            RateLimit(requests=10, window_seconds=60, scope="chat_per_minute"),     # 10 chat/min per IP
            RateLimit(requests=5, window_seconds=60, scope="voice_per_minute"),     # 5 voice/min per IP
        ]
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            "/api/chat/simple": [RateLimit(requests=30, window_seconds=60, scope="endpoint")],
            "/api/voice/chat": [RateLimit(requests=5, window_seconds=60, scope="endpoint")],
            "/api/voice/test": [RateLimit(requests=10, window_seconds=60, scope="endpoint")],
            "/health": [RateLimit(requests=300, window_seconds=60, scope="endpoint")],  # Higher for health checks
        }
        
        # Track WebSocket connections per IP
        self.websocket_connections: Dict[str, int] = {}
        self.max_websocket_per_ip = 5
        
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method."""
        
        if not self.enabled:
            return await call_next(request)
            
        # Skip rate limiting for health checks from localhost (monitoring)
        if request.url.path == "/health" and self._is_localhost(request):
            return await call_next(request)
            
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Check WebSocket connection limits
            if request.url.path.startswith("/ws/"):
                if not self._check_websocket_limit(client_ip):
                    self.logger.warning("WebSocket connection limit exceeded", client_ip=client_ip)
                    raise HTTPException(
                        status_code=429,
                        detail="Too many WebSocket connections from this IP"
                    )
            
            # Check rate limits
            rate_limit_result = await self._check_rate_limits(request, client_ip)
            
            if not rate_limit_result.allowed:
                self.logger.warning("Rate limit exceeded", 
                                  client_ip=client_ip,
                                  path=request.url.path,
                                  requests_made=rate_limit_result.requests_made,
                                  reset_time=rate_limit_result.reset_time)
                
                # Return 429 Too Many Requests with headers
                response = Response(
                    content=json.dumps({
                        "error": "Rate limit exceeded",
                        "requests_remaining": rate_limit_result.requests_remaining,
                        "reset_time": rate_limit_result.reset_time,
                        "retry_after": rate_limit_result.retry_after
                    }),
                    status_code=429,
                    media_type="application/json"
                )
                
                # Add rate limit headers
                self._add_rate_limit_headers(response, rate_limit_result)
                return response
            
            # Process the request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            self._add_rate_limit_headers(response, rate_limit_result)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error("Rate limiting error", error=str(e))
            # On error, allow the request through (fail open)
            return await call_next(request)
    
    async def _check_rate_limits(self, request: Request, client_ip: str) -> RateLimitResult:
        """Check all applicable rate limits for the request."""
        
        # Get applicable limits
        limits_to_check = []
        
        # Add default IP-based limits
        limits_to_check.extend(self.default_limits)
        
        # Add endpoint-specific limits
        endpoint_path = request.url.path
        if endpoint_path in self.endpoint_limits:
            limits_to_check.extend(self.endpoint_limits[endpoint_path])
        
        # Add special limits for chat and voice endpoints
        if "/chat" in endpoint_path:
            limits_to_check.append(RateLimit(requests=10, window_seconds=60, scope="chat"))
        elif "/voice" in endpoint_path:
            limits_to_check.append(RateLimit(requests=5, window_seconds=60, scope="voice"))
        
        # Check each limit
        most_restrictive_result = RateLimitResult(
            allowed=True,
            requests_made=0,
            requests_remaining=999999,
            reset_time=int(time.time()) + 3600
        )
        
        for limit in limits_to_check:
            result = await self._check_single_limit(client_ip, endpoint_path, limit)
            
            if not result.allowed:
                return result  # Return immediately if any limit is exceeded
            
            # Track the most restrictive limit for headers
            if result.requests_remaining < most_restrictive_result.requests_remaining:
                most_restrictive_result = result
        
        return most_restrictive_result
    
    async def _check_single_limit(self, client_ip: str, endpoint: str, limit: RateLimit) -> RateLimitResult:
        """Check a single rate limit using Redis."""
        
        # Create Redis key
        key_parts = [self.redis_key_prefix, limit.scope, client_ip]
        if limit.scope == "endpoint":
            key_parts.append(endpoint.replace("/", "_"))
        
        redis_key = ":".join(key_parts)
        
        try:
            redis_client = get_redis_connection()
            if not redis_client:
                # Redis unavailable - allow request (fail open)
                self.logger.warning("Redis unavailable for rate limiting - allowing request")
                return RateLimitResult(
                    allowed=True,
                    requests_made=0,
                    requests_remaining=limit.requests,
                    reset_time=int(time.time()) + limit.window_seconds
                )
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            current_time = int(time.time())
            window_start = current_time - limit.window_seconds
            
            # Remove old entries outside the time window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiry on the key
            pipe.expire(redis_key, limit.window_seconds + 1)
            
            # Execute pipeline
            results = pipe.execute()
            current_requests = results[1]  # Count after removing old entries
            
            # Check if limit exceeded
            allowed = current_requests < limit.requests
            requests_remaining = max(0, limit.requests - current_requests - 1)
            reset_time = current_time + limit.window_seconds
            retry_after = limit.window_seconds if not allowed else None
            
            return RateLimitResult(
                allowed=allowed,
                requests_made=current_requests + 1,
                requests_remaining=requests_remaining,
                reset_time=reset_time,
                retry_after=retry_after
            )
            
        except Exception as e:
            self.logger.error("Redis rate limiting error", error=str(e), redis_key=redis_key)
            # On Redis error, allow request (fail open)
            return RateLimitResult(
                allowed=True,
                requests_made=0,
                requests_remaining=limit.requests,
                reset_time=int(time.time()) + limit.window_seconds
            )
    
    def _check_websocket_limit(self, client_ip: str) -> bool:
        """Check WebSocket connection limits per IP."""
        current_connections = self.websocket_connections.get(client_ip, 0)
        return current_connections < self.max_websocket_per_ip
    
    def register_websocket_connection(self, client_ip: str):
        """Register a new WebSocket connection."""
        self.websocket_connections[client_ip] = self.websocket_connections.get(client_ip, 0) + 1
        self.logger.debug("WebSocket connection registered", 
                         client_ip=client_ip, 
                         total_connections=self.websocket_connections[client_ip])
    
    def unregister_websocket_connection(self, client_ip: str):
        """Unregister a WebSocket connection."""
        if client_ip in self.websocket_connections:
            self.websocket_connections[client_ip] = max(0, self.websocket_connections[client_ip] - 1)
            if self.websocket_connections[client_ip] == 0:
                del self.websocket_connections[client_ip]
            self.logger.debug("WebSocket connection unregistered", 
                             client_ip=client_ip, 
                             remaining_connections=self.websocket_connections.get(client_ip, 0))
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded headers first (proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _is_localhost(self, request: Request) -> bool:
        """Check if request is from localhost."""
        client_ip = self._get_client_ip(request)
        return client_ip in ["127.0.0.1", "::1", "localhost"]
    
    def _add_rate_limit_headers(self, response: Response, result: RateLimitResult):
        """Add rate limiting headers to response."""
        response.headers["X-RateLimit-Limit"] = str(result.requests_made + result.requests_remaining)
        response.headers["X-RateLimit-Remaining"] = str(result.requests_remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_time)
        
        if result.retry_after:
            response.headers["Retry-After"] = str(result.retry_after)