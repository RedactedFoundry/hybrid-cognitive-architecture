#!/usr/bin/env python3
"""
Error Handling Utilities

This module provides standardized error handling utilities that integrate
the error boundaries framework with the existing system components.
"""

import asyncio
import json
from typing import Any, Callable, Dict, Optional, TypeVar

import structlog
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from core.error_boundaries import (
    SystemError,
    ProcessingError,
    ConnectionError,
    ValidationError,
    TimeoutError,
    RateLimitError,
    ErrorSeverity,
    ErrorResponse,
    create_error_response,
    error_to_http_exception,
    error_registry,
    handle_service_error,
    is_retryable_error,
    get_user_friendly_message,
    classify_error_severity,
    error_boundary,
    with_retry,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerConfig
)

logger = structlog.get_logger("error_utils")

T = TypeVar('T')

# ================================
# WebSocket Error Handling
# ================================

async def handle_websocket_error(
    websocket: WebSocket,
    error: Exception,
    request_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    connection_id: Optional[str] = None
) -> bool:
    """
    Standardized WebSocket error handling.
    
    Args:
        websocket: The WebSocket connection
        error: The error that occurred
        request_id: Request ID for tracking
        conversation_id: Conversation ID for context
        connection_id: Connection ID for tracking
        
    Returns:
        True if error was handled and connection can continue, False if connection should close
    """
    
    # Record error for analysis
    error_registry.record_error(error, {
        "component": "websocket",
        "request_id": request_id,
        "conversation_id": conversation_id,
        "connection_id": connection_id
    })
    
    # Create standardized error response
    error_response = create_error_response(
        error=error,
        request_id=request_id,
        conversation_id=conversation_id
    )
    
    # Add user-friendly message
    error_response.message = get_user_friendly_message(error)
    
    try:
        # Attempt to send error response
        await websocket.send_text(json.dumps(error_response.to_dict()))
        
        # Log the error with appropriate severity
        severity = classify_error_severity(error)
        error_logger = logger.bind(
            connection_id=connection_id,
            request_id=request_id,
            severity=severity.value
        )
        
        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            error_logger.error(
                "WebSocket error handled",
                error_type=type(error).__name__,
                error_message=str(error),
                exc_info=True
            )
        else:
            error_logger.warning(
                "WebSocket error handled",
                error_type=type(error).__name__,
                error_message=str(error)
            )
        
        # Determine if connection should continue
        return _should_continue_connection(error)
        
    except Exception as send_error:
        # WebSocket is likely closed, connection should terminate
        logger.debug(
            "Could not send error response, WebSocket likely closed",
            connection_id=connection_id,
            original_error=str(error),
            send_error=str(send_error)
        )
        return False


def _should_continue_connection(error: Exception) -> bool:
    """Determine if WebSocket connection should continue after an error."""
    
    # Connection should close for these error types
    fatal_errors = (
        ConnectionError,
        SystemError,
        WebSocketDisconnect
    )
    
    # Connection can continue for these error types
    recoverable_errors = (
        ValidationError,
        ProcessingError,
        TimeoutError
    )
    
    if isinstance(error, fatal_errors):
        return False
    elif isinstance(error, recoverable_errors):
        return True
    else:
        # Conservative approach: close connection for unknown errors
        return False


# ================================
# Client Error Handling
# ================================

@error_boundary(severity=ErrorSeverity.HIGH, component="client_connection")
async def safe_client_operation(
    client_func: Callable[..., T],
    service_name: str,
    *args,
    **kwargs
) -> T:
    """
    Safely execute client operations with proper error handling.
    
    Args:
        client_func: The client function to execute
        service_name: Name of the service for logging
        *args: Arguments for the client function
        **kwargs: Keyword arguments for the client function
        
    Returns:
        Result of the client function
        
    Raises:
        ConnectionError: If unable to connect to the service
        TimeoutError: If the operation times out
        SystemError: For other unexpected errors
    """
    
    try:
        return await client_func(*args, **kwargs)
    except asyncio.TimeoutError as e:
        raise TimeoutError(
            operation=f"{service_name}_operation",
            timeout_seconds=kwargs.get('timeout', 30.0),
            details={'service': service_name}
        ) from e
    except Exception as e:
        await handle_service_error(service_name, e, {
            'operation': client_func.__name__,
            'args_count': len(args),
            'kwargs_keys': list(kwargs.keys())
        })
        
        if is_retryable_error(e):
            raise ConnectionError(
                service=service_name,
                message=f"Connection to {service_name} failed: {str(e)}",
                retryable=True,
                details={'original_error': str(e)}
            ) from e
        else:
            raise ProcessingError(
                message=f"Operation failed in {service_name}: {str(e)}",
                component=service_name,
                details={'original_error': str(e)}
            ) from e


# ================================
# Circuit Breakers for Services
# ================================

# Pre-configured circuit breakers for common services
ollama_circuit_breaker = CircuitBreaker(
    name="ollama_service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30,
        expected_exception=ConnectionError
    )
)

redis_circuit_breaker = CircuitBreaker(
    name="redis_service", 
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60,
        expected_exception=ConnectionError
    )
)

tigergraph_circuit_breaker = CircuitBreaker(
    name="tigergraph_service",
    config=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,
        expected_exception=ConnectionError
    )
)

# Service-specific retry configurations
ollama_retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    retryable_exceptions=(ConnectionError, TimeoutError, asyncio.TimeoutError)
)

redis_retry_config = RetryConfig(
    max_attempts=2,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)

tigergraph_retry_config = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)


# ================================
# Service-Specific Error Handlers
# ================================

async def handle_ollama_error(error: Exception, context: Optional[Dict] = None) -> None:
    """Handle Ollama service errors with specific context."""
    await handle_service_error("ollama", error, {
        "context": context or {},
        "recovery_suggestions": [
            "Check if Ollama service is running",
            "Verify model availability with 'ollama list'",
            "Check CUDA memory usage"
        ]
    })


async def handle_redis_error(error: Exception, context: Optional[Dict] = None) -> None:
    """Handle Redis service errors with specific context."""
    await handle_service_error("redis", error, {
        "context": context or {},
        "recovery_suggestions": [
            "Check if Redis container is running",
            "Verify Redis connection parameters",
            "Check Redis memory usage"
        ]
    })


async def handle_tigergraph_error(error: Exception, context: Optional[Dict] = None) -> None:
    """Handle TigerGraph service errors with specific context."""
    await handle_service_error("tigergraph", error, {
        "context": context or {},
        "recovery_suggestions": [
            "Check if TigerGraph container is running",
            "Verify TigerGraph setup script was run",
            "Check TigerGraph system resources"
        ]
    })


# ================================
# Processing Error Handlers
# ================================

async def handle_cognitive_processing_error(
    error: Exception,
    phase: str,
    component: str,
    request_id: Optional[str] = None
) -> ProcessingError:
    """
    Handle errors in cognitive processing with rich context.
    
    Args:
        error: The original error
        phase: Processing phase where error occurred
        component: Component name (pheromind, council, kip)
        request_id: Request ID for tracking
        
    Returns:
        ProcessingError with appropriate context
    """
    
    error_registry.record_error(error, {
        "component": "cognitive_processing",
        "phase": phase,
        "processing_component": component,
        "request_id": request_id
    })
    
    # Create appropriate error based on type
    if isinstance(error, SystemError):
        return error
    elif is_retryable_error(error):
        return ProcessingError(
            message=f"Retryable error in {component} during {phase}: {str(error)}",
            component=component,
            phase=phase,
            details={
                "retryable": True,
                "original_error": str(error),
                "request_id": request_id
            }
        )
    else:
        return ProcessingError(
            message=f"Processing failed in {component} during {phase}: {str(error)}",
            component=component,
            phase=phase,
            details={
                "retryable": False,
                "original_error": str(error),
                "request_id": request_id
            }
        )


# ================================
# Input Validation Helpers
# ================================

def validate_user_input(user_input: str) -> None:
    """
    Validate user input with comprehensive checks.
    
    Args:
        user_input: The user input to validate
        
    Raises:
        ValidationError: If input fails validation
    """
    
    if not user_input:
        raise ValidationError("user_input", "Input cannot be empty")
    
    if not isinstance(user_input, str):
        raise ValidationError("user_input", "Input must be a string")
    
    if not user_input.strip():
        raise ValidationError("user_input", "Input cannot be only whitespace")
    
    if len(user_input) > 10000:
        raise ValidationError(
            "user_input", 
            f"Input too long: {len(user_input)} characters (max: 10,000)"
        )
    
    # Check for suspicious patterns that might indicate injection attacks
    suspicious_patterns = [
        '<script',
        'javascript:',
        'data:text/html',
        'vbscript:',
        'onload=',
        'onerror='
    ]
    
    user_input_lower = user_input.lower()
    for pattern in suspicious_patterns:
        if pattern in user_input_lower:
            raise ValidationError(
                "user_input",
                "Input contains potentially malicious content",
                value=pattern
            )


def validate_request_id(request_id: str) -> None:
    """Validate request ID format."""
    
    if not request_id:
        raise ValidationError("request_id", "Request ID cannot be empty")
    
    if not isinstance(request_id, str):
        raise ValidationError("request_id", "Request ID must be a string")
    
    if len(request_id) > 100:
        raise ValidationError("request_id", "Request ID too long")


def validate_conversation_id(conversation_id: str) -> None:
    """Validate conversation ID format."""
    
    if not conversation_id:
        raise ValidationError("conversation_id", "Conversation ID cannot be empty")
    
    if not isinstance(conversation_id, str):
        raise ValidationError("conversation_id", "Conversation ID must be a string")
    
    if len(conversation_id) > 100:
        raise ValidationError("conversation_id", "Conversation ID too long")


# ================================
# Health Check Error Helpers
# ================================

def create_health_check_error(service: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create standardized health check error response."""
    
    return {
        "service": service,
        "status": "unhealthy",
        "error": f"{service} service is not available",
        "details": details or {},
        "timestamp": logger._get_timestamp(),
        "recovery_suggestions": _get_recovery_suggestions(service)
    }


def _get_recovery_suggestions(service: str) -> list[str]:
    """Get service-specific recovery suggestions."""
    
    suggestions = {
        "ollama": [
            "Check if Ollama service is running",
            "Verify models are loaded",
            "Check CUDA availability"
        ],
        "redis": [
            "Check if Redis container is running", 
            "Verify Redis connection settings",
            "Check Redis memory usage"
        ],
        "tigergraph": [
            "Check if TigerGraph container is running",
            "Run TigerGraph setup script",
            "Verify graph schema is installed"
        ]
    }
    
    return suggestions.get(service, ["Check service configuration and restart"])


# ================================
# Error Metrics and Monitoring
# ================================

def get_error_dashboard_data() -> Dict[str, Any]:
    """Get error data for monitoring dashboard."""
    
    return {
        "error_summary_24h": error_registry.get_error_summary(24),
        "error_summary_1h": error_registry.get_error_summary(1),
        "circuit_breaker_status": {
            "ollama": {
                "state": ollama_circuit_breaker.state.value,
                "failure_count": ollama_circuit_breaker.failure_count
            },
            "redis": {
                "state": redis_circuit_breaker.state.value,
                "failure_count": redis_circuit_breaker.failure_count
            },
            "tigergraph": {
                "state": tigergraph_circuit_breaker.state.value,
                "failure_count": tigergraph_circuit_breaker.failure_count
            }
        },
        "top_error_types": dict(list(error_registry.error_counts.items())[:10])
    }


async def reset_circuit_breakers() -> Dict[str, str]:
    """Reset all circuit breakers (admin function)."""
    
    circuit_breakers = {
        "ollama": ollama_circuit_breaker,
        "redis": redis_circuit_breaker, 
        "tigergraph": tigergraph_circuit_breaker
    }
    
    results = {}
    for name, breaker in circuit_breakers.items():
        old_state = breaker.state.value
        breaker.failure_count = 0
        breaker.last_failure_time = None
        breaker.state = breaker.CircuitState.CLOSED
        results[name] = f"Reset from {old_state} to closed"
        
        logger.info("Circuit breaker manually reset", circuit_breaker=name)
    
    return results


# ================================
# Export commonly used decorators and utilities
# ================================

__all__ = [
    # Core error types
    'SystemError',
    'ProcessingError', 
    'ConnectionError',
    'ValidationError',
    'TimeoutError',
    'RateLimitError',
    'ErrorSeverity',
    'ErrorResponse',
    
    # Error handling functions
    'create_error_response',
    'error_to_http_exception', 
    'handle_websocket_error',
    'safe_client_operation',
    'handle_cognitive_processing_error',
    
    # Service-specific handlers
    'handle_ollama_error',
    'handle_redis_error',
    'handle_tigergraph_error',
    
    # Validation
    'validate_user_input',
    'validate_request_id',
    'validate_conversation_id',
    
    # Decorators
    'error_boundary',
    'with_retry',
    
    # Circuit breakers
    'ollama_circuit_breaker',
    'redis_circuit_breaker',
    'tigergraph_circuit_breaker',
    
    # Retry configs
    'ollama_retry_config',
    'redis_retry_config', 
    'tigergraph_retry_config',
    
    # Monitoring
    'get_error_dashboard_data',
    'reset_circuit_breakers',
    'error_registry'
]