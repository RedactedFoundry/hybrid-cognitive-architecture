#!/usr/bin/env python3
"""
Essential Error Boundaries - Simplified
========================================

Streamlined error handling for the Hybrid AI Council system.
Focuses on core functionality without over-engineering.

No external dependencies to avoid circular imports.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

import structlog

logger = structlog.get_logger("error_boundaries")

T = TypeVar('T')

# ================================
# Core System Exceptions
# ================================

class SystemError(Exception):
    """Base exception for all Hybrid AI Council system errors."""
    
    def __init__(self, message: str, error_code: str = "SYSTEM_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)
        super().__init__(message)


class ProcessingError(SystemError):
    """Error during cognitive processing."""
    
    def __init__(self, message: str, component: str, phase: Optional[str] = None, details: Optional[Dict] = None):
        self.component = component
        self.phase = phase
        super().__init__(message, "PROCESSING_ERROR", details)


class ConnectionError(SystemError):
    """Error connecting to external services."""
    
    def __init__(self, service: str, message: str, retryable: bool = True, details: Optional[Dict] = None):
        self.service = service
        self.retryable = retryable
        super().__init__(message, "CONNECTION_ERROR", details)


class ValidationError(SystemError):
    """Input validation error."""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message, "VALIDATION_ERROR", {"field": field, "value": str(value)})


class TimeoutError(SystemError):
    """Operation timeout error."""
    
    def __init__(self, operation: str, timeout_seconds: float, details: Optional[Dict] = None):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        super().__init__(message, "TIMEOUT_ERROR", details)


class RateLimitError(SystemError):
    """Rate limit exceeded error."""
    
    def __init__(self, resource: str, limit: int, details: Optional[Dict] = None):
        self.resource = resource
        self.limit = limit
        message = f"Rate limit exceeded for {resource}: {limit} requests"
        super().__init__(message, "RATE_LIMIT_ERROR", {"resource": resource, "limit": limit})


class ResourceLimitError(SystemError):
    """Resource limit exceeded error."""
    
    def __init__(self, resource: str, limit: int, current: int, details: Optional[Dict] = None):
        self.resource = resource
        self.limit = limit
        self.current = current
        message = f"Resource limit exceeded for {resource}: {current}/{limit}"
        super().__init__(message, "RESOURCE_LIMIT_ERROR", {"resource": resource, "limit": limit, "current": current})


# ================================
# Error Severity Levels
# ================================

class ErrorSeverity(Enum):
    """Error severity levels for proper escalation and handling."""
    
    LOW = "low"           # Minor issues, system continues normally
    MEDIUM = "medium"     # Issues requiring attention but not blocking
    HIGH = "high"         # Significant issues affecting functionality
    CRITICAL = "critical" # System-threatening issues requiring immediate action


# ================================
# Essential Error Boundary Decorator
# ================================

def error_boundary(component: str = "unknown", severity: ErrorSeverity = ErrorSeverity.HIGH):
    """
    Essential error boundary decorator for consistent error handling.
    
    Args:
        component: Component name for logging context
        severity: Default severity level for unhandled errors
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except (SystemError, ProcessingError, ConnectionError, ValidationError, TimeoutError, RateLimitError) as e:
                # Log known system errors with context
                logger.error(
                    "System error in component",
                    component=component,
                    error_type=type(e).__name__,
                    error_code=getattr(e, 'error_code', 'UNKNOWN'),
                    error_message=str(e),
                    details=getattr(e, 'details', {})
                )
                raise
            except Exception as e:
                # Log unexpected errors with full context
                logger.error(
                    "Unexpected error in component", 
                    component=component,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    severity=severity.value,
                    exc_info=True
                )
                # Wrap in SystemError for consistent handling
                raise SystemError(f"Unexpected error in {component}: {str(e)}", "UNEXPECTED_ERROR")
        
        @wraps(func) 
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except (SystemError, ProcessingError, ConnectionError, ValidationError, TimeoutError, RateLimitError) as e:
                # Log known system errors with context
                logger.error(
                    "System error in component",
                    component=component,
                    error_type=type(e).__name__,
                    error_code=getattr(e, 'error_code', 'UNKNOWN'),
                    error_message=str(e),
                    details=getattr(e, 'details', {})
                )
                raise
            except Exception as e:
                # Log unexpected errors with full context
                logger.error(
                    "Unexpected error in component",
                    component=component, 
                    error_type=type(e).__name__,
                    error_message=str(e),
                    severity=severity.value,
                    exc_info=True
                )
                # Wrap in SystemError for consistent handling
                raise SystemError(f"Unexpected error in {component}: {str(e)}", "UNEXPECTED_ERROR")
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ================================
# Utility Functions
# ================================

def classify_error_severity(error: Exception) -> ErrorSeverity:
    """Classify error severity based on error type."""
    
    if isinstance(error, ValidationError):
        return ErrorSeverity.LOW
    elif isinstance(error, (TimeoutError, RateLimitError)):
        return ErrorSeverity.MEDIUM  
    elif isinstance(error, ConnectionError):
        return ErrorSeverity.HIGH
    elif isinstance(error, (SystemError, ProcessingError)):
        return ErrorSeverity.CRITICAL
    else:
        return ErrorSeverity.HIGH  # Default for unknown errors


# ================================
# Error Response Model (for backward compatibility)
# ================================

class ErrorResponse:
    """Standardized error response format."""
    
    def __init__(self, error: Exception, request_id: Optional[str] = None):
        if isinstance(error, SystemError):
            self.type = "error"
            self.error_code = error.error_code
            self.message = error.message
            self.details = error.details
            self.timestamp = error.timestamp.isoformat()
            self.request_id = request_id
            self.severity = classify_error_severity(error).value
        else:
            self.type = "error"
            self.error_code = "UNEXPECTED_ERROR"
            self.message = str(error)
            self.details = {}
            self.timestamp = datetime.now(timezone.utc).isoformat()
            self.request_id = request_id
            self.severity = classify_error_severity(error).value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "type": self.type,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "severity": self.severity
        }


def create_error_response(error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Create standardized error response dictionary."""
    return ErrorResponse(error, request_id).to_dict()


# ================================
# Backward Compatibility Stubs  
# ================================

def error_to_http_exception(error: Exception) -> Exception:
    """Convert system error to HTTP exception."""
    if isinstance(error, ValidationError):
        from fastapi import HTTPException
        return HTTPException(status_code=400, detail=error.message)
    elif isinstance(error, ConnectionError):
        from fastapi import HTTPException
        return HTTPException(status_code=503, detail=error.message)
    else:
        from fastapi import HTTPException
        return HTTPException(status_code=500, detail=str(error))


def is_retryable_error(error: Exception) -> bool:
    """Check if error is retryable."""
    if isinstance(error, ConnectionError):
        return getattr(error, 'retryable', True)
    elif isinstance(error, TimeoutError):
        return True
    else:
        return False


def get_user_friendly_message(error: Exception) -> str:
    """Get user-friendly error message."""
    if isinstance(error, SystemError):
        return error.message
    else:
        return "An unexpected error occurred. Please try again."


# Minimal stubs for removed complex features
class RetryConfig:
    def __init__(self, max_attempts: int = 3, delay: float = 1.0, base_delay: float = 1.0, 
                 max_delay: float = 60.0, retryable_exceptions: tuple = (), exponential_base: float = 2.0):
        self.max_attempts = max_attempts
        self.delay = delay
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable_exceptions = retryable_exceptions
        self.exponential_base = exponential_base


class CircuitBreakerConfig:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, recovery_timeout: int = 30, expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception


class CircuitBreaker:
    def __init__(self, name: str = "default", config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error("Circuit breaker triggered", name=self.name, error=str(e))
            raise


# Global registry stub
class ErrorRegistry:
    """Simple error registry for tracking errors across the system."""
    
    def __init__(self):
        self.errors = []
        self.error_counts = {}
    
    def record_error(self, error: Exception, context: dict = None):
        """Record an error with context."""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        error_record = {
            "error_type": error_type,
            "message": str(error),
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        self.errors.append(error_record)
        
        # Keep only last 1000 errors to prevent memory issues
        if len(self.errors) > 1000:
            self.errors = self.errors[-1000:]
    
    def get_error_summary(self, hours: int = 24):
        """Get error summary for the last N hours."""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            err for err in self.errors 
            if datetime.fromisoformat(err["timestamp"]) > cutoff
        ]
        
        return {
            "total_errors": len(recent_errors),
            "error_types": {},
            "recent_errors": recent_errors[-10:]  # Last 10 errors
        }

# Create global error registry instance
error_registry = ErrorRegistry()


def handle_service_error(error: Exception, service: str) -> Exception:
    """Handle service-specific error."""
    logger.error("Service error", service=service, error=str(error))
    return error


def with_retry(config: RetryConfig):
    """Retry decorator stub."""
    def decorator(func):
        return func
    return decorator