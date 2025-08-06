#!/usr/bin/env python3
"""
Voice Foundation Integration with Orchestrator

This module provides the integration layer between the voice foundation
and the Hybrid AI Council's cognitive orchestrator, enabling voice-driven
conversations through the 3-layer architecture.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional, AsyncGenerator, Dict, Any
from datetime import datetime, timezone
import structlog

# Import orchestrator components
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.orchestrator import UserFacingOrchestrator

# Import voice foundation
from voice_foundation.production_voice_engines import create_voice_foundation
from voice_foundation.simple_voice_pipeline import VoiceFoundation

# Set up structured logging
logger = structlog.get_logger("voice_orchestrator")

class VoiceOrchestrator:
    """
    Integration layer that connects voice input/output with the cognitive orchestrator
    """
    
    def __init__(self, use_production=True, force_parakeet=True):
        self.orchestrator = UserFacingOrchestrator()
        self.voice_foundation = None
        self.use_production = use_production
        self.force_parakeet = force_parakeet
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize both voice foundation and orchestrator"""
        logger.info("Initializing Voice-Enabled Orchestrator")
        
        # Create and initialize voice foundation
        if self.use_production:
            logger.info("Using SOTA Production Voice Pipeline (2025)")
        else:
            logger.info("Using Mock Voice Pipeline for testing")
            
        self.voice_foundation = await create_voice_foundation(
            use_production=self.use_production,
            force_parakeet=self.force_parakeet
        )
        
        # Initialize orchestrator (if not already done)
        # Note: orchestrator initialization is handled in __post_init__
        
        self.is_initialized = True
        logger.info("Voice-Enabled Orchestrator ready")
        
    async def process_voice_request(
        self, 
        audio_input_path: str, 
        audio_output_path: str,
        user_id: str = "voice_user",
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a complete voice request through the cognitive architecture
        
        Args:
            audio_input_path: Path to input audio file
            audio_output_path: Path to output audio file  
            user_id: User identifier
            conversation_id: Optional conversation ID for context
            
        Returns:
            Dict with request details and results
        """
        if not self.is_initialized:
            await self.initialize()
            
        request_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        logger.info("Processing voice request", request_id=request_id)
        
        try:
            # Step 1: Speech to Text
            logger.info("Starting Step 1: Speech to Text", request_id=request_id)
            transcription = await self.voice_foundation.process_audio_to_text(audio_input_path)
            
            if not transcription:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": "Speech transcription failed",
                    "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Step 2: Process through cognitive orchestrator  
            logger.info("Starting Step 2: Cognitive Processing", 
                       request_id=request_id,
                       transcription=transcription[:50])
            # Note: user_id not yet supported by orchestrator but kept in voice API for future enhancement
            orchestrator_response = await self.orchestrator.process_request(
                user_input=transcription,
                conversation_id=conversation_id or request_id
            )
            
            if not orchestrator_response or not orchestrator_response.final_response:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": "Orchestrator processing failed",
                    "transcription": transcription,
                    "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            response_text = orchestrator_response.final_response
            
            # Step 3: Text to Speech
            logger.info("Starting Step 3: Text to Speech", 
                       request_id=request_id,
                       response_text=response_text[:50])
            tts_success = await self.voice_foundation.process_text_to_audio(response_text, audio_output_path)
            
            if not tts_success:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": "Speech synthesis failed",
                    "transcription": transcription,
                    "response_text": response_text,
                    "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Success!
            total_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "request_id": request_id,
                "success": True,
                "transcription": transcription,
                "response_text": response_text,
                "audio_output_path": audio_output_path,
                "processing_time": total_time,
                "orchestrator_state": {
                    "phases_completed": orchestrator_response.current_phase.value,
                    "messages_count": len(orchestrator_response.messages),
                    "pheromind_signals": len(orchestrator_response.pheromind_signals) if orchestrator_response.pheromind_signals else 0
                }
            }
            
        except Exception as e:
            return {
                "request_id": request_id,
                "success": False,
                "error": f"Voice processing error: {str(e)}",
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def process_voice_request_streaming(
        self,
        audio_input_path: str,
        user_id: str = "voice_user",
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process voice request with streaming updates (for future WebSocket integration)
        
        Args:
            audio_input_path: Path to input audio file
            user_id: User identifier
            conversation_id: Optional conversation ID
            
        Yields:
            Streaming updates during processing
        """
        if not self.is_initialized:
            await self.initialize()
            
        request_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        try:
            yield {
                "type": "voice_request_start",
                "request_id": request_id,
                "timestamp": start_time.isoformat()
            }
            
            # Step 1: Speech to Text
            yield {
                "type": "stt_start", 
                "request_id": request_id,
                "message": "Converting speech to text..."
            }
            
            transcription = await self.voice_foundation.process_audio_to_text(audio_input_path)
            
            if not transcription:
                yield {
                    "type": "error",
                    "request_id": request_id,
                    "error": "Speech transcription failed"
                }
                return
                
            yield {
                "type": "stt_complete",
                "request_id": request_id,
                "transcription": transcription
            }
            
            # Step 2: Stream orchestrator processing
            yield {
                "type": "orchestrator_start",
                "request_id": request_id,
                "message": "Processing through cognitive architecture..."
            }
            
            # Note: user_id not yet supported by orchestrator streaming but kept in voice API for future enhancement
            async for event in self.orchestrator.process_request_stream(
                user_input=transcription,
                conversation_id=conversation_id or request_id
            ):
                # Forward orchestrator streaming events
                yield {
                    "type": "orchestrator_event",
                    "request_id": request_id,
                    "event": event
                }
            
            # Get final orchestrator state  
            # Note: user_id not yet supported by orchestrator but kept in voice API for future enhancement
            final_state = await self.orchestrator.process_request(
                user_input=transcription,
                conversation_id=conversation_id or request_id
            )
            
            if not final_state or not final_state.final_response:
                yield {
                    "type": "error",
                    "request_id": request_id,
                    "error": "Orchestrator processing failed"
                }
                return
            
            yield {
                "type": "orchestrator_complete",
                "request_id": request_id,
                "response_text": final_state.final_response
            }
            
            # Step 3: Text to Speech
            yield {
                "type": "tts_start",
                "request_id": request_id,
                "message": "Converting response to speech..."
            }
            
            # For streaming, we'll create a unique output path
            audio_output_path = f"voice_foundation/outputs/{request_id}_response.wav"
            Path(audio_output_path).parent.mkdir(parents=True, exist_ok=True)
            
            tts_success = await self.voice_foundation.process_text_to_audio(
                final_state.final_response, 
                audio_output_path
            )
            
            if tts_success:
                yield {
                    "type": "tts_complete",
                    "request_id": request_id,
                    "audio_output_path": audio_output_path
                }
                
                yield {
                    "type": "voice_request_complete",
                    "request_id": request_id,
                    "transcription": transcription,
                    "response_text": final_state.final_response,
                    "audio_output_path": audio_output_path,
                    "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            else:
                yield {
                    "type": "error",
                    "request_id": request_id,
                    "error": "Speech synthesis failed"
                }
                
        except Exception as e:
            yield {
                "type": "error",
                "request_id": request_id,
                "error": f"Voice processing error: {str(e)}"
            }

# Global voice orchestrator instance - using SOTA production models (2025)
# Created lazily to avoid blocking imports
voice_orchestrator = None

def get_voice_orchestrator():
    """Get or create the global voice orchestrator instance."""
    global voice_orchestrator
    if voice_orchestrator is None:
        voice_orchestrator = VoiceOrchestrator(use_production=True, force_parakeet=True)
        # Note: Initialization happens lazily when first used
        # This prevents blocking imports and startup
    return voice_orchestrator

async def get_initialized_voice_orchestrator():
    """Get or create and initialize the global voice orchestrator instance."""
    global voice_orchestrator
    if voice_orchestrator is None:
        voice_orchestrator = VoiceOrchestrator(use_production=True, force_parakeet=True)
    
    if not voice_orchestrator.is_initialized:
        # Add retry logic for voice service connection
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                await voice_orchestrator.initialize()
                logger.info("Voice orchestrator initialized successfully")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Voice orchestrator initialization attempt {attempt + 1} failed, retrying in {retry_delay}s", error=str(e))
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Voice orchestrator initialization failed after all retries", error=str(e))
                    # Don't raise - let the application continue without voice
                    return None
    
    return voice_orchestrator

# Convenience functions
async def process_voice_conversation(
    audio_input_path: str,
    audio_output_path: str,
    user_id: str = "voice_user",
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function for voice conversations"""
    voice_orch = get_voice_orchestrator()
    return await voice_orch.process_voice_request(
        audio_input_path, audio_output_path, user_id, conversation_id
    )

async def stream_voice_conversation(
    audio_input_path: str,
    user_id: str = "voice_user", 
    conversation_id: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """Convenience function for streaming voice conversations"""
    voice_orch = get_voice_orchestrator()
    async for event in voice_orch.process_voice_request_streaming(
        audio_input_path, user_id, conversation_id
    ):
        yield event

if __name__ == "__main__":
    # Test the integration
    async def test_integration():
        logger.info("Testing Voice-Orchestrator Integration")
        
        # Create test audio if needed
        if not Path("voice_foundation/test_audio.wav").exists():
            import voice_foundation.create_test_audio as cta
            cta.create_test_audio("voice_foundation/test_audio.wav")
        
        # Test basic integration
        result = await process_voice_conversation(
            "voice_foundation/test_audio.wav",
            "voice_foundation/integration_test_output.wav"
        )
        
        logger.info("Integration Test Results",
                   success=result['success'],
                   transcription=result.get('transcription', ''),
                   response_text=result.get('response_text', ''),
                   processing_time=result.get('processing_time', 0),
                   audio_output_path=result.get('audio_output_path', ''),
                   error=result.get('error', ''))
    
    asyncio.run(test_integration())