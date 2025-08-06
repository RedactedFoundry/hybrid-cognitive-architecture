"""
Voice Foundation Package
Microservice-based voice processing for Hybrid AI Council
"""

# Import main components for easier access
from .voice_client import VoiceServiceClient, transcribe_audio, synthesize_speech
from .production_voice_engines import (
    ProductionVoiceFoundation, 
    ProductionSTTEngine, 
    ProductionTTSEngine,
    create_voice_foundation
)

__all__ = [
    "VoiceServiceClient",
    "transcribe_audio", 
    "synthesize_speech",
    "ProductionVoiceFoundation",
    "ProductionSTTEngine",
    "ProductionTTSEngine", 
    "create_voice_foundation"
]