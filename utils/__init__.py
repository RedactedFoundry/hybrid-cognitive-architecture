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

from .client_utils import (
    get_cached_ollama_client,
    get_client_with_fallback
)

__all__ = [
    # WebSocket utilities
    "WebSocketConnectionManager",
    "WebSocketError", 
    "create_error_response",
    "create_status_response",
    
    # Client utilities
    "get_cached_ollama_client",
    "get_client_with_fallback"
]