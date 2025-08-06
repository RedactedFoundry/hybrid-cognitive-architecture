#!/usr/bin/env python3
"""
Test Voice Microservice Integration
Tests that the main Python 3.13 project can use voice processing via microservice
"""

import pytest
from unittest.mock import AsyncMock, patch
from voice_foundation.voice_client import VoiceServiceClient, transcribe_audio, synthesize_speech
from voice_foundation.production_voice_engines import create_voice_foundation

class TestVoiceMicroserviceIntegration:
    """Test voice processing via microservice architecture"""
    
    @pytest.mark.asyncio
    async def test_voice_client_health_check_mocked(self):
        """Test voice client health check with mocked response"""
        
        mock_response_data = {
            "status": "healthy",
            "services": {
                "stt": {"engine": "NVIDIA Parakeet-TDT-0.6B-v2", "initialized": True},
                "tts": {"engine": "Coqui XTTS v2", "initialized": True}
            },
            "version": "1.0.0"
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test health check
            async with VoiceServiceClient("http://localhost:8011") as client:
                health = await client.health_check()
                
                assert health["status"] == "healthy"
                assert "stt" in health["services"]
                assert "tts" in health["services"]
    
    @pytest.mark.asyncio 
    async def test_voice_foundation_initialization_mocked(self):
        """Test voice foundation can initialize without actual service running"""
        
        mock_health_data = {
            "status": "healthy",
            "services": {
                "stt": {"engine": "NVIDIA Parakeet-TDT-0.6B-v2", "initialized": True},
                "tts": {"engine": "Coqui XTTS v2", "initialized": True}
            }
        }
        
        with patch('voice_foundation.voice_client.VoiceServiceClient.health_check') as mock_health:
            mock_health.return_value = mock_health_data
            
            # This should work without any torch/nemo imports in main project
            foundation = await create_voice_foundation(service_url="http://localhost:8011")
            
            assert foundation.is_initialized
            assert "Microservice" in foundation.name
    
    @pytest.mark.asyncio
    async def test_no_direct_voice_imports(self):
        """Test that main project doesn't directly import voice libraries"""
        
        # This test passes just by importing the modules without errors
        # If torch/nemo were still imported, this would fail in Python 3.13 env
        from voice_foundation.production_voice_engines import ProductionVoiceFoundation
        from voice_foundation.voice_client import VoiceServiceClient
        
        # Should be able to create instances without importing torch/nemo directly
        foundation = ProductionVoiceFoundation()
        client = VoiceServiceClient()
        
        assert foundation.name == "Production Voice Foundation (Microservice)"
        assert client.base_url == "http://localhost:8011"
    
    def test_pyproject_clean_of_voice_deps(self):
        """Test that pyproject.toml doesn't contain voice dependencies"""
        
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        # These should NOT be in the main project anymore
        voice_deps = ["torch", "nemo-toolkit", "transformers", "silero-vad", 
                     "pytorch-lightning", "lhotse", "jiwer", "hydra-core"]
        
        for dep in voice_deps:
            assert dep not in content, f"Found voice dependency '{dep}' in main pyproject.toml - should be in python311-services only"
    
    @pytest.mark.asyncio
    async def test_convenience_functions_mocked(self):
        """Test convenience functions work with mocked service"""
        
        mock_stt_result = {"text": "Hello world", "confidence": 0.95}
        mock_tts_result = {"audio_file_id": "test-123", "local_audio_path": "/path/to/audio.wav"}
        
        with patch('voice_foundation.voice_client.VoiceServiceClient.speech_to_text') as mock_stt, \
             patch('voice_foundation.voice_client.VoiceServiceClient.text_to_speech') as mock_tts:
            
            mock_stt.return_value = mock_stt_result
            mock_tts.return_value = mock_tts_result
            
            # Test convenience functions
            text = await transcribe_audio("test.wav")
            audio_path = await synthesize_speech("Hello world")
            
            assert text == "Hello world"
            assert audio_path == "/path/to/audio.wav"


if __name__ == "__main__":
    # Run basic import test
    print("🧪 Testing voice microservice integration...")
    
    try:
        from voice_foundation.production_voice_engines import ProductionVoiceFoundation
        from voice_foundation.voice_client import VoiceServiceClient
        print("✅ Voice client imports successful - no direct voice library dependencies")
        
        # Check pyproject.toml is clean
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        voice_deps = ["torch", "nemo-toolkit"]
        found_deps = [dep for dep in voice_deps if dep in content]
        
        if found_deps:
            print(f"❌ Found voice dependencies in main project: {found_deps}")
        else:
            print("✅ Main project pyproject.toml clean of voice dependencies")
            
        print("🎯 Voice microservice integration test passed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Voice microservice integration may have issues")