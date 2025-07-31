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

# Import orchestrator components
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.orchestrator import UserFacingOrchestrator

# Import voice foundation
from voice_foundation.simple_voice_pipeline import voice_foundation, VoiceFoundation

class VoiceOrchestrator:
    """
    Integration layer that connects voice input/output with the cognitive orchestrator
    """
    
    def __init__(self):
        self.orchestrator = UserFacingOrchestrator()
        self.voice_foundation = voice_foundation
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize both voice foundation and orchestrator"""
        print("🎤 Initializing Voice-Enabled Orchestrator...")
        
        # Initialize voice foundation
        await self.voice_foundation.initialize()
        
        # Initialize orchestrator (if not already done)
        # Note: orchestrator initialization is handled in __post_init__
        
        self.is_initialized = True
        print("✅ Voice-Enabled Orchestrator ready!")
        
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
        
        print(f"🎯 Processing voice request {request_id}")
        
        try:
            # Step 1: Speech to Text
            print("📝 Step 1: Speech to Text")
            transcription = await self.voice_foundation.process_audio_to_text(audio_input_path)
            
            if not transcription:
                return {
                    "request_id": request_id,
                    "success": False,
                    "error": "Speech transcription failed",
                    "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
                }
            
            # Step 2: Process through cognitive orchestrator  
            print("🧠 Step 2: Cognitive Processing")
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
            print("🔊 Step 3: Text to Speech")
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

# Global voice orchestrator instance
voice_orchestrator = VoiceOrchestrator()

# Convenience functions
async def process_voice_conversation(
    audio_input_path: str,
    audio_output_path: str,
    user_id: str = "voice_user",
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function for voice conversations"""
    return await voice_orchestrator.process_voice_request(
        audio_input_path, audio_output_path, user_id, conversation_id
    )

async def stream_voice_conversation(
    audio_input_path: str,
    user_id: str = "voice_user", 
    conversation_id: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """Convenience function for streaming voice conversations"""
    async for event in voice_orchestrator.process_voice_request_streaming(
        audio_input_path, user_id, conversation_id
    ):
        yield event

if __name__ == "__main__":
    # Test the integration
    async def test_integration():
        print("🧪 Testing Voice-Orchestrator Integration...")
        
        # Create test audio if needed
        if not Path("voice_foundation/test_audio.wav").exists():
            import voice_foundation.create_test_audio as cta
            cta.create_test_audio("voice_foundation/test_audio.wav")
        
        # Test basic integration
        result = await process_voice_conversation(
            "voice_foundation/test_audio.wav",
            "voice_foundation/integration_test_output.wav"
        )
        
        print(f"\n🎯 Integration Test Results:")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Transcription: '{result['transcription']}'")
            print(f"Response: '{result['response_text']}'")
            print(f"Processing Time: {result['processing_time']:.2f}s")
            print(f"Audio Output: {result['audio_output_path']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    asyncio.run(test_integration())