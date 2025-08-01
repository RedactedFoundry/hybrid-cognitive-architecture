"""
Chat WebSocket Handlers for Hybrid AI Council
=============================================

Chat-specific WebSocket handling functions for real-time text-based interactions,
AI Council deliberation streaming, and conversation management.

Extracted from handlers.py for better modularity and maintainability.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect
import structlog

from core.orchestrator import ProcessingPhase, UserFacingOrchestrator
from models.api_models import ChatMessage, ChatResponse
from utils.websocket_utils import WebSocketConnectionManager, active_connections
# Import error handling directly from core to avoid circular imports
from core.error_boundaries import (
    ValidationError, 
    ProcessingError, 
    error_boundary
)

# Import websocket utilities from utils.error_utils
# These are safe because they don't cause circular imports
try:
    from utils.error_utils import (
        handle_websocket_error,
        validate_user_input,
        validate_conversation_id
    )
except ImportError:
    # Simple fallback implementations
    async def handle_websocket_error(ws, error, conn_id):
        return False
    def validate_user_input(text):
        pass
    def validate_conversation_id(conv_id):
        pass

# Set up logger
logger = structlog.get_logger(__name__)


@error_boundary(component="conversation_interrupt_handler")
async def handle_conversation_interrupt(websocket: WebSocket, conversation_id: str):
    """Handle conversation interruption (when user starts talking while AI is responding) with error boundaries."""
    logger.info("Conversation interrupted", conversation_id=conversation_id)
    
    # Get connection ID for task cancellation
    connection_id = None
    for conn_id, ws in active_connections.items():
        if ws == websocket:
            connection_id = conn_id
            break
    
    if connection_id:
        # Create connection manager to handle task cancellation
        connection_manager = WebSocketConnectionManager("chat")
        
        # Cancel all active response tasks for this connection
        await connection_manager.cancel_active_response_tasks(connection_id)
        
        logger.info("AI response tasks cancelled due to interruption", 
                   connection_id=connection_id,
                   conversation_id=conversation_id)
    
    # Send interruption acknowledgment
    await websocket.send_json({
        "type": "interrupt_acknowledged",
        "message": "AI response interrupted - ready for new input",
        "conversation_id": conversation_id
    })


@error_boundary(component="websocket_chat_handler")
async def websocket_chat_handler(websocket: WebSocket, orchestrator: UserFacingOrchestrator):
    """
    Real-time WebSocket handler for AI Council chat interaction with comprehensive error boundaries.
    
    This handler provides real-time streaming of AI Council deliberation,
    allowing users to see the multi-agent reasoning process as it happens.
    
    Message format:
    - Client sends: {"message": "user question", "conversation_id": "optional"}
    - Server streams: Multiple responses with different types (status, partial, final)
    """
    # Use connection manager for standardized setup
    connection_manager = WebSocketConnectionManager("chat")
    connection_id = await connection_manager.establish_connection(websocket)
    
    try:
        # Send welcome message using utility
        await connection_manager.send_welcome_message(
            websocket, 
            connection_id,
            "🤖 AI Council WebSocket connected. Send your questions for multi-agent deliberation!"
        )
        
        while True:
            # Receive message from client
            try:
                raw_message = await websocket.receive_text()
                message_data = json.loads(raw_message)
                chat_message = ChatMessage(**message_data)
            except json.JSONDecodeError as e:
                # Use utility for standardized error handling
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
                continue
            except (ValidationError, ProcessingError) as e:
                # Handle validation and processing errors specifically
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
                continue
            except Exception as e:
                # Use utility for standardized error handling of unexpected errors
                logger.error("Unexpected message processing error", error=str(e), error_type=type(e).__name__)
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
                continue
            
            # Input validation using new error utilities
            try:
                validate_user_input(chat_message.message)
                if chat_message.conversation_id:
                    validate_conversation_id(chat_message.conversation_id)
            except ValidationError as e:
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break
                continue
            
            # Generate request ID and conversation ID
            request_id = str(uuid.uuid4())
            conversation_id = chat_message.conversation_id or str(uuid.uuid4())
            
            logger.info("Processing WebSocket chat request", 
                       request_id=request_id,
                       conversation_id=conversation_id,
                       input_preview=chat_message.message[:100])
            
            # Send acknowledgment
            try:
                ack_response = ChatResponse(
                    type="acknowledgment",
                    content="Message received, processing...",
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase="received",
                    processing_time=0.0
                )
                await websocket.send_text(ack_response.model_dump_json())
            except Exception as ack_error:
                # WebSocket closed before we could send acknowledgment
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
                # Use utility for comprehensive error handling
                logger.error("Smart Router processing failed", 
                           connection_id=connection_id,
                           request_id=request_id,
                           error=str(e),
                           exc_info=True)
                
                # Try to send error response
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
    
    except WebSocketDisconnect as e:
        # Handle client disconnection gracefully
        await connection_manager.handle_disconnect(connection_id, e)
    
    except Exception as e:
        # Handle unexpected errors
        logger.error("Unexpected WebSocket error", 
                   connection_id=connection_id,
                   error=str(e), 
                   exc_info=True)
        
        await connection_manager.cleanup_connection(connection_id, "error")

    finally:
        # Ensure connection is cleaned up
        await connection_manager.cleanup_connection(connection_id)


@error_boundary(component="streaming_processor")
async def process_with_streaming(
    websocket: WebSocket,
    user_input: str,
    request_id: str,
    conversation_id: str,
    orchestrator: UserFacingOrchestrator
):
    """
    Process user input through the orchestrator with real-time token streaming and comprehensive error handling.
    
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
                    metadata={"agent": event.agent}
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
                # Send error events
                error_response = ChatResponse(
                    type="error",
                    content=f"Processing error: {event.content}",
                    request_id=request_id,
                    conversation_id=conversation_id,
                    phase="error",
                    processing_time=current_time,
                    metadata={"error_details": event.metadata}
                )
                await websocket.send_text(error_response.model_dump_json())
                break
    
    except Exception as e:
        # Handle streaming errors gracefully
        error_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.error("Streaming processing failed", 
                   request_id=request_id,
                   error=str(e),
                   exc_info=True)
        
        try:
            error_response = ChatResponse(
                type="error",
                content="Stream processing failed - please try again",
                request_id=request_id,
                conversation_id=conversation_id,
                phase="error",
                processing_time=error_time,
                metadata={"error": str(e)}
            )
            await websocket.send_text(error_response.model_dump_json())
        except (WebSocketDisconnect, ConnectionError, RuntimeError):
            # WebSocket likely closed, ignore send error
            pass
        
        raise  # Re-raise for error boundary handling