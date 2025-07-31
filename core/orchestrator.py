#!/usr/bin/env python3
"""
User-Facing Orchestrator for Hybrid AI Council
==============================================

This module implements the central coordination layer that orchestrates
the 3-layer cognitive architecture:
- Pheromind: Ambient pattern detection and processing
- Council: Deliberative decision-making layer  
- KIP: Knowledge-Incentive Protocol agent execution

The orchestrator uses LangGraph to manage state transitions and coordinate
between these layers in response to user interactions.

Architecture Flow:
User Input → Pheromind Processing → Council Deliberation → KIP Execution → Response
"""

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

import structlog

# Import Ollama client for LLM integration
from clients.ollama_client import get_ollama_client, LLMResponse

# Type aliases for clarity
RequestID = str
AgentID = str
ConversationID = str


class ProcessingPhase(str, Enum):
    """
    Enumeration of processing phases in the cognitive architecture.
    
    Each phase represents a distinct stage in the AI's decision-making process,
    following the Hybrid AI Council's 3-layer approach.
    """
    INITIALIZATION = "initialization"      # Initial request processing
    PHEROMIND_SCAN = "pheromind_scan"     # Ambient pattern detection
    COUNCIL_DELIBERATION = "council_deliberation"  # Multi-agent decision making
    KIP_EXECUTION = "kip_execution"       # Agent task execution
    RESPONSE_SYNTHESIS = "response_synthesis"  # Final response generation
    COMPLETED = "completed"               # Processing complete
    ERROR = "error"                      # Error state


class PheromindSignal(BaseModel):
    """
    Represents a pheromone signal detected during ambient processing.
    
    Pheromones have a 12-second TTL and influence decision-making patterns
    across the cognitive architecture.
    """
    pattern_id: str = Field(description="Unique identifier for the detected pattern")
    strength: float = Field(ge=0.0, le=1.0, description="Signal strength (0-1)")
    source_agent: str = Field(description="Agent that generated this pheromone")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(description="When this pheromone expires (12s TTL)")
    content: str = Field(description="Pattern description or content")


class CouncilDecision(BaseModel):
    """
    Represents a decision made by the Council layer.
    
    The Council evaluates input using multiple perspectives and reaches
    consensus decisions that guide KIP agent execution.
    """
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str = Field(description="The question or problem being decided")
    outcome: str = Field(description="The decision reached by the council")
    reasoning: str = Field(description="Explanation of the decision rationale")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in decision (0-1)")
    voting_agents: List[str] = Field(default_factory=list, description="Agents that participated")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Added fields for multi-agent deliberation
    initial_responses: Dict[str, str] = Field(default_factory=dict, description="Initial agent responses")
    critiques: Dict[str, str] = Field(default_factory=dict, description="Agent critiques of others")
    final_vote_scores: Dict[str, float] = Field(default_factory=dict, description="Final voting scores")
    winning_agent: Optional[str] = Field(default=None, description="Agent whose response was chosen")


class KIPTask(BaseModel):
    """
    Represents a task assigned to a KIP (Knowledge-Incentive Protocol) agent.
    
    KIP agents execute specific tasks based on Council decisions and
    report back with results.
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = Field(description="ID of the assigned KIP agent")
    task_type: str = Field(description="Type of task (e.g., 'research', 'execute', 'analyze')")
    instruction: str = Field(description="Detailed task instruction")
    priority: int = Field(ge=1, le=10, default=5, description="Task priority (1-10)")
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    result: Optional[str] = Field(default=None, description="Task execution result")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class OrchestratorState(BaseModel):
    """
    Central state model for the UserFacingOrchestrator.
    
    This state is passed between all nodes in the LangGraph state machine,
    maintaining context and coordination data throughout the processing pipeline.
    """
    # Request tracking
    request_id: RequestID = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: ConversationID = Field(description="ID of the conversation session")
    user_input: str = Field(description="Original user input message")
    
    # Processing state
    current_phase: ProcessingPhase = ProcessingPhase.INITIALIZATION
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Layer outputs
    pheromind_signals: List[PheromindSignal] = Field(default_factory=list)
    council_decision: Optional[CouncilDecision] = None
    kip_tasks: List[KIPTask] = Field(default_factory=list)
    
    # Messages and responses
    messages: List[BaseMessage] = Field(default_factory=list)
    final_response: Optional[str] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def update_phase(self, new_phase: ProcessingPhase) -> None:
        """Update the current processing phase with timestamp."""
        self.current_phase = new_phase
        self.updated_at = datetime.now(timezone.utc)
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history."""
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_error(self, error: str) -> None:
        """Mark the state as error and record the error message."""
        self.current_phase = ProcessingPhase.ERROR
        self.error_message = error
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class UserFacingOrchestrator:
    """
    Central orchestrator for the Hybrid AI Council system.
    
    This class implements a LangGraph state machine that coordinates the
    3-layer cognitive architecture to process user requests and generate
    intelligent responses.
    
    The orchestrator manages the flow:
    User Input → Pheromind → Council → KIP → Response
    
    Attributes:
        logger: Structured logger for observability
        graph: Compiled LangGraph state machine
        _initialized: Flag indicating if the orchestrator is ready
    """
    
    logger: structlog.stdlib.BoundLogger = field(default_factory=lambda: structlog.get_logger("orchestrator"))
    graph: Optional[CompiledStateGraph] = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)
    
    def __post_init__(self) -> None:
        """Initialize the orchestrator after dataclass creation."""
        self.logger = self.logger.bind(component="UserFacingOrchestrator")
        self._build_graph()
        self._initialized = True
        self.logger.info("UserFacingOrchestrator initialized successfully")
    
    def _build_graph(self) -> None:
        """
        Constructs the LangGraph state machine for cognitive processing.
        
        The graph defines the flow between cognitive layers with robust error handling:
        START → Initialize → Pheromind → Council → KIP → Synthesize → END
        
        Each node uses conditional routing to check for errors and route to error_handler
        if needed, creating a resilient state machine that can fail gracefully.
        """
        # Create the state graph
        graph_builder = StateGraph(OrchestratorState)
        
        # Add nodes for each processing phase
        graph_builder.add_node("initialize", self._initialize_node)
        graph_builder.add_node("pheromind_scan", self._pheromind_scan_node)
        graph_builder.add_node("council_deliberation", self._council_deliberation_node)
        graph_builder.add_node("kip_execution", self._kip_execution_node)
        graph_builder.add_node("response_synthesis", self._response_synthesis_node)
        graph_builder.add_node("error_handler", self._error_handler_node)
        
        # Define the entry point
        graph_builder.add_edge(START, "initialize")
        
        # Define conditional routing for each processing node
        # Each node checks for errors and routes accordingly
        graph_builder.add_conditional_edges(
            "initialize",
            self._route_from_initialize,
            {
                "pheromind_scan": "pheromind_scan",
                "error_handler": "error_handler"
            }
        )
        
        graph_builder.add_conditional_edges(
            "pheromind_scan", 
            self._route_from_pheromind,
            {
                "council_deliberation": "council_deliberation",
                "error_handler": "error_handler"
            }
        )
        
        graph_builder.add_conditional_edges(
            "council_deliberation",
            self._route_from_council,
            {
                "kip_execution": "kip_execution", 
                "error_handler": "error_handler"
            }
        )
        
        graph_builder.add_conditional_edges(
            "kip_execution",
            self._route_from_kip,
            {
                "response_synthesis": "response_synthesis",
                "error_handler": "error_handler"
            }
        )
        
        graph_builder.add_conditional_edges(
            "response_synthesis",
            self._route_from_response_synthesis,
            {
                END: END,
                "error_handler": "error_handler"
            }
        )
        
        # Error handler always routes to END
        graph_builder.add_edge("error_handler", END)
        
        # Compile the graph
        self.graph = graph_builder.compile()
        self.logger.debug("LangGraph state machine compiled successfully with conditional routing")
    
    # Conditional routing functions for error handling
    
    def _route_from_initialize(self, state: OrchestratorState) -> str:
        """Route from initialize node - check for errors or continue to pheromind_scan."""
        if state.error_message:
            self.logger.warning("Error detected in initialize phase, routing to error handler")
            return "error_handler"
        return "pheromind_scan"
    
    def _route_from_pheromind(self, state: OrchestratorState) -> str:
        """Route from pheromind_scan node - check for errors or continue to council_deliberation."""
        if state.error_message:
            self.logger.warning("Error detected in pheromind phase, routing to error handler")
            return "error_handler"
        return "council_deliberation"
    
    def _route_from_council(self, state: OrchestratorState) -> str:
        """Route from council_deliberation node - check for errors or continue to kip_execution."""
        if state.error_message:
            self.logger.warning("Error detected in council phase, routing to error handler")
            return "error_handler"
        return "kip_execution"
    
    def _route_from_kip(self, state: OrchestratorState) -> str:
        """Route from kip_execution node - check for errors or continue to response_synthesis."""
        if state.error_message:
            self.logger.warning("Error detected in KIP phase, routing to error handler")
            return "error_handler"
        return "response_synthesis"
    
    def _route_from_response_synthesis(self, state: OrchestratorState) -> str:
        """Route from response_synthesis node - check for errors or end processing."""
        if state.error_message:
            self.logger.warning("Error detected in response synthesis phase, routing to error handler")
            return "error_handler"
        return END
    
    async def process_request(
        self, 
        user_input: str, 
        conversation_id: Optional[ConversationID] = None
    ) -> OrchestratorState:
        """
        Main entry point for processing user requests.
        
        This method creates the initial state and runs it through the
        complete cognitive processing pipeline.
        
        Args:
            user_input: The user's input message or question
            conversation_id: Optional conversation ID for context
            
        Returns:
            Final orchestrator state with response and processing details
            
        Raises:
            RuntimeError: If the orchestrator is not properly initialized
        """
        if not self._initialized or not self.graph:
            raise RuntimeError("Orchestrator not properly initialized")
        
        # Create initial state
        initial_state = OrchestratorState(
            user_input=user_input,
            conversation_id=conversation_id or str(uuid.uuid4()),
            messages=[HumanMessage(content=user_input)]
        )
        
        request_id = initial_state.request_id
        self.logger = self.logger.bind(request_id=request_id, conversation_id=initial_state.conversation_id)
        self.logger.info("Processing new user request", user_input_preview=user_input[:100])
        
        try:
            # Execute the state machine
            final_state = await self.graph.ainvoke(initial_state)
            
            # LangGraph returns dict-like object, extract our state
            if hasattr(final_state, 'model_dump'):
                # If it's still a Pydantic model, use it directly
                pass
            else:
                # If it's a dict, convert back to OrchestratorState
                final_state = OrchestratorState.model_validate(final_state)
            
            self.logger.info(
                "Request processing completed",
                final_phase=final_state.current_phase,
                processing_time=(final_state.updated_at - final_state.started_at).total_seconds()
            )
            
            return final_state
            
        except Exception as e:
            self.logger.error("Request processing failed", error=str(e), exc_info=True)
            # Return error state
            initial_state.mark_error(f"Processing failed: {str(e)}")
            return initial_state
    
    # Node implementations (scaffolds for now)
    
    async def _initialize_node(self, state: OrchestratorState) -> OrchestratorState:
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
    
    async def _pheromind_scan_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute Pheromind ambient pattern detection."""
        self.logger.debug("Starting Pheromind ambient scan")
        state.update_phase(ProcessingPhase.PHEROMIND_SCAN)
        
        # TODO: Implement Pheromind integration
        # - Check Redis for existing pheromones
        # - Detect new patterns in user input
        # - Generate pheromone signals
        # - Store in Redis with 12-second TTL
        
        # Placeholder pheromone signal
        from datetime import timedelta
        sample_signal = PheromindSignal(
            pattern_id=f"pattern_{uuid.uuid4()}",
            strength=0.7,
            source_agent="ambient_scanner",
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=12),
            content=f"Detected user intent pattern in: {state.user_input[:50]}..."
        )
        state.pheromind_signals.append(sample_signal)
        
        return state
    
    async def _council_deliberation_node(self, state: OrchestratorState) -> OrchestratorState:
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
            # Initialize Ollama client for LLM inference
            ollama_client = get_ollama_client()
            
            # Check if Ollama is available
            if not await ollama_client.health_check():
                raise Exception("Ollama service is not available")
            
            # Define council agents with different perspectives
            council_agents = {
                "analytical_agent": {
                    "model": "qwen3-council",
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
                    "model": "deepseek-council", 
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
                model_alias="mistral-council",
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
    
    async def _kip_execution_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute KIP agent tasks based on Council decisions."""
        self.logger.debug("Starting KIP agent execution")
        state.update_phase(ProcessingPhase.KIP_EXECUTION)
        
        # TODO: Implement KIP layer
        # - Create tasks based on council decision
        # - Assign to appropriate agents
        # - Execute tasks (research, analysis, etc.)
        # - Collect results
        
        # Placeholder KIP task
        task = KIPTask(
            agent_id="response_generator",
            task_type="generate",
            instruction=f"Generate helpful response for: {state.user_input}",
            status="completed",
            result="Task executed successfully - response ready"
        )
        task.completed_at = datetime.now(timezone.utc)
        state.kip_tasks.append(task)
        
        return state
    
    async def _response_synthesis_node(self, state: OrchestratorState) -> OrchestratorState:
        """Synthesize final response from all processing layers."""
        self.logger.debug("Synthesizing final response")
        state.update_phase(ProcessingPhase.RESPONSE_SYNTHESIS)
        
        # TODO: Implement response synthesis
        # - Combine insights from all layers
        # - Generate coherent response
        # - Apply personality and style
        # - Store conversation in TigerGraph
        
        # Enhanced response synthesis using council decision
        if state.council_decision:
            state.final_response = state.council_decision.outcome
        else:
            # Fallback response
            response_parts = [
                f"Based on my analysis of your request: '{state.user_input}'",
                f"I detected {len(state.pheromind_signals)} ambient patterns,",
                f"completed council deliberation,",
                f"and executed {len(state.kip_tasks)} specialized tasks.",
                "I'm ready to help you with whatever you need!"
            ]
            state.final_response = " ".join(response_parts)
        
        state.add_message(AIMessage(content=state.final_response))
        state.update_phase(ProcessingPhase.COMPLETED)
        
        return state
    
    async def _error_handler_node(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors and provide graceful degradation."""
        self.logger.warning("Processing error occurred", error=state.error_message)
        
        # TODO: Implement error recovery
        # - Attempt retry if within limits
        # - Graceful degradation
        # - User-friendly error messages
        
        if state.retry_count < state.max_retries:
            state.retry_count += 1
            self.logger.info("Attempting retry", retry_count=state.retry_count)
            # Reset to previous phase for retry
            state.current_phase = ProcessingPhase.INITIALIZATION
        else:
            state.final_response = "I apologize, but I encountered an error processing your request. Please try again."
            state.add_message(AIMessage(content=state.final_response))
        
        return state


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
    print(f"Pheromone Signals: {len(result.pheromind_signals)}")
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