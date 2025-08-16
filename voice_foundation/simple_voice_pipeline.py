#!/usr/bin/env python3
"""
Deprecated simple voice pipeline kept for backward compatibility.
Production voice runs under python311-services/voice with Coqui XTTS + NeMo Parakeet.
"""

import asyncio
import time
import math
from pathlib import Path
from typing import Optional, AsyncGenerator
# import soundfile as sf  # Removed for mock implementation
import numpy as np
import structlog

# Set up structured logging
logger = structlog.get_logger("voice_pipeline")

class MockSTTEngine:
    """Mock Speech-to-Text engine for testing integration"""
    
    def __init__(self):
        self.name = "MockSTT"
        
    async def transcribe(self, audio_path: str) -> Optional[str]:
        """Mock transcription - returns a simulated result"""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Simulate transcription based on audio file size (mock)
        try:
            file_size = Path(audio_path).stat().st_size if Path(audio_path).exists() else 1024
            duration = file_size / 16000  # Mock duration calculation
            
            # Mock responses based on mock duration
            if duration < 1.0:
                return "Hello"
            elif duration < 3.0:
                return "Hello, how can I help you today?"
            else:
                return "Hello, this is a test of the voice foundation system."
                
        except (FileNotFoundError, OSError, ValueError, AttributeError):
            return "Could not process audio"

class MockTTSEngine:
    """Mock Text-to-Speech engine for testing integration"""
    
    def __init__(self):
        self.name = "MockTTS"
        
    async def synthesize(self, text: str, output_path: str) -> bool:
        """Mock synthesis - creates a simple audio file"""
        try:
            await asyncio.sleep(0.2)  # Simulate processing time
            
            # Create simple audio based on text length
            duration = min(len(text) * 0.05, 10.0)  # 50ms per character, max 10s
            sample_rate = 22050
            
            # Generate a simple sine wave tone
            t = np.linspace(0, duration, int(sample_rate * duration))
            frequency = 440.0  # A note
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Add some variation for different text
            if "error" in text.lower():
                frequency = 220.0  # Lower pitch for errors
            elif "success" in text.lower():
                frequency = 880.0  # Higher pitch for success
                
            audio = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Generate audible test tone based on text content
            duration = min(max(len(text) / 20, 1.0), 5.0)  # 1-5 seconds based on text length
            sample_rate = 16000
            num_samples = int(sample_rate * duration)
            
            # Choose frequency based on text content for variety
            if "hello" in text.lower():
                frequency = 440.0  # A note
            elif "error" in text.lower() or "failed" in text.lower():
                frequency = 220.0  # Lower pitch for errors
            elif "success" in text.lower() or "complete" in text.lower():
                frequency = 880.0  # Higher pitch for success
            else:
                frequency = 523.25  # C note for general responses
            
            # Generate simple sine wave
            audio_data = []
            for i in range(num_samples):
                t = i / sample_rate
                # Fade in/out to avoid clicks
                fade = min(t * 10, (duration - t) * 10, 1.0)
                sample = int(fade * 0.3 * 32767 * math.sin(2 * math.pi * frequency * t))
                # Convert to 16-bit signed integer bytes (little endian)
                audio_data.extend([sample & 0xFF, (sample >> 8) & 0xFF])
            
            # Create WAV file with proper header
            data_size = len(audio_data)
            file_size = 36 + data_size
            
            with open(output_path, 'wb') as f:
                # WAV header
                f.write(b'RIFF')
                f.write(file_size.to_bytes(4, 'little'))
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write((16).to_bytes(4, 'little'))  # Chunk size
                f.write((1).to_bytes(2, 'little'))   # Audio format (PCM)
                f.write((1).to_bytes(2, 'little'))   # Number of channels (mono)
                f.write(sample_rate.to_bytes(4, 'little'))  # Sample rate
                f.write((sample_rate * 2).to_bytes(4, 'little'))  # Byte rate
                f.write((2).to_bytes(2, 'little'))   # Block align
                f.write((16).to_bytes(2, 'little'))  # Bits per sample
                f.write(b'data')
                f.write(data_size.to_bytes(4, 'little'))
                f.write(bytes(audio_data))
            return True
            
        except (OSError, IOError, ValueError, TypeError) as e:
            logger.error("TTS synthesis failed", error=str(e))
            return False

class VoiceFoundation:
    """
    Main voice foundation class that integrates STT and TTS
    """
    
    def __init__(self):
        self.stt = MockSTTEngine()
        self.tts = MockTTSEngine()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the voice foundation"""
        logger.info("Initializing Voice Foundation Mock Pipeline")
        await asyncio.sleep(0.1)  # Simulate initialization
        self.is_initialized = True
        logger.info("Voice Foundation ready", stt_engine=self.stt.name, tts_engine=self.tts.name)
        
    async def process_audio_to_text(self, audio_path: str) -> Optional[str]:
        """Convert audio file to text"""
        if not self.is_initialized:
            await self.initialize()
            
        logger.info("Processing audio", audio_path=audio_path)
        start_time = time.time()
        
        result = await self.stt.transcribe(audio_path)
        
        latency = time.time() - start_time
        logger.info("Transcription completed", 
                   result=result, 
                   latency_seconds=latency)
        return result
        
    async def process_text_to_audio(self, text: str, output_path: str) -> bool:
        """Convert text to audio file"""
        if not self.is_initialized:
            await self.initialize()
            
        logger.info("Starting TTS synthesis", text_preview=text[:50])
        start_time = time.time()
        
        success = await self.tts.synthesize(text, output_path)
        
        latency = time.time() - start_time
        if success:
            logger.info("TTS synthesis successful", 
                       output_path=output_path,
                       latency_seconds=latency)
        else:
            logger.error("TTS synthesis failed")
            
        return success
        
    async def process_voice_request(self, audio_input: str, audio_output: str, text_processor=None) -> Optional[str]:
        """
        Complete voice pipeline: audio -> text -> processing -> text -> audio
        
        Args:
            audio_input: Path to input audio file
            audio_output: Path to output audio file  
            text_processor: Optional function to process the transcribed text
            
        Returns:
            The processed text response
        """
        # Step 1: Speech to Text
        transcription = await self.process_audio_to_text(audio_input)
        if not transcription:
            return None
            
        # Step 2: Process text (this is where orchestrator integration happens)
        if text_processor:
            response_text = await text_processor(transcription)
        else:
            response_text = f"I heard you say: {transcription}"
            
        # Step 3: Text to Speech
        success = await self.process_text_to_audio(response_text, audio_output)
        
        if success:
            return response_text
        else:
            return None

# Convenience functions for integration
voice_foundation = VoiceFoundation()

async def transcribe_audio(audio_path: str) -> Optional[str]:
    """Convenience function for STT"""
    return await voice_foundation.process_audio_to_text(audio_path)

async def synthesize_speech(text: str, output_path: str) -> bool:
    """Convenience function for TTS"""
    return await voice_foundation.process_text_to_audio(text, output_path)

async def process_voice_pipeline(input_audio: str, output_audio: str, text_processor=None) -> Optional[str]:
    """Convenience function for full pipeline"""
    return await voice_foundation.process_voice_request(input_audio, output_audio, text_processor)

if __name__ == "__main__":
    # Simple test
    async def test():
        # Create test audio if needed
        if not Path("voice_foundation/test_audio.wav").exists():
            from voice_foundation.create_test_audio import create_test_audio
            create_test_audio("voice_foundation/test_audio.wav")
            
        # Test the pipeline
        result = await process_voice_pipeline(
            "voice_foundation/test_audio.wav",
            "voice_foundation/test_output.wav"
        )
        
        if result:
            logger.info("Voice pipeline test successful", response=result)
        else:
            logger.error("Voice pipeline test failed")
    
    asyncio.run(test())