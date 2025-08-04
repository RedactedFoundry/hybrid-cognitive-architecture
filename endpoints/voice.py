"""
Voice Endpoints for Hybrid AI Council
=====================================

REST and WebSocket endpoints for voice-based interactions.
Extracted from main.py for better modularity and maintainability.
"""

import os
import uuid
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
import structlog

from models.api_models import VoiceChatResponse
from utils.websocket_utils import WebSocketConnectionManager
from voice_foundation.orchestrator_integration import get_voice_orchestrator
from websocket_handlers.voice_handlers import handle_voice_input
from websocket_handlers.chat_handlers import handle_conversation_interrupt

# Set up logger
logger = structlog.get_logger(__name__)

# Create router for voice endpoints
router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/chat", response_model=VoiceChatResponse)
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
        voice_orch = get_voice_orchestrator()
        result = await voice_orch.process_voice_request(
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


@router.post("/test")
async def voice_test():
    """Quick test endpoint to verify voice API is working."""
    return {"status": "Voice API is working", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/audio/{filename}")
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


# WebSocket voice endpoint (to be mounted in main.py)
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for voice conversation.
    
    This endpoint handles real-time voice chat with the AI Council,
    providing natural conversation flow with interruption handling.
    """
    # Use connection manager for standardized setup
    connection_manager = WebSocketConnectionManager("voice")
    connection_id = await connection_manager.establish_connection(websocket)
    conversation_id = f"voice_{connection_id}"
    
    logger.info("Real-time voice connection established", 
                connection_id=connection_id, 
                conversation_id=conversation_id)
    
    try:
        # Send welcome message using utility
        await connection_manager.send_welcome_message(
            websocket,
            connection_id,
            "Real-time voice chat ready"
        )
        
        while True:
            try:
                # Receive message from client
                request_data = await websocket.receive_json()
                
                if request_data["type"] == "voice_input":
                    await handle_voice_input(websocket, request_data, conversation_id)
                elif request_data["type"] == "interrupt":
                    await handle_conversation_interrupt(websocket, conversation_id)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {request_data['type']}"
                    })
                    
            except Exception as e:
                # Use utility for standardized error handling
                if not await connection_manager.handle_message_error(websocket, e, connection_id):
                    break  # Connection should be closed
                
    except WebSocketDisconnect as disconnect_error:
        await connection_manager.handle_disconnect(connection_id, disconnect_error)
    except Exception as e:
        logger.error("Voice WebSocket error", connection_id=connection_id, error=str(e))
        await connection_manager.cleanup_connection(connection_id, "error")
    finally:
        # Ensure connection is cleaned up
        await connection_manager.cleanup_connection(connection_id, "normal")