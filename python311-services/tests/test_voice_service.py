#!/usr/bin/env python3
"""
Test Voice Service FastAPI Application
Tests the HTTP API endpoints for the Python 3.11 voice service
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
import sys
from httpx import AsyncClient

# Add voice package to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from voice.main import app

class TestVoiceServiceAPI:
    """Test the FastAPI voice service endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test the health check endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert "services" in data
            assert "stt" in data["services"]
            assert "tts" in data["services"]
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test the root information endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["service"] == "Hybrid AI Council - Voice Processing Service"
            assert data["python_version"] == "3.11"
            assert "engines" in data
            assert "endpoints" in data
    
    @pytest.mark.asyncio 
    async def test_tts_endpoint(self):
        """Test the text-to-speech endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            tts_request = {
                "text": "Hello, this is a test of the TTS API endpoint.",
                "voice_id": "default",
                "language": "en"
            }
            
            response = await client.post("/voice/tts", json=tts_request)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "audio_file_id" in data
            assert "duration_seconds" in data
            assert "voice_used" in data
            
            # Test downloading the generated audio
            audio_id = data["audio_file_id"]
            audio_response = await client.get(f"/voice/audio/{audio_id}")
            
            assert audio_response.status_code == 200
            assert audio_response.headers["content-type"] == "audio/wav"
            
            # Clean up - the actual file cleanup is handled by the service
            print(f"✅ TTS API test successful, audio ID: {audio_id}")
    
    @pytest.mark.asyncio
    async def test_tts_with_invalid_text(self):
        """Test TTS endpoint with invalid input"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test empty text
            response = await client.post("/voice/tts", json={"text": ""})
            assert response.status_code == 400
            
            # Test very long text
            long_text = "A" * 6000  # Over 5000 character limit
            response = await client.post("/voice/tts", json={"text": long_text})
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_stt_endpoint_with_mock_audio(self):
        """Test the speech-to-text endpoint with mock audio"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create a simple mock WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                # Write a minimal WAV header + silence
                sample_rate = 16000
                duration = 1.0
                samples = int(sample_rate * duration)
                
                # WAV header
                wav_header = bytearray(44)
                wav_header[0:4] = b'RIFF'
                wav_header[8:12] = b'WAVE'
                wav_header[12:16] = b'fmt '
                wav_header[16:20] = (16).to_bytes(4, 'little')
                wav_header[20:22] = (1).to_bytes(2, 'little')
                wav_header[22:24] = (1).to_bytes(2, 'little')
                wav_header[24:28] = sample_rate.to_bytes(4, 'little')
                wav_header[28:32] = (sample_rate * 2).to_bytes(4, 'little')
                wav_header[32:34] = (2).to_bytes(2, 'little')
                wav_header[34:36] = (16).to_bytes(2, 'little')
                wav_header[36:40] = b'data'
                wav_header[40:44] = (samples * 2).to_bytes(4, 'little')
                
                temp_audio.write(wav_header)
                temp_audio.write(b'\x00' * (samples * 2))  # Silence
                temp_audio_path = temp_audio.name
            
            try:
                # Test STT endpoint
                with open(temp_audio_path, 'rb') as audio_file:
                    files = {"audio_file": ("test.wav", audio_file, "audio/wav")}
                    response = await client.post("/voice/stt", files=files)
                
                # STT might return empty text for silence, but should not error
                assert response.status_code == 200
                data = response.json()
                
                assert "text" in data
                assert "confidence" in data
                assert "processing_time_seconds" in data
                
                print(f"✅ STT API test successful, transcription: '{data['text']}'")
                
            finally:
                os.unlink(temp_audio_path)
    
    @pytest.mark.asyncio
    async def test_stt_with_invalid_file(self):
        """Test STT endpoint with invalid file format"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test with non-audio file
            files = {"audio_file": ("test.txt", b"not audio data", "text/plain")}
            response = await client.post("/voice/stt", files=files)
            
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_audio_file_not_found(self):
        """Test downloading non-existent audio file"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/voice/audio/nonexistent-id")
            assert response.status_code == 404


if __name__ == "__main__":
    # Run basic API test
    async def api_smoke_test():
        print("🧪 Running Voice Service API Smoke Test...")
        
        try:
            async with AsyncClient(app=app, base_url="http://test") as client:
                print("1. Testing health endpoint...")
                response = await client.get("/health")
                assert response.status_code == 200
                print("✅ Health endpoint working")
                
                print("2. Testing TTS endpoint...")
                tts_request = {"text": "API smoke test", "voice_id": "default"}
                response = await client.post("/voice/tts", json=tts_request)
                assert response.status_code == 200
                print("✅ TTS API working")
                
                print("🎯 Voice service API smoke test passed!")
                
        except Exception as e:
            print(f"❌ API smoke test failed: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(api_smoke_test())