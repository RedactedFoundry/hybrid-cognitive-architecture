"""
Voice WebSocket Handlers for Hybrid AI Council
==============================================

Voice-specific WebSocket handling functions for real-time speech-to-text,
AI Council processing, and text-to-speech responses.

Extracted from handlers.py for better modularity and maintainability.
"""

import base64
import os
import tempfile
import uuid
from typing import Dict

from fastapi import WebSocket
import structlog

# Import error types directly from core to avoid circular imports
from core.error_boundaries import (
    ValidationError, 
    ProcessingError, 
    error_boundary
)
from voice_foundation.orchestrator_integration import get_initialized_voice_orchestrator

# Set up logger
logger = structlog.get_logger(__name__)


@error_boundary(component="voice_input_handler")
async def handle_voice_input(websocket: WebSocket, data: dict, conversation_id: str):
    """Handle incoming voice input and process through AI Council with comprehensive error handling."""
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
        voice_orch = await get_initialized_voice_orchestrator()
        
        if voice_orch is None or voice_orch.voice_foundation is None:
            logger.error("Voice orchestrator not available")
            await websocket.send_json({
                "type": "error",
                "message": "Voice service not available - please try again later"
            })
            return
            
        transcription = await voice_orch.voice_foundation.process_audio_to_text(wav_path)
        
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
            orchestrator_result = await voice_orch.orchestrator.process_request(
                user_input=transcription,
                conversation_id=conversation_id
            )
            
            if orchestrator_result and orchestrator_result.final_response:
                # Generate audio response
                response_audio_path = f"voice_foundation/outputs/realtime_{uuid.uuid4()}.wav"
                os.makedirs("voice_foundation/outputs", exist_ok=True)
                
                tts_success = await voice_orch.voice_foundation.process_text_to_audio(
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
            
    except (ValidationError, ProcessingError) as e:
        logger.error("Voice input validation/processing error", error=str(e), error_type=type(e).__name__)
        await websocket.send_json({
            "type": "error",
            "message": "Voice processing failed - please try again"
        })
    except (ConnectionError, TimeoutError) as e:
        logger.error("Voice input connection/timeout error", error=str(e), error_type=type(e).__name__)
        await websocket.send_json({
            "type": "error",
            "message": "Voice processing timeout - please try again"
        })
    except Exception as e:
        logger.error("Voice input unexpected error", error=str(e), error_type=type(e).__name__, exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": "Voice processing failed - please try again"
        })