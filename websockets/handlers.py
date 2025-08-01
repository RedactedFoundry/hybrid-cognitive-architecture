"""
Legacy WebSocket Handlers - DEPRECATED
======================================

This file has been split into focused modules for better maintainability:
- websockets/voice_handlers.py - Voice-specific WebSocket handling  
- websockets/chat_handlers.py - Chat-specific WebSocket handling

This file remains for backward compatibility during transition.
Import from the specific modules instead:

  from websockets.voice_handlers import handle_voice_input
  from websockets.chat_handlers import websocket_chat_handler, process_with_streaming, handle_conversation_interrupt
"""

# Re-export functions for backward compatibility
from .voice_handlers import handle_voice_input
from .chat_handlers import (
    websocket_chat_handler,
    process_with_streaming,
    handle_conversation_interrupt
)

# Maintain imports for any external references
from fastapi import WebSocket, WebSocketDisconnect
import structlog

# Deprecated - use specific modules instead
logger = structlog.get_logger(__name__)
logger.warning("handlers.py is deprecated - use voice_handlers.py or chat_handlers.py instead")