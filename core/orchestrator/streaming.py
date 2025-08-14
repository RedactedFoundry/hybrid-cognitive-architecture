#!/usr/bin/env python3
"""
Orchestrator Streaming - Real-time Event Processing

This module handles real-time streaming of the orchestrator processing stages,
essential for voice interactions and responsive UI experiences.

The streaming system provides token-by-token generation and phase updates
that enable natural conversational interfaces.
"""

import asyncio
import uuid
from typing import AsyncGenerator, Optional, TYPE_CHECKING

import structlog

from config.models import ANALYTICAL_MODEL, CREATIVE_MODEL, COORDINATOR_MODEL

from .models import (
    StreamEvent, StreamEventType, ProcessingPhase, OrchestratorState
)

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .orchestrator import UserFacingOrchestrator


class StreamingProcessor:
    """
    Handles real-time streaming of orchestrator processing.
    
    This class provides token-by-token streaming and phase updates
    for voice interactions and responsive user interfaces.
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize the streaming processor.
        
        Args:
            orchestrator: The parent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger("StreamingProcessor")
    
    async def process_request_stream(
        self, 
        user_input: str, 
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream processing events for user requests in real-time.
        
        This method provides token-by-token streaming essential for voice interactions
        and real-time UI updates. It yields events for phase transitions, individual
        tokens, and completion status.
        
        Args:
            user_input: The user's input message or question
            conversation_id: Optional conversation ID for context
            
        Yields:
            StreamEvent objects containing phase updates, tokens, and metadata
            
        Raises:
            RuntimeError: If the orchestrator is not properly initialized
        """
        if not self.orchestrator._initialized or not self.orchestrator.graph:
            raise RuntimeError("Orchestrator not properly initialized")
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        conversation_id = conversation_id or str(uuid.uuid4())
        
        self.logger = self.logger.bind(request_id=request_id, conversation_id=conversation_id)
        self.logger.info("Starting streaming request processing", user_input_preview=user_input[:100])
        
        try:
            # Yield initialization event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🔍 Initializing Constitution v5.4 processing...",
                phase=ProcessingPhase.INITIALIZATION,
                request_id=request_id,
                metadata={"input_length": len(user_input)}
            )
            
            # Create state and delegate to state machine (Constitution v5.4 flow)
            initial_state = OrchestratorState(
                user_input=user_input,
                conversation_id=conversation_id,
                request_id=request_id
            )
            
            # Yield smart router event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🧠 Smart Router analyzing intent...",
                phase=ProcessingPhase.SMART_TRIAGE,
                request_id=request_id
            )
            
            # Process through the state machine (Smart Router → Simple Generation)
            result_state = await self.orchestrator.graph.ainvoke(initial_state)
            
            # Yield final response event (LangGraph returns dict, not OrchestratorState)
            final_response = result_state.get("final_response", "")
            metadata = result_state.get("metadata", {})
            
            yield StreamEvent(
                event_type=StreamEventType.FINAL_RESPONSE,
                content=final_response,
                phase=ProcessingPhase.COMPLETED,
                metadata=metadata,
                request_id=request_id
            )
            
            # Yield completion event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="✅ Processing completed",
                phase=ProcessingPhase.COMPLETED,
                request_id=request_id
            )
            
        except Exception as e:
            self.logger.error("Streaming request processing failed", error=str(e), exc_info=True)
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                content=f"Processing failed: {str(e)}",
                phase=ProcessingPhase.ERROR,
                request_id=request_id,
                metadata={"error": str(e)}
            )
    
    # Legacy multi-agent council streaming methods removed
    # Constitution v5.4 uses simple generator-verifier flow via state machine
