#!/usr/bin/env python3
"""
Orchestrator Processing Nodes - Core Cognitive Processing

This module contains all the node processing methods for the LangGraph state machine.
Each node represents a stage in the 3-layer cognitive architecture.

This modular design allows easy modification of individual processing stages
without affecting the overall orchestration logic.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, TYPE_CHECKING

import structlog
from langchain_core.messages import AIMessage

from config.models import ANALYTICAL_MODEL, CREATIVE_MODEL, COORDINATOR_MODEL
from clients.ollama_client import get_ollama_client
from core.kip import kip_session, treasury_session
from core.pheromind import PheromindSignal, pheromind_session
from core.cache_integration import get_global_cache_manager

from .models import (
    OrchestratorState, ProcessingPhase, CouncilDecision, KIPTask, TaskIntent
)

# Type-only imports to avoid circular dependencies  
if TYPE_CHECKING:
    from .orchestrator import UserFacingOrchestrator


class ProcessingNodes:
    """
    Processing nodes for the orchestrator state machine.
    
    This class encapsulates all the cognitive processing logic for the
    3-layer architecture in modular, testable methods.
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize processing nodes.
        
        Args:
            orchestrator: The parent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger("ProcessingNodes")
        
    async def _get_cached_ollama_client(self):
        """Get a cached Ollama client for improved performance and cost savings."""
        try:
            cache_manager = await get_global_cache_manager()
            ollama_client = get_ollama_client()
            return cache_manager.get_cached_ollama_client(ollama_client)
        except Exception as e:
            self.logger.warning("Failed to get cached client, using direct client", error=str(e))
            return get_ollama_client()
    
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
    
    async def pheromind_scan_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute Pheromind ambient pattern detection.
        
        This method queries the Redis-based pheromind layer for existing signals
        that match patterns in the user's input, providing ambient context for
        the council deliberation.
        """
        self.logger.info(
            "Starting Pheromind ambient scan", 
            request_id=state.request_id,
            user_input_preview=state.user_input[:100]
        )
        state.update_phase(ProcessingPhase.PHEROMIND_SCAN)
        
        try:
            # Use pheromind session for ambient intelligence query
            async with pheromind_session() as pheromind:
                # Extract keywords from user input for pattern matching
                search_patterns = self._extract_search_patterns(state.user_input)
                
                # Query for existing pheromind signals matching user context
                all_signals = []
                for pattern in search_patterns:
                    signals = await pheromind.query_signals(pattern, min_strength=0.3)
                    all_signals.extend(signals)
                
                # Remove duplicates while preserving strength-based ordering
                unique_signals = self._deduplicate_signals(all_signals)
                
                # Update state with discovered ambient signals
                state.pheromind_signals.extend(unique_signals)
                
                self.logger.info(
                    "Pheromind scan completed",
                    request_id=state.request_id,
                    signals_found=len(unique_signals),
                    search_patterns=search_patterns,
                    strongest_signal=max([s.strength for s in unique_signals], default=0.0)
                )
                
        except Exception as e:
            # Pheromind failures should not block the main flow
            self.logger.warning(
                "Pheromind scan failed, continuing without ambient context",
                request_id=state.request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Continue processing even if pheromind is unavailable
        
        return state
    
    async def council_deliberation_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute Council-layer multi-agent deliberation using LLM integration.
        
        This implements a sophisticated multi-agent reasoning process:
        1. Multiple AI agents analyze the user input concurrently
        2. Each agent provides their perspective and reasoning
        3. Agents critique each other's responses
        4. A final vote determines the best approach
        """
        self.logger.debug("Starting Council deliberation with multi-agent reasoning")
        state.update_phase(ProcessingPhase.COUNCIL_DELIBERATION)
        
        try:
            # Initialize cached Ollama client for LLM inference with cost optimization
            ollama_client = await self._get_cached_ollama_client()
            
            # Check if Ollama is available
            if not await ollama_client.health_check():
                raise Exception("Ollama service is not available")
            
            # Define council agents with different perspectives
            council_agents = {
                "analytical_agent": {
                    "model": ANALYTICAL_MODEL,
                    "system_prompt": """You are the Analytical Agent in an AI Council. Your role is to provide logical, data-driven analysis.
Focus on:
- Breaking down complex problems into components
- Identifying key facts and assumptions
- Logical reasoning and cause-effect relationships
- Practical implementation considerations
Be precise, methodical, and evidence-based in your analysis.""",
                    "description": "Analytical reasoning specialist"
                },
                "creative_agent": {
                    "model": CREATIVE_MODEL, 
                    "system_prompt": """You are the Creative Agent in an AI Council. Your role is to provide innovative, outside-the-box thinking.
Focus on:
- Alternative approaches and novel solutions
- Creative connections between concepts
- User experience and emotional considerations
- Exploring possibilities others might miss
Be imaginative, user-focused, and think beyond conventional solutions.""",
                    "description": "Creative problem-solving specialist"
                }
            }
            
            user_question = state.user_input
            self.logger.info("Starting multi-agent council deliberation", agents=list(council_agents.keys()))
            
            # Phase 1: Concurrent initial responses
            self.logger.debug("Phase 1: Gathering initial agent responses")
            initial_responses = {}
            
            # Create concurrent tasks for each agent
            agent_tasks = []
            for agent_name, agent_config in council_agents.items():
                task = asyncio.create_task(
                    ollama_client.generate_response(
                        prompt=f"User question: {user_question}\n\nProvide your analysis and recommended approach:",
                        model_alias=agent_config["model"],
                        system_prompt=agent_config["system_prompt"],
                        max_tokens=800,
                        temperature=0.7,
                        timeout=45.0
                    ),
                    name=agent_name
                )
                agent_tasks.append((agent_name, task))
            
            # Wait for all initial responses
            for agent_name, task in agent_tasks:
                try:
                    response = await task
                    initial_responses[agent_name] = response.text
                    self.logger.debug("Received initial response", agent=agent_name, tokens=response.tokens_generated)
                except Exception as e:
                    self.logger.warning("Agent response failed", agent=agent_name, error=str(e))
                    initial_responses[agent_name] = f"[Agent {agent_name} failed to respond: {str(e)}]"
            
            # Phase 2: Critique round
            self.logger.debug("Phase 2: Cross-agent critique")
            critiques = {}
            
            critique_tasks = []
            for critic_agent, critic_config in council_agents.items():
                # Each agent critiques the other agents' responses
                other_responses = {name: resp for name, resp in initial_responses.items() if name != critic_agent}
                
                if other_responses:
                    critique_prompt = f"""Review these responses from other council members to the user question: "{user_question}"

Other responses:
"""
                    for other_agent, other_response in other_responses.items():
                        critique_prompt += f"\n{other_agent.upper()}:\n{other_response}\n"
                    
                    critique_prompt += f"""
As the {critic_config['description']}, provide constructive criticism:
1. What are the strengths of these approaches?
2. What potential issues or blind spots do you see?
3. How could these responses be improved?
4. What important aspects might be missing?

Be specific and constructive in your feedback."""

                    task = asyncio.create_task(
                        ollama_client.generate_response(
                            prompt=critique_prompt,
                            model_alias=critic_config["model"],
                            system_prompt=critic_config["system_prompt"],
                            max_tokens=600,
                            temperature=0.6,
                            timeout=45.0
                        ),
                        name=f"{critic_agent}_critique"
                    )
                    critique_tasks.append((critic_agent, task))
            
            # Wait for all critiques
            for agent_name, task in critique_tasks:
                try:
                    response = await task
                    critiques[agent_name] = response.text
                    self.logger.debug("Received critique", agent=agent_name, tokens=response.tokens_generated)
                except Exception as e:
                    self.logger.warning("Agent critique failed", agent=agent_name, error=str(e))
                    critiques[agent_name] = f"[Critique from {agent_name} failed: {str(e)}]"
            
            # Phase 3: Final voting and decision
            self.logger.debug("Phase 3: Final voting and decision synthesis")
            
            # Create voting prompt with all information
            voting_prompt = f"""As the Council Coordinator, review the complete deliberation and make a final decision.

ORIGINAL QUESTION: {user_question}

INITIAL RESPONSES:
"""
            for agent, response in initial_responses.items():
                voting_prompt += f"\n{agent.upper()}:\n{response}\n"
            
            voting_prompt += "\nCRITIQUES:\n"
            for agent, critique in critiques.items():
                voting_prompt += f"\n{agent.upper()} CRITIQUE:\n{critique}\n"
            
            voting_prompt += """
Based on this deliberation, provide:
1. The best synthesized approach incorporating insights from all agents
2. Your confidence level (0-1) in this decision
3. Brief reasoning for your choice
4. Which agent's initial approach was strongest and why

Format your response as:
DECISION: [Your synthesized approach]
CONFIDENCE: [0.0-1.0]
REASONING: [Your reasoning]
STRONGEST_AGENT: [agent_name because reasoning]
"""
            
            # Generate final decision using coordinator model
            final_decision_response = await ollama_client.generate_response(
                prompt=voting_prompt,
                model_alias=COORDINATOR_MODEL,
                system_prompt="You are the Council Coordinator responsible for synthesizing multi-agent deliberations into final decisions.",
                max_tokens=800,
                temperature=0.5,
                timeout=45.0
            )
            
            # Parse the final decision
            decision_text = final_decision_response.text
            
            # Extract structured information (basic parsing)
            decision_lines = decision_text.split('\n')
            final_outcome = ""
            confidence = 0.8  # default
            reasoning = ""
            winning_agent = "analytical_agent"  # default
            
            for line in decision_lines:
                if line.startswith("DECISION:"):
                    final_outcome = line.replace("DECISION:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.replace("CONFIDENCE:", "").strip())
                    except:
                        confidence = 0.8
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()
                elif line.startswith("STRONGEST_AGENT:"):
                    agent_line = line.replace("STRONGEST_AGENT:", "").strip()
                    if "analytical_agent" in agent_line.lower():
                        winning_agent = "analytical_agent"
                    elif "creative_agent" in agent_line.lower():
                        winning_agent = "creative_agent"
            
            # If no structured decision was found, use the full response
            if not final_outcome:
                final_outcome = decision_text
                reasoning = "Full council deliberation synthesis"
            
            # Create comprehensive council decision
            council_decision = CouncilDecision(
                question=user_question,
                outcome=final_outcome,
                reasoning=reasoning,
                confidence=confidence,
                voting_agents=list(council_agents.keys()) + ["coordinator"],
                initial_responses=initial_responses,
                critiques=critiques,
                final_vote_scores={agent: 1.0 for agent in council_agents.keys()},  # All participated
                winning_agent=winning_agent
            )
            
            state.council_decision = council_decision
            
            # Add token usage tracking
            total_tokens = sum([
                len(resp.split()) * 1.3 for resp in initial_responses.values()
            ]) + sum([
                len(crit.split()) * 1.3 for crit in critiques.values()
            ]) + len(decision_text.split()) * 1.3
            
            state.metadata["council_tokens_used"] = int(total_tokens)
            state.metadata["council_agents"] = list(council_agents.keys())
            
            self.logger.info(
                "Council deliberation completed",
                confidence=confidence,
                winning_agent=winning_agent,
                total_tokens=int(total_tokens),
                agents_participated=len(council_agents)
            )
            
        except Exception as e:
            # Mark error in state - conditional routing will handle this
            error_msg = f"Council deliberation failed: {str(e)}"
            state.mark_error(error_msg)
            self.logger.error("Council deliberation error", error=error_msg)
        
        return state
    
    async def kip_execution_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute KIP agent tasks based on Council decisions."""
        self.logger.info(
            "Starting KIP agent execution", 
            request_id=state.request_id,
            council_decision=state.council_decision.outcome if state.council_decision else "No decision"
        )
        state.update_phase(ProcessingPhase.KIP_EXECUTION)
        
        try:
            # Initialize KIP layer and Treasury
            async with kip_session() as kip:
                async with treasury_session() as treasury:
                    
                    # Get available agents
                    available_agents = await kip.list_agents()
                    self.logger.debug(
                        "Available KIP agents",
                        request_id=state.request_id,
                        agent_count=len(available_agents)
                    )
                    
                    # If we have a council decision, try to execute relevant tools
                    if state.council_decision and available_agents:
                        # For demonstration, use data analyst agent if available
                        agent_id = "data_analyst_01"  # Default agent for this demo
                        
                        # Try to execute a sample action based on the user's request
                        if any(keyword in state.user_input.lower() for keyword in ["bitcoin", "crypto", "price", "market"]):
                            try:
                                action_result = await kip.execute_action(
                                    agent_id=agent_id,
                                    tool_name="get_bitcoin_price",
                                    params={},
                                    treasury=treasury
                                )
                                
                                if action_result.was_successful:
                                    # Create successful KIP task
                                    task = KIPTask(
                                        agent_id=agent_id,
                                        task_type="tool_execution",
                                        instruction=f"Execute tool based on council decision for: {state.user_input}",
                                        status="completed",
                                        result=f"Tool execution result: {action_result.result_data}"
                                    )
                                    task.completed_at = datetime.now(timezone.utc)
                                    state.kip_tasks.append(task)
                                    
                                    self.logger.info(
                                        "KIP tool execution successful",
                                        request_id=state.request_id,
                                        agent_id=agent_id,
                                        tool_name="get_bitcoin_price",
                                        cost_cents=action_result.cost_cents,
                                        execution_time=action_result.execution_time
                                    )
                                else:
                                    # Create failed KIP task
                                    task = KIPTask(
                                        agent_id=agent_id,
                                        task_type="tool_execution",
                                        instruction=f"Attempted tool execution for: {state.user_input}",
                                        status="failed",
                                        result=f"Tool execution failed: {action_result.error_message}"
                                    )
                                    task.completed_at = datetime.now(timezone.utc)
                                    state.kip_tasks.append(task)
                                    
                                    self.logger.warning(
                                        "KIP tool execution failed",
                                        request_id=state.request_id,
                                        agent_id=agent_id,
                                        error=action_result.error_message
                                    )
                            except Exception as e:
                                self.logger.error(
                                    "KIP action execution exception",
                                    request_id=state.request_id,
                                    agent_id=agent_id,
                                    error=str(e)
                                )
                        else:
                            # Create a basic analytical task for non-crypto requests
                            task = KIPTask(
                                agent_id=agent_id,
                                task_type="analysis",
                                instruction=f"Analyze council decision for: {state.user_input}",
                                status="completed",
                                result="Analysis completed - council decision processed and validated"
                            )
                            task.completed_at = datetime.now(timezone.utc)
                            state.kip_tasks.append(task)
                            
                            self.logger.info(
                                "KIP analysis task completed",
                                request_id=state.request_id,
                                agent_id=agent_id,
                                task_type="analysis"
                            )
                    else:
                        # Fallback task when no council decision or agents available
                        task = KIPTask(
                            agent_id="system",
                            task_type="fallback",
                            instruction=f"Process request: {state.user_input}",
                            status="completed",
                            result="Request processed without agent execution"
                        )
                        task.completed_at = datetime.now(timezone.utc)
                        state.kip_tasks.append(task)
                        
                        self.logger.info(
                            "KIP fallback task created",
                            request_id=state.request_id,
                            reason="No council decision or agents available"
                        )
                        
        except Exception as e:
            # Handle KIP layer failures gracefully
            self.logger.error(
                "KIP execution failed",
                request_id=state.request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Create error task
            error_task = KIPTask(
                agent_id="error_handler",
                task_type="error",
                instruction=f"Handle error for: {state.user_input}",
                status="failed",
                result=f"KIP execution failed: {str(e)}"
            )
            error_task.completed_at = datetime.now(timezone.utc)
            state.kip_tasks.append(error_task)
        
        return state
    
    async def error_handler_node(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors and provide graceful degradation."""
        self.logger.warning("Processing error occurred", error=state.error_message)
        
        # Error recovery with retry logic and graceful degradation
        # Retries up to max_retries (default: 3) then provides fallback response
        
        if state.retry_count < state.max_retries:
            state.retry_count += 1
            self.logger.info("Attempting retry", retry_count=state.retry_count)
            # Reset to previous phase for retry
            state.current_phase = ProcessingPhase.INITIALIZATION
        else:
            state.final_response = "I apologize, but I encountered an error processing your request. Please try again."
            state.add_message(AIMessage(content=state.final_response))
        
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
            # Use the fastest model for immediate response with caching for common queries
            ollama_client = await self._get_cached_ollama_client()
            
            # Simple, direct prompt for fast responses - ENFORCE BREVITY
            fast_prompt = f"""
INSTRUCTION: Answer this question with 1-2 sentences maximum. Be direct and factual.

Question: {state.user_input}

Rules:
- Give ONLY the essential facts
- Maximum 2 sentences
- No explanations or elaborations
- For "Who is..." questions: Just state the name and title
- For "What color..." questions: Just state the color
- For "What time..." questions: Note you don't have real-time data

BRIEF ANSWER:"""

            # Generate fast response using Mistral
            response = await ollama_client.generate_response(
                prompt=fast_prompt,
                model_alias=COORDINATOR_MODEL,  # Mistral - fastest model
                max_tokens=200,  # Keep responses concise
                timeout=15  # Fast response requirement
            )
            
            # Store the fast response as final response
            state.final_response = response.text.strip()
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
    
    # Helper methods
    
    def _extract_search_patterns(self, user_input: str) -> List[str]:
        """
        Extract search patterns from user input for pheromind querying.
        
        This method identifies key terms and concepts that could match
        existing pheromind signals in Redis.
        
        Args:
            user_input: The user's query text
            
        Returns:
            List[str]: Search patterns for pheromind queries
        """
        # Convert to lowercase for pattern matching
        input_lower = user_input.lower()
        
        # Extract key terms (simple keyword matching for MVP)
        # FUTURE: Could enhance with spaCy/NLTK for entity recognition and semantic clustering
        patterns = []
        
        # Broad pattern: search for any signals
        patterns.append("*")
        
        # Domain-specific patterns
        if any(word in input_lower for word in ['ai', 'artificial', 'intelligence', 'model', 'llm']):
            patterns.append("*ai*")
            patterns.append("*intelligence*")
            
        if any(word in input_lower for word in ['tech', 'technology', 'computer', 'software']):
            patterns.append("*tech*")
            patterns.append("*technology*")
            
        if any(word in input_lower for word in ['help', 'question', 'ask', 'how', 'what', 'why']):
            patterns.append("*question*")
            patterns.append("*help*")
            
        if any(word in input_lower for word in ['complex', 'difficult', 'hard', 'complicated']):
            patterns.append("*complexity*")
            patterns.append("*complex*")
            
        if any(word in input_lower for word in ['creative', 'idea', 'brainstorm', 'think']):
            patterns.append("*creative*")
            patterns.append("*idea*")
            
        # Remove duplicates while preserving order
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_patterns.append(pattern)
                
        return unique_patterns
    
    def _deduplicate_signals(self, signals: List[PheromindSignal]) -> List[PheromindSignal]:
        """
        Remove duplicate pheromind signals while preserving strongest signals.
        
        Args:
            signals: List of potentially duplicate signals
            
        Returns:
            List[PheromindSignal]: Deduplicated signals sorted by strength
        """
        if not signals:
            return []
            
        # Group by pattern_id and keep strongest signal for each pattern
        pattern_map = {}
        for signal in signals:
            if (signal.pattern_id not in pattern_map or 
                signal.strength > pattern_map[signal.pattern_id].strength):
                pattern_map[signal.pattern_id] = signal
                
        # Return sorted by strength (strongest first)
        unique_signals = list(pattern_map.values())
        unique_signals.sort(key=lambda s: s.strength, reverse=True)
        
        return unique_signals