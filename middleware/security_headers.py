#!/usr/bin/env python3
"""
Security Headers Middleware - Comprehensive Web Security

This module implements security headers and protections for the Hybrid AI Council API.
It adds essential security headers to protect against common web vulnerabilities.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog


@dataclass
class SecurityConfig:
    """Configuration for security headers and policies."""
    
    # Content Security Policy
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'"
    )
    
    # HSTS configuration
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    
    # Referrer Policy
    referrer_policy: str = "strict-origin-when-cross-origin"
    
    # Permissions Policy (formerly Feature Policy)
    permissions_policy: str = (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), "
        "gyroscope=(), accelerometer=()"
    )
    
    # CORS settings for production
    allowed_origins: List[str] = None  # Set to specific domains in production
    allowed_methods: List[str] = None
    allowed_headers: List[str] = None
    allow_credentials: bool = False
    
    # Additional security settings
    enable_xss_protection: bool = True
    enable_content_type_nosniff: bool = True
    enable_frame_options: bool = True
    enable_download_options: bool = True
    enable_cross_origin_embedder_policy: bool = True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security headers middleware.
    
    Features:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options protection
    - X-Content-Type-Options
    - X-XSS-Protection  
    - Referrer Policy
    - Permissions Policy
    - Cross-Origin-Embedder-Policy
    - Server header removal
    """
    
    def __init__(
        self, 
        app,
        config: Optional[SecurityConfig] = None,
        enabled: bool = True
    ):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.enabled = enabled
        self.logger = structlog.get_logger("SecurityHeadersMiddleware")
        
        # Security headers to add
        self.security_headers = self._build_security_headers()
        
    def _build_security_headers(self) -> Dict[str, str]:
        """Build the security headers dictionary."""
        headers = {}
        
        # Content Security Policy
        if self.config.csp_policy:
            headers["Content-Security-Policy"] = self.config.csp_policy
        
        # HSTS (only add in production with HTTPS)
        if self.config.hsts_max_age > 0:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            headers["Strict-Transport-Security"] = hsts_value
        
        # X-Frame-Options
        if self.config.enable_frame_options:
            headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        if self.config.enable_content_type_nosniff:
            headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection (legacy but still useful)
        if self.config.enable_xss_protection:
            headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        if self.config.referrer_policy:
            headers["Referrer-Policy"] = self.config.referrer_policy
        
        # Permissions Policy
        if self.config.permissions_policy:
            headers["Permissions-Policy"] = self.config.permissions_policy
        
        # X-Download-Options (IE specific)
        if self.config.enable_download_options:
            headers["X-Download-Options"] = "noopen"
        
        # Cross-Origin-Embedder-Policy
        if self.config.enable_cross_origin_embedder_policy:
            headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        
        # Cross-Origin-Opener-Policy
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # Cross-Origin-Resource-Policy
        headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        return headers
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method."""
        
        if not self.enabled:
            return await call_next(request)
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response, request)
            
            # Remove server information
            self._remove_server_headers(response)
            
            return response
            
        except Exception as e:
            self.logger.error("Security headers middleware error", error=str(e))
            # Continue processing even if security headers fail
            return await call_next(request)
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add security headers to the response."""
        
        # Add all configured security headers
        for header_name, header_value in self.security_headers.items():
            # Skip HSTS for non-HTTPS requests
            if header_name == "Strict-Transport-Security" and request.url.scheme != "https":
                continue
                
            response.headers[header_name] = header_value
        
        # Add API-specific headers
        if request.url.path.startswith("/api/"):
            # Cache control for API responses
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # WebSocket-specific headers
        if request.url.path.startswith("/ws/"):
            # Remove frame options for WebSocket endpoints
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
        
        # Add custom headers for AI API
        response.headers["X-AI-Council-Version"] = "1.0.0"
        response.headers["X-Powered-By"] = "Hybrid-AI-Council"
    
    def _remove_server_headers(self, response: Response):
        """Remove or modify server identification headers."""
        
        # Remove default server header
        if "server" in response.headers:
            del response.headers["server"]
        
        # Remove FastAPI version info
        if "x-fastapi-version" in response.headers:
            del response.headers["x-fastapi-version"]
    
    def update_cors_for_production(
        self,
        allowed_origins: List[str],
        allowed_methods: Optional[List[str]] = None,
        allowed_headers: Optional[List[str]] = None,
        allow_credentials: bool = False
    ):
        """Update CORS settings for production deployment."""
        
        self.config.allowed_origins = allowed_origins
        self.config.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.config.allowed_headers = allowed_headers or ["*"]
        self.config.allow_credentials = allow_credentials
        
        self.logger.info("CORS configuration updated for production",
                        allowed_origins=allowed_origins,
                        allow_credentials=allow_credentials)


class ProductionSecurityConfig(SecurityConfig):
    """Production-ready security configuration with stricter policies."""
    
    def __init__(self):
        super().__init__()
        
        # Stricter CSP for production
        self.csp_policy = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' wss:; "
            "frame-src 'none'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        # Production CORS - should be configured with specific domains
        self.allowed_origins = []  # Must be set explicitly
        self.allowed_methods = ["GET", "POST", "OPTIONS"]
        self.allowed_headers = ["Content-Type", "Authorization", "X-Request-ID"]
        self.allow_credentials = False
        
        # Enhanced HSTS for production
        self.hsts_max_age = 63072000  # 2 years
        self.hsts_include_subdomains = True
        self.hsts_preload = True