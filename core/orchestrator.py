#!/usr/bin/env python3
"""
User-Facing Orchestrator for Hybrid AI Council
==============================================

This module provides backward compatibility for the refactored orchestrator.
The actual implementation has been modularized into the orchestrator/ package
for better maintainability and plug-and-play architecture adaptability.

Architecture Flow:
User Input → Pheromind Processing → Council Deliberation → KIP Execution → Response
"""

# Import specific components from the new modular orchestrator package
from .orchestrator import (
    UserFacingOrchestrator,
    ProcessingPhase,
    StreamEventType,
    StreamEvent,
    CouncilDecision,
    KIPTask,
    OrchestratorState,
    RequestID,
    AgentID,
    ConversationID,
    StateMachineBuilder,
    ProcessingNodes,
    StreamingProcessor,
    ResponseSynthesizer,
    example_usage
)