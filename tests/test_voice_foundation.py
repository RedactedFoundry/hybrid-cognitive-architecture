# tests/test_voice_foundation.py
"""
Comprehensive tests for Voice Foundation Integration.

This test suite covers:
- Voice orchestrator integration with cognitive architecture
- STT/TTS engine testing (both production and mock)
- Voice pipeline end-to-end workflows
- Voice WebSocket endpoint integration
- Error handling and graceful degradation
- Audio processing and file handling
- Performance and latency validation
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import pytest
from datetime import datetime, timezone

# Import voice foundation components
from voice_foundation.orchestrator_integration import VoiceOrchestrator
from voice_foundation.simple_voice_pipeline import VoiceFoundation, MockSTTEngine, MockTTSEngine
from voice_foundation.production_voice_engines import create_voice_foundation

# Import related models for integration testing
from models.api_models import VoiceChatResponse
from core.orchestrator.models import OrchestratorState
from endpoints.voice import voice_chat


class TestMockVoiceEngines:
    """Test the mock STT/TTS engines used for integration testing."""
    
    @pytest.mark.asyncio
    async def test_mock_stt_engine_basic_transcription(self):
        """Test basic mock STT engine functionality."""
        engine = MockSTTEngine()
        
        assert engine.name == "MockSTT"
        
        # Test with mock file (doesn't need to exist for mock)
        with patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True):
            
            # Mock small file
            mock_stat.return_value.st_size = 8000  # Small file
            result = await engine.transcribe("small_audio.wav")
            assert result == "Hello"
            
            # Mock medium file
            mock_stat.return_value.st_size = 32000  # Medium file
            result = await engine.transcribe("medium_audio.wav")
            assert result == "Hello, how can I help you today?"
            
            # Mock large file
            mock_stat.return_value.st_size = 80000  # Large file
            result = await engine.transcribe("large_audio.wav")
            assert result == "Hello, this is a test of the voice foundation system."
    
    @pytest.mark.asyncio
    async def test_mock_stt_engine_error_handling(self):
        """Test mock STT engine error handling."""
        engine = MockSTTEngine()
        
        # Test with file stat error (which should trigger exception handling)
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat', side_effect=OSError("File access error")):
            result = await engine.transcribe("error_file.wav")
            assert result == "Could not process audio"
        
        # Test with non-existent file (note: mock engine provides fallback, so test actual behavior)
        with patch('pathlib.Path.exists', return_value=False):
            result = await engine.transcribe("nonexistent.wav")
            # Mock engine uses fallback size of 1024, so it returns "Hello" 
            assert result == "Hello"
    
    @pytest.mark.asyncio
    async def test_mock_tts_engine_basic_synthesis(self):
        """Test basic mock TTS engine functionality."""
        engine = MockTTSEngine()
        
        assert engine.name == "MockTTS"
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Test basic synthesis
            success = await engine.synthesize("Hello world", temp_path)
            assert success is True
            assert Path(temp_path).exists()
            
            # Test empty text (mock engine handles empty text by generating minimum duration audio)
            success = await engine.synthesize("", temp_path)
            assert success is True  # Mock engine still creates audio file
            
        finally:
            # Cleanup
            if Path(temp_path).exists():
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_mock_tts_engine_error_handling(self):
        """Test mock TTS engine error handling."""
        engine = MockTTSEngine()
        
        # Test with invalid output path that should cause an error
        with patch('builtins.open', side_effect=OSError("Permission denied")):
            success = await engine.synthesize("Hello world", "/invalid/path/output.wav")
            assert success is False


class TestVoiceFoundation:
    """Test the VoiceFoundation class that coordinates STT/TTS engines."""
    
    @pytest.fixture
    def voice_foundation(self):
        """Create VoiceFoundation instance for testing."""
        return VoiceFoundation()  # Always uses mock engines
    
    @pytest.mark.asyncio
    async def test_voice_foundation_initialization(self, voice_foundation):
        """Test voice foundation initialization."""
        await voice_foundation.initialize()
        
        assert voice_foundation.is_initialized is True
        assert voice_foundation.stt is not None
        assert voice_foundation.tts is not None
        assert voice_foundation.stt.name == "MockSTT"
        assert voice_foundation.tts.name == "MockTTS"
    
    @pytest.mark.asyncio
    async def test_process_audio_to_text(self, voice_foundation):
        """Test audio to text processing."""
        await voice_foundation.initialize()
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 16000  # Medium file
            result = await voice_foundation.process_audio_to_text("test_audio.wav")
            
            assert result == "Hello, how can I help you today?"
    
    @pytest.mark.asyncio
    async def test_process_text_to_audio(self, voice_foundation):
        """Test text to audio processing."""
        await voice_foundation.initialize()
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            success = await voice_foundation.process_text_to_audio("Hello world", temp_path)
            assert success is True
            assert Path(temp_path).exists()
            
        finally:
            if Path(temp_path).exists():
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_voice_foundation_auto_initialization(self):
        """Test that voice foundation auto-initializes when used."""
        foundation = VoiceFoundation()
        
        # Should not be initialized initially
        assert foundation.is_initialized is False
        
        # Using it should auto-initialize and return result
        result = await foundation.process_audio_to_text("test.wav")
        assert result is not None  # Should auto-initialize and work
        assert foundation.is_initialized is True
        
        # Test TTS auto-initialization
        foundation2 = VoiceFoundation()
        assert foundation2.is_initialized is False
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            success = await foundation2.process_text_to_audio("test", temp_path)
            assert success is True  # Should auto-initialize and work
            assert foundation2.is_initialized is True
        finally:
            if Path(temp_path).exists():
                os.unlink(temp_path)


class TestVoiceOrchestrator:
    """Test the VoiceOrchestrator that integrates voice with cognitive architecture."""
    
    @pytest.fixture
    def mock_orchestrator_response(self):
        """Create mock orchestrator response."""
        response = MagicMock()
        response.final_response = "Thank you for your question. I understand you're asking about AI capabilities."
        return response
    
    @pytest.mark.asyncio
    async def test_voice_orchestrator_initialization(self):
        """Test voice orchestrator initialization."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            mock_foundation = MagicMock()
            mock_create.return_value = mock_foundation
            mock_orchestrator = MagicMock()
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            await voice_orch.initialize()
            
            assert voice_orch.is_initialized is True
            assert voice_orch.voice_foundation == mock_foundation
            mock_create.assert_called_once_with(use_production=False, force_parakeet=True)
    
    @pytest.mark.asyncio
    async def test_process_voice_request_success(self, mock_orchestrator_response):
        """Test successful voice request processing."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            # Mock voice foundation
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value="Hello, what can you tell me about AI?")
            mock_foundation.process_text_to_audio = AsyncMock(return_value=True)
            mock_create.return_value = mock_foundation
            
            # Mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.process_request = AsyncMock(return_value=mock_orchestrator_response)
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_file, \
                 tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
                
                input_path = input_file.name
                output_path = output_file.name
                
                try:
                    result = await voice_orch.process_voice_request(
                        audio_input_path=input_path,
                        audio_output_path=output_path,
                        user_id="test_user",
                        conversation_id="test_conv_123"
                    )
                    
                    # Verify successful processing
                    assert result["success"] is True
                    assert result["transcription"] == "Hello, what can you tell me about AI?"
                    assert result["response_text"] == "Thank you for your question. I understand you're asking about AI capabilities."
                    assert result["audio_output_path"] == output_path
                    assert "request_id" in result
                    assert "processing_time" in result
                    
                    # Verify all components were called
                    mock_foundation.process_audio_to_text.assert_called_once_with(input_path)
                    mock_orchestrator.process_request.assert_called_once()
                    mock_foundation.process_text_to_audio.assert_called_once_with(
                        "Thank you for your question. I understand you're asking about AI capabilities.", 
                        output_path
                    )
                    
                finally:
                    # Cleanup with retry for Windows file locking
                    import time
                    for path in [input_path, output_path]:
                        if Path(path).exists():
                            try:
                                os.unlink(path)
                            except PermissionError:
                                # Windows file locking - wait and retry
                                time.sleep(0.1)
                                try:
                                    os.unlink(path)
                                except PermissionError:
                                    pass  # Skip cleanup if still locked
    
    @pytest.mark.asyncio
    async def test_process_voice_request_stt_failure(self):
        """Test voice request with STT failure."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create:
            
            # Mock voice foundation with STT failure
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value=None)  # STT failure
            mock_create.return_value = mock_foundation
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                result = await voice_orch.process_voice_request(
                    audio_input_path=temp_file.name,
                    audio_output_path="output.wav"
                )
                
                assert result["success"] is False
                assert result["error"] == "Speech transcription failed"
                assert "processing_time" in result
    
    @pytest.mark.asyncio
    async def test_process_voice_request_orchestrator_failure(self, mock_orchestrator_response):
        """Test voice request with orchestrator failure."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            # Mock voice foundation
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value="Test question")
            mock_create.return_value = mock_foundation
            
            # Mock orchestrator failure
            mock_orchestrator = MagicMock()
            mock_orchestrator.process_request = AsyncMock(return_value=None)  # Orchestrator failure
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                result = await voice_orch.process_voice_request(
                    audio_input_path=temp_file.name,
                    audio_output_path="output.wav"
                )
                
                assert result["success"] is False
                assert result["error"] == "Orchestrator processing failed"
                assert result["transcription"] == "Test question"
    
    @pytest.mark.asyncio
    async def test_process_voice_request_tts_failure(self, mock_orchestrator_response):
        """Test voice request with TTS failure."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            # Mock voice foundation with TTS failure
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value="Test question")
            mock_foundation.process_text_to_audio = AsyncMock(return_value=False)  # TTS failure
            mock_create.return_value = mock_foundation
            
            # Mock orchestrator
            mock_orchestrator = MagicMock()
            mock_orchestrator.process_request = AsyncMock(return_value=mock_orchestrator_response)
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                result = await voice_orch.process_voice_request(
                    audio_input_path=temp_file.name,
                    audio_output_path="output.wav"
                )
                
                assert result["success"] is False
                assert result["error"] == "Speech synthesis failed"
                assert result["transcription"] == "Test question"
                assert result["response_text"] == "Thank you for your question. I understand you're asking about AI capabilities."


# NOTE: Production voice engine tests moved to python311-services/tests/
# The production engines now use microservice architecture and are tested
# in the Python 3.11 service where the actual models run.
# See:
# - python311-services/tests/test_voice_engines.py (engine tests)  
# - python311-services/tests/test_voice_service.py (API tests)
# - tests/test_voice_microservice_integration.py (integration tests)

class TestVoiceFoundationMicroserviceIntegration:
    """Test voice foundation integration with microservice architecture."""
    
    @pytest.mark.asyncio
    async def test_create_voice_foundation_production_mocked(self):
        """Test creating voice foundation with production engines (mocked microservice)."""
        # Mock the health check to simulate a running voice service
        mock_health_data = {
            "status": "healthy",
            "services": {
                "stt": {"engine": "NVIDIA Parakeet-TDT-0.6B-v2", "initialized": True},
                "tts": {"engine": "Coqui XTTS v2", "initialized": True}
            }
        }
        
        with patch('voice_foundation.voice_client.VoiceServiceClient.health_check') as mock_health:
            mock_health.return_value = mock_health_data
            
            foundation = await create_voice_foundation(use_production=True, force_parakeet=True)
            
            assert foundation is not None
            assert foundation.is_initialized
            assert "Microservice" in foundation.name
    
    @pytest.mark.asyncio
    async def test_create_voice_foundation_mock(self):
        """Test creating voice foundation with mock engines."""
        foundation = await create_voice_foundation(use_production=False, force_parakeet=False)
        
        assert foundation is not None
        assert hasattr(foundation, 'process_audio_to_text')
        assert hasattr(foundation, 'process_text_to_audio')


class TestVoiceEndpointIntegration:
    """Test integration with voice REST endpoints."""
    
    @pytest.mark.asyncio
    async def test_voice_chat_endpoint_success(self):
        """Test successful voice chat endpoint processing."""
        from fastapi import UploadFile
        from io import BytesIO
        
        # Mock successful voice processing
        with patch('endpoints.voice.voice_orchestrator') as mock_voice_orch:
            mock_voice_orch.process_voice_request = AsyncMock(return_value={
                "request_id": "test_123",
                "success": True,
                "transcription": "Hello AI",
                "response_text": "Hello! How can I help you?",
                "audio_output_path": "/tmp/response.wav",
                "processing_time": 2.5
            })
            
            # Create mock audio file
            audio_content = b"fake_audio_data"
            audio_file = UploadFile(
                filename="test_audio.wav",
                file=BytesIO(audio_content)
            )
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp, \
                 patch('os.makedirs'), \
                 patch('os.unlink'):
                
                mock_temp.return_value.__enter__.return_value.name = "/tmp/temp_audio.wav"
                
                response = await voice_chat(
                    audio=audio_file,
                    conversation_id="test_conv",
                    user_id="test_user"
                )
                
                assert isinstance(response, VoiceChatResponse)
                assert response.success is True
                assert response.transcription == "Hello AI"
                assert response.response_text == "Hello! How can I help you?"
                # Audio URL should contain the actual request ID, not our mock ID
                assert response.audio_url is not None
                assert "response.wav" in response.audio_url
    
    @pytest.mark.asyncio
    async def test_voice_chat_endpoint_invalid_format(self):
        """Test voice chat endpoint with invalid file format."""
        from fastapi import UploadFile, HTTPException
        from io import BytesIO
        
        # Create mock file with invalid format
        audio_file = UploadFile(
            filename="test_audio.txt",  # Invalid format
            file=BytesIO(b"not_audio_data")
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await voice_chat(audio=audio_file)
        
        assert exc_info.value.status_code == 400
        assert "Audio file must be" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_voice_chat_endpoint_processing_failure(self):
        """Test voice chat endpoint with processing failure."""
        from fastapi import UploadFile, HTTPException
        from io import BytesIO
        
        # Mock voice processing failure
        with patch('endpoints.voice.voice_orchestrator') as mock_voice_orch:
            mock_voice_orch.process_voice_request = AsyncMock(return_value={
                "request_id": "test_123",
                "success": False,
                "error": "Speech transcription failed",
                "processing_time": 1.0
            })
            
            audio_file = UploadFile(
                filename="test_audio.wav",
                file=BytesIO(b"fake_audio_data")
            )
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp, \
                 patch('os.makedirs'), \
                 patch('os.unlink'):
                
                mock_temp.return_value.__enter__.return_value.name = "/tmp/temp_audio.wav"
                
                response = await voice_chat(audio=audio_file)
                
                assert isinstance(response, VoiceChatResponse)
                assert response.success is False
                assert response.error == "Speech transcription failed"


class TestVoiceErrorHandling:
    """Test error handling and edge cases in voice processing."""
    
    @pytest.mark.asyncio
    async def test_voice_foundation_audio_file_not_found(self):
        """Test handling of non-existent audio files."""
        foundation = VoiceFoundation()
        await foundation.initialize()
        
        result = await foundation.process_audio_to_text("/nonexistent/audio.wav")
        # Mock engine provides fallback response for non-existent files
        assert result == "Hello"  # Default mock response for 1024 byte fallback
    
    @pytest.mark.asyncio
    async def test_voice_foundation_invalid_output_path(self):
        """Test handling of invalid output paths."""
        foundation = VoiceFoundation()
        await foundation.initialize()
        
        # Mock TTS engine creates directories as needed and succeeds
        success = await foundation.process_text_to_audio("Hello", "/invalid/path/output.wav")
        assert success is True  # Mock engine creates directories and succeeds
        
        # Cleanup the created directory
        import shutil
        try:
            shutil.rmtree("/invalid")
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors
    
    @pytest.mark.asyncio
    async def test_voice_orchestrator_auto_initialization(self):
        """Test voice orchestrator auto-initialization on first request."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator'):
            
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value=None)  # Force early return
            mock_create.return_value = mock_foundation
            
            voice_orch = VoiceOrchestrator(use_production=False)
            assert voice_orch.is_initialized is False
            
            with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                await voice_orch.process_voice_request(temp_file.name, "output.wav")
            
            assert voice_orch.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_concurrent_voice_requests(self):
        """Test handling of concurrent voice requests."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            # Mock components
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value="Concurrent request")
            mock_foundation.process_text_to_audio = AsyncMock(return_value=True)
            mock_create.return_value = mock_foundation
            
            mock_response = MagicMock()
            mock_response.final_response = "Processed"
            mock_orchestrator = MagicMock()
            mock_orchestrator.process_request = AsyncMock(return_value=mock_response)
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            # Submit multiple concurrent requests
            tasks = []
            for i in range(3):
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as input_file, \
                     tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as output_file:
                    
                    task = asyncio.create_task(voice_orch.process_voice_request(
                        input_file.name, output_file.name, conversation_id=f"conv_{i}"
                    ))
                    tasks.append((task, input_file.name, output_file.name))
            
            try:
                # Wait for all requests to complete
                results = []
                for task, input_path, output_path in tasks:
                    result = await task
                    results.append(result)
                    
                    # Cleanup with Windows file locking protection
                    for path in [input_path, output_path]:
                        if Path(path).exists():
                            try:
                                os.unlink(path)
                            except PermissionError:
                                time.sleep(0.1)
                                try:
                                    os.unlink(path)
                                except PermissionError:
                                    pass  # Skip cleanup if still locked
                
                # Verify all requests succeeded
                assert len(results) == 3
                for result in results:
                    assert result["success"] is True
                    assert result["transcription"] == "Concurrent request"
                    assert result["response_text"] == "Processed"
                    
            except Exception as e:
                # Cleanup on error with Windows file locking protection
                import time
                for task, input_path, output_path in tasks:
                    if not task.done():
                        task.cancel()
                    for path in [input_path, output_path]:
                        if Path(path).exists():
                            try:
                                os.unlink(path)
                            except PermissionError:
                                time.sleep(0.1)
                                try:
                                    os.unlink(path)
                                except PermissionError:
                                    pass  # Skip cleanup if still locked
                raise


class TestVoicePerformanceMetrics:
    """Test voice processing performance and metrics."""
    
    @pytest.mark.asyncio
    async def test_voice_processing_timing(self):
        """Test that voice processing includes timing metrics."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            # Mock components with delays to test timing
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value="Test input")
            mock_foundation.process_text_to_audio = AsyncMock(return_value=True)
            mock_create.return_value = mock_foundation
            
            # Add delay to simulate processing time
            async def delayed_processing(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                mock_response = MagicMock()
                mock_response.final_response = "Test response"
                return mock_response
            
            mock_orchestrator = MagicMock()
            mock_orchestrator.process_request = delayed_processing
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            with tempfile.NamedTemporaryFile(suffix='.wav') as input_file, \
                 tempfile.NamedTemporaryFile(suffix='.wav') as output_file:
                
                start_time = datetime.now(timezone.utc)
                result = await voice_orch.process_voice_request(input_file.name, output_file.name)
                end_time = datetime.now(timezone.utc)
                
                # Verify timing information
                assert result["success"] is True
                assert "processing_time" in result
                
                # Should have taken at least 100ms due to our mock delay
                total_time = (end_time - start_time).total_seconds()
                assert result["processing_time"] >= 0.1
                assert result["processing_time"] <= total_time + 0.1  # Allow for overhead
    
    @pytest.mark.asyncio
    async def test_voice_request_id_generation(self):
        """Test that each voice request gets a unique ID."""
        with patch('voice_foundation.orchestrator_integration.create_voice_foundation') as mock_create, \
             patch('voice_foundation.orchestrator_integration.UserFacingOrchestrator') as mock_orch_class:
            
            mock_foundation = MagicMock()
            mock_foundation.process_audio_to_text = AsyncMock(return_value="Test")
            mock_foundation.process_text_to_audio = AsyncMock(return_value=True)
            mock_create.return_value = mock_foundation
            
            mock_response = MagicMock()
            mock_response.final_response = "Response"
            mock_orchestrator = MagicMock()
            mock_orchestrator.process_request = AsyncMock(return_value=mock_response)
            mock_orch_class.return_value = mock_orchestrator
            
            voice_orch = VoiceOrchestrator(use_production=False)
            
            # Process multiple requests and collect IDs
            request_ids = []
            for _ in range(3):
                with tempfile.NamedTemporaryFile(suffix='.wav') as input_file, \
                     tempfile.NamedTemporaryFile(suffix='.wav') as output_file:
                    
                    result = await voice_orch.process_voice_request(input_file.name, output_file.name)
                    request_ids.append(result["request_id"])
            
            # Verify all IDs are unique and valid UUIDs
            assert len(set(request_ids)) == 3  # All unique
            for req_id in request_ids:
                # Should be valid UUID format
                uuid.UUID(req_id)  # Will raise ValueError if invalid


# Integration with existing test infrastructure
if __name__ == "__main__":
    pytest.main([__file__, "-v"])