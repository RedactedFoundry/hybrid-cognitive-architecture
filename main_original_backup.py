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
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

from config import Config

# Import our core orchestrator
from core.orchestrator import UserFacingOrchestrator, ProcessingPhase
from core.logging_config import setup_logging

# Import voice foundation
from voice_foundation.orchestrator_integration import voice_orchestrator

# Import clients for health checks
from clients.ollama_client import get_ollama_client
from clients.redis_client import get_redis_connection
from clients.tigervector_client import get_tigergraph_connection


# Request/Response models
class ChatMessage(BaseModel):
    """WebSocket chat message from client."""
    message: str = Field(description="User's message content")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for context")

class VoiceChatResponse(BaseModel):
    """Response model for voice chat endpoint."""
    success: bool = Field(description="Whether the voice processing was successful")
    request_id: str = Field(description="Unique identifier for this request")
    transcription: Optional[str] = Field(default=None, description="Transcribed text from audio input")
    response_text: Optional[str] = Field(default=None, description="AI response text")
    audio_url: Optional[str] = Field(default=None, description="URL to download response audio")
    processing_time: float = Field(description="Total processing time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")
    orchestrator_stats: Optional[Dict[str, Any]] = Field(default=None, description="Statistics from cognitive processing")
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


class SimpleChatRequest(BaseModel):
    """Request model for simple chat testing."""
    message: str = Field(description="User message")
    conversation_id: Optional[str] = Field(default="test", description="Conversation ID")


class SimpleChatResponse(BaseModel):
    """Response model for simple chat testing."""
    response: str = Field(description="AI response")
    intent: Optional[str] = Field(default=None, description="Detected intent from Smart Router")
    processing_time: float = Field(description="Processing time in seconds")
    path_taken: str = Field(description="Which cognitive path was used")


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

# Add CORS middleware for web client development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


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


@app.get("/cache-stats")
async def get_cache_stats():
    """
    Get prompt cache performance statistics.
    
    Returns detailed information about cache hit rates, cost savings,
    and performance metrics for monitoring and optimization.
    """
    try:
        from core.cache_integration import get_global_cache_manager
        
        cache_manager = await get_global_cache_manager()
        if cache_manager:
            stats = await cache_manager.get_orchestrator_cache_stats()
            
            logger.info("Cache stats requested", 
                       cache_enabled=stats.get("cache_enabled", False),
                       hit_rate=stats.get("cache_stats", {}).get("hit_rate", 0))
            
            return {
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cache_configuration": {
                    "enabled": stats.get("cache_enabled", False),
                    "ttl_hours": stats.get("cache_ttl_hours", 0),
                    "clients_cached": stats.get("clients_cached", 0)
                },
                "performance_stats": stats.get("cache_stats", {}),
                "actions": {
                    "clear_cache": "/cache-clear",
                    "cleanup_cache": "/cache-cleanup"
                }
            }
        else:
            return {
                "status": "disabled",
                "message": "Cache manager not initialized or caching disabled",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error("Error retrieving cache stats", error=str(e))
        return {
            "status": "error",
            "message": f"Failed to retrieve cache statistics: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.post("/cache-clear")
async def clear_cache(pattern: Optional[str] = None):
    """
    Clear cache entries.
    
    Args:
        pattern: Optional pattern to match keys for selective clearing
    """
    try:
        from core.cache_integration import get_global_cache_manager
        
        cache_manager = await get_global_cache_manager()
        if cache_manager:
            # Clear cache on all cached clients
            total_cleared = 0
            for client in cache_manager._cached_clients.values():
                if hasattr(client, 'clear_cache'):
                    cleared = await client.clear_cache(pattern)
                    total_cleared += cleared
                    
            logger.info("Cache cleared", pattern=pattern, entries_cleared=total_cleared)
            
            return {
                "status": "success",
                "message": f"Cache cleared successfully",
                "entries_cleared": total_cleared,
                "pattern": pattern,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "status": "disabled", 
                "message": "Cache manager not available"
            }
            
    except Exception as e:
        logger.error("Error clearing cache", error=str(e), pattern=pattern)
        return {
            "status": "error",
            "message": f"Failed to clear cache: {str(e)}"
        }


@app.post("/cache-cleanup")
async def cleanup_cache():
    """
    Perform cache cleanup to remove expired entries and optimize storage.
    """
    try:
        from core.cache_integration import get_global_cache_manager
        
        cache_manager = await get_global_cache_manager()
        if cache_manager:
            cleanup_results = await cache_manager.perform_cache_cleanup()
            
            logger.info("Cache cleanup performed", results=cleanup_results)
            
            return {
                "status": "success",
                "message": "Cache cleanup completed successfully",
                "cleanup_results": cleanup_results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "status": "disabled",
                "message": "Cache manager not available"
            }
            
    except Exception as e:
        logger.error("Error during cache cleanup", error=str(e))
        return {
            "status": "error", 
            "message": f"Cache cleanup failed: {str(e)}"
        }


# Simple Chat Endpoint for Smart Router Testing

@app.post("/api/chat", response_model=SimpleChatResponse)
async def simple_chat(request: SimpleChatRequest):
    """
    Simple REST chat endpoint for testing the Smart Router.
    
    This endpoint processes text messages through the full cognitive architecture
    and returns the response with Smart Router metadata for debugging.
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Process through the Smart Router orchestrator
        orchestrator_result = await orchestrator.process_request(
            user_input=request.message,
            conversation_id=request.conversation_id
        )
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Determine which path was taken based on metadata and phase
        path_taken = "unknown"
        intent = None
        
        if hasattr(orchestrator_result, 'routing_intent') and orchestrator_result.routing_intent:
            intent = orchestrator_result.routing_intent.value
            
            if orchestrator_result.routing_intent.value == "simple_query_task":
                path_taken = "fast_response"
            elif orchestrator_result.routing_intent.value == "complex_reasoning_task":
                path_taken = "council_deliberation" 
            elif orchestrator_result.routing_intent.value == "exploratory_task":
                path_taken = "pheromind_scan"
            elif orchestrator_result.routing_intent.value == "action_task":
                path_taken = "kip_execution"
        
        # Check metadata for additional clues
        if hasattr(orchestrator_result, 'metadata') and orchestrator_result.metadata:
            if orchestrator_result.metadata.get("fast_path_used"):
                path_taken = "fast_response"
        
        return SimpleChatResponse(
            response=orchestrator_result.final_response or "No response generated",
            intent=intent,
            processing_time=processing_time,
            path_taken=path_taken
        )
        
    except Exception as e:
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error("Simple chat error", error=str(e), exc_info=True)
        
        return SimpleChatResponse(
            response=f"Error processing request: {str(e)}",
            intent=None,
            processing_time=processing_time,
            path_taken="error"
        )


# Voice Foundation Endpoints

@app.post("/api/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(
    audio: UploadFile = File(..., description="Audio file (WAV format recommended)"),
    conversation_id: Optional[str] = Form(None, description="Conversation ID for context"),
    user_id: Optional[str] = Form("voice_user", description="User identifier")
):
    """
    Voice-to-voice chat endpoint.
    
    Upload an audio file and receive an AI response as both text and audio.
    This endpoint processes the audio through the full 3-layer cognitive architecture.
    """
    request_id = str(uuid.uuid4())
    logger.info("Voice chat request received", request_id=request_id, filename=audio.filename)
    
    try:
        # Validate file type
        if not audio.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg')):
            raise HTTPException(status_code=400, detail="Audio file must be WAV, MP3, M4A, or OGG format")
        
        # Create unique filename for this request
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            # Save uploaded audio
            content = await audio.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        # Create output path
        output_dir = "voice_foundation/outputs"
        os.makedirs(output_dir, exist_ok=True)
        output_audio_path = f"{output_dir}/{request_id}_response.wav"
        
        # Process through voice foundation
        result = await voice_orchestrator.process_voice_request(
            audio_input_path=temp_audio_path,
            audio_output_path=output_audio_path,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        # Clean up temp file
        os.unlink(temp_audio_path)
        
        if result["success"]:
            # Create public URL for audio response
            audio_url = f"/api/voice/audio/{request_id}_response.wav"
            
            response = VoiceChatResponse(
                success=True,
                request_id=result["request_id"],
                transcription=result["transcription"],
                response_text=result["response_text"],
                audio_url=audio_url,
                processing_time=result["processing_time"],
                orchestrator_stats=result.get("orchestrator_state", {}),
                metadata={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "audio_format": audio.filename.split('.')[-1].lower()
                }
            )
            
            logger.info("Voice chat completed successfully", 
                       request_id=request_id, 
                       processing_time=result["processing_time"],
                       response_length=len(result["response_text"]))
            
            return response
        else:
            logger.error("Voice chat processing failed", 
                        request_id=request_id, 
                        error=result.get("error"))
            
            return VoiceChatResponse(
                success=False,
                request_id=result["request_id"],
                transcription=result.get("transcription"),
                processing_time=result["processing_time"],
                error=result.get("error"),
                metadata={
                    "conversation_id": conversation_id,
                    "user_id": user_id
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Voice chat endpoint error", request_id=request_id, error=str(e), exc_info=True)
        return VoiceChatResponse(
            success=False,
            request_id=request_id,
            processing_time=0.0,
            error=f"Internal server error: {str(e)}",
            metadata={"conversation_id": conversation_id, "user_id": user_id}
        )


@app.post("/api/voice/test")
async def voice_test():
    """Quick test endpoint to verify voice API is working."""
    return {"status": "Voice API is working", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/voice/audio/{filename}")
async def get_voice_audio(filename: str):
    """
    Download generated voice response audio files.
    
    This endpoint serves the audio files generated by the voice chat endpoint.
    """
    try:
        file_path = f"voice_foundation/outputs/{filename}"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            filename=filename,
            headers={"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
        )
        
    except Exception as e:
        logger.error("Error serving voice audio", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail="Error serving audio file")


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for voice conversation.
    
    This endpoint handles real-time voice chat with the AI Council,
    providing natural conversation flow with interruption handling.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    conversation_id = f"voice_{connection_id}"
    
    logger.info("Real-time voice connection established", 
                connection_id=connection_id, 
                conversation_id=conversation_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "Real-time voice chat ready"
        })
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                if data["type"] == "voice_input":
                    await handle_voice_input(websocket, data, conversation_id)
                elif data["type"] == "interrupt":
                    await handle_conversation_interrupt(websocket, conversation_id)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {data['type']}"
                    })
                    
            except Exception as e:
                logger.error("Error processing voice message", 
                           connection_id=connection_id, 
                           error=str(e), 
                           exc_info=True)
                
                await websocket.send_json({
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        logger.info("Real-time voice connection closed", connection_id=connection_id)
    except Exception as e:
        logger.error("Voice WebSocket error", connection_id=connection_id, error=str(e))
        
        
async def handle_voice_input(websocket: WebSocket, data: dict, conversation_id: str):
    """Handle incoming voice input and process through AI Council."""
    import base64
    import tempfile
    import os
    
    try:
        # Send processing update
        await websocket.send_json({
            "type": "processing_update",
            "message": "Processing your voice..."
        })
        
        # Decode audio data
        audio_data = base64.b64decode(data["audio_data"])
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            temp_file.write(audio_data)
            temp_audio_path = temp_file.name
        
        # Convert WebM to WAV if needed (simplified for now)
        # Note: In production, you'd want proper audio format conversion
        wav_path = temp_audio_path.replace('.webm', '.wav')
        
        # For now, assume the audio works directly (mock conversion)
        # In production: use ffmpeg or similar for format conversion
        os.rename(temp_audio_path, wav_path)
        
        # Process through voice foundation (STT)
        transcription = await voice_orchestrator.voice_foundation.process_audio_to_text(wav_path)
        
        if transcription:
            # Send transcription to client
            await websocket.send_json({
                "type": "transcription",
                "text": transcription
            })
            
            # Send processing update
            await websocket.send_json({
                "type": "processing_update", 
                "message": "AI Council deliberating..."
            })
            
            # Process through orchestrator
            orchestrator_result = await voice_orchestrator.orchestrator.process_request(
                user_input=transcription,
                conversation_id=conversation_id
            )
            
            if orchestrator_result and orchestrator_result.final_response:
                # Generate audio response
                response_audio_path = f"voice_foundation/outputs/realtime_{uuid.uuid4()}.wav"
                os.makedirs("voice_foundation/outputs", exist_ok=True)
                
                tts_success = await voice_orchestrator.voice_foundation.process_text_to_audio(
                    orchestrator_result.final_response,
                    response_audio_path
                )
                
                if tts_success:
                    # Send response with audio URL
                    audio_url = f"/api/voice/audio/{os.path.basename(response_audio_path)}"
                    
                    await websocket.send_json({
                        "type": "ai_response",
                        "text": orchestrator_result.final_response,
                        "audio_url": audio_url,
                        "processing_stats": {
                            "phase": orchestrator_result.current_phase.value if hasattr(orchestrator_result, 'current_phase') else 'completed',
                            "messages": len(orchestrator_result.messages) if hasattr(orchestrator_result, 'messages') else 0
                        }
                    })
                else:
                    await websocket.send_json({
                        "type": "ai_response",
                        "text": orchestrator_result.final_response,
                        "audio_url": None
                    })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": "AI processing failed - please try again"
                })
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Could not understand audio - please try again"
            })
        
        # Clean up temporary file
        if os.path.exists(wav_path):
            os.unlink(wav_path)
            
    except Exception as e:
        logger.error("Voice input processing error", error=str(e), exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": f"Voice processing error: {str(e)}"
        })


async def handle_conversation_interrupt(websocket: WebSocket, conversation_id: str):
    """Handle conversation interruption (when user starts talking while AI is responding)."""
    logger.info("Conversation interrupted", conversation_id=conversation_id)
    
    # TODO: Implement AI response interruption logic
    # For now, just acknowledge the interruption
    await websocket.send_json({
        "type": "interrupt_acknowledged",
        "message": "AI response interrupted - ready for new input"
    })


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
                try:
                    error_response = ChatResponse(
                        type="error",
                        content=f"Invalid JSON format: {str(e)}",
                        request_id="error_" + str(uuid.uuid4()),
                        conversation_id="error"
                    )
                    await websocket.send_text(error_response.model_dump_json())
                except Exception:
                    # WebSocket likely closed, just continue
                    pass
                continue
            except Exception as e:
                try:
                    error_response = ChatResponse(
                        type="error",
                        content=f"Message format error: {str(e)}",
                        request_id="error_" + str(uuid.uuid4()),
                        conversation_id="error"
                    )
                    await websocket.send_text(error_response.model_dump_json())
                except Exception:
                    # WebSocket likely closed, just continue  
                    pass
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
            
            # Send acknowledgment (if websocket still connected)
            try:
                ack_response = ChatResponse(
                    type="status",
                    content="Message received. Starting AI Council deliberation...",
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase="received"
                )
                await websocket.send_text(ack_response.model_dump_json())
            except Exception:
                # WebSocket disconnected before ack, continue processing anyway
                logger.debug("Could not send acknowledgment, WebSocket likely closed", connection_id=connection_id)
            
            try:
                # Process through Smart Router orchestrator
                process_start_time = datetime.now(timezone.utc)
                orchestrator_result = await orchestrator.process_request(
                    user_input=chat_message.message,
                    conversation_id=conversation_id
                )
                
                # Send the Smart Router result
                processing_time = (datetime.now(timezone.utc) - process_start_time).total_seconds()
                
                try:
                    final_response = ChatResponse(
                        type="final",
                        content=orchestrator_result.final_response or "No response generated",
                        request_id=request_id,
                        conversation_id=conversation_id,
                        phase="completed",
                        processing_time=processing_time,
                        metadata={
                            "intent": orchestrator_result.routing_intent.value if orchestrator_result.routing_intent else None,
                            "smart_router_used": True
                        }
                    )
                    await websocket.send_text(final_response.model_dump_json())
                except Exception as send_error:
                    # WebSocket closed before we could send final response
                    logger.debug("Could not send final response, WebSocket likely closed", 
                               connection_id=connection_id, 
                               send_error=str(send_error))
                
            except Exception as e:
                logger.error(
                    "Error processing chat message",
                    connection_id=connection_id,
                    request_id=request_id,
                    error=str(e),
                    exc_info=True
                )
                
                # Only send error response if websocket is still connected
                # (don't try to send through a disconnected websocket)
                try:
                    error_response = ChatResponse(
                        type="error",
                        content=f"I apologize, but I encountered an error processing your request: {str(e)}",
                        request_id=request_id,
                        conversation_id=conversation_id,
                        phase="error"
                    )
                    await websocket.send_text(error_response.model_dump_json())
                except Exception as send_error:
                    # WebSocket already closed or other send error
                    logger.debug("Could not send error response, WebSocket likely closed", 
                               connection_id=connection_id, 
                               send_error=str(send_error))
    
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
    
    # Determine base URL for cloud compatibility
    if config.environment in ["production", "prod", "staging"]:
        # In production, use environment-specific URLs
        base_url = os.getenv("PUBLIC_URL", f"http://{config.api_host}:{config.api_port}")
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    else:
        # Development - use localhost
        base_url = f"http://localhost:{config.api_port}"
        ws_url = f"ws://localhost:{config.api_port}"
    
    print("🚀 Starting Hybrid AI Council API server...")
    print(f"📊 Health check: {base_url}/health")
    print(f"🧠 WebSocket chat: {ws_url}/ws/chat")
    print(f"🌐 Test client: {base_url}/")
    print(f"📖 API docs: {base_url}/docs")
    print(f"🔧 Environment: {config.environment}")
    
    uvicorn.run(
        "main:app",
        host=config.api_host,
        port=config.api_port,
        reload=(config.environment == "development"),
        log_level=config.log_level.lower()
    )
    )