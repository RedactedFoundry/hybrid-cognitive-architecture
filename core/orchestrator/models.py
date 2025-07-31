#!/usr/bin/env python3
"""
Orchestrator Models - Data Structures for Cognitive Processing

This module contains all Pydantic models, enums, and data structures
used throughout the orchestrator's 3-layer cognitive architecture.

These models enable plug-and-play modularity as AI frameworks evolve.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

# Import Pheromind signals for state management
from core.pheromind import PheromindSignal

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
    SMART_TRIAGE = "smart_triage"         # Intent classification and routing 
    PHEROMIND_SCAN = "pheromind_scan"     # Ambient pattern detection
    COUNCIL_DELIBERATION = "council_deliberation"  # Multi-agent decision making
    KIP_EXECUTION = "kip_execution"       # Agent task execution
    FAST_RESPONSE = "fast_response"       # Direct response for simple queries
    RESPONSE_SYNTHESIS = "response_synthesis"  # Final response generation
    COMPLETED = "completed"               # Processing complete
    ERROR = "error"                      # Error state


class TaskIntent(str, Enum):
    """
    Intent classification for Smart Router routing decisions.
    
    The central nervous system uses these intents to route requests to the
    appropriate cognitive layer based on complexity and task type.
    """
    EXPLORATORY_TASK = "exploratory_task"     # "Find connections in my notes"
    ACTION_TASK = "action_task"               # "Execute Q2 sales report" 
    COMPLEX_REASONING_TASK = "complex_reasoning_task"  # "Pros and cons of AI in education"
    SIMPLE_QUERY_TASK = "simple_query_task"  # "What time is it?"


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
    routing_intent: Optional[TaskIntent] = None  # Smart Router decision
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