"""
Voice Service Client for Main Project
Communicates with Python 3.11 voice microservice via HTTP API
"""

import asyncio
import aiohttp
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Union
import structlog

logger = structlog.get_logger("VoiceClient")

class VoiceServiceClient:
    """Client for communicating with the Python 3.11 voice processing service"""
    
    def __init__(self, base_url: str = "http://localhost:8011"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure we have an active session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the voice service is healthy"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Voice service health check successful", status=data.get("status"))
                    return data
                else:
                    error_text = await response.text()
                    logger.error("Voice service health check failed", status=response.status, error=error_text)
                    raise Exception(f"Health check failed: {response.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error("Failed to connect to voice service", error=str(e))
            raise Exception(f"Cannot connect to voice service at {self.base_url}: {str(e)}")
    
    async def speech_to_text(self, audio_file_path: Union[str, Path]) -> Dict[str, Any]:
        """Convert audio file to text using NeMo Parakeet STT"""
        await self._ensure_session()
        
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            logger.info("Sending STT request", audio_file=str(audio_path))
            
            with open(audio_path, 'rb') as audio_file:
                data = aiohttp.FormData()
                data.add_field('audio_file', audio_file, filename=audio_path.name, content_type='audio/wav')
                
                async with self.session.post(f"{self.base_url}/voice/stt", data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("STT request successful", text_length=len(result.get("text", "")))
                        return result
                    else:
                        error_text = await response.text()
                        logger.error("STT request failed", status=response.status, error=error_text)
                        raise Exception(f"STT failed: {response.status} - {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error("STT request failed", error=str(e))
            raise Exception(f"STT request failed: {str(e)}")
    
    async def text_to_speech(
        self, 
        text: str, 
        voice_id: str = "default",
        language: str = "en",
        output_dir: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Convert text to speech using Coqui XTTS v2"""
        await self._ensure_session()
        
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            logger.info("Sending TTS request", text_length=len(text), voice_id=voice_id)
            
            # Send TTS request
            request_data = {
                "text": text,
                "voice_id": voice_id,
                "language": language
            }
            
            async with self.session.post(f"{self.base_url}/voice/tts", json=request_data) as response:
                if response.status == 200:
                    tts_result = await response.json()
                    audio_file_id = tts_result["audio_file_id"]
                    
                    # Download the generated audio file
                    audio_data = await self._download_audio_file(audio_file_id)
                    
                    # Save to local file
                    if output_dir:
                        output_path = Path(output_dir) / f"{audio_file_id}.wav"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        output_path = Path(f"voice_foundation/outputs/{audio_file_id}.wav")
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        f.write(audio_data)
                    
                    result = {
                        **tts_result,
                        "local_audio_path": str(output_path)
                    }
                    
                    logger.info("TTS request successful", output_file=str(output_path))
                    return result
                    
                else:
                    error_text = await response.text()
                    logger.error("TTS request failed", status=response.status, error=error_text)
                    raise Exception(f"TTS failed: {response.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error("TTS request failed", error=str(e))
            raise Exception(f"TTS request failed: {str(e)}")
    
    async def _download_audio_file(self, audio_file_id: str) -> bytes:
        """Download audio file from voice service"""
        async with self.session.get(f"{self.base_url}/voice/audio/{audio_file_id}") as response:
            if response.status == 200:
                return await response.read()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to download audio: {response.status} - {error_text}")
    
    async def list_voices(self) -> Dict[str, Any]:
        """Get available voice configurations"""
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/voices") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get voices: {response.status} - {error_text}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to get voices: {str(e)}")


# Convenience functions for direct usage
async def transcribe_audio(audio_file_path: Union[str, Path], service_url: str = "http://localhost:8011") -> str:
    """Convenience function to transcribe audio to text"""
    async with VoiceServiceClient(service_url) as client:
        result = await client.speech_to_text(audio_file_path)
        return result.get("text", "")

async def synthesize_speech(
    text: str, 
    voice_id: str = "default",
    language: str = "en",
    output_dir: Optional[Union[str, Path]] = None,
    service_url: str = "http://localhost:8011"
) -> str:
    """Convenience function to synthesize text to speech"""
    async with VoiceServiceClient(service_url) as client:
        result = await client.text_to_speech(text, voice_id, language, output_dir)
        return result.get("local_audio_path", "")