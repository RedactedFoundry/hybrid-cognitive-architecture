#!/usr/bin/env python3
"""
Tests for Security Middleware

Tests the security middleware components:
- RateLimitingMiddleware: API rate limiting and abuse prevention
- SecurityHeadersMiddleware: Security headers and browser protection  
- RequestValidationMiddleware: Input validation and attack prevention
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, Response, HTTPException
from starlette.datastructures import Headers

from middleware.rate_limiting import RateLimitingMiddleware, RateLimit, RateLimitResult
from middleware.security_headers import SecurityHeadersMiddleware, SecurityConfig
from middleware.request_validation import RequestValidationMiddleware, ValidationConfig


class MockRequest:
    """Mock FastAPI Request for testing."""
    
    def __init__(self, method="GET", url_path="/", headers=None, client_ip="127.0.0.1", query_params=None):
        self.method = method
        self.url = MagicMock()
        self.url.path = url_path
        self.url.scheme = "http"
        self.headers = Headers(headers or {})
        self.client = MagicMock()
        self.client.host = client_ip
        self._query_params = query_params or {}
        self._body = b'{"test": "data"}'
    
    def query_params(self):
        return self._query_params
    
    async def body(self):
        return self._body
    
    async def form(self):
        return {}


class MockResponse:
    """Mock FastAPI Response for testing."""
    
    def __init__(self, status_code=200, content="OK"):
        self.status_code = status_code
        self.content = content
        self.headers = {}


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for rate limiting tests."""
    mock_client = MagicMock()
    mock_client.pipeline.return_value = mock_client
    mock_client.zremrangebyscore.return_value = None
    mock_client.zcard.return_value = 5  # Current request count
    mock_client.zadd.return_value = None
    mock_client.expire.return_value = None
    mock_client.execute.return_value = [None, 5, None, None]  # Pipeline results
    return mock_client


class TestRateLimitingMiddleware:
    """Test rate limiting middleware."""
    
    def test_initialization(self):
        """Test RateLimitingMiddleware initialization."""
        middleware = RateLimitingMiddleware(None, enabled=True)
        assert middleware.enabled is True
        assert len(middleware.default_limits) > 0
        assert middleware.max_websocket_per_ip == 5
    
    def test_rate_limit_configuration(self):
        """Test custom rate limit configuration."""
        custom_limits = [
            RateLimit(requests=50, window_seconds=60, scope="test")
        ]
        middleware = RateLimitingMiddleware(None, default_limits=custom_limits)
        assert middleware.default_limits == custom_limits
    
    def test_get_client_ip(self):
        """Test client IP extraction with proxy headers."""
        middleware = RateLimitingMiddleware(None, enabled=True)
        
        # Test direct IP
        request = MockRequest(client_ip="192.168.1.1")
        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"
        
        # Test X-Forwarded-For header
        request = MockRequest(
            client_ip="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}
        )
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"
        
        # Test X-Real-IP header
        request = MockRequest(
            client_ip="10.0.0.1", 
            headers={"X-Real-IP": "203.0.113.2"}
        )
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.2"
    
    def test_localhost_detection(self):
        """Test localhost request detection."""
        middleware = RateLimitingMiddleware(None, enabled=True)
        
        localhost_ips = ["127.0.0.1", "::1"]
        for ip in localhost_ips:
            request = MockRequest(client_ip=ip)
            assert middleware._is_localhost(request) is True
        
        request = MockRequest(client_ip="203.0.113.1")
        assert middleware._is_localhost(request) is False
    
    @patch('middleware.rate_limiting.get_redis_connection')
    async def test_check_single_limit_success(self, mock_redis, mock_redis_client):
        """Test successful rate limit check."""
        mock_redis.return_value = mock_redis_client
        
        middleware = RateLimitingMiddleware(None, enabled=True)
        limit = RateLimit(requests=100, window_seconds=60, scope="test")
        
        result = await middleware._check_single_limit("127.0.0.1", "/test", limit)
        
        assert isinstance(result, RateLimitResult)
        assert result.allowed is True
    
    @patch('middleware.rate_limiting.get_redis_connection')
    async def test_check_single_limit_exceeded(self, mock_redis, mock_redis_client):
        """Test rate limit exceeded scenario."""
        mock_redis.return_value = mock_redis_client
        mock_redis_client.execute.return_value = [None, 100, None, None]  # Limit exceeded
        
        middleware = RateLimitingMiddleware(None, enabled=True)
        limit = RateLimit(requests=10, window_seconds=60, scope="test")
        
        result = await middleware._check_single_limit("127.0.0.1", "/test", limit)
        
        assert result.allowed is False
        assert result.requests_remaining == 0
    
    def test_websocket_connection_tracking(self):
        """Test WebSocket connection limits."""
        middleware = RateLimitingMiddleware(None, enabled=True)
        client_ip = "192.168.1.1"
        
        # Test registration
        for i in range(3):
            middleware.register_websocket_connection(client_ip)
        assert middleware.websocket_connections[client_ip] == 3
        
        # Test limit checking
        assert middleware._check_websocket_limit(client_ip) is True
        
        # Test exceeding limit
        for i in range(3):  # Total = 6, limit = 5
            middleware.register_websocket_connection(client_ip)
        assert middleware._check_websocket_limit(client_ip) is False
        
        # Test unregistration
        middleware.unregister_websocket_connection(client_ip)
        assert middleware.websocket_connections[client_ip] == 5


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    def test_initialization(self):
        """Test SecurityHeadersMiddleware initialization."""
        config = SecurityConfig()
        middleware = SecurityHeadersMiddleware(None, config=config, enabled=True)
        assert middleware.enabled is True
        assert middleware.config == config
        assert len(middleware.security_headers) > 0
    
    def test_security_headers_generation(self):
        """Test security headers are properly generated."""
        config = SecurityConfig()
        middleware = SecurityHeadersMiddleware(None, config=config, enabled=True)
        
        headers = middleware.security_headers
        
        # Check essential security headers
        assert "Content-Security-Policy" in headers
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Referrer-Policy" in headers
    
    def test_add_security_headers(self):
        """Test security headers are added to responses."""
        config = SecurityConfig()
        middleware = SecurityHeadersMiddleware(None, config=config, enabled=True)
        
        request = MockRequest(url_path="/api/test")
        response = MockResponse()
        
        middleware._add_security_headers(response, request)
        
        # Verify headers were added
        assert "Content-Security-Policy" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Cache-Control" in response.headers  # API-specific header
    
    def test_server_header_removal(self):
        """Test server information headers are removed."""
        config = SecurityConfig()
        middleware = SecurityHeadersMiddleware(None, config=config, enabled=True)
        
        response = MockResponse()
        response.headers["server"] = "FastAPI/0.68.0"
        response.headers["x-fastapi-version"] = "0.68.0"
        
        middleware._remove_server_headers(response)
        
        assert "server" not in response.headers
        assert "x-fastapi-version" not in response.headers


class TestRequestValidationMiddleware:
    """Test request validation middleware."""
    
    def test_initialization(self):
        """Test RequestValidationMiddleware initialization."""
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        assert middleware.enabled is True
        assert middleware.config == config
        assert len(middleware.sql_patterns) > 0
        assert len(middleware.xss_patterns) > 0
    
    def test_request_size_validation(self):
        """Test request size limits."""
        config = ValidationConfig(max_request_size=1024)  # 1KB limit
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test oversized request
        request = MockRequest(headers={"content-length": "2048"})
        
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(middleware._validate_request_size(request))
        assert exc_info.value.status_code == 413
    
    def test_header_validation(self):
        """Test header validation."""
        config = ValidationConfig(max_headers=5)
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test too many headers
        large_headers = {f"header_{i}": f"value_{i}" for i in range(10)}
        request = MockRequest(headers=large_headers)
        
        with pytest.raises(HTTPException) as exc_info:
            middleware._validate_headers(request)
        assert exc_info.value.status_code == 400
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test SQL injection patterns
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM secrets"
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(HTTPException) as exc_info:
                middleware._validate_input_string("test", malicious_input)
            assert exc_info.value.status_code == 400
    
    def test_xss_detection(self):
        """Test XSS attack pattern detection."""
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test XSS patterns
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(HTTPException) as exc_info:
                middleware._validate_input_string("test", malicious_input)
            assert exc_info.value.status_code == 400
    
    def test_path_traversal_detection(self):
        """Test path traversal attack detection."""
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test path traversal patterns
        malicious_inputs = [
            "../etc/passwd",
            "..\\windows\\system32",
            "%2e%2e%2f"  # URL encoded ../
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(HTTPException) as exc_info:
                middleware._validate_input_string("test", malicious_input)
            assert exc_info.value.status_code == 400
    
    def test_safe_input_validation(self):
        """Test that safe inputs pass validation."""
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test safe inputs
        safe_inputs = [
            "Hello, how are you?",
            "What is artificial intelligence?",
            "Please help me with machine learning",
            "I need assistance with Python programming"
        ]
        
        for safe_input in safe_inputs:
            # Should not raise any exception
            middleware._validate_input_string("test", safe_input)
    
    def test_json_content_validation(self):
        """Test JSON content validation."""
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Test safe JSON
        safe_data = {"message": "Hello", "user": "test"}
        middleware._validate_json_content(safe_data)
        
        # Test malicious JSON
        malicious_data = {"message": "<script>alert('xss')</script>"}
        with pytest.raises(HTTPException):
            middleware._validate_json_content(malicious_data)


class TestMiddlewareIntegration:
    """Test integration between middleware components."""
    
    async def test_middleware_disabled(self):
        """Test that disabled middleware passes requests through."""
        middlewares = [
            RateLimitingMiddleware(None, enabled=False),
            SecurityHeadersMiddleware(None, enabled=False),
            RequestValidationMiddleware(None, enabled=False)
        ]
        
        request = MockRequest()
        
        async def mock_call_next(req):
            return MockResponse()
        
        for middleware in middlewares:
            response = await middleware.dispatch(request, mock_call_next)
            assert response.status_code == 200
    
    def test_middleware_fail_closed_behavior(self):
        """Test that middleware fails closed on errors (secure by default)."""
        # This tests that the system blocks requests when validation fails
        config = ValidationConfig()
        middleware = RequestValidationMiddleware(None, config=config, enabled=True)
        
        # Mock the dispatch method to simulate internal validation error
        with patch.object(middleware, '_validate_headers', side_effect=Exception("Unexpected error")):
            request = MockRequest()
            
            # Test that internal errors get converted to HTTPException (fail-closed)
            async def test_dispatch():
                with pytest.raises(HTTPException) as exc_info:
                    await middleware.dispatch(request, lambda r: None)
                
                # Should convert internal error to 400 Bad Request
                assert exc_info.value.status_code == 400
                assert "Request validation failed" in str(exc_info.value.detail)
            
            # Run the async test
            import asyncio
            asyncio.run(test_dispatch())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])