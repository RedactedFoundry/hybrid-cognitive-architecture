#!/usr/bin/env python3
"""
Smart Router Processing Node - Central Nervous System

This module contains the Smart Router logic for intent classification and routing.
The Smart Router analyzes user input and routes requests to the appropriate 
cognitive layer based on complexity and task type.

Now with comprehensive error boundaries for production reliability.
"""

from config.models import COORDINATOR_MODEL
from clients.model_router import get_model_router
from .base import CognitiveProcessingNode
from ..models import OrchestratorState, ProcessingPhase, TaskIntent
from utils.error_utils import (
    error_boundary,
    handle_cognitive_processing_error
)


class SmartRouterNode(CognitiveProcessingNode):
    """
    Smart Router - Central Nervous System for Intent Classification.
    
    This is the core decision point that analyzes user intent and routes
    requests to the appropriate cognitive layer based on complexity and task type.
    
    Routes to:
    - exploratory_task: Pheromind layer for pattern discovery
    - action_task: KIP engine for direct execution  
    - complex_reasoning_task: Council for multi-agent deliberation
    - simple_query_task: Fast response path for immediate answers
    """
    
    @error_boundary(component="smart_router_process")
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process Smart Router triage analysis with comprehensive error handling."""
        return await self.smart_triage_node(state)
    
    @error_boundary(component="smart_router_triage")
    async def smart_triage_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Smart Router - Central Nervous System for Intent Classification.
        
        This is the core decision point that analyzes user intent and routes
        requests to the appropriate cognitive layer based on complexity and task type.
        
        Routes to:
        - exploratory_task: Pheromind layer for pattern discovery
        - action_task: KIP engine for direct execution  
        - complex_reasoning_task: Council for multi-agent deliberation
        - simple_query_task: Fast response path for immediate answers
        """
        self.logger.info("Smart Router starting triage analysis", user_input=state.user_input)
        state.update_phase(ProcessingPhase.SMART_TRIAGE)
        
        try:
            # Use the fastest model (Mistral via llama.cpp) for quick intent classification
            router = await get_model_router()
            
            # Intent classification prompt - HEAVILY BIASED TOWARD SIMPLE QUERIES
            classification_prompt = f"""
CRITICAL: Classify this as simple_query_task unless it explicitly requires analysis or complex reasoning.

USER REQUEST: "{state.user_input}"

RESPOND WITH ONLY ONE WORD: simple_query_task OR action_task OR exploratory_task OR complex_reasoning_task

CLASSIFICATION RULES:

simple_query_task = ANY factual question that can be answered with basic information:
- "Who is [person]?" 
- "What is [thing]?"
- "What color is [object]?"
- "When did [event]?"
- "Where is [place]?"
- "How much is [item]?"
- Simple definitions
- Basic facts
- Time/date questions

action_task = Commands that start with action verbs:
- "Execute [task]", "Run [process]", "Create [item]", "Send [message]"
- "Buy [stock]", "Sell [asset]", "Delete [file]", "Generate [report]"

exploratory_task = Find patterns or connections:
- "Find connections", "Explore", "Brainstorm", "Discover patterns"

complex_reasoning_task = Analysis, explanation, or multi-faceted questions:
- "Pros and cons"
- "Compare X vs Y" 
- "Should I choose..."
- "Analyze the impact of..."
- "How does X help/affect/impact Y?"
- "What are the ways/methods/approaches to..."
- "In depth ways/detailed explanation of..."
- "Why is/does/would..."
- Questions asking for multiple points or detailed explanations

DEFAULT: If uncertain, choose simple_query_task

EXAMPLES:
"Who is the CEO of Google?" = simple_query_task
"What color is the sky?" = simple_query_task
"What time is it?" = simple_query_task
"What is AI?" = simple_query_task
"Define machine learning" = simple_query_task
"Execute the quarterly sales report" = action_task
"Create a new document" = action_task
"Buy 100 shares of Tesla" = action_task
"Find connections in my notes" = exploratory_task
"What are the pros and cons of AI?" = complex_reasoning_task

YOUR CLASSIFICATION (ONE WORD ONLY):"""

            # Get intent classification from Mistral (fastest model)
            classification_result = await router.generate(
                model_alias=COORDINATOR_MODEL,
                prompt=classification_prompt,
                max_tokens=50,
                temperature=0.0
            )
            
            # Parse the classification response  
            classification = str(classification_result.get("content", "")).strip().lower()
            
            self.logger.debug("Smart Router classification received", 
                           raw_classification=classification,
                           user_input_preview=state.user_input[:100])
            
            # Enhanced classification logic - prioritize simple queries
            user_input_lower = state.user_input.lower()
            
            # Rule-based overrides for obvious patterns
            simple_rule_match = (user_input_lower.startswith(("who is", "what is", "what color", "when did", "where is", "how much", "how do", "how to")) or
                                 "ceo of" in user_input_lower or 
                                 "time is it" in user_input_lower or
                                 "weather" in user_input_lower or
                                 user_input_lower.startswith(("define",)))
            
            # Complex reasoning indicators - EXPANDED to catch analytical questions that were misrouted
            complex_rule_match = (
                # Original patterns
                user_input_lower.startswith(("compare", "should i", "pros and cons", "analyze")) or
                "vs " in user_input_lower or
                "versus" in user_input_lower or
                "how does" in user_input_lower or
                "how will" in user_input_lower or
                "why does" in user_input_lower or
                "why is" in user_input_lower or
                "why would" in user_input_lower or
                "in depth" in user_input_lower or
                "detailed" in user_input_lower or
                "ways to" in user_input_lower or
                "methods to" in user_input_lower or
                "approaches to" in user_input_lower or
                ("help" in user_input_lower and len(user_input_lower.split()) > 5) or
                ("impact" in user_input_lower and len(user_input_lower.split()) > 4) or
                
                # CRITICAL MISSING PATTERNS that caused misrouting:
                
                # Decision-making patterns
                "deciding between" in user_input_lower or
                "should i choose" in user_input_lower or
                "factors should i consider" in user_input_lower or
                "factors to consider" in user_input_lower or
                "what factors" in user_input_lower or
                
                # Balance/trade-off patterns  
                "how should" in user_input_lower or
                "how can" in user_input_lower or
                "balance" in user_input_lower or
                "trade-offs" in user_input_lower or
                "trade offs" in user_input_lower or
                
                # Analysis request patterns
                "analyze" in user_input_lower or
                "analysis" in user_input_lower or
                "multiple approaches" in user_input_lower or
                "different approaches" in user_input_lower or
                "various approaches" in user_input_lower or
                "effectiveness" in user_input_lower or
                
                # Complex problem-solving patterns
                "address the problem" in user_input_lower or
                "solve the problem" in user_input_lower or
                "while preserving" in user_input_lower or
                "while maintaining" in user_input_lower or
                
                # Ethical/policy patterns
                "ethical implications" in user_input_lower or
                "implications" in user_input_lower or
                "arguments for and against" in user_input_lower or
                "for and against" in user_input_lower or
                
                # Rights/governance patterns
                user_input_lower.startswith("should governments") or
                user_input_lower.startswith("should companies") or
                user_input_lower.startswith("should society") or
                "rights" in user_input_lower or
                "needs" in user_input_lower or
                
                # Complex "what" questions that need analysis
                (user_input_lower.startswith("what are") and 
                 ("benefits" in user_input_lower or "risks" in user_input_lower or 
                  "implications" in user_input_lower or "effects" in user_input_lower or
                  "consequences" in user_input_lower)) or
                  
                # Long questions are likely complex (>15 words often need analysis)
                len(user_input_lower.split()) > 15
            )
            
            # Exploratory task indicators  
            exploratory_rule_match = (user_input_lower.startswith(("find connections", "discover patterns", "explore", "brainstorm")) or
                                     "find connections" in user_input_lower or
                                     "discover patterns" in user_input_lower or
                                     "explore relationships" in user_input_lower)
            
            # Action tasks - but not if it's a "how to" question
            action_rule_match = (user_input_lower.startswith(("execute", "run", "create", "send", "buy", "sell", "delete", "generate")) and
                                not user_input_lower.startswith(("how", "what", "when", "where", "why")))
            
            if complex_rule_match:
                intent = TaskIntent.COMPLEX_REASONING_TASK
                self.logger.info("Smart Router: Rule-based override for complex reasoning", 
                               user_input=state.user_input, 
                               override_reason="Matches complex reasoning pattern")
            elif exploratory_rule_match:
                intent = TaskIntent.EXPLORATORY_TASK
                self.logger.info("Smart Router: Rule-based override for exploratory task", 
                               user_input=state.user_input, 
                               override_reason="Matches exploratory pattern")
            elif action_rule_match:
                intent = TaskIntent.ACTION_TASK
                self.logger.info("Smart Router: Rule-based override for action task", 
                               user_input=state.user_input, 
                               override_reason="Matches action verb pattern")
            elif simple_rule_match:
                intent = TaskIntent.SIMPLE_QUERY_TASK
                self.logger.info("Smart Router: Rule-based override for simple query", 
                               user_input=state.user_input, 
                               override_reason="Matches simple query pattern")
            # Map response to TaskIntent enum  
            elif "simple_query_task" in classification:
                intent = TaskIntent.SIMPLE_QUERY_TASK
            elif "exploratory_task" in classification:
                intent = TaskIntent.EXPLORATORY_TASK
            elif "action_task" in classification:
                intent = TaskIntent.ACTION_TASK
            elif "complex_reasoning_task" in classification:
                intent = TaskIntent.COMPLEX_REASONING_TASK
            else:
                # Default to simple query if uncertain (bias toward speed)
                intent = TaskIntent.SIMPLE_QUERY_TASK
                self.logger.warning("Unclear intent classification, defaulting to simple query for speed", 
                                   classification=classification,
                                   user_input=state.user_input)
            
            # Store the routing decision
            state.routing_intent = intent
            
            self.logger.info("Smart Router triage completed", 
                           intent=intent.value,
                           user_input=state.user_input,
                           will_route_to=f"{intent.value} path")
            
        except Exception as e:
            # Handle processing error with comprehensive logging and fallback
            processing_error = await handle_cognitive_processing_error(
                error=e,
                phase="smart_triage",
                component="smart_router",
                request_id=state.request_id
            )
            
            # On error, default to complex reasoning (safe fallback)
            state.routing_intent = TaskIntent.COMPLEX_REASONING_TASK
            state.metadata["smart_router_error"] = str(processing_error)
            state.metadata["fallback_reason"] = "Error in intent classification, using safe fallback"
            
            self.logger.warning(
                "Smart triage error, defaulting to complex reasoning for safety",
                error=str(processing_error),
                fallback_intent=TaskIntent.COMPLEX_REASONING_TASK.value,
                request_id=state.request_id
            )
        
        return state