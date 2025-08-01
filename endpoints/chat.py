"""
Chat Endpoints for Hybrid AI Council
====================================

REST and WebSocket endpoints for text-based chat interactions.
Extracted from main.py for better modularity and maintainability.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket
import structlog

from core.orchestrator import UserFacingOrchestrator
from models.api_models import SimpleChatRequest, SimpleChatResponse
from websockets.chat_handlers import websocket_chat_handler

# Set up logger
logger = structlog.get_logger(__name__)

# Global orchestrator instance (initialized in main.py)
orchestrator: UserFacingOrchestrator = None

def set_orchestrator(orch: UserFacingOrchestrator):
    """Set the global orchestrator instance."""
    global orchestrator
    orchestrator = orch

# Create router for chat endpoints
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=SimpleChatResponse)
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


# WebSocket chat endpoint (to be mounted in main.py)
async def websocket_chat_endpoint(websocket: WebSocket, orchestrator: UserFacingOrchestrator):
    """
    Real-time WebSocket endpoint for AI Council chat interaction.
    
    This endpoint provides real-time streaming of AI Council deliberation,
    allowing users to see the multi-agent reasoning process as it happens.
    
    Message format:
    - Client sends: {"message": "user question", "conversation_id": "optional"}
    - Server streams: Multiple responses with different types (status, partial, final)
    """
    await websocket_chat_handler(websocket, orchestrator)