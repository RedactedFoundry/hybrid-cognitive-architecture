# clients/redis_client.py
import os

import redis
import structlog

from utils.error_utils import (
    ConnectionError,
    error_boundary,
    redis_circuit_breaker,
    handle_redis_error
)

# Set up structured logging
logger = structlog.get_logger("redis_client")

@error_boundary(component="redis_connection")
def get_redis_connection():
    """
    Establishes a connection to the Redis server with circuit breaker protection.

    Reads connection details from environment variables.
    Includes comprehensive error handling and circuit breaker protection.

    Returns:
        A Redis connection object if successful, otherwise None.
        
    Raises:
        ConnectionError: If unable to connect to Redis after retries
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    
    try:
        # Check circuit breaker state (simplified for sync function)
        if hasattr(redis_circuit_breaker, 'state') and redis_circuit_breaker.state.name == "OPEN":
            if not redis_circuit_breaker._should_attempt_reset():
                raise ConnectionError(
                    service="redis",
                    message="Redis circuit breaker is open",
                    retryable=True,
                    details={"retry_after": redis_circuit_breaker._time_until_reset()}
                )
        
        # The decode_responses=True argument ensures that Redis returns strings, not bytes.
        r = redis.Redis(host=host, port=port, decode_responses=True)

        # Ping the server to confirm the connection is alive.
        r.ping()
        
        # Reset circuit breaker on success
        if hasattr(redis_circuit_breaker, 'failure_count'):
            redis_circuit_breaker.failure_count = 0
        
        logger.info("Successfully connected to Redis", host=host, port=port)
        return r
        
    except redis.exceptions.ConnectionError as e:
        # Update circuit breaker
        redis_circuit_breaker.failure_count += 1
        if redis_circuit_breaker.failure_count >= redis_circuit_breaker.config.failure_threshold:
            redis_circuit_breaker.state = redis_circuit_breaker.CircuitState.OPEN
            from datetime import datetime, timezone
            redis_circuit_breaker.last_failure_time = datetime.now(timezone.utc)
        
        connection_error = ConnectionError(
            service="redis",
            message=f"Failed to connect to Redis: {str(e)}",
            retryable=True,
            details={"host": host, "port": port, "error_type": type(e).__name__}
        )
        
        # Use sync version of handle_redis_error by calling it directly
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(handle_redis_error(connection_error, {
                "operation": "get_connection",
                "host": host,
                "port": port
            }))
        except RuntimeError:
            # No event loop running, just log
            logger.error(
                "Redis connection failed",
                error=str(e),
                host=host,
                port=port,
                circuit_breaker_state=redis_circuit_breaker.state.name
            )
        
        return None
    
    except Exception as e:
        # Update circuit breaker for unexpected errors
        redis_circuit_breaker.failure_count += 1
        if redis_circuit_breaker.failure_count >= redis_circuit_breaker.config.failure_threshold:
            redis_circuit_breaker.state = redis_circuit_breaker.CircuitState.OPEN
            from datetime import datetime, timezone
            redis_circuit_breaker.last_failure_time = datetime.now(timezone.utc)
        
        # Use sync version of handle_redis_error
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(handle_redis_error(e, {
                "operation": "get_connection",
                "host": host,
                "port": port
            }))
        except RuntimeError:
            # No event loop running, just log
            logger.error(
                "Unexpected Redis connection error",
                error=str(e),
                host=host,
                port=port,
                circuit_breaker_state=redis_circuit_breaker.state.name
            )
        
        return None 