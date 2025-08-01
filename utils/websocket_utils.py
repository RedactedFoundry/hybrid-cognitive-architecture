#!/usr/bin/env python3
"""
WebSocket Utilities - Eliminate Connection Management Duplication
=================================================================

This module provides common utilities for WebSocket connection management,
eliminating duplication across chat and voice endpoints.

Features:
- Standardized connection establishment
- Consistent error handling and response formatting
- Automatic connection tracking and cleanup
- Graceful disconnection handling
"""

import asyncio
import json
import uuid
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
import structlog

# Set up logger
logger = structlog.get_logger(__name__)

# Global connection tracking (shared with handlers)
active_connections: Dict[str, WebSocket] = {}

# Track active response tasks for cancellation support
active_response_tasks: Dict[str, set] = {}


class WebSocketError(Exception):
    """Custom exception for WebSocket-related errors."""
    
    def __init__(self, message: str, error_type: str = "error", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)


class WebSocketConnectionManager:
    """
    Manages WebSocket connections with standardized patterns.
    
    Eliminates duplication of connection setup, error handling, and cleanup
    across different WebSocket endpoints.
    """
    
    def __init__(self, connection_type: str = "chat"):
        """
        Initialize connection manager.
        
        Args:
            connection_type: Type of connection (chat, voice, etc.) for logging
        """
        self.connection_type = connection_type
        self.logger = logger.bind(connection_type=connection_type)
    
    async def establish_connection(self, websocket: WebSocket, custom_id: Optional[str] = None) -> str:
        """
        Establish WebSocket connection with standardized setup.
        
        Args:
            websocket: The WebSocket connection to establish
            custom_id: Optional custom connection ID (generates UUID if not provided)
            
        Returns:
            Connection ID for tracking
            
        Raises:
            WebSocketError: If connection establishment fails
        """
        try:
            # Generate or use provided connection ID
            connection_id = custom_id or str(uuid.uuid4())
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Track active connection
            active_connections[connection_id] = websocket
            
            # Initialize task tracking for this connection
            active_response_tasks[connection_id] = set()
            
            self.logger.info("WebSocket connection established", 
                           connection_id=connection_id,
                           total_connections=len(active_connections))
            
            return connection_id
            
        except Exception as e:
            self.logger.error("Failed to establish WebSocket connection", error=str(e))
            raise WebSocketError(f"Connection establishment failed: {str(e)}", "connection_error")
    
    async def send_welcome_message(self, websocket: WebSocket, connection_id: str, 
                                 custom_message: Optional[str] = None) -> None:
        """
        Send standardized welcome message.
        
        Args:
            websocket: The WebSocket connection
            connection_id: Connection ID for tracking
            custom_message: Optional custom welcome message
        """
        try:
            welcome_data = create_status_response(
                content=custom_message or f"{self.connection_type.title()} connection established. Ready for interaction.",
                request_id=f"connection_{connection_id}",
                conversation_id="welcome",
                phase="connected"
            )
            
            await websocket.send_text(json.dumps(welcome_data))
            self.logger.debug("Welcome message sent", connection_id=connection_id)
            
        except Exception as e:
            self.logger.warning("Failed to send welcome message", 
                              connection_id=connection_id, 
                              error=str(e))
    
    async def handle_message_error(self, websocket: WebSocket, error: Exception, 
                                 connection_id: str) -> bool:
        """
        Handle message processing errors with standardized responses.
        
        Args:
            websocket: The WebSocket connection
            error: The error that occurred
            connection_id: Connection ID for tracking
            
        Returns:
            True if error was handled successfully, False if connection should be closed
        """
        try:
            if isinstance(error, json.JSONDecodeError):
                error_type = "json_decode_error"
                error_message = f"Invalid JSON format: {str(error)}"
            elif isinstance(error, ValueError):
                error_type = "validation_error"  
                error_message = f"Message validation error: {str(error)}"
            else:
                error_type = "processing_error"
                error_message = f"Message processing error: {str(error)}"
            
            # Send error response
            error_response = create_error_response(
                content=error_message,
                request_id=f"error_{str(uuid.uuid4())}",
                conversation_id="error",
                error_type=error_type
            )
            
            await websocket.send_text(json.dumps(error_response))
            
            self.logger.warning("Handled message error", 
                              connection_id=connection_id,
                              error_type=error_type,
                              error=str(error))
            
            return True
            
        except Exception as send_error:
            # WebSocket likely closed, connection should be terminated
            self.logger.debug("Could not send error response, WebSocket likely closed",
                            connection_id=connection_id,
                            original_error=str(error),
                            send_error=str(send_error))
            return False
    
    async def cleanup_connection(self, connection_id: str, reason: str = "normal") -> None:
        """
        Clean up WebSocket connection with proper logging.
        
        Args:
            connection_id: Connection ID to clean up
            reason: Reason for cleanup (normal, error, disconnect)
        """
        # Cancel any active response tasks for this connection
        await self.cancel_active_response_tasks(connection_id)
        
        if connection_id in active_connections:
            websocket = active_connections.pop(connection_id)
            
            # Attempt to close gracefully if not already closed
            if reason == "error":
                try:
                    await websocket.close(code=1011, reason="Server error")
                except (WebSocketDisconnect, ConnectionError, RuntimeError):
                    pass  # Already closed or closing
            
        # Clean up task tracking for this connection
        if connection_id in active_response_tasks:
            active_response_tasks.pop(connection_id)
            
        self.logger.info("WebSocket connection cleaned up", 
                        connection_id=connection_id,
                        reason=reason,
                        remaining_connections=len(active_connections))
    
    async def handle_disconnect(self, connection_id: str, disconnect_exception: WebSocketDisconnect) -> None:
        """
        Handle WebSocket disconnection with proper cleanup.
        
        Args:
            connection_id: Connection ID that disconnected
            disconnect_exception: The WebSocketDisconnect exception
        """
        await self.cleanup_connection(connection_id, "disconnect")
        
        self.logger.info("WebSocket connection closed by client", 
                        connection_id=connection_id,
                        disconnect_code=getattr(disconnect_exception, 'code', 'unknown'))
    
    def register_response_task(self, connection_id: str, task: asyncio.Task) -> None:
        """
        Register an active response task for cancellation support.
        
        Args:
            connection_id: Connection ID associated with the task
            task: The asyncio Task to track
        """
        if connection_id not in active_response_tasks:
            active_response_tasks[connection_id] = set()
        
        active_response_tasks[connection_id].add(task)
        self.logger.debug("Response task registered", 
                         connection_id=connection_id,
                         task_count=len(active_response_tasks[connection_id]))
    
    async def cancel_active_response_tasks(self, connection_id: str) -> None:
        """
        Cancel all active response tasks for a connection.
        
        Args:
            connection_id: Connection ID to cancel tasks for
        """
        if connection_id not in active_response_tasks:
            return
        
        tasks = active_response_tasks[connection_id].copy()
        if not tasks:
            return
        
        self.logger.info("Cancelling active response tasks", 
                        connection_id=connection_id,
                        task_count=len(tasks))
        
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete cancellation
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except (asyncio.CancelledError, RuntimeError):
                # Ignore cancellation exceptions
                pass
        
        # Clear the task set
        active_response_tasks[connection_id].clear()
        
        self.logger.debug("All response tasks cancelled", connection_id=connection_id)


# Utility functions for response creation

def create_error_response(content: str, request_id: str, conversation_id: str, 
                         error_type: str = "error", **kwargs) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        content: Error message
        request_id: Request ID for tracking
        conversation_id: Conversation ID
        error_type: Type of error for categorization
        **kwargs: Additional fields to include
        
    Returns:
        Dictionary containing error response
    """
    response = {
        "type": "error",
        "content": content,
        "request_id": request_id,
        "conversation_id": conversation_id,
        "error_type": error_type,
        "timestamp": str(uuid.uuid4())  # Simple timestamp placeholder
    }
    response.update(kwargs)
    return response


def create_status_response(content: str, request_id: str, conversation_id: str,
                          phase: str = "status", **kwargs) -> Dict[str, Any]:
    """
    Create standardized status response.
    
    Args:
        content: Status message
        request_id: Request ID for tracking  
        conversation_id: Conversation ID
        phase: Processing phase for context
        **kwargs: Additional fields to include
        
    Returns:
        Dictionary containing status response
    """
    response = {
        "type": "status",
        "content": content,
        "request_id": request_id,
        "conversation_id": conversation_id,
        "phase": phase,
        "timestamp": str(uuid.uuid4())  # Simple timestamp placeholder
    }
    response.update(kwargs)
    return response


def create_data_response(content: Any, request_id: str, conversation_id: str,
                        data_type: str = "data", **kwargs) -> Dict[str, Any]:
    """
    Create standardized data response.
    
    Args:
        content: Response data/content
        request_id: Request ID for tracking
        conversation_id: Conversation ID  
        data_type: Type of data being sent
        **kwargs: Additional fields to include
        
    Returns:
        Dictionary containing data response
    """
    response = {
        "type": data_type,
        "content": content,
        "request_id": request_id,
        "conversation_id": conversation_id,
        "timestamp": str(uuid.uuid4())  # Simple timestamp placeholder
    }
    response.update(kwargs)
    return response


# Utility function to get active connections (for backward compatibility)
def get_active_connections() -> Dict[str, WebSocket]:
    """Get current active WebSocket connections."""
    return active_connections.copy()


def get_connection_count() -> int:
    """Get count of active WebSocket connections."""
    return len(active_connections)