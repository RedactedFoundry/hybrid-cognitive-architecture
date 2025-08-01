#!/usr/bin/env python3
"""
Request Validation Middleware - Input Protection

This module implements request validation and protection against malicious inputs
for the Hybrid AI Council API.
"""

import json
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog


@dataclass
class ValidationConfig:
    """Configuration for request validation."""
    
    # Size limits
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_json_size: int = 1 * 1024 * 1024      # 1MB for JSON
    max_query_params: int = 50
    max_headers: int = 100
    max_header_size: int = 8192  # 8KB
    
    # Content validation
    allowed_content_types: Set[str] = None
    blocked_file_extensions: Set[str] = None
    blocked_user_agents: Set[str] = None
    
    # Input sanitization
    enable_sql_injection_protection: bool = True
    enable_xss_protection: bool = True
    enable_path_traversal_protection: bool = True
    enable_command_injection_protection: bool = True
    
    # Rate limiting per validation
    max_validation_time_ms: int = 100  # Max time to spend on validation


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation and security middleware.
    
    Features:
    - Request size validation
    - Content type validation
    - Input sanitization
    - SQL injection detection
    - XSS protection
    - Path traversal detection
    - Command injection detection
    - User agent filtering
    """
    
    def __init__(
        self,
        app,
        config: Optional[ValidationConfig] = None,
        enabled: bool = True
    ):
        super().__init__(app)
        self.config = config or ValidationConfig()
        self.enabled = enabled
        self.logger = structlog.get_logger("RequestValidationMiddleware")
        
        # Initialize default configurations
        self._init_default_configs()
        
        # Compile regex patterns for performance
        self._compile_security_patterns()
    
    def _init_default_configs(self):
        """Initialize default configuration values."""
        
        if self.config.allowed_content_types is None:
            self.config.allowed_content_types = {
                "application/json",
                "application/x-www-form-urlencoded", 
                "multipart/form-data",
                "text/plain",
                "audio/wav",
                "audio/mpeg",
                "audio/mp4"
            }
        
        if self.config.blocked_file_extensions is None:
            self.config.blocked_file_extensions = {
                ".exe", ".bat", ".cmd", ".com", ".pif", ".scr",
                ".vbs", ".js", ".jar", ".php", ".asp", ".jsp"
            }
        
        if self.config.blocked_user_agents is None:
            self.config.blocked_user_agents = {
                "bot", "crawler", "spider", "scraper", "scanner"
            }
    
    def _compile_security_patterns(self):
        """Compile regex patterns for security checks."""
        
        # SQL injection patterns
        self.sql_patterns = [
            re.compile(r"(\bunion\b.*\bselect\b)", re.IGNORECASE),
            re.compile(r"(\bdrop\b.*\btable\b)", re.IGNORECASE),
            re.compile(r"(\binsert\b.*\binto\b)", re.IGNORECASE),
            re.compile(r"(\bdelete\b.*\bfrom\b)", re.IGNORECASE),
            re.compile(r"(\bupdate\b.*\bset\b)", re.IGNORECASE),
            re.compile(r"(\bselect\b.*\bfrom\b)", re.IGNORECASE),
            re.compile(r"(\bor\b.*\b1\s*=\s*1\b)", re.IGNORECASE),
            re.compile(r"(\band\b.*\b1\s*=\s*1\b)", re.IGNORECASE),
            re.compile(r"(\'.*\bor\b.*\')", re.IGNORECASE),
            re.compile(r"(\-\-)", re.IGNORECASE),
            re.compile(r"(\/\*.*\*\/)", re.IGNORECASE)
        ]
        
        # XSS patterns
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
            re.compile(r"<iframe[^>]*>", re.IGNORECASE),
            re.compile(r"<object[^>]*>", re.IGNORECASE),
            re.compile(r"<embed[^>]*>", re.IGNORECASE),
            re.compile(r"<link[^>]*>", re.IGNORECASE),
            re.compile(r"<meta[^>]*>", re.IGNORECASE)
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            re.compile(r"\.\.\/", re.IGNORECASE),
            re.compile(r"\.\.\\", re.IGNORECASE),
            re.compile(r"%2e%2e%2f", re.IGNORECASE),
            re.compile(r"%2e%2e%5c", re.IGNORECASE),
            re.compile(r"..%2f", re.IGNORECASE),
            re.compile(r"..%5c", re.IGNORECASE)
        ]
        
        # Command injection patterns
        self.command_patterns = [
            re.compile(r"[;&|`]", re.IGNORECASE),
            re.compile(r"\$\([^)]*\)", re.IGNORECASE),
            re.compile(r"`[^`]*`", re.IGNORECASE),
            re.compile(r"\|\s*(cat|ls|pwd|whoami|id|uname)", re.IGNORECASE)
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method."""
        
        if not self.enabled:
            return await call_next(request)
        
        try:
            # Validate request size
            await self._validate_request_size(request)
            
            # Validate headers
            self._validate_headers(request)
            
            # Validate content type
            self._validate_content_type(request)
            
            # Validate user agent
            self._validate_user_agent(request)
            
            # Validate query parameters
            self._validate_query_params(request)
            
            # Read and validate request body if present
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)
            
            # Process the request
            response = await call_next(request)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error("Request validation error", error=str(e))
            # On validation error, reject the request
            raise HTTPException(
                status_code=400,
                detail="Request validation failed"
            )
    
    async def _validate_request_size(self, request: Request):
        """Validate overall request size."""
        
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.config.max_request_size:
                    self.logger.warning("Request too large", 
                                      size=size, 
                                      max_size=self.config.max_request_size)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request entity too large. Maximum size: {self.config.max_request_size} bytes"
                    )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Content-Length header")
    
    def _validate_headers(self, request: Request):
        """Validate request headers."""
        
        headers = dict(request.headers)
        
        # Check number of headers
        if len(headers) > self.config.max_headers:
            self.logger.warning("Too many headers", count=len(headers))
            raise HTTPException(
                status_code=400,
                detail=f"Too many headers. Maximum: {self.config.max_headers}"
            )
        
        # Check header sizes
        for name, value in headers.items():
            if len(name) + len(value) > self.config.max_header_size:
                self.logger.warning("Header too large", header=name)
                raise HTTPException(
                    status_code=400,
                    detail=f"Header too large: {name}"
                )
    
    def _validate_content_type(self, request: Request):
        """Validate request content type."""
        
        content_type = request.headers.get("content-type", "").split(";")[0].strip()
        
        if content_type and content_type not in self.config.allowed_content_types:
            self.logger.warning("Unsupported content type", content_type=content_type)
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported media type: {content_type}"
            )
    
    def _validate_user_agent(self, request: Request):
        """Validate user agent string."""
        
        user_agent = request.headers.get("user-agent", "").lower()
        
        for blocked_agent in self.config.blocked_user_agents:
            if blocked_agent in user_agent:
                self.logger.warning("Blocked user agent", user_agent=user_agent)
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )
    
    def _validate_query_params(self, request: Request):
        """Validate query parameters."""
        
        query_params = dict(request.query_params)
        
        # Check number of parameters
        if len(query_params) > self.config.max_query_params:
            self.logger.warning("Too many query parameters", count=len(query_params))
            raise HTTPException(
                status_code=400,
                detail=f"Too many query parameters. Maximum: {self.config.max_query_params}"
            )
        
        # Validate parameter values
        for key, value in query_params.items():
            self._validate_input_string(f"query param {key}", value)
    
    async def _validate_request_body(self, request: Request):
        """Validate request body content."""
        
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            await self._validate_json_body(request)
        elif "application/x-www-form-urlencoded" in content_type:
            await self._validate_form_body(request)
    
    async def _validate_json_body(self, request: Request):
        """Validate JSON request body."""
        
        try:
            body = await request.body()
            
            # Check JSON size
            if len(body) > self.config.max_json_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"JSON payload too large. Maximum: {self.config.max_json_size} bytes"
                )
            
            # Parse and validate JSON content
            if body:
                json_data = json.loads(body)
                self._validate_json_content(json_data)
                
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    
    async def _validate_form_body(self, request: Request):
        """Validate form data body."""
        
        try:
            form_data = await request.form()
            
            for key, value in form_data.items():
                if isinstance(value, str):
                    self._validate_input_string(f"form field {key}", value)
                    
        except Exception as e:
            self.logger.warning("Form validation error", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid form data")
    
    def _validate_json_content(self, data, path="root"):
        """Recursively validate JSON content."""
        
        if isinstance(data, dict):
            for key, value in data.items():
                self._validate_input_string(f"JSON key {path}.{key}", str(key))
                if isinstance(value, str):
                    self._validate_input_string(f"JSON value {path}.{key}", value)
                elif isinstance(value, (dict, list)):
                    self._validate_json_content(value, f"{path}.{key}")
                    
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str):
                    self._validate_input_string(f"JSON array {path}[{i}]", item)
                elif isinstance(item, (dict, list)):
                    self._validate_json_content(item, f"{path}[{i}]")
    
    def _validate_input_string(self, context: str, value: str):
        """Validate a string input for security threats."""
        
        if not value:
            return
        
        # SQL injection detection
        if self.config.enable_sql_injection_protection:
            for pattern in self.sql_patterns:
                if pattern.search(value):
                    self.logger.warning("SQL injection attempt detected", 
                                      context=context, value=value[:100])
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid input detected"
                    )
        
        # XSS detection
        if self.config.enable_xss_protection:
            for pattern in self.xss_patterns:
                if pattern.search(value):
                    self.logger.warning("XSS attempt detected", 
                                      context=context, value=value[:100])
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid input detected"
                    )
        
        # Path traversal detection
        if self.config.enable_path_traversal_protection:
            for pattern in self.path_traversal_patterns:
                if pattern.search(value):
                    self.logger.warning("Path traversal attempt detected", 
                                      context=context, value=value[:100])
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid input detected"
                    )
        
        # Command injection detection
        if self.config.enable_command_injection_protection:
            for pattern in self.command_patterns:
                if pattern.search(value):
                    self.logger.warning("Command injection attempt detected", 
                                      context=context, value=value[:100])
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid input detected"
                    )