# python311-services/voice/main.py
"""
Voice Processing Microservice (Python 3.11)

FastAPI service that handles STT and TTS processing for the Hybrid AI Council.
Runs independently from the main Python 3.13 project.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import uuid

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import structlog
import uvicorn

from engines.voice_engines import VoiceProcessor

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("VoiceService")

# Initialize FastAPI app
app = FastAPI(
    title="Voice Processing Service",
    description="Python 3.11 voice processing microservice for Hybrid AI Council",
    version="1.0.0"
)

# Global voice processor instance
voice_processor: Optional[VoiceProcessor] = None

# Request/Response models
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "default"
    language: str = "en"
    
class TTSResponse(BaseModel):
    audio_file_id: str
    duration_seconds: float
    voice_used: str
    
class STTResponse(BaseModel):
    text: str
    confidence: float
    processing_time_seconds: float

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, Any]
    version: str

@app.on_event("startup")
async def startup_event():
    """Initialize voice processing engines on startup."""
    global voice_processor
    
    logger.info("Starting Voice Processing Service (Python 3.11)")
    
    try:
        voice_processor = VoiceProcessor()
        await voice_processor.initialize()
        
        logger.info(
            "Voice Processing Service initialized successfully",
            stt_engine=voice_processor.stt_engine.name,
            tts_engine=voice_processor.tts_engine.name
        )
        
    except Exception as e:
        logger.error(
            "Failed to initialize voice processing service",
            error=str(e),
            exc_info=True
        )
        raise

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if not voice_processor:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    return HealthResponse(
        status="healthy",
        services={
            "stt": {
                "engine": voice_processor.stt_engine.name,
                "initialized": voice_processor.stt_engine.is_initialized
            },
            "tts": {
                "engine": voice_processor.tts_engine.name,
                "initialized": voice_processor.tts_engine.is_initialized
            }
        },
        version="1.0.0"
    )

@app.post("/voice/stt", response_model=STTResponse)
async def speech_to_text(audio_file: UploadFile = File(...)):
    """Convert speech to text."""
    if not voice_processor:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    # Create temporary file for audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        content = await audio_file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Process audio with STT
        result = await voice_processor.transcribe_audio(temp_file_path)
        
        logger.info(
            "STT processing completed",
            text_length=len(result["text"]),
            confidence=result["confidence"],
            processing_time=result["processing_time_seconds"]
        )
        
        return STTResponse(**result)
        
    except Exception as e:
        logger.error(
            "STT processing failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"STT processing failed: {str(e)}")
        
    finally:
        # Clean up temp file
        os.unlink(temp_file_path)

@app.post("/voice/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Convert text to speech."""
    if not voice_processor:
        raise HTTPException(status_code=503, detail="Voice processor not initialized")
    
    try:
        # Generate unique file ID
        audio_file_id = str(uuid.uuid4())
        
        # Process text with TTS
        result = await voice_processor.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            language=request.language,
            output_file_id=audio_file_id
        )
        
        logger.info(
            "TTS processing completed",
            text_length=len(request.text),
            voice_id=request.voice_id,
            audio_file_id=audio_file_id,
            duration=result["duration_seconds"]
        )
        
        return TTSResponse(
            audio_file_id=audio_file_id,
            duration_seconds=result["duration_seconds"],
            voice_used=result["voice_used"]
        )
        
    except Exception as e:
        logger.error(
            "TTS processing failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"TTS processing failed: {str(e)}")

@app.get("/voice/audio/{audio_file_id}")
async def get_audio_file(audio_file_id: str):
    """Download generated audio file."""
    output_dir = Path("outputs")
    audio_file = output_dir / f"{audio_file_id}.wav"
    
    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(audio_file),
        media_type="audio/wav",
        filename=f"{audio_file_id}.wav"
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8011,
        reload=True,
        log_level="info"
    )