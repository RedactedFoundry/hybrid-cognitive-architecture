#!/usr/bin/env python3
"""
Hybrid AI Council - Main FastAPI Application
===========================================

This is the main entry point for the Hybrid AI Council system.
It provides a FastAPI application with WebSocket endpoints for real-time
interaction with the 3-layer cognitive architecture.

Refactored for modularity and maintainability.

Features:
- WebSocket endpoint for real-time chat (/ws/chat)
- Health monitoring endpoint (/health)
- Request ID tracking through the entire pipeline
- Real-time streaming of AI Council deliberation phases
- Structured logging for observability

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import structlog

from clients.ollama_client import get_ollama_client
from clients.redis_client import get_redis_connection
from clients.tigervector_client import get_tigergraph_connection
from config import Config
from core.logging_config import setup_logging
from core.orchestrator import UserFacingOrchestrator
from endpoints.chat import router as chat_router, websocket_chat_endpoint, set_orchestrator
from endpoints.health import router as health_router, set_health_dependencies
from endpoints.voice import router as voice_router, websocket_voice_endpoint
from middleware import (
    RateLimitingMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware
)
from middleware.rate_limiting import RateLimit
from middleware.request_validation import ValidationConfig
from middleware.security_headers import ProductionSecurityConfig, SecurityConfig
from voice_foundation.orchestrator_integration import voice_orchestrator
from utils.websocket_utils import active_connections

# Global state
app_start_time = datetime.now(timezone.utc)
orchestrator: Optional[UserFacingOrchestrator] = None
logger = structlog.get_logger("main")


async def _verify_services_startup():
    """Verify that core services are available at startup."""
    logger.info("Verifying core services...")
    
    # Check Ollama
    try:
        ollama_client = get_ollama_client()
        if await ollama_client.health_check():
            logger.info("✅ Ollama service is available")
        else:
            logger.warning("⚠️ Ollama service health check failed")
    except (ConnectionError, TimeoutError) as e:
        logger.error("Ollama service connection failed", error=str(e), error_type=type(e).__name__)
    except Exception as e:
        logger.error("Ollama service unexpected error", error=str(e), error_type=type(e).__name__)
    
    # Check Redis (optional for startup)
    try:
        redis_client = get_redis_connection()
        if redis_client:
            redis_client.ping()
            logger.info("✅ Redis service is available")
        else:
            logger.warning("⚠️ Redis service unavailable (degraded mode)")
    except (ConnectionError, TimeoutError) as e:
        logger.warning("Redis connection failed - degraded mode", error=str(e), error_type=type(e).__name__)
    except Exception as e:
        logger.warning("Redis unexpected error - degraded mode", error=str(e), error_type=type(e).__name__)
    
    # Check TigerGraph (optional for startup)
    try:
        tg_client = get_tigergraph_connection()
        # TigerGraph client might not have async health check
        if tg_client:
            logger.info("✅ TigerGraph service is available")
        else:
            logger.warning("⚠️ TigerGraph service unavailable (degraded mode)")
    except (ConnectionError, TimeoutError) as e:
        logger.warning("TigerGraph connection failed - degraded mode", error=str(e), error_type=type(e).__name__)
    except Exception as e:
        logger.warning("TigerGraph unexpected error - degraded mode", error=str(e), error_type=type(e).__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown logic."""
    
    # Startup
    logger.info("Starting Hybrid AI Council API server...")
    
    # Setup logging
    setup_logging()
    
    # Initialize orchestrator
    global orchestrator
    orchestrator = UserFacingOrchestrator()
    logger.info("UserFacingOrchestrator initialized successfully")
    
    # Set orchestrator dependencies for endpoints
    set_orchestrator(orchestrator)
    set_health_dependencies(app_start_time, orchestrator)
    
    # Initialize voice foundation
    try:
        await voice_orchestrator.initialize()
        logger.info("Voice Foundation initialized successfully")
    except Exception as e:
        logger.warning("Voice Foundation initialization failed - voice endpoints may not work", error=str(e))
    
    # Verify core services
    await _verify_services_startup()
    
    logger.info("Hybrid AI Council API server started successfully", 
                port=8000, 
                endpoints=["WebSocket Chat (/ws/chat)", "Voice Chat (/api/voice/chat)", "Health Check (/health)"])
    
    yield
    
    # Shutdown
    logger.info("Shutting down Hybrid AI Council API server...")
    
    # Close active WebSocket connections
    for connection_id, websocket in active_connections.items():
        try:
            await websocket.close()
            logger.debug("Closed WebSocket connection", connection_id=connection_id)
        except Exception as e:
            logger.warning("Error closing WebSocket connection", connection_id=connection_id, error=str(e))
    
    logger.info("Hybrid AI Council API server shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Hybrid AI Council API",
    description="Real-time API for the 3-layer cognitive AI architecture",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure and add security middleware
config = Config()

# Setup security configuration based on environment
if config.environment == "production":
    security_config = ProductionSecurityConfig()
    # Parse production CORS origins from config
    allowed_origins = [origin.strip() for origin in config.cors_allowed_origins.split(",") if origin.strip()]
    if not allowed_origins or allowed_origins == ["*"]:
        # In production, we must have specific origins
        logger.warning("Production environment detected but CORS origins not properly configured")
        allowed_origins = ["https://yourdomain.com"]  # Replace with actual domain
else:
    security_config = SecurityConfig()
    # Development - more permissive
    allowed_origins = [origin.strip() for origin in config.cors_allowed_origins.split(",")]

# Add CORS middleware with environment-appropriate configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=[method.strip() for method in config.cors_allowed_methods.split(",")],
    allow_headers=[header.strip() for header in config.cors_allowed_headers.split(",")],
)

# Add security headers middleware
if config.security_headers_enabled:
    app.add_middleware(
        SecurityHeadersMiddleware,
        config=security_config,
        enabled=True
    )

# Add request validation middleware
if config.request_validation_enabled:
    validation_config = ValidationConfig(
        max_request_size=config.max_request_size_mb * 1024 * 1024,
        max_json_size=config.max_json_size_mb * 1024 * 1024,
        max_query_params=config.max_query_params
    )
    app.add_middleware(
        RequestValidationMiddleware,
        config=validation_config,
        enabled=True
    )

# Add rate limiting middleware (should be one of the first middleware)
if config.rate_limiting_enabled:
    rate_limits = [
        RateLimit(requests=config.rate_limit_requests_per_minute, window_seconds=60, scope="ip_per_minute"),
        RateLimit(requests=config.rate_limit_requests_per_hour, window_seconds=3600, scope="ip_per_hour"),
        RateLimit(requests=config.rate_limit_chat_per_minute, window_seconds=60, scope="chat_per_minute"),
        RateLimit(requests=config.rate_limit_voice_per_minute, window_seconds=60, scope="voice_per_minute"),
    ]
    
    app.add_middleware(
        RateLimitingMiddleware,
        enabled=True,
        default_limits=rate_limits
    )

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include modular routers
app.include_router(chat_router)
app.include_router(voice_router)

# Include health router (dependencies injected via closure after startup)
app.include_router(health_router)


# WebSocket endpoints (these need to be defined at app level)
@app.websocket("/ws/chat")
async def websocket_chat_route(websocket: WebSocket):
    """WebSocket endpoint for chat - routed to modular handler."""
    await websocket_chat_endpoint(websocket, orchestrator)


@app.websocket("/ws/voice")
async def websocket_voice_route(websocket: WebSocket):
    """WebSocket endpoint for voice - routed to modular handler."""
    await websocket_voice_endpoint(websocket)


# Root redirect
@app.get("/")
async def get_test_client():
    """
    Redirect to static HTML client for testing WebSocket functionality.
    """
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Load configuration
    config = Config()
    
    # Determine base URL for cloud compatibility - fully configurable via environment
    public_url = os.getenv("PUBLIC_URL")
    api_host = os.getenv("API_HOST", config.api_host)
    
    if public_url:
        # Use explicit PUBLIC_URL if provided (for production/staging)
        base_url = public_url
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    else:
        # Build URL from host and port (development default, but configurable)
        base_url = f"http://{api_host}:{config.api_port}"
        ws_url = f"ws://{api_host}:{config.api_port}"
    
    logger.info("Starting Hybrid AI Council API server",
                health_check=f"{base_url}/health",
                websocket_chat=f"{ws_url}/ws/chat", 
                test_client=f"{base_url}/",
                api_docs=f"{base_url}/docs",
                environment=config.environment)
    
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=(config.environment == "development"),
        log_level=config.log_level.lower()
    )