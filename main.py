#!/usr/bin/env python3
"""
Hybrid AI Council - Main FastAPI Application
===========================================

This is the main entry point for the Hybrid AI Council system.
It provides a FastAPI application with WebSocket endpoints for real-time
interaction with the 3-layer cognitive architecture.

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
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

# Import our core orchestrator
from core.orchestrator import UserFacingOrchestrator, ProcessingPhase
from core.logging_config import setup_logging

# Import clients for health checks
from clients.ollama_client import get_ollama_client
from clients.redis_client import get_redis_connection
from clients.tigervector_client import get_tigergraph_connection


# Request/Response models
class ChatMessage(BaseModel):
    """WebSocket chat message from client."""
    message: str = Field(description="User's message content")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChatResponse(BaseModel):
    """WebSocket response to client."""
    type: str = Field(description="Response type: 'status', 'partial', 'final', 'error'")
    content: str = Field(description="Response content") 
    request_id: str = Field(description="Request ID for tracking")
    conversation_id: str = Field(description="Conversation ID")
    phase: Optional[str] = Field(default=None, description="Current processing phase")
    confidence: Optional[float] = Field(default=None, description="Confidence score for final responses")
    processing_time: Optional[float] = Field(default=None, description="Total processing time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")


class HealthStatus(BaseModel):
    """System health status."""
    status: str = Field(description="Overall system status")
    timestamp: datetime = Field(description="Health check timestamp")
    services: Dict[str, Dict[str, Any]] = Field(description="Individual service statuses")
    uptime_seconds: float = Field(description="System uptime in seconds")


# Global state
app_start_time = datetime.now(timezone.utc)
active_connections: Dict[str, WebSocket] = {}
orchestrator: Optional[UserFacingOrchestrator] = None
logger = structlog.get_logger("main")


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
    
    # Verify core services
    await _verify_services_startup()
    
    logger.info("Hybrid AI Council API server started successfully", port=8000)
    
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

# Add CORS middleware for web client development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    except Exception as e:
        logger.error("❌ Ollama service unavailable", error=str(e))
    
    # Check Redis (optional for startup)
    try:
        redis_client = get_redis_connection()
        if redis_client:
            redis_client.ping()
            logger.info("✅ Redis service is available")
        else:
            logger.warning("⚠️ Redis service unavailable (degraded mode)")
    except Exception as e:
        logger.warning("⚠️ Redis service unavailable (degraded mode)", error=str(e))
    
    # Check TigerGraph (optional for startup)
    try:
        tg_client = get_tigergraph_connection()
        # TigerGraph client might not have async health check
        if tg_client:
            logger.info("✅ TigerGraph service is available")
        else:
            logger.warning("⚠️ TigerGraph service unavailable (degraded mode)")
    except Exception as e:
        logger.warning("⚠️ TigerGraph service unavailable (degraded mode)", error=str(e))


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Checks the status of all core services and returns detailed health information.
    This endpoint is used by monitoring systems and load balancers.
    """
    logger.debug("Health check requested")
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "services": {},
        "uptime_seconds": (datetime.now(timezone.utc) - app_start_time).total_seconds()
    }
    
    # Check Ollama service
    try:
        ollama_client = get_ollama_client()
        ollama_healthy = await ollama_client.health_check()
        health_status["services"]["ollama"] = {
            "status": "healthy" if ollama_healthy else "unhealthy",
            "message": "LLM inference service",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        if not ollama_healthy:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["ollama"] = {
            "status": "error",
            "message": f"Failed to check Ollama: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        health_status["status"] = "degraded"
    
    # Check Redis service
    try:
        redis_client = get_redis_connection()
        if redis_client:
            redis_client.ping()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "message": "Pheromind working memory",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            health_status["services"]["redis"] = {
                "status": "error", 
                "message": "Redis connection failed",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "error", 
            "message": f"Redis unavailable: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        # Redis failure doesn't make system unhealthy, just degrades Pheromind
    
    # Check TigerGraph service
    try:
        tg_client = get_tigergraph_connection()
        if tg_client:
            health_status["services"]["tigergraph"] = {
                "status": "healthy",
                "message": "Persistent knowledge store",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            health_status["services"]["tigergraph"] = {
                "status": "error",
                "message": "TigerGraph connection failed",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        health_status["services"]["tigergraph"] = {
            "status": "error",
            "message": f"TigerGraph unavailable: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        # TigerGraph failure doesn't immediately break the system
    
    # Check orchestrator
    if orchestrator and orchestrator._initialized:
        health_status["services"]["orchestrator"] = {
            "status": "healthy", 
            "message": "AI Council orchestrator ready",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        health_status["services"]["orchestrator"] = {
            "status": "error",
            "message": "Orchestrator not initialized",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        health_status["status"] = "unhealthy"
    
    logger.debug("Health check completed", status=health_status["status"], services_count=len(health_status["services"]))
    
    return HealthStatus(**health_status)


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for AI Council chat interaction.
    
    This endpoint provides real-time streaming of AI Council deliberation,
    allowing users to see the multi-agent reasoning process as it happens.
    
    Message format:
    - Client sends: {"message": "user question", "conversation_id": "optional"}
    - Server streams: Multiple responses with different types (status, partial, final)
    """
    # Generate connection ID for tracking
    connection_id = str(uuid.uuid4())
    
    # Accept WebSocket connection
    await websocket.accept()
    active_connections[connection_id] = websocket
    
    logger.info("WebSocket connection established", connection_id=connection_id)
    
    try:
        # Send welcome message
        welcome_response = ChatResponse(
            type="status",
            content="Connected to Hybrid AI Council. Send your message to begin deliberation.",
            request_id="connection_" + connection_id,
            conversation_id="welcome",
            phase="connected"
        )
        await websocket.send_text(welcome_response.model_dump_json())
        
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                chat_message = ChatMessage(**message_data)
            except json.JSONDecodeError as e:
                error_response = ChatResponse(
                    type="error",
                    content=f"Invalid JSON format: {str(e)}",
                    request_id="error_" + str(uuid.uuid4()),
                    conversation_id="error"
                )
                await websocket.send_text(error_response.model_dump_json())
                continue
            except Exception as e:
                error_response = ChatResponse(
                    type="error",
                    content=f"Message format error: {str(e)}",
                    request_id="error_" + str(uuid.uuid4()),
                    conversation_id="error"
                )
                await websocket.send_text(error_response.model_dump_json())
                continue
            
            # Generate request ID and conversation ID
            request_id = str(uuid.uuid4())
            conversation_id = chat_message.conversation_id or str(uuid.uuid4())
            
            logger.info(
                "Processing WebSocket chat message",
                connection_id=connection_id,
                request_id=request_id,
                conversation_id=conversation_id,
                message_preview=chat_message.message[:100]
            )
            
            # Send acknowledgment
            ack_response = ChatResponse(
                type="status",
                content="Message received. Starting AI Council deliberation...",
                request_id=request_id,
                conversation_id=conversation_id,
                phase="received"
            )
            await websocket.send_text(ack_response.model_dump_json())
            
            try:
                # Process through orchestrator with real-time streaming
                await _process_with_streaming(
                    websocket=websocket,
                    user_input=chat_message.message,
                    request_id=request_id,
                    conversation_id=conversation_id
                )
                
            except Exception as e:
                logger.error(
                    "Error processing chat message",
                    connection_id=connection_id,
                    request_id=request_id,
                    error=str(e),
                    exc_info=True
                )
                
                error_response = ChatResponse(
                    type="error",
                    content=f"I apologize, but I encountered an error processing your request: {str(e)}",
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase="error"
                )
                await websocket.send_text(error_response.model_dump_json())
    
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client", connection_id=connection_id)
    except Exception as e:
        logger.error("WebSocket connection error", connection_id=connection_id, error=str(e), exc_info=True)
    finally:
        # Clean up connection
        if connection_id in active_connections:
            del active_connections[connection_id]
        logger.debug("WebSocket connection cleaned up", connection_id=connection_id)


async def _process_with_streaming(
    websocket: WebSocket,
    user_input: str,
    request_id: str,
    conversation_id: str
):
    """
    Process user input through the orchestrator with real-time token streaming.
    
    This function provides true token-by-token streaming essential for voice interactions,
    where the AI must begin speaking immediately as tokens are generated.
    """
    if not orchestrator:
        raise RuntimeError("Orchestrator not initialized")
    
    start_time = datetime.now(timezone.utc)
    accumulated_response = ""
    
    try:
        # Stream events from the orchestrator
        async for event in orchestrator.process_request_stream(
            user_input=user_input,
            conversation_id=conversation_id
        ):
            current_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Handle different event types
            if event.event_type == "phase_update":
                # Send phase transition updates
                phase_response = ChatResponse(
                    type="status",
                    content=event.content,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase=event.phase.value if event.phase else "unknown",
                    processing_time=current_time
                )
                await websocket.send_text(phase_response.model_dump_json())
            
            elif event.event_type == "agent_start":
                # Send agent start notifications
                agent_response = ChatResponse(
                    type="status",
                    content=event.content,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase=event.phase.value if event.phase else "unknown",
                    processing_time=current_time,
                    metadata={"agent": event.agent}
                )
                await websocket.send_text(agent_response.model_dump_json())
            
            elif event.event_type == "agent_complete":
                # Send agent completion notifications
                complete_response = ChatResponse(
                    type="status",
                    content=event.content,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase=event.phase.value if event.phase else "unknown",
                    processing_time=current_time,
                    metadata={"agent": event.agent, **event.metadata}
                )
                await websocket.send_text(complete_response.model_dump_json())
            
            elif event.event_type == "token":
                # Stream individual tokens as they're generated
                accumulated_response += event.content
                token_response = ChatResponse(
                    type="partial",
                    content=event.content,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase=event.phase.value if event.phase else "unknown",
                    processing_time=current_time,
                    metadata={
                        "agent": event.agent,
                        "accumulated_length": len(accumulated_response)
                    }
                )
                await websocket.send_text(token_response.model_dump_json())
            
            elif event.event_type == "final_response":
                # Send final response with complete metadata
                final_response = ChatResponse(
                    type="final",
                    content=event.content,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase=event.phase.value if event.phase else "completed",
                    processing_time=current_time,
                    metadata={
                        "agent": event.agent,
                        **event.metadata,
                        "total_processing_time": current_time
                    }
                )
                await websocket.send_text(final_response.model_dump_json())
                
                logger.info(
                    "WebSocket streaming completed",
                    request_id=request_id,
                    processing_time=current_time,
                    response_length=len(event.content),
                    agents_participated=event.metadata.get("agents_participated", [])
                )
            
            elif event.event_type == "error":
                # Handle error events
                error_response = ChatResponse(
                    type="error",
                    content=event.content,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase=event.phase.value if event.phase else "error",
                    processing_time=current_time,
                    metadata=event.metadata
                )
                await websocket.send_text(error_response.model_dump_json())
                
                logger.error(
                    "WebSocket streaming error",
                    request_id=request_id,
                    error=event.content,
                    metadata=event.metadata
                )
                break
        
    except Exception as e:
        # Send error response for unexpected exceptions
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        error_response = ChatResponse(
            type="error",
            content=f"Streaming failed: {str(e)}",
            request_id=request_id,
            conversation_id=conversation_id,
            phase="error",
            processing_time=processing_time
        )
        await websocket.send_text(error_response.model_dump_json())
        logger.error("WebSocket streaming exception", request_id=request_id, error=str(e), exc_info=True)
        raise


@app.get("/", response_class=HTMLResponse)
async def get_test_client():
    """
    Simple HTML test client for WebSocket testing.
    
    This provides a basic web interface for testing the WebSocket chat functionality
    during development.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hybrid AI Council - Test Client</title>
        <style>
            :root {
                --bg-primary: #1a1a1a;
                --bg-secondary: #2d2d2d;
                --bg-tertiary: #3a3a3a;
                --text-primary: #e0e0e0;
                --text-secondary: #b0b0b0;
                --border-color: #404040;
                --accent-blue: #4a9eff;
                --accent-green: #4caf50;
                --accent-red: #f44336;
                --accent-purple: #9c27b0;
                --accent-orange: #ff9800;
                --shadow: rgba(0, 0, 0, 0.3);
            }
            
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                max-width: 1000px; 
                margin: 0 auto; 
                padding: 20px;
                background-color: var(--bg-primary);
                color: var(--text-primary);
                line-height: 1.5;
            }
            .container {
                background: var(--bg-secondary);
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 20px var(--shadow);
                border: 1px solid var(--border-color);
            }
            h1 {
                text-align: center;
                color: var(--accent-blue);
                margin-bottom: 30px;
                font-size: 2.2em;
                font-weight: 300;
            }
            .phase-indicator {
                text-align: center;
                margin-bottom: 20px;
                padding: 10px;
                background: var(--bg-tertiary);
                border-radius: 8px;
                border: 1px solid var(--border-color);
                font-weight: 500;
            }
            #messages {
                height: 500px;
                border: 1px solid var(--border-color);
                padding: 15px;
                overflow-y: auto;
                background-color: var(--bg-primary);
                margin-bottom: 15px;
                border-radius: 8px;
                scrollbar-width: thin;
                scrollbar-color: var(--border-color) var(--bg-primary);
            }
            #messages::-webkit-scrollbar {
                width: 8px;
            }
            #messages::-webkit-scrollbar-track {
                background: var(--bg-primary);
            }
            #messages::-webkit-scrollbar-thumb {
                background: var(--border-color);
                border-radius: 4px;
            }
            .message {
                margin: 8px 0;
                padding: 12px;
                border-radius: 8px;
                border-left: 4px solid transparent;
                transition: all 0.2s ease;
            }
            .message:hover {
                transform: translateX(4px);
            }
            .status { 
                background-color: rgba(74, 158, 255, 0.15); 
                border-left-color: var(--accent-blue);
                color: var(--text-primary);
            }
            .final { 
                background-color: rgba(76, 175, 80, 0.15); 
                border-left-color: var(--accent-green);
                color: var(--text-primary);
            }
            .error { 
                background-color: rgba(244, 67, 54, 0.15); 
                border-left-color: var(--accent-red);
                color: var(--text-primary);
            }
            .user { 
                background-color: rgba(156, 39, 176, 0.15); 
                border-left-color: var(--accent-purple);
                color: var(--text-primary);
            }
            .streaming { 
                background-color: rgba(255, 152, 0, 0.15); 
                border-left-color: var(--accent-orange);
                color: var(--text-primary);
                position: relative;
            }
            .streaming::after {
                content: '▌';
                animation: blink 1s infinite;
                color: var(--accent-orange);
                font-weight: bold;
                margin-left: 4px;
            }
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.3; }
            }
            .input-container {
                display: flex;
                gap: 10px;
                align-items: center;
            }
            input[type="text"] {
                flex: 1;
                padding: 12px;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                background: var(--bg-tertiary);
                color: var(--text-primary);
                font-size: 14px;
                transition: border-color 0.3s ease, box-shadow 0.3s ease;
            }
            input[type="text"]:focus {
                outline: none;
                border-color: var(--accent-blue);
                box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2);
            }
            input[type="text"]::placeholder {
                color: var(--text-secondary);
            }
            button {
                padding: 12px 24px;
                background-color: var(--accent-blue);
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s ease;
                white-space: nowrap;
            }
            button:hover {
                background-color: #357abd;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(74, 158, 255, 0.3);
            }
            button:disabled {
                background-color: #555;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            .metadata {
                font-size: 0.85em;
                color: var(--text-secondary);
                margin-top: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            .connection-status {
                text-align: center;
                margin-bottom: 20px;
                padding: 10px;
                background: var(--bg-tertiary);
                border-radius: 6px;
                border: 1px solid var(--border-color);
                font-size: 0.9em;
            }
            .phase-badges {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .phase-badge {
                padding: 6px 12px;
                background: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 20px;
                font-size: 0.8em;
                color: var(--text-secondary);
            }
            .phase-badge.active {
                background: var(--accent-blue);
                color: white;
                border-color: var(--accent-blue);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 Hybrid AI Council</h1>
            <p style="text-align: center; color: var(--text-secondary); margin-bottom: 30px;">
                Experience true multi-agent deliberation with token-by-token streaming • Three phases of AI reasoning
            </p>
            
            <div class="phase-badges">
                <div class="phase-badge" id="phase-1">Phase 1: Concurrent Analysis</div>
                <div class="phase-badge" id="phase-2">Phase 2: Cross-Critique</div>
                <div class="phase-badge" id="phase-3">Phase 3: Final Synthesis</div>
            </div>
            
            <div class="connection-status" id="statusContainer">
                <span id="status">🔌 Connecting to AI Council...</span>
                <span style="margin-left: 15px; font-size: 0.8em;">
                    Connection ID: <span id="connectionId">-</span>
                </span>
            </div>
            
            <div id="messages"></div>
            
            <div class="input-container">
                <input type="text" id="messageInput" placeholder="Ask the AI Council anything..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()" id="sendButton">Send Message</button>
            </div>
            
            <div style="text-align: center; margin-top: 20px; font-size: 0.8em; color: var(--text-secondary);">
                <p>💡 Try asking: "How does quantum computing work?" or "What's the future of AI?"</p>
            </div>
        </div>

        <script>
            let ws = null;
            let connectionId = null;

            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    document.getElementById('status').innerHTML = '🟢 Connected to AI Council';
                    document.getElementById('statusContainer').style.borderColor = 'var(--accent-green)';
                    resetPhases();
                };
                
                ws.onmessage = function(event) {
                    const response = JSON.parse(event.data);
                    displayMessage(response);
                };
                
                ws.onclose = function(event) {
                    document.getElementById('status').innerHTML = '🔴 Disconnected';
                    document.getElementById('statusContainer').style.borderColor = 'var(--accent-red)';
                    setTimeout(connect, 3000); // Reconnect after 3 seconds
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    document.getElementById('status').innerHTML = '❌ Connection Error';
                    document.getElementById('statusContainer').style.borderColor = 'var(--accent-red)';
                };
            }

            let currentStreamingMessage = null;
            let streamingContent = '';
            let currentPhase = 0;

            function resetPhases() {
                currentPhase = 0;
                const phases = ['phase-1', 'phase-2', 'phase-3'];
                phases.forEach(id => {
                    document.getElementById(id).classList.remove('active');
                });
            }

            function activatePhase(phaseNum) {
                if (phaseNum > currentPhase) {
                    currentPhase = phaseNum;
                    const phaseId = `phase-${phaseNum}`;
                    document.getElementById(phaseId).classList.add('active');
                }
            }

            function updatePhaseFromContent(content) {
                if (content.includes('Phase 1') || content.includes('concurrent') || content.includes('analyzing concurrently')) {
                    activatePhase(1);
                } else if (content.includes('Phase 2') || content.includes('critique') || content.includes('critiquing')) {
                    activatePhase(2);
                } else if (content.includes('Phase 3') || content.includes('synthesis') || content.includes('synthesizing')) {
                    activatePhase(3);
                }
            }

            function displayMessage(response) {
                const messagesDiv = document.getElementById('messages');
                
                if (response.type === 'partial') {
                    // Handle streaming tokens
                    if (!currentStreamingMessage) {
                        // Create new streaming message container
                        currentStreamingMessage = document.createElement('div');
                        currentStreamingMessage.className = 'message streaming';
                        currentStreamingMessage.innerHTML = `<strong>AI COUNCIL:</strong> <span class="streaming-content"></span>`;
                        messagesDiv.appendChild(currentStreamingMessage);
                        streamingContent = '';
                    }
                    
                    // Append token to streaming content
                    streamingContent += response.content;
                    const contentSpan = currentStreamingMessage.querySelector('.streaming-content');
                    contentSpan.textContent = streamingContent;
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    
                } else if (response.type === 'final') {
                    // Complete the streaming message
                    if (currentStreamingMessage) {
                        currentStreamingMessage.className = 'message final';
                        const contentSpan = currentStreamingMessage.querySelector('.streaming-content');
                        contentSpan.textContent = response.content;
                        
                        // Add metadata
                        if (response.metadata && Object.keys(response.metadata).length > 0) {
                            const metadataDiv = document.createElement('div');
                            metadataDiv.className = 'metadata';
                            metadataDiv.innerHTML = `Time: ${response.processing_time.toFixed(1)}s | ` + 
                                                   `Agents: ${response.metadata.agents_participated ? response.metadata.agents_participated.join(', ') : 'unknown'}`;
                            currentStreamingMessage.appendChild(metadataDiv);
                        }
                        
                        currentStreamingMessage = null;
                        streamingContent = '';
                    } else {
                        // Fallback for non-streaming final response
                        const messageDiv = document.createElement('div');
                        messageDiv.className = 'message final';
                        messageDiv.innerHTML = `<strong>FINAL:</strong> ${response.content}`;
                        messagesDiv.appendChild(messageDiv);
                    }
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    
                } else {
                    // Handle status, error, and other message types
                    const messageDiv = document.createElement('div');
                    messageDiv.className = `message ${response.type}`;
                    
                    // Update phase indicators for status messages
                    if (response.type === 'status') {
                        updatePhaseFromContent(response.content);
                    }
                    
                    let content = `<strong>${response.type.toUpperCase()}:</strong> ${response.content}`;
                    
                    if (response.phase && response.type === 'status') {
                        content += `<div class="metadata">Phase: ${response.phase}`;
                        if (response.processing_time) {
                            content += ` | Time: ${response.processing_time.toFixed(1)}s`;
                        }
                        if (response.metadata && response.metadata.agent) {
                            content += ` | Agent: ${response.metadata.agent}`;
                        }
                        content += `</div>`;
                    }
                    
                    messageDiv.innerHTML = content;
                    messagesDiv.appendChild(messageDiv);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
                
                // Store connection info
                if (response.type === 'status' && response.request_id.startsWith('connection_')) {
                    connectionId = response.request_id.replace('connection_', '');
                    document.getElementById('connectionId').textContent = connectionId.substring(0, 8) + '...';
                }
            }

            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (!message || !ws || ws.readyState !== WebSocket.OPEN) {
                    return;
                }
                
                // Reset phases for new deliberation
                resetPhases();
                
                // Display user message
                const messagesDiv = document.getElementById('messages');
                const userDiv = document.createElement('div');
                userDiv.className = 'message user';
                userDiv.innerHTML = `<strong>YOU:</strong> ${message}`;
                messagesDiv.appendChild(userDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                
                // Send to server
                ws.send(JSON.stringify({
                    message: message,
                    conversation_id: connectionId || 'test_conversation'
                }));
                
                input.value = '';
                
                // Disable send button temporarily
                const sendButton = document.getElementById('sendButton');
                sendButton.disabled = true;
                sendButton.textContent = 'Processing...';
                
                setTimeout(() => {
                    sendButton.disabled = false;
                    sendButton.textContent = 'Send Message';
                }, 3000);
            }

            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }

            // Connect on page load
            connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Hybrid AI Council API server...")
    print("📊 Health check: http://localhost:8000/health")
    print("🧠 WebSocket chat: ws://localhost:8000/ws/chat")
    print("🌐 Test client: http://localhost:8000/")
    print("📖 API docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )