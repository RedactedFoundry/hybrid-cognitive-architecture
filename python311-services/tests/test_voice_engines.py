#!/usr/bin/env python3
"""
Test Voice Engines for Python 3.11 Service
Tests the actual NeMo Parakeet STT and Coqui XTTS v2 engines
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add voice package to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from voice.engines.voice_engines import VoiceProcessor, STTEngine, TTSEngine

class TestVoiceEngines:
    """Test the actual voice engines with real models"""
    
    @pytest.mark.asyncio
    async def test_voice_processor_initialization(self):
        """Test voice processor can initialize both engines"""
        processor = VoiceProcessor()
        
        # This will download models if not cached - takes time on first run
        await processor.initialize()
        
        assert processor.is_initialized
        assert processor.stt_engine.is_initialized
        assert processor.tts_engine.is_initialized
        assert "Parakeet" in processor.stt_engine.name
        assert "XTTS" in processor.tts_engine.name
    
    @pytest.mark.asyncio
    async def test_stt_engine_initialization(self):
        """Test STT engine initializes correctly"""
        stt = STTEngine(force_parakeet=True)
        await stt.initialize()
        
        assert stt.is_initialized
        assert stt.use_nemo  # Should use NeMo Parakeet
        assert "Parakeet" in stt.name
    
    @pytest.mark.asyncio 
    async def test_tts_engine_initialization(self):
        """Test TTS engine initializes correctly"""
        tts = TTSEngine()
        await tts.initialize()
        
        assert tts.is_initialized
        assert tts.model is not None
        assert "XTTS" in tts.name
    
    @pytest.mark.asyncio
    async def test_tts_synthesis_basic(self):
        """Test basic TTS synthesis"""
        tts = TTSEngine()
        await tts.initialize()
        
        test_text = "Hello, this is a test of Coqui XTTS version 2."
        
        result = await tts.synthesize(
            text=test_text,
            voice_id="default",
            language="en"
        )
        
        assert "audio_file_path" in result
        assert "duration_seconds" in result
        assert "synthesis_time_seconds" in result
        
        # Check file was created
        audio_file = Path(result["audio_file_path"])
        assert audio_file.exists()
        assert audio_file.suffix == ".wav"
        
        # Clean up
        audio_file.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_complete_voice_pipeline_with_mock_audio(self):
        """Test complete pipeline with mock audio file"""
        processor = VoiceProcessor()
        await processor.initialize()
        
        # Create a simple test audio file (mock WAV)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            # Write a simple WAV header + silence
            sample_rate = 16000
            duration = 1.0  # 1 second
            samples = int(sample_rate * duration)
            
            # Simple WAV header (44 bytes)
            wav_header = bytearray(44)
            wav_header[0:4] = b'RIFF'
            wav_header[8:12] = b'WAVE'
            wav_header[12:16] = b'fmt '
            wav_header[16:20] = (16).to_bytes(4, 'little')  # PCM format size
            wav_header[20:22] = (1).to_bytes(2, 'little')   # PCM format
            wav_header[22:24] = (1).to_bytes(2, 'little')   # Mono
            wav_header[24:28] = sample_rate.to_bytes(4, 'little')
            wav_header[28:32] = (sample_rate * 2).to_bytes(4, 'little')  # Byte rate
            wav_header[32:34] = (2).to_bytes(2, 'little')   # Block align
            wav_header[34:36] = (16).to_bytes(2, 'little')  # Bits per sample
            wav_header[36:40] = b'data'
            wav_header[40:44] = (samples * 2).to_bytes(4, 'little')  # Data size
            
            temp_audio.write(wav_header)
            # Write silence (zeros)
            temp_audio.write(b'\x00' * (samples * 2))
            temp_audio_path = temp_audio.name
        
        try:
            # Test TTS synthesis
            print("Testing TTS synthesis...")
            tts_result = await processor.synthesize_speech(
                text="This is a test of the voice pipeline.",
                voice_id="default"
            )
            
            assert "audio_file_path" in tts_result
            assert Path(tts_result["audio_file_path"]).exists()
            
            print(f"✅ TTS synthesis successful: {tts_result['audio_file_path']}")
            
            # Note: STT test with real audio would require actual speech audio
            # For now, we can test that the STT engine is ready
            print("Testing STT readiness...")
            assert processor.stt_engine.is_initialized
            print("✅ STT engine ready")
            
        finally:
            # Clean up
            os.unlink(temp_audio_path)
            if 'tts_result' in locals():
                Path(tts_result["audio_file_path"]).unlink(missing_ok=True)


class TestVoiceEnginePerformance:
    """Performance tests for voice engines"""
    
    @pytest.mark.asyncio
    async def test_tts_latency(self):
        """Test TTS synthesis latency meets requirements"""
        tts = TTSEngine()
        await tts.initialize()
        
        test_text = "Quick test for latency measurement."
        
        result = await tts.synthesize(text=test_text)
        
        synthesis_time = result["synthesis_time_seconds"]
        
        # XTTS v2 should synthesize short text quickly
        # For this short text, should be well under 5 seconds
        assert synthesis_time < 5.0, f"TTS took {synthesis_time}s - too slow"
        
        print(f"✅ TTS synthesis completed in {synthesis_time:.2f}s")
        
        # Clean up
        Path(result["audio_file_path"]).unlink(missing_ok=True)


if __name__ == "__main__":
    # Run basic smoke test
    async def smoke_test():
        print("🧪 Running Voice Engines Smoke Test...")
        
        try:
            processor = VoiceProcessor()
            print("1. Initializing voice processor...")
            await processor.initialize()
            print("✅ Voice processor initialized")
            
            print("2. Testing TTS synthesis...")
            result = await processor.synthesize_speech("Hello from Python 3.11 voice service!")
            print(f"✅ TTS synthesis successful: {result['audio_file_path']}")
            
            # Clean up
            Path(result["audio_file_path"]).unlink(missing_ok=True)
            
            print("🎯 Voice engines smoke test passed!")
            
        except Exception as e:
            print(f"❌ Smoke test failed: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(smoke_test())