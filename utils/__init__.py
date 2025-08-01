"""
Utilities Package for Hybrid AI Council
=======================================

Common utility functions to reduce code duplication and improve maintainability.

Modules:
- websocket_utils: WebSocket connection management utilities
- client_utils: Client initialization and caching utilities
"""

from .websocket_utils import (
    WebSocketConnectionManager,
    WebSocketError,
    create_error_response,
    create_status_response
)

# Removed client_utils imports to prevent circular imports
# Import client_utils directly: from utils.client_utils import get_cached_ollama_client

__all__ = [
    # WebSocket utilities
    "WebSocketConnectionManager",
    "WebSocketError", 
    "create_error_response",
    "create_status_response",
    
    # Client utilities removed to prevent circular imports
    # Use: from utils.client_utils import get_cached_ollama_client
]