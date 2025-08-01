"""
WebSockets package for Hybrid AI Council
========================================

Contains all WebSocket handlers and utilities.
"""

from .handlers import (
    active_connections,
    handle_voice_input,
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