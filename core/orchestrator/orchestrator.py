#!/usr/bin/env python3
"""
User-Facing Orchestrator for Hybrid AI Council
==============================================

This module implements the central coordination layer that orchestrates
the 3-layer cognitive architecture using a modular, plug-and-play design.

The orchestrator coordinates:
- Pheromind: Ambient pattern detection and processing
- Council: Deliberative decision-making layer  
- KIP: Knowledge-Incentive Protocol agent execution

Architecture Flow:
User Input → Pheromind Processing → Council Deliberation → KIP Execution → Response
"""

import asyncio
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, AsyncGenerator

import structlog
from langchain_core.messages import HumanMessage

from .models import OrchestratorState, StreamEvent
from .state_machine import StateMachineBuilder
from .processing_nodes import ProcessingNodes
from .streaming import StreamingProcessor
from .synthesis import ResponseSynthesizer

# Type aliases for clarity
RequestID = str
ConversationID = str


@dataclass
class UserFacingOrchestrator:
    """
    Central orchestrator for the Hybrid AI Council system.
    
    This class implements a modular LangGraph state machine that coordinates the
    3-layer cognitive architecture to process user requests and generate
    intelligent responses.
    
    The orchestrator uses a plug-and-play modular design:
    - StateMachineBuilder: Constructs and manages the LangGraph state machine
    - ProcessingNodes: Handles the core cognitive processing logic
    - StreamingProcessor: Provides real-time token streaming
    - ResponseSynthesizer: Integrates final responses from all layers
    
    This modularity enables easy adaptation as AI frameworks evolve.
    
    Attributes:
        logger: Structured logger for observability
        graph: Compiled LangGraph state machine
        _initialized: Flag indicating if the orchestrator is ready
    """
    
    logger: structlog.stdlib.BoundLogger = field(default_factory=lambda: structlog.get_logger("orchestrator"))
    graph: Optional[object] = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)
    
    # Modular components
    _state_machine_builder: Optional[StateMachineBuilder] = field(default=None, init=False)
    _processing_nodes: Optional[ProcessingNodes] = field(default=None, init=False)
    _streaming_processor: Optional[StreamingProcessor] = field(default=None, init=False)
    _response_synthesizer: Optional[ResponseSynthesizer] = field(default=None, init=False)
    
    def __post_init__(self) -> None:
        """Initialize the orchestrator after dataclass creation."""
        self.logger = self.logger.bind(component="UserFacingOrchestrator")
        
        # Initialize modular components
        self._processing_nodes = ProcessingNodes(self)
        self._state_machine_builder = StateMachineBuilder(self)
        self._streaming_processor = StreamingProcessor(self)
        self._response_synthesizer = ResponseSynthesizer(self)
        
        # Build the state machine
        self.graph = self._state_machine_builder.build_graph()
        
        self._initialized = True
        self.logger.info("UserFacingOrchestrator initialized successfully with modular architecture")
    
    async def process_request(
        self, 
        user_input: str, 
        conversation_id: Optional[ConversationID] = None
    ) -> OrchestratorState:
        """
        Process a user request through the full cognitive pipeline.
        
        This method executes the complete 3-layer processing:
        1. Pheromind scan for ambient patterns
        2. Council deliberation with multi-agent reasoning
        3. KIP agent execution for tool usage
        4. Response synthesis from all layers
        
        Args:
            user_input: The user's input message or question
            conversation_id: Optional conversation ID for context tracking
            
        Returns:
            OrchestratorState: Final state with complete processing results
            
        Raises:
            RuntimeError: If the orchestrator is not properly initialized
        """
        if not self._initialized or not self.graph:
            raise RuntimeError("Orchestrator not properly initialized")
        
        # Generate request ID and conversation ID
        request_id = str(uuid.uuid4())
        conversation_id = conversation_id or str(uuid.uuid4())
        
        # Bind request context to logger
        self.logger = self.logger.bind(request_id=request_id, conversation_id=conversation_id)
        self.logger.info("Processing user request", user_input_preview=user_input[:100])
        
        try:
            # Create initial state
            initial_state = OrchestratorState(
                request_id=request_id,
                conversation_id=conversation_id,
                user_input=user_input,
                messages=[HumanMessage(content=user_input)]
            )
            
            # Execute the state machine
            final_state_dict = await self.graph.ainvoke(initial_state)
            
            # Convert dict back to OrchestratorState (LangGraph serializes the state)
            if isinstance(final_state_dict, dict):
                final_state = OrchestratorState(**final_state_dict)
            else:
                final_state = final_state_dict
            
            self.logger.info(
                "Request processing completed",
                final_phase=final_state.current_phase.value if hasattr(final_state, 'current_phase') else 'completed',
                processing_time=(final_state.updated_at - final_state.started_at).total_seconds() if hasattr(final_state, 'updated_at') and hasattr(final_state, 'started_at') else 0,
                response_length=len(final_state.final_response) if final_state.final_response else 0
            )
            
            return final_state
            
        except Exception as e:
            self.logger.error("Request processing failed", error=str(e), exc_info=True)
            # Return error state
            initial_state.mark_error(f"Processing failed: {str(e)}")
            return initial_state
    
    async def process_request_stream(
        self, 
        user_input: str, 
        conversation_id: Optional[ConversationID] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream processing events for user requests in real-time.
        
        This method delegates to the StreamingProcessor for token-by-token
        streaming essential for voice interactions and real-time UI updates.
        
        Args:
            user_input: The user's input message or question
            conversation_id: Optional conversation ID for context
            
        Yields:
            StreamEvent objects containing phase updates, tokens, and metadata
        """
        async for event in self._streaming_processor.process_request_stream(
            user_input, conversation_id
        ):
            yield event
    
    # Processing node methods (delegated to ProcessingNodes)
    
    async def _initialize_node(self, state: OrchestratorState) -> OrchestratorState:
        """Initialize the processing pipeline and validate input."""
        return await self._processing_nodes.initialize_node(state)
    
    async def _smart_triage_node(self, state: OrchestratorState) -> OrchestratorState:
        """Smart Router - Central Nervous System for intent classification and routing."""
        return await self._processing_nodes.smart_triage_node(state)
    
    async def _fast_response_node(self, state: OrchestratorState) -> OrchestratorState:
        """Fast Response Path - Direct answers for simple queries."""
        return await self._processing_nodes.fast_response_node(state)
    
    async def _pheromind_scan_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute Pheromind ambient pattern detection."""
        return await self._processing_nodes.pheromind_scan_node(state)
    
    async def _council_deliberation_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute Council-layer multi-agent deliberation."""
        return await self._processing_nodes.council_deliberation_node(state)
    
    async def _simple_generation_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute Constitution v5.4 compliant simple generator-verifier flow."""
        return await self._processing_nodes.simple_generator_verifier.process(state)
    
    async def _kip_execution_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute KIP agent tasks based on Council decisions."""
        return await self._processing_nodes.kip_execution_node(state)
    
    async def _response_synthesis_node(self, state: OrchestratorState) -> OrchestratorState:
        """Synthesize final response from all processing layers."""
        return await self._response_synthesizer.synthesize_response(state)
    
    async def _error_handler_node(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors and provide graceful degradation."""
        return await self._processing_nodes.error_handler_node(state)


# Example usage and testing functions

async def example_usage():
    """
    Example demonstrating how to use the UserFacingOrchestrator.
    """
    orchestrator = UserFacingOrchestrator()
    
    # Process a sample user request
    result = await orchestrator.process_request(
        user_input="Hello, can you help me understand how AI systems work?",
        conversation_id="example_conversation_001"
    )
    
    print(f"Final Response: {result.final_response}")
    print(f"Processing Time: {(result.updated_at - result.started_at).total_seconds():.2f}s")
    print(f"Pheromind Signals: {len(result.pheromind_signals)}")
    if result.council_decision:
        print(f"Council Decision Confidence: {result.council_decision.confidence:.1%}")
        print(f"Winning Agent: {result.council_decision.winning_agent}")
        print(f"Agents Participated: {', '.join(result.council_decision.voting_agents)}")
    else:
        print("Council Decision: Not available")
    print(f"Current Phase: {result.current_phase}")
    print(f"KIP Tasks: {len(result.kip_tasks)}")


if __name__ == "__main__":
    # Run the example if script is executed directly
    asyncio.run(example_usage())