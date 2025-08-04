"""
WebSockets package for Hybrid AI Council
========================================

Contains all WebSocket handlers and utilities.
"""

# Import from the new focused modules
from utils.websocket_utils import active_connections
from .voice_handlers import handle_voice_input
from .chat_handlers import (
    handle_conversation_interrupt,
    websocket_chat_handler, 
    process_with_streaming
)

__all__ = [
    "active_connections",
    "handle_voice_input", 
    "handle_conversation_interrupt",
    "websocket_chat_handler",
    "process_with_streaming"
]