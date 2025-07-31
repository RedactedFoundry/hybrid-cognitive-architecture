#!/usr/bin/env python3
"""
Orchestrator Package - Modular 3-Layer Cognitive Architecture

This package implements the central coordination layer for the Hybrid AI Council
using a modular, plug-and-play design that can adapt as AI frameworks evolve.

The orchestrator coordinates:
- Pheromind: Ambient pattern detection and processing
- Council: Deliberative decision-making layer  
- KIP: Knowledge-Incentive Protocol agent execution

Public API exports maintain compatibility with the original monolithic design.
"""

# Export the main orchestrator class and data models
from .orchestrator import UserFacingOrchestrator, example_usage
from .models import (
    ProcessingPhase,
    StreamEventType, 
    StreamEvent,
    CouncilDecision,
    KIPTask,
    OrchestratorState,
    RequestID,
    AgentID,
    ConversationID
)

# Export modular components for advanced usage
from .state_machine import StateMachineBuilder
from .processing_nodes import ProcessingNodes
from .streaming import StreamingProcessor
from .synthesis import ResponseSynthesizer

__all__ = [
    # Main orchestrator class
    "UserFacingOrchestrator",
    
    # Data models and enums
    "ProcessingPhase",
    "StreamEventType",
    "StreamEvent", 
    "CouncilDecision",
    "KIPTask",
    "OrchestratorState",
    
    # Type aliases
    "RequestID",
    "AgentID", 
    "ConversationID",
    
    # Modular components (for advanced usage)
    "StateMachineBuilder",
    "ProcessingNodes",
    "StreamingProcessor", 
    "ResponseSynthesizer",
    
    # Example function
    "example_usage"
]