#!/usr/bin/env python3
"""
Support Processing Nodes - Infrastructure and Error Handling

This module contains support nodes for initialization, error handling, 
and fast response processing.
"""

from langchain_core.messages import AIMessage

from config.models import COORDINATOR_MODEL
from .base import BaseProcessingNode
from ..models import OrchestratorState, ProcessingPhase


class SupportNode(BaseProcessingNode):
    """
    Support Nodes - Infrastructure and Error Handling.
    
    This class contains utility nodes for:
    - Initialization and validation
    - Error handling and recovery
    - Fast response processing for simple queries
    """
    
    async def initialize_node(self, state: OrchestratorState) -> OrchestratorState:
        """Initialize the processing pipeline and validate input."""
        self.logger.debug("Initializing request processing")
        state.update_phase(ProcessingPhase.INITIALIZATION)
        
        try:
            # Add initialization logic here:
            # - Input validation
            # - Context loading  
            # - Security checks
            
            # Basic input validation
            if not state.user_input or not state.user_input.strip():
                raise ValueError("User input cannot be empty")
            
            if len(state.user_input) > 10000:  # 10K character limit
                raise ValueError("User input exceeds maximum length of 10,000 characters")
            
            # Add metadata about the initialization
            state.metadata["initialized_at"] = state.updated_at.isoformat()
            state.metadata["input_length"] = len(state.user_input)
            
        except Exception as e:
            # Mark error in state - conditional routing will handle this
            error_msg = f"Initialization failed: {str(e)}"
            state.mark_error(error_msg)
            self.logger.error("Initialization error", error=error_msg)
        
        return state
    
    async def error_handler_node(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors and provide graceful degradation."""
        self.logger.warning("Processing error occurred", error=state.error_message)
        
        # Error recovery with retry logic and graceful degradation
        # Retries up to max_retries (default: 3) then provides fallback response
        
        # Always set a user-visible fallback to avoid empty final responses in UI
        if not state.final_response:
            state.final_response = "I apologize, but I encountered an error processing your request. Please try again."
            state.add_message(AIMessage(content=state.final_response))
        
        # Maintain retry counters for observability, but do not loop in this graph
        if state.retry_count < state.max_retries:
            state.retry_count += 1
            self.logger.info("Retry recorded (no loop)", retry_count=state.retry_count)
        
        return state
    
    async def fast_response_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Fast Response Path - Direct answers for simple queries.
        
        This node handles simple queries that don't require the full council
        deliberation. Uses only the fastest model (Mistral) for near-instant
        responses to factual questions, definitions, and basic queries.
        
        Designed for queries like:
        - "What time is it?"
        - "Who is the CEO of Google?"
        - "What's 2+2?"
        - "Define machine learning"
        """
        self.logger.info("Processing via fast response path", 
                        user_input_preview=state.user_input[:100])
        state.update_phase(ProcessingPhase.FAST_RESPONSE)
        
        try:
            # Use the model router (llama.cpp) for immediate response
            from clients.model_router import get_model_router
            router = await get_model_router()
            
            # Simple, direct prompt for fast responses - ENFORCE BREVITY
            fast_prompt = f"""
Answer in 1–2 short, conversational sentences.
Do not use a single-word answer; include a natural phrase (e.g., "X and Y make Z").
Do not include any preamble, role language, or headings.

Question: {state.user_input}
"""

            # Generate fast response using Mistral
            result = await router.generate(
                model_alias=COORDINATOR_MODEL,
                prompt=fast_prompt,
                max_tokens=200,
                temperature=0.2
            )
            
            # Store the fast response as final response
            state.final_response = str(result.get("content", "")).strip()
            state.add_message(AIMessage(content=state.final_response))
            
            # Add metadata about fast path usage
            state.metadata["fast_path_used"] = True
            state.metadata["response_model"] = COORDINATOR_MODEL
            state.metadata["processing_mode"] = "fast_response"
            
            self.logger.info("Fast response generated", 
                           response_length=len(state.final_response),
                           model=COORDINATOR_MODEL)
                           
        except Exception as e:
            # On error, provide a basic fallback response
            error_msg = f"Fast response failed: {str(e)}"
            state.final_response = "I'm having trouble processing that request right now. Could you try rephrasing it?"
            state.add_message(AIMessage(content=state.final_response))
            
            self.logger.error("Fast response error", error=error_msg)
        
        return state