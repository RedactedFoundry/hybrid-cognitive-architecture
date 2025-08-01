#!/usr/bin/env python3
"""
Smart Router Processing Node - Central Nervous System

This module contains the Smart Router logic for intent classification and routing.
The Smart Router analyzes user input and routes requests to the appropriate 
cognitive layer based on complexity and task type.
"""

from config.models import COORDINATOR_MODEL
from .base import CognitiveProcessingNode
from ..models import OrchestratorState, ProcessingPhase, TaskIntent


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
    
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process Smart Router triage analysis."""
        return await self.smart_triage_node(state)
    
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
            # Use the fastest model (Mistral) for quick intent classification with caching
            ollama_client = await self._get_cached_ollama_client()
            
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

complex_reasoning_task = ONLY when explicitly asking for analysis:
- "Pros and cons"
- "Compare X vs Y" 
- "Should I choose..."
- "Analyze the impact of..."

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
            classification_response = await ollama_client.generate_response(
                prompt=classification_prompt,
                model_alias=COORDINATOR_MODEL,  # Mistral for speed
                max_tokens=50,
                timeout=10  # Fast classification
            )
            
            # Parse the classification response  
            classification = classification_response.text.strip().lower()
            
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
                                 user_input_lower.startswith(("define", "explain")))
            
            # Complex reasoning indicators
            complex_rule_match = (user_input_lower.startswith(("compare", "should i", "pros and cons", "analyze")) or
                                 "vs " in user_input_lower or
                                 "versus" in user_input_lower)
            
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
            # On error, default to complex reasoning (safe fallback)
            error_msg = f"Smart triage failed: {str(e)}"
            state.routing_intent = TaskIntent.COMPLEX_REASONING_TASK
            self.logger.error("Smart triage error, defaulting to complex reasoning", 
                            error=error_msg)
        
        return state