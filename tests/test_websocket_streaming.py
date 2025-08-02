# tests/test_websocket_streaming.py
"""
Comprehensive tests for WebSocket Streaming and Real-Time Communication.

This test suite covers:
- WebSocket connection management
- Real-time token streaming
- Voice WebSocket integration  
- Connection error handling and recovery
- Multi-client scenarios
- Task cancellation and cleanup
- Response formatting and phase updates
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

# Import modules we're testing
from utils.websocket_utils import (
    WebSocketConnectionManager,
    WebSocketError,
    active_connections,
    active_response_tasks,
    create_error_response,
    create_status_response,
    create_data_response,
    get_active_connections,
    get_connection_count
)
from core.orchestrator.streaming import StreamingProcessor, StreamEvent, StreamEventType
from core.orchestrator.models import ProcessingPhase
from websockets.chat_handlers import websocket_chat_handler, handle_conversation_interrupt
from endpoints.voice import websocket_voice_endpoint
from endpoints.chat import websocket_chat_endpoint


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.closed = False
        self.sent_messages = []
        self.received_messages = []
        self.accept_called = False
        self.close_called = False
        self.close_code = None
        self.close_reason = None
    
    async def accept(self):
        """Mock WebSocket accept."""
        self.accept_called = True
    
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Mock WebSocket close."""
        self.close_called = True
        self.close_code = code
        self.close_reason = reason
        self.closed = True
    
    async def send_text(self, data: str):
        """Mock sending text data."""
        if self.closed:
            raise WebSocketDisconnect(code=1000, reason="Connection closed")
        self.sent_messages.append({"type": "text", "data": data})
    
    async def send_json(self, data: dict):
        """Mock sending JSON data."""
        if self.closed:
            raise WebSocketDisconnect(code=1000, reason="Connection closed")
        self.sent_messages.append({"type": "json", "data": data})
    
    async def receive_json(self):
        """Mock receiving JSON data."""
        if self.closed:
            raise WebSocketDisconnect(code=1000, reason="Connection closed")
        if self.received_messages:
            return self.received_messages.pop(0)
        # If no messages, wait indefinitely (for testing interrupts)
        await asyncio.sleep(3600)
    
    async def receive_text(self):
        """Mock receiving text data."""
        if self.closed:
            raise WebSocketDisconnect(code=1000, reason="Connection closed")
        if self.received_messages:
            import json
            msg = self.received_messages.pop(0)
            return json.dumps(msg)
        # If no messages, wait indefinitely (for testing interrupts)
        await asyncio.sleep(3600)
    
    def add_received_message(self, message: dict):
        """Add a message to be received."""
        self.received_messages.append(message)


class TestWebSocketConnectionManager:
    """Test the WebSocket connection management system."""
    
    def setup_method(self):
        """Clear active connections before each test."""
        active_connections.clear()
        active_response_tasks.clear()
    
    def test_connection_manager_initialization(self):
        """Test connection manager initialization."""
        manager = WebSocketConnectionManager("test")
        assert manager.connection_type == "test"
        assert manager.logger is not None
    
    @pytest.mark.asyncio
    async def test_establish_connection_success(self):
        """Test successful WebSocket connection establishment."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        
        connection_id = await manager.establish_connection(websocket)
        
        # Verify connection was established
        assert websocket.accept_called
        assert connection_id in active_connections
        assert active_connections[connection_id] == websocket
        assert connection_id in active_response_tasks
        assert len(active_response_tasks[connection_id]) == 0
    
    @pytest.mark.asyncio
    async def test_establish_connection_with_custom_id(self):
        """Test WebSocket connection establishment with custom ID."""
        manager = WebSocketConnectionManager("voice")
        websocket = MockWebSocket()
        custom_id = "test_voice_123"
        
        connection_id = await manager.establish_connection(websocket, custom_id)
        
        # Verify custom ID was used
        assert connection_id == custom_id
        assert connection_id in active_connections
    
    @pytest.mark.asyncio
    async def test_establish_connection_failure(self):
        """Test WebSocket connection establishment failure."""
        manager = WebSocketConnectionManager("chat")
        
        # Create mock that raises exception on accept
        websocket = MagicMock()
        websocket.accept = AsyncMock(side_effect=Exception("Connection failed"))
        
        with pytest.raises(WebSocketError) as exc_info:
            await manager.establish_connection(websocket)
        
        assert "Connection establishment failed" in str(exc_info.value)
        assert exc_info.value.error_type == "connection_error"
    
    @pytest.mark.asyncio
    async def test_send_welcome_message(self):
        """Test sending welcome message."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        await manager.send_welcome_message(websocket, connection_id, "Test welcome")
        
        # Verify welcome message was sent
        assert len(websocket.sent_messages) == 1
        message_data = json.loads(websocket.sent_messages[0]["data"])
        assert message_data["type"] == "status"
        assert "Test welcome" in message_data["content"]
        assert message_data["phase"] == "connected"
    
    @pytest.mark.asyncio
    async def test_handle_message_error_json_decode(self):
        """Test handling JSON decode errors."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        json_error = json.JSONDecodeError("Invalid JSON", "test", 0)
        result = await manager.handle_message_error(websocket, json_error, connection_id)
        
        # Verify error was handled
        assert result is True
        assert len(websocket.sent_messages) == 1
        
        error_message = json.loads(websocket.sent_messages[0]["data"])
        assert error_message["type"] == "error"
        assert error_message["error_type"] == "json_decode_error"
        assert "Invalid JSON format" in error_message["content"]
    
    @pytest.mark.asyncio
    async def test_handle_message_error_validation(self):
        """Test handling validation errors."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        validation_error = ValueError("Invalid message format")
        result = await manager.handle_message_error(websocket, validation_error, connection_id)
        
        # Verify error was handled
        assert result is True
        error_message = json.loads(websocket.sent_messages[0]["data"])
        assert error_message["error_type"] == "validation_error"
        assert "Message validation error" in error_message["content"]
    
    @pytest.mark.asyncio
    async def test_handle_message_error_websocket_closed(self):
        """Test handling errors when WebSocket is closed."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        # Close the WebSocket
        websocket.closed = True
        
        error = Exception("Processing error")
        result = await manager.handle_message_error(websocket, error, connection_id)
        
        # Verify error handling failed (connection should be closed)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_register_and_cancel_response_tasks(self):
        """Test response task registration and cancellation."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        # Create real asyncio tasks
        async def dummy_task1():
            await asyncio.sleep(10)  # Long running task
            return "task1_result"
        
        async def dummy_task2():
            return "task2_result"  # Quick task
        
        task1 = asyncio.create_task(dummy_task1())
        task2 = asyncio.create_task(dummy_task2())
        
        # Let task2 complete
        await asyncio.sleep(0.1)
        
        # Register tasks
        manager.register_response_task(connection_id, task1)
        manager.register_response_task(connection_id, task2)
        
        assert len(active_response_tasks[connection_id]) == 2
        
        # Cancel tasks
        await manager.cancel_active_response_tasks(connection_id)
        
        # Verify tasks were handled appropriately
        assert task1.cancelled() or task1.done()
        assert task2.done()  # Should have completed normally
        assert len(active_response_tasks[connection_id]) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_connection(self):
        """Test connection cleanup."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        # Add real task
        async def dummy_task():
            await asyncio.sleep(5)
            return "result"
        
        task = asyncio.create_task(dummy_task())
        manager.register_response_task(connection_id, task)
        
        # Cleanup connection
        await manager.cleanup_connection(connection_id, "error")
        
        # Verify cleanup
        assert connection_id not in active_connections
        assert connection_id not in active_response_tasks
        assert websocket.close_called
        assert websocket.close_code == 1011
        assert task.cancelled() or task.done()
    
    @pytest.mark.asyncio
    async def test_handle_disconnect(self):
        """Test WebSocket disconnect handling."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        disconnect_error = WebSocketDisconnect(code=1001, reason="Going away")
        await manager.handle_disconnect(connection_id, disconnect_error)
        
        # Verify connection was cleaned up
        assert connection_id not in active_connections
        assert connection_id not in active_response_tasks


class TestWebSocketUtilityFunctions:
    """Test WebSocket utility functions."""
    
    def test_create_error_response(self):
        """Test error response creation."""
        response = create_error_response(
            content="Test error",
            request_id="req_123",
            conversation_id="conv_456",
            error_type="test_error",
            custom_field="custom_value"
        )
        
        assert response["type"] == "error"
        assert response["content"] == "Test error"
        assert response["request_id"] == "req_123"
        assert response["conversation_id"] == "conv_456"
        assert response["error_type"] == "test_error"
        assert response["custom_field"] == "custom_value"
        assert "timestamp" in response
    
    def test_create_status_response(self):
        """Test status response creation."""
        response = create_status_response(
            content="Processing...",
            request_id="req_123",
            conversation_id="conv_456",
            phase="deliberation"
        )
        
        assert response["type"] == "status"
        assert response["content"] == "Processing..."
        assert response["phase"] == "deliberation"
    
    def test_create_data_response(self):
        """Test data response creation."""
        test_data = {"result": "success", "tokens": 150}
        response = create_data_response(
            content=test_data,
            request_id="req_123",
            conversation_id="conv_456",
            data_type="final_response"
        )
        
        assert response["type"] == "final_response"
        assert response["content"] == test_data
    
    def test_get_active_connections(self):
        """Test getting active connections."""
        # Clear first
        active_connections.clear()
        
        # Add test connections
        active_connections["conn1"] = MockWebSocket()
        active_connections["conn2"] = MockWebSocket()
        
        connections = get_active_connections()
        assert len(connections) == 2
        assert "conn1" in connections
        assert "conn2" in connections
        
        # Verify it's a copy (not the original)
        connections["conn3"] = MockWebSocket()
        assert "conn3" not in active_connections
    
    def test_get_connection_count(self):
        """Test getting connection count."""
        active_connections.clear()
        assert get_connection_count() == 0
        
        active_connections["conn1"] = MockWebSocket()
        assert get_connection_count() == 1
        
        active_connections["conn2"] = MockWebSocket()
        assert get_connection_count() == 2


class TestStreamingProcessor:
    """Test the orchestrator streaming processor."""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        orchestrator = MagicMock()
        orchestrator._initialized = True
        orchestrator.graph = MagicMock()
        return orchestrator
    
    @pytest.fixture
    def streaming_processor(self, mock_orchestrator):
        """Create streaming processor with mock orchestrator."""
        return StreamingProcessor(mock_orchestrator)
    
    @pytest.mark.asyncio
    async def test_process_request_stream_initialization_error(self):
        """Test streaming when orchestrator not initialized."""
        orchestrator = MagicMock()
        orchestrator._initialized = False
        processor = StreamingProcessor(orchestrator)
        
        with pytest.raises(RuntimeError) as exc_info:
            async for _ in processor.process_request_stream("test input"):
                pass
        
        assert "not properly initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_request_stream_success(self, streaming_processor):
        """Test successful streaming request processing."""
        # Mock the council deliberation stream
        with patch.object(streaming_processor, '_stream_council_deliberation') as mock_stream:
            # Create mock stream events
            async def mock_deliberation_stream(user_input, request_id):
                yield StreamEvent(
                    event_type=StreamEventType.AGENT_COMPLETE,
                    content="Agent response complete",
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    request_id=request_id
                )
                yield StreamEvent(
                    event_type=StreamEventType.TOKEN,
                    content="token",
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    request_id=request_id
                )
            
            mock_stream.return_value = mock_deliberation_stream("test", "req_123")
            
            # Collect stream events
            events = []
            async for event in streaming_processor.process_request_stream("test input"):
                events.append(event)
            
            # Verify event sequence
            assert len(events) >= 5  # Init, pheromind, council start, deliberation events, completion
            
            # Check initialization event
            assert events[0].event_type == StreamEventType.PHASE_UPDATE
            assert events[0].phase == ProcessingPhase.INITIALIZATION
            assert "Initializing" in events[0].content
            
            # Check pheromind event
            assert events[1].event_type == StreamEventType.PHASE_UPDATE
            assert events[1].phase == ProcessingPhase.PHEROMIND_SCAN
            assert "Pheromind" in events[1].content
            
            # Check council event
            assert events[2].event_type == StreamEventType.PHASE_UPDATE
            assert events[2].phase == ProcessingPhase.COUNCIL_DELIBERATION
            assert "Council" in events[2].content
            
            # Check completion event
            final_event = events[-1]
            assert final_event.event_type == StreamEventType.PHASE_UPDATE
            assert final_event.phase == ProcessingPhase.COMPLETED
    
    @pytest.mark.asyncio
    async def test_process_request_stream_error_handling(self, streaming_processor):
        """Test error handling in streaming."""
        # Mock the council deliberation to raise an error
        with patch.object(streaming_processor, '_stream_council_deliberation') as mock_stream:
            mock_stream.side_effect = Exception("Deliberation failed")
            
            events = []
            async for event in streaming_processor.process_request_stream("test input"):
                events.append(event)
            
            # Should have initialization events and error event
            assert len(events) >= 4
            
            # Check error event
            error_event = events[-1]
            assert error_event.event_type == StreamEventType.ERROR
            assert error_event.phase == ProcessingPhase.ERROR
            assert "Processing failed" in error_event.content


class TestChatWebSocketHandler:
    """Test the chat WebSocket handler."""
    
    def setup_method(self):
        """Clear active connections before each test."""
        active_connections.clear()
        active_response_tasks.clear()
    
    @pytest.mark.asyncio
    async def test_websocket_chat_handler_connection_setup(self):
        """Test chat WebSocket handler connection setup."""
        websocket = MockWebSocket()
        mock_orchestrator = MagicMock()
        
        # Mock the connection manager to avoid infinite loops
        with patch('websockets.chat_handlers.WebSocketConnectionManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.establish_connection = AsyncMock(return_value="test_conn_123")
            mock_manager.send_welcome_message = AsyncMock()
            mock_manager.handle_message_error = AsyncMock(return_value=False)  # Return False to break loop
            mock_manager.cleanup_connection = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            # Mock to terminate loop immediately
            with patch('websockets.chat_handlers.asyncio.sleep', side_effect=WebSocketDisconnect()):
                try:
                    await websocket_chat_handler(websocket, mock_orchestrator)
                except WebSocketDisconnect:
                    pass
            
            # Verify connection manager was used correctly
            mock_manager.establish_connection.assert_called_once_with(websocket)
            mock_manager.send_welcome_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_conversation_interrupt(self):
        """Test conversation interrupt handling."""
        websocket = MockWebSocket()
        conversation_id = "test_conv_123"
        
        await handle_conversation_interrupt(websocket, conversation_id)
        
        # Verify interrupt response was sent
        assert len(websocket.sent_messages) == 1
        response = websocket.sent_messages[0]["data"]
        assert response["type"] == "interrupt_acknowledged"
        assert response["conversation_id"] == conversation_id


class TestVoiceWebSocketIntegration:
    """Test voice WebSocket integration."""
    
    def setup_method(self):
        """Clear active connections before each test."""
        active_connections.clear()
        active_response_tasks.clear()
    
    @pytest.mark.asyncio
    async def test_websocket_voice_endpoint_connection_setup(self):
        """Test voice WebSocket endpoint connection setup."""
        websocket = MockWebSocket()
        
        # Mock the connection manager to avoid infinite loops
        with patch('endpoints.voice.WebSocketConnectionManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.establish_connection = AsyncMock(return_value="voice_conn_123")
            mock_manager.send_welcome_message = AsyncMock()
            mock_manager.handle_message_error = AsyncMock(return_value=False)  # Return False to break loop
            mock_manager.cleanup_connection = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            # Mock to terminate loop immediately
            with patch('asyncio.sleep', side_effect=WebSocketDisconnect()):
                try:
                    await websocket_voice_endpoint(websocket)
                except WebSocketDisconnect:
                    pass
            
            # Verify connection manager was used correctly
            mock_manager.establish_connection.assert_called_once_with(websocket)
            mock_manager.send_welcome_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_voice_websocket_message_handling(self):
        """Test voice WebSocket message handling structure."""
        websocket = MockWebSocket()
        
        # Mock voice handlers to avoid complex integration
        with patch('endpoints.voice.handle_voice_input') as mock_voice_handler, \
             patch('endpoints.voice.handle_conversation_interrupt') as mock_interrupt_handler, \
             patch('endpoints.voice.WebSocketConnectionManager') as mock_manager_class:
            
            mock_manager = MagicMock()
            mock_manager.establish_connection = AsyncMock(return_value="voice_conn_123")
            mock_manager.send_welcome_message = AsyncMock()
            mock_manager.handle_message_error = AsyncMock(return_value=False)
            mock_manager.cleanup_connection = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            mock_voice_handler.return_value = AsyncMock()
            mock_interrupt_handler.return_value = AsyncMock()
            
            # Add message and simulate quick disconnect
            websocket.add_received_message({
                "type": "voice_input",
                "audio_data": "test_data"
            })
            
            # Mock receive_json to return message then disconnect
            call_count = 0
            async def mock_receive():
                nonlocal call_count
                call_count += 1
                if call_count == 1 and websocket.received_messages:
                    return websocket.received_messages.pop(0)
                raise WebSocketDisconnect()
            
            websocket.receive_json = mock_receive
            
            try:
                await websocket_voice_endpoint(websocket)
            except WebSocketDisconnect:
                pass
            
            # Verify handlers would be called for voice input
            # (In a real scenario, handle_voice_input would be called)


class TestMultiClientScenarios:
    """Test scenarios with multiple concurrent WebSocket clients."""
    
    def setup_method(self):
        """Clear active connections before each test."""
        active_connections.clear()
        active_response_tasks.clear()
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self):
        """Test handling multiple concurrent WebSocket connections."""
        manager = WebSocketConnectionManager("chat")
        
        # Create multiple WebSocket connections
        websockets = [MockWebSocket() for _ in range(3)]
        connection_ids = []
        
        # Establish all connections
        for websocket in websockets:
            connection_id = await manager.establish_connection(websocket)
            connection_ids.append(connection_id)
        
        # Verify all connections are tracked
        assert len(active_connections) == 3
        assert len(active_response_tasks) == 3
        
        for conn_id in connection_ids:
            assert conn_id in active_connections
            assert conn_id in active_response_tasks
        
        # Cleanup one connection
        await manager.cleanup_connection(connection_ids[0])
        
        # Verify partial cleanup
        assert len(active_connections) == 2
        assert connection_ids[0] not in active_connections
        assert connection_ids[1] in active_connections
        assert connection_ids[2] in active_connections
    
    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """Test handling messages from multiple clients concurrently."""
        manager = WebSocketConnectionManager("chat")
        
        # Establish multiple connections
        websockets = []
        connection_ids = []
        
        for i in range(3):
            websocket = MockWebSocket()
            connection_id = await manager.establish_connection(websocket)
            websockets.append(websocket)
            connection_ids.append(connection_id)
        
        # Send welcome messages to all
        tasks = []
        for i, (websocket, conn_id) in enumerate(zip(websockets, connection_ids)):
            task = asyncio.create_task(
                manager.send_welcome_message(websocket, conn_id, f"Welcome client {i}")
            )
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        
        # Verify all received welcome messages
        for i, websocket in enumerate(websockets):
            assert len(websocket.sent_messages) == 1
            message = json.loads(websocket.sent_messages[0]["data"])
            assert f"Welcome client {i}" in message["content"]
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_errors(self):
        """Test that connections are properly cleaned up on errors."""
        manager = WebSocketConnectionManager("chat")
        
        # Establish connections
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        conn_id1 = await manager.establish_connection(websocket1)
        conn_id2 = await manager.establish_connection(websocket2)
        
        # Simulate error on first connection
        await manager.cleanup_connection(conn_id1, "error")
        
        # Verify first connection cleaned up, second remains
        assert conn_id1 not in active_connections
        assert conn_id2 in active_connections
        assert websocket1.close_called
        assert not websocket2.close_called


class TestWebSocketErrorScenarios:
    """Test various error scenarios in WebSocket operations."""
    
    def setup_method(self):
        """Clear active connections before each test."""
        active_connections.clear()
        active_response_tasks.clear()
    
    @pytest.mark.asyncio
    async def test_connection_establishment_timeout(self):
        """Test connection establishment timeout handling."""
        manager = WebSocketConnectionManager("chat")
        
        # Mock WebSocket that times out on accept
        websocket = MagicMock()
        websocket.accept = AsyncMock(side_effect=asyncio.TimeoutError("Connection timeout"))
        
        with pytest.raises(WebSocketError) as exc_info:
            await manager.establish_connection(websocket)
        
        assert "Connection establishment failed" in str(exc_info.value)
        assert "Connection timeout" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_message_sending_failure(self):
        """Test handling of message sending failures."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        # Close WebSocket to simulate sending failure
        websocket.closed = True
        
        # Attempt to send welcome message (should handle gracefully)
        await manager.send_welcome_message(websocket, connection_id, "Test")
        
        # Should handle gracefully without raising exception
        # (logged as warning internally)
    
    @pytest.mark.asyncio
    async def test_task_cancellation_exception_handling(self):
        """Test handling of task cancellation exceptions."""
        manager = WebSocketConnectionManager("chat")
        websocket = MockWebSocket()
        connection_id = await manager.establish_connection(websocket)
        
        # Create task that can be cancelled
        async def cancellable_task():
            try:
                await asyncio.sleep(10)  # Long sleep to ensure it gets cancelled
                return "completed"
            except asyncio.CancelledError:
                raise  # Re-raise to test cancellation handling
        
        task = asyncio.create_task(cancellable_task())
        manager.register_response_task(connection_id, task)
        
        # Cancel tasks
        await manager.cancel_active_response_tasks(connection_id)
        
        # Should handle CancelledError gracefully
        assert len(active_response_tasks[connection_id]) == 0
        assert task.cancelled()


# Integration with existing test infrastructure
if __name__ == "__main__":
    pytest.main([__file__, "-v"])