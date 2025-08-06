"""
Production Voice Engines - Microservice Architecture (August 2025)
Uses Python 3.11 Voice Service for NeMo Parakeet STT + Coqui XTTS v2

Migration from local engines to microservice architecture for Python version compatibility.
"""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

from .voice_client import VoiceServiceClient

# Set up structured logging
logger = structlog.get_logger("voice_engines")

class ProductionSTTEngine:
    """
    NVIDIA Parakeet-TDT-0.6B-v2 STT Engine via Microservice
    Performance: 6.05% WER, RTF 3380 (60 min in 1 sec)
    """
    
    def __init__(self, service_url: str = "http://localhost:8011"):
        self.name = "NVIDIA Parakeet-TDT-0.6B-v2 (Microservice)"
        self.service_url = service_url
        self.client = VoiceServiceClient(service_url)
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize STT engine by checking service health"""
        if self.is_initialized:
            return
            
        try:
            logger.info("Initializing STT via voice service", service_url=self.service_url)
            
            # Check if service is healthy
            health_status = await self.client.health_check()
            
            if health_status.get("status") == "healthy":
                stt_info = health_status.get("services", {}).get("stt", {})
                logger.info("STT engine initialized successfully",
                           engine=stt_info.get("engine", "Unknown"),
                           service_status="healthy")
                self.is_initialized = True
            else:
                raise Exception(f"Voice service unhealthy: {health_status}")
                
        except Exception as e:
            logger.error("STT initialization failed", error=str(e))
            raise
    
    async def transcribe(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file to text"""
        if not self.is_initialized:
            await self.initialize()
            
        try:
            start_time = time.time()
            result = await self.client.speech_to_text(audio_path)
            processing_time = time.time() - start_time
            
            text = result.get("text", "")
            confidence = result.get("confidence", 0.0)
            
            logger.info("STT transcription completed",
                       text_length=len(text),
                       confidence=confidence,
                       processing_time_seconds=processing_time)
            
            return text
            
        except Exception as e:
            logger.error("STT transcription failed", error=str(e), audio_path=audio_path)
            return None


class ProductionTTSEngine:
    """
    Coqui XTTS v2 TTS Engine via Microservice
    Multi-voice synthesis with voice cloning support
    """
    
    def __init__(self, service_url: str = "http://localhost:8011"):
        self.name = "Coqui XTTS v2 (Microservice)"
        self.service_url = service_url
        self.client = VoiceServiceClient(service_url)
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize TTS engine by checking service health"""
        if self.is_initialized:
            return
            
        try:
            logger.info("Initializing TTS via voice service", service_url=self.service_url)
            
            # Check if service is healthy
            health_status = await self.client.health_check()
            
            if health_status.get("status") == "healthy":
                tts_info = health_status.get("services", {}).get("tts", {})
                logger.info("TTS engine initialized successfully",
                           engine=tts_info.get("engine", "Unknown"),
                           service_status="healthy")
                self.is_initialized = True
            else:
                raise Exception(f"Voice service unhealthy: {health_status}")
                
        except Exception as e:
            logger.error("TTS initialization failed", error=str(e))
            raise
    
    async def synthesize(self, text: str, output_path: str, voice_id: str = "default") -> bool:
        """Synthesize speech from text"""
        if not self.is_initialized:
            await self.initialize()
            
        try:
            start_time = time.time()
            
            # Get the output directory from the provided path
            output_dir = Path(output_path).parent
            
            result = await self.client.text_to_speech(
                text=text,
                voice_id=voice_id,
                output_dir=output_dir
            )
            
            processing_time = time.time() - start_time
            
            # Move the generated file to the exact requested path
            generated_path = Path(result.get("local_audio_path", ""))
            if generated_path.exists() and str(generated_path) != output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                generated_path.rename(output_path)
            
            logger.info("TTS synthesis completed",
                       text_length=len(text),
                       voice_id=voice_id,
                       output_path=output_path,
                       processing_time_seconds=processing_time)
            
            return True
            
        except Exception as e:
            logger.error("TTS synthesis failed", error=str(e), text_preview=text[:30])
            return False
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available voices"""
        if not self.is_initialized:
            await self.initialize()
            
        try:
            return await self.client.list_voices()
        except Exception as e:
            logger.error("Failed to get available voices", error=str(e))
            return {"available_voices": {}, "error": str(e)}


class ProductionVoiceFoundation:
    """
    Complete voice processing foundation using microservice architecture
    Integrates STT and TTS via Python 3.11 voice service
    """
    
    def __init__(self, service_url: str = "http://localhost:8011", force_parakeet: bool = True):
        self.name = "Production Voice Foundation (Microservice)"
        self.service_url = service_url
        self.stt = ProductionSTTEngine(service_url)
        self.tts = ProductionTTSEngine(service_url)
        self.is_initialized = False
        
        # Create output directory
        self.output_dir = Path("voice_foundation/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def initialize(self):
        """Initialize both STT and TTS engines"""
        if self.is_initialized:
            return
            
        try:
            logger.info("Initializing Production Voice Foundation", service_url=self.service_url)
            
            # Initialize STT engine
            await self.stt.initialize()
            
            # Initialize TTS engine
            await self.tts.initialize()
            
            self.is_initialized = True
            
            logger.info("Production Voice Foundation initialized successfully",
                       stt_engine=self.stt.name,
                       tts_engine=self.tts.name,
                       service_url=self.service_url)
                       
        except Exception as e:
            logger.error("Voice foundation initialization failed", error=str(e))
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of voice processing services"""
        try:
            client = VoiceServiceClient(self.service_url)
            health_status = await client.health_check()
            
            return {
                "status": "healthy" if health_status.get("status") == "healthy" else "unhealthy",
                "foundation": self.name,
                "service_url": self.service_url,
                "details": health_status
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "foundation": self.name,
                "service_url": self.service_url,
                "error": str(e)
            }
    
    async def process_audio_to_text(self, audio_path: str) -> Optional[str]:
        """Convert audio file to text using STT"""
        if not self.is_initialized:
            await self.initialize()
            
        logger.info("Processing audio with STT", audio_path=audio_path)
        return await self.stt.transcribe(audio_path)
    
    async def process_text_to_audio(self, text: str, output_path: Optional[str] = None, voice_id: str = "default") -> Optional[str]:
        """Convert text to audio using TTS"""
        if not self.is_initialized:
            await self.initialize()
            
        if not output_path:
            output_path = str(self.output_dir / f"tts_{uuid.uuid4()}.wav")
        
        logger.info("Synthesizing with TTS", text_preview=text[:30], voice_id=voice_id)
        
        success = await self.tts.synthesize(text, output_path, voice_id)
        return output_path if success else None
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """Get available voice configurations"""
        if not self.is_initialized:
            await self.initialize()
            
        return await self.tts.get_available_voices()


# Compatibility function for existing code
async def create_voice_foundation(use_production=True, force_parakeet=True, service_url="http://localhost:8011"):
    """Create production voice foundation using microservice architecture"""
    if use_production:
        foundation = ProductionVoiceFoundation(service_url=service_url, force_parakeet=force_parakeet)
    else:
        # Fall back to mock for testing
        from .simple_voice_pipeline import VoiceFoundation
        foundation = VoiceFoundation()
    
    await foundation.initialize()
    return foundation


# Legacy compatibility for any old imports
ProductionVADEngine = None  # VAD now handled by the voice service