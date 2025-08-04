#!/usr/bin/env python3
"""
Orchestrator State Machine - LangGraph Construction and Routing

This module handles the construction of the LangGraph state machine that
coordinates the 3-layer cognitive architecture. It's designed for modularity
so we can easily swap out processing nodes as AI frameworks evolve.

The state machine flow:
START → Initialize → Pheromind → Council → KIP → Synthesize → END
"""

import structlog
from typing import TYPE_CHECKING

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from .models import OrchestratorState

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .orchestrator import UserFacingOrchestrator


class StateMachineBuilder:
    """
    Builds and manages the LangGraph state machine for cognitive processing.
    
    This class is separated to enable easy modification of the state machine
    structure without touching the main orchestrator logic.
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize the state machine builder.
        
        Args:
            orchestrator: The orchestrator instance that provides the processing nodes
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger("StateMachine")
    
    def build_graph(self) -> CompiledStateGraph:
        """
        Constructs the Smart Router LangGraph state machine for cognitive processing.
        
        The new Smart Router architecture uses intent classification to route requests
        to the appropriate cognitive layer:
        
        START → Initialize → Smart Triage → [Route by Intent] → Response Synthesis → END
        
        Routing Logic:
        - exploratory_task → Pheromind (pattern discovery)
        - action_task → KIP (direct execution)
        - complex_reasoning_task → Council (multi-agent deliberation) 
        - simple_query_task → Fast Response (immediate answer)
        
        Returns:
            CompiledStateGraph: Ready-to-use Smart Router state machine
        """
        # Create the state graph with context_schema to avoid deprecated warnings
        from typing import Dict, Any
        graph_builder = StateGraph(OrchestratorState, config_schema=Dict[str, Any])
        
        # Add nodes for Smart Router architecture
        graph_builder.add_node("initialize", self.orchestrator._initialize_node)
        graph_builder.add_node("smart_triage", self.orchestrator._smart_triage_node)
        graph_builder.add_node("pheromind_scan", self.orchestrator._pheromind_scan_node)
        graph_builder.add_node("council_deliberation", self.orchestrator._council_deliberation_node)
        graph_builder.add_node("kip_execution", self.orchestrator._kip_execution_node)
        graph_builder.add_node("fast_response", self.orchestrator._fast_response_node)
        graph_builder.add_node("response_synthesis", self.orchestrator._response_synthesis_node)
        graph_builder.add_node("error_handler", self.orchestrator._error_handler_node)
        
        # Define the entry point
        graph_builder.add_edge(START, "initialize")
        
        # Initialize → Smart Triage (Central Nervous System)
        graph_builder.add_conditional_edges(
            "initialize",
            self._route_from_initialize,
            {
                "smart_triage": "smart_triage",
                "error_handler": "error_handler"
            }
        )
        
        # Smart Triage → Route by Intent (The Core Intelligence Routing)
        graph_builder.add_conditional_edges(
            "smart_triage",
            self._route_from_smart_triage,
            {
                "pheromind_scan": "pheromind_scan",         # exploratory_task
                "kip_execution": "kip_execution",           # action_task
                "council_deliberation": "council_deliberation", # complex_reasoning_task
                "fast_response": "fast_response",           # simple_query_task
                "error_handler": "error_handler"
            }
        )
        
        # All cognitive paths route to response synthesis
        graph_builder.add_conditional_edges(
            "pheromind_scan", 
            self._route_from_pheromind,
            {
                "response_synthesis": "response_synthesis",
                "error_handler": "error_handler"
            }
        )
        
        graph_builder.add_conditional_edges(
            "council_deliberation",
            self._route_from_council,
            {
                "response_synthesis": "response_synthesis", 
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
        
        # Fast response goes directly to END (already has final response)
        graph_builder.add_conditional_edges(
            "fast_response",
            self._route_from_fast_response,
            {
                END: END,
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
        compiled_graph = graph_builder.compile()
        self.logger.debug("Smart Router LangGraph state machine compiled successfully with intelligent routing")
        return compiled_graph
    
    # Conditional routing functions for error handling
    
    def _route_from_initialize(self, state: OrchestratorState) -> str:
        """Route from initialize node - check for errors or continue to smart triage."""
        if state.error_message:
            self.logger.warning("Error detected in initialize phase, routing to error handler")
            return "error_handler"
        return "smart_triage"
    
    def _route_from_smart_triage(self, state: OrchestratorState) -> str:
        """
        Smart Router - Central Nervous System routing logic.
        
        Routes requests to appropriate cognitive layer based on intent classification:
        - exploratory_task → Pheromind (pattern discovery)
        - action_task → KIP (direct execution)
        - complex_reasoning_task → Council (multi-agent deliberation)
        - simple_query_task → Fast Response (immediate answer)
        """
        if state.error_message:
            self.logger.warning("Error detected in smart triage phase, routing to error handler")
            return "error_handler"
        
        # Import here to avoid circular imports
        from .models import TaskIntent
        
        intent = state.routing_intent
        
        if intent == TaskIntent.EXPLORATORY_TASK:
            self.logger.info("Smart Router: Routing to Pheromind for pattern discovery", intent=intent.value)
            return "pheromind_scan"
        elif intent == TaskIntent.ACTION_TASK:
            self.logger.info("Smart Router: Routing to KIP for direct execution", intent=intent.value)
            return "kip_execution"
        elif intent == TaskIntent.COMPLEX_REASONING_TASK:
            self.logger.info("Smart Router: Routing to Council for deliberation", intent=intent.value)
            return "council_deliberation"
        elif intent == TaskIntent.SIMPLE_QUERY_TASK:
            self.logger.info("Smart Router: Routing to Fast Response for immediate answer", intent=intent.value)
            return "fast_response"
        else:
            # Default fallback to council for safety
            self.logger.warning("Smart Router: Unknown intent, defaulting to Council", intent=intent)
            return "council_deliberation"
    
    def _route_from_pheromind(self, state: OrchestratorState) -> str:
        """Route from pheromind_scan node - check for errors or continue to response synthesis."""
        if state.error_message:
            self.logger.warning("Error detected in pheromind phase, routing to error handler")
            return "error_handler"
        return "response_synthesis"
    
    def _route_from_council(self, state: OrchestratorState) -> str:
        """Route from council_deliberation node - check for errors or continue to response synthesis."""
        if state.error_message:
            self.logger.warning("Error detected in council phase, routing to error handler")
            return "error_handler"
        return "response_synthesis"
    
    def _route_from_kip(self, state: OrchestratorState) -> str:
        """Route from kip_execution node - check for errors or continue to response synthesis."""
        if state.error_message:
            self.logger.warning("Error detected in KIP phase, routing to error handler")
            return "error_handler"
        return "response_synthesis"
    
    def _route_from_fast_response(self, state: OrchestratorState) -> str:
        """Route from fast_response node - check for errors or go directly to END."""
        if state.error_message:
            self.logger.warning("Error detected in fast response phase, routing to error handler")
            return "error_handler"
        # Fast response already has final_response, go directly to END
        return END
    
    def _route_from_response_synthesis(self, state: OrchestratorState) -> str:
        """Route from response_synthesis node - check for errors or end processing."""
        if state.error_message:
            self.logger.warning("Error detected in response synthesis phase, routing to error handler")
            return "error_handler"
        return END