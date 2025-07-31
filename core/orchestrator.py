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
from typing import Any, Dict, List, Optional, Union, Literal, AsyncGenerator
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

import structlog

# Import Ollama client for LLM integration
from clients.ollama_client import get_ollama_client, LLMResponse

# Import Pheromind layer for ambient intelligence
from core.pheromind import PheromindLayer, PheromindSignal, pheromind_session

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


class StreamEventType(str, Enum):
    """
    Types of events that can be streamed during processing.
    
    This enables real-time streaming of the AI Council's deliberation process,
    essential for future voice capabilities where low-latency response is critical.
    """
    PHASE_UPDATE = "phase_update"         # Phase transition event
    TOKEN = "token"                       # Individual token being generated
    AGENT_START = "agent_start"          # Agent begins responding
    AGENT_COMPLETE = "agent_complete"    # Agent completes response
    FINAL_RESPONSE = "final_response"    # Final complete response
    ERROR = "error"                      # Error during processing


class StreamEvent(BaseModel):
    """
    Represents a streaming event during AI Council processing.
    
    This enables token-by-token streaming for natural voice interactions
    and real-time visibility into the multi-agent deliberation process.
    """
    event_type: StreamEventType = Field(description="Type of streaming event")
    content: str = Field(description="Event content (token, message, etc.)")
    phase: Optional[ProcessingPhase] = Field(default=None, description="Current processing phase")
    agent: Optional[str] = Field(default=None, description="Agent generating content (if applicable)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = Field(default=None, description="Request ID for tracking")


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
    
    async def process_request_stream(
        self, 
        user_input: str, 
        conversation_id: Optional[ConversationID] = None
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
        if not self._initialized or not self.graph:
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
                content="🔍 Initializing request processing...",
                phase=ProcessingPhase.INITIALIZATION,
                request_id=request_id,
                metadata={"input_length": len(user_input)}
            )
            
            # Yield pheromind scanning event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🧠 Pheromind scanning for ambient patterns...",
                phase=ProcessingPhase.PHEROMIND_SCAN,
                request_id=request_id
            )
            
            # Yield council deliberation start event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="⚖️ AI Council beginning multi-agent deliberation...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id
            )
            
            # Process through council deliberation with streaming
            async for event in self._stream_council_deliberation(user_input, request_id):
                yield event
            
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
        
        # Extract key terms (simple approach for MVP)
        # TODO: Enhance with NLP-based keyword extraction in future iterations
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
    
    async def _stream_council_deliberation(
        self, 
        user_input: str, 
        request_id: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream the council deliberation process with real-time token generation.
        
        This method handles the multi-agent reasoning process while streaming
        the final response token-by-token for immediate voice/UI consumption.
        
        Args:
            user_input: The user's input to process
            request_id: Request ID for tracking
            
        Yields:
            StreamEvent objects for agent updates and tokens
        """
        try:
            # Initialize Ollama client
            ollama_client = get_ollama_client()
            
            if not await ollama_client.health_check():
                raise Exception("Ollama service is not available")
            
            # Define council agents
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
            
            # Phase 1: Concurrent initial responses (FAST multi-agent processing)
            self.logger.debug("Phase 1: Gathering concurrent agent responses")
            initial_responses = {}
            
            # Send start notifications for all agents
            for agent_name in council_agents.keys():
                yield StreamEvent(
                    event_type=StreamEventType.AGENT_START,
                    content=f"🤖 {agent_name} analyzing concurrently...",
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    agent=agent_name,
                    request_id=request_id
                )
            
            # Create concurrent tasks for ALL agents (this is the key fix!)
            agent_tasks = []
            for agent_name, agent_config in council_agents.items():
                task = asyncio.create_task(
                    ollama_client.generate_response(
                        prompt=f"User question: {user_input}\n\nProvide your analysis and recommended approach:",
                        model_alias=agent_config["model"],
                        system_prompt=agent_config["system_prompt"],
                        max_tokens=600,
                        temperature=0.7,
                        timeout=30.0
                    ),
                    name=agent_name
                )
                agent_tasks.append((agent_name, task))
            
            # Wait for all concurrent responses and stream completion events
            for agent_name, task in agent_tasks:
                try:
                    response = await task
                    if response.success:
                        initial_responses[agent_name] = response.text
                        yield StreamEvent(
                            event_type=StreamEventType.AGENT_COMPLETE,
                            content=f"✅ {agent_name} analysis complete ({response.tokens_generated} tokens)",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"tokens": response.tokens_generated, "generation_time": response.generation_time}
                        )
                    else:
                        initial_responses[agent_name] = f"[{agent_name} failed to respond]"
                        yield StreamEvent(
                            event_type=StreamEventType.ERROR,
                            content=f"❌ {agent_name} failed to respond",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"error": response.error}
                        )
                except Exception as e:
                    initial_responses[agent_name] = f"[{agent_name} failed to respond: {str(e)}]"
                    yield StreamEvent(
                        event_type=StreamEventType.ERROR,
                        content=f"❌ {agent_name} exception: {str(e)}",
                        phase=ProcessingPhase.COUNCIL_DELIBERATION,
                        agent=agent_name,
                        request_id=request_id,
                        metadata={"error": str(e)}
                    )
            
            # Phase 2: Cross-Agent Critique Round (NEW!)
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🤝 Phase 2: Cross-agent critique round beginning...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id
            )
            
            critiques = {}
            
            # Send critique start notifications for all agents
            for agent_name in council_agents.keys():
                yield StreamEvent(
                    event_type=StreamEventType.AGENT_START,
                    content=f"🔍 {agent_name} critiquing other agents' responses...",
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    agent=agent_name,
                    request_id=request_id
                )
            
            # Create concurrent critique tasks for ALL agents
            critique_tasks = []
            for critic_agent, critic_config in council_agents.items():
                # Each agent critiques the other agents' responses
                other_responses = {name: resp for name, resp in initial_responses.items() if name != critic_agent}
                
                if other_responses:
                    critique_prompt = f"""Review these responses from other council members to the user question: "{user_input}"

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
            
            # Wait for all concurrent critiques and stream completion events
            for agent_name, task in critique_tasks:
                try:
                    response = await task
                    if response.success:
                        critiques[agent_name] = response.text
                        yield StreamEvent(
                            event_type=StreamEventType.AGENT_COMPLETE,
                            content=f"✅ {agent_name} critique complete ({response.tokens_generated} tokens)",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"tokens": response.tokens_generated, "generation_time": response.generation_time}
                        )
                    else:
                        critiques[agent_name] = f"[Critique from {agent_name} failed]"
                        yield StreamEvent(
                            event_type=StreamEventType.ERROR,
                            content=f"❌ {agent_name} critique failed",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"error": response.error}
                        )
                except Exception as e:
                    critiques[agent_name] = f"[Critique from {agent_name} failed: {str(e)}]"
                    yield StreamEvent(
                        event_type=StreamEventType.ERROR,
                        content=f"❌ {agent_name} critique exception: {str(e)}",
                        phase=ProcessingPhase.COUNCIL_DELIBERATION,
                        agent=agent_name,
                        request_id=request_id,
                        metadata={"error": str(e)}
                    )
            
            # Phase 3: Enhanced Final Synthesis with Critiques
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🧠 Phase 3: Council Coordinator synthesizing with critiques...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id
            )
            
            yield StreamEvent(
                event_type=StreamEventType.AGENT_START,
                content="🧠 Council Coordinator synthesizing final response with all perspectives...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                agent="coordinator",
                request_id=request_id
            )
            
            # Create enhanced synthesis prompt with critiques
            synthesis_prompt = f"""As the Council Coordinator, review the complete deliberation and provide the best possible final response.

ORIGINAL QUESTION: {user_input}

INITIAL AGENT RESPONSES:
"""
            for agent, response in initial_responses.items():
                synthesis_prompt += f"\n{agent.upper()}:\n{response}\n"
            
            synthesis_prompt += "\nAGENT CRITIQUES:\n"
            for agent, critique in critiques.items():
                synthesis_prompt += f"\n{agent.upper()} CRITIQUE:\n{critique}\n"
            
            synthesis_prompt += """
Based on this complete deliberation (initial responses AND critiques), synthesize the most accurate, nuanced, and helpful final response. Incorporate the best insights from all perspectives while addressing any valid concerns raised in the critiques. Be comprehensive, accurate, and engaging."""
            
            # Stream the final response token by token
            full_response = ""
            async for token in ollama_client.generate_response_stream(
                prompt=synthesis_prompt,
                model_alias="mistral-council",
                system_prompt="You are the Council Coordinator responsible for synthesizing multi-agent deliberations into final, helpful responses.",
                max_tokens=800,
                temperature=0.6,
                timeout=60.0
            ):
                full_response += token
                yield StreamEvent(
                    event_type=StreamEventType.TOKEN,
                    content=token,
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    agent="coordinator",
                    request_id=request_id
                )
            
            # Final response complete
            yield StreamEvent(
                event_type=StreamEventType.FINAL_RESPONSE,
                content=full_response,
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                agent="coordinator",
                request_id=request_id,
                metadata={
                    "agents_participated": list(council_agents.keys()),
                    "response_length": len(full_response),
                    "total_tokens": len(full_response.split()) * 1.3  # Rough estimate
                }
            )
            
        except Exception as e:
            self.logger.error("Council deliberation streaming failed", error=str(e))
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                content=f"Council deliberation failed: {str(e)}",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id,
                metadata={"error": str(e)}
            )
    
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