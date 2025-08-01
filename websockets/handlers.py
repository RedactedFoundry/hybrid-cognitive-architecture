"""
WebSocket Handlers for Hybrid AI Council
========================================

Centralized WebSocket handling functions for chat and voice interactions.
Extracted from main.py for better modularity and maintainability.
"""

import asyncio
import base64
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect
import structlog

from core.orchestrator import ProcessingPhase, UserFacingOrchestrator
from models.api_models import ChatMessage, ChatResponse
from utils.websocket_utils import WebSocketConnectionManager, active_connections
from voice_foundation.orchestrator_integration import voice_orchestrator

# Set up logger
logger = structlog.get_logger(__name__)


async def handle_voice_input(websocket: WebSocket, data: dict, conversation_id: str):
    """Handle incoming voice input and process through AI Council."""
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


async def websocket_chat_handler(websocket: WebSocket, orchestrator: UserFacingOrchestrator):
    """
    Real-time WebSocket handler for AI Council chat interaction.
    
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
            "Connected to Hybrid AI Council. Send your message to begin deliberation."
        )
        
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                chat_message = ChatMessage(**message_data)
            except json.JSONDecodeError as e:
                # Use utility for standardized error handling
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
                continue
            except Exception as e:
                # Use utility for standardized error handling
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
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
    
    except WebSocketDisconnect as disconnect_error:
        await connection_manager.handle_disconnect(connection_id, disconnect_error)
    except Exception as e:
        logger.error("WebSocket connection error", connection_id=connection_id, error=str(e), exc_info=True)
        await connection_manager.cleanup_connection(connection_id, "error")
    finally:
        # Ensure connection is cleaned up
        await connection_manager.cleanup_connection(connection_id, "normal")


async def process_with_streaming(
    websocket: WebSocket,
    user_input: str,
    request_id: str,
    conversation_id: str,
    orchestrator: UserFacingOrchestrator
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