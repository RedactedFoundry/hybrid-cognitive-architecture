"""
Endpoints package for Hybrid AI Council
=======================================

Contains all FastAPI routers and endpoint handlers.
"""

from .chat import router as chat_router
from .voice import router as voice_router  
from .health import router as health_router

__all__ = [
    "chat_router",
    "voice_router",
    "health_router"
]