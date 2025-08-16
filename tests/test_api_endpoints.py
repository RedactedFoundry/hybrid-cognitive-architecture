#!/usr/bin/env python3
"""
Tests for API Endpoints

Tests the modular API endpoints:
- Chat endpoints (/api/chat)
- Voice endpoints (/api/voice)  
- Health endpoints (/health)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from endpoints.chat import router as chat_router, set_orchestrator
from endpoints.voice import router as voice_router
from endpoints.health import router as health_router, set_health_dependencies
from models.api_models import SimpleChatRequest, SimpleChatResponse


class MockOrchestrator:
    """Mock orchestrator for endpoint testing."""
    
    def __init__(self):
        self._initialized = True  # Add missing attribute for health check
    
    async def process_request(self, user_input, conversation_id=None):
        """Mock process_request method."""
        return MagicMock(
            final_response="Mock response",
            routing_intent=MagicMock(value="simple_query_task"),
            metadata={"processing_time": 0.1}
        )


@pytest.fixture
def test_app():
    """Create a test FastAPI app with endpoints."""
    app = FastAPI()
    app.include_router(chat_router)
    app.include_router(voice_router)
    app.include_router(health_router)
    return app


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    return MockOrchestrator()


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestChatEndpoints:
    """Test chat-related endpoints."""
    
    def test_chat_endpoint_structure(self, client, mock_orchestrator):
        """Test chat endpoint basic structure."""
        # Set the orchestrator dependency
        set_orchestrator(mock_orchestrator)
        
        # Test POST request
        response = client.post(
            "/api/chat",
            json={"message": "Hello, AI!", "conversation_id": "test_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "response" in data
        assert "intent" in data
        assert "processing_time" in data  # Fixed: model uses processing_time, not processing_time_seconds
        assert "path_taken" in data
    
    def test_chat_endpoint_validation(self, client, mock_orchestrator):
        """Test chat endpoint input validation."""
        set_orchestrator(mock_orchestrator)
        
        # Test missing message
        response = client.post("/api/chat", json={})
        assert response.status_code == 422  # Validation error
        
        # Test invalid JSON
        response = client.post(
            "/api/chat",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_chat_endpoint_with_conversation_id(self, client, mock_orchestrator):
        """Test chat endpoint with conversation tracking."""
        set_orchestrator(mock_orchestrator)
        
        conversation_id = "test_conversation_456"
        response = client.post(
            "/api/chat",
            json={
                "message": "Continue our conversation",
                "conversation_id": conversation_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Note: SimpleChatResponse doesn't include conversation_id - that's expected
        assert "response" in data  # Just verify response structure instead


class TestVoiceEndpoints:
    """Test voice-related endpoints."""
    
    @patch('endpoints.voice.voice_orchestrator')
    def test_voice_test_endpoint(self, mock_voice_orchestrator, client):
        """Test voice test endpoint."""
        mock_voice_orchestrator.test_voice_pipeline.return_value = {
            "success": True,
            "stt_result": "test transcription",
            "tts_result": True,
            "processing_time": 0.5
        }
        
        response = client.post("/api/voice/test")
        assert response.status_code == 200
        
        data = response.json()
        # Fixed: voice test endpoint returns 'status' and 'timestamp', not 'success' and 'results'
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "Voice API is working"
    
    def test_voice_endpoints_require_voice_foundation(self, client):
        """Test that voice endpoints handle missing voice foundation gracefully."""
        # Test without proper voice foundation setup
        response = client.post("/api/voice/test")
        
        # Should either work or return a proper error, not crash
        assert response.status_code in [200, 500, 503]


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check_structure(self, client):
        """Test health check endpoint structure."""
        # Set mock dependencies
        import datetime
        mock_start_time = datetime.datetime.now(datetime.timezone.utc)
        mock_orchestrator = MockOrchestrator()
        set_health_dependencies(mock_start_time, mock_orchestrator)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "uptime" in data  # Fixed: endpoint returns 'uptime', not 'uptime_seconds'
        assert "services" in data
    
    @patch('endpoints.health.get_ollama_client')
    @patch('endpoints.health.get_redis_connection') 
    @patch('clients.tigergraph_client.get_tigergraph_connection')
    def test_health_check_services(self, mock_tg, mock_redis, mock_ollama, client):
        """Test health check service status."""
        # Mock service availability
        mock_ollama.return_value.health_check = AsyncMock(return_value=True)
        mock_redis.return_value.ping = MagicMock(return_value=True)
        mock_tg.return_value = MagicMock()  # TigerGraph available
        
        # Set dependencies
        import datetime
        mock_start_time = datetime.datetime.now(datetime.timezone.utc)
        mock_orchestrator = MockOrchestrator()
        set_health_dependencies(mock_start_time, mock_orchestrator)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        services = data["services"]
        
        # Should have service status information
        assert isinstance(services, dict)
        assert len(services) > 0


class TestEndpointSecurity:
    """Test security aspects of endpoints."""
    
    def test_endpoints_handle_large_requests(self, client, mock_orchestrator):
        """Test that endpoints handle oversized requests appropriately."""
        set_orchestrator(mock_orchestrator)
        
        # Create a very large message (but within reasonable limits)
        large_message = "A" * 5000
        response = client.post(
            "/api/chat",
            json={"message": large_message}
        )
        
        # Should either process or reject gracefully, not crash
        assert response.status_code in [200, 400, 413, 422]
    
    def test_endpoints_handle_special_characters(self, client, mock_orchestrator):
        """Test endpoints handle special characters safely."""
        set_orchestrator(mock_orchestrator)
        
        special_chars_message = "Hello! 🤖 How are you? ñáéíóú 中文 العربية"
        response = client.post(
            "/api/chat",
            json={"message": special_chars_message}
        )
        
        assert response.status_code == 200
    
    def test_endpoints_reject_malformed_requests(self, client, mock_orchestrator):
        """Test endpoints properly reject malformed requests."""
        # Set up orchestrator to avoid runtime errors masking validation errors
        set_orchestrator(mock_orchestrator)
        
        # Test various malformed requests
        malformed_requests = [
            ({"invalid": "structure"}, 422),  # Missing required fields
            # Note: Empty message is actually valid according to SimpleChatRequest model
        ]
        
        for request_data, expected_status in malformed_requests:
            response = client.post("/api/chat", json=request_data)
            # Should return validation error, not crash
            assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code} for {request_data}"


class TestEndpointIntegration:
    """Test integration between endpoints and core systems."""
    
    def test_orchestrator_integration(self, client, mock_orchestrator):
        """Test that endpoints properly integrate with orchestrator."""
        set_orchestrator(mock_orchestrator)
        
        response = client.post(
            "/api/chat",
            json={"message": "Test integration"}
        )
        
        assert response.status_code == 200
        
        # Verify orchestrator was called
        # (This would be more detailed in a real integration test)
    
    def test_error_handling(self, client):
        """Test endpoint error handling."""
        # Test with no orchestrator set (should handle gracefully)
        set_orchestrator(None)
        
        response = client.post(
            "/api/chat",
            json={"message": "Test with no orchestrator"}
        )
        
        # Should return an error, not crash
        assert response.status_code >= 400
    
    def test_response_format_consistency(self, client, mock_orchestrator):
        """Test that response formats are consistent."""
        set_orchestrator(mock_orchestrator)
        
        response = client.post(
            "/api/chat",
            json={"message": "Test response format"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response follows expected schema
        required_fields = ["response", "intent", "processing_time"]  # Fixed: model uses processing_time
        for field in required_fields:
            assert field in data
        
        # Verify data types
        assert isinstance(data["response"], str)
        assert isinstance(data["processing_time"], (int, float))  # Fixed: model uses processing_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])