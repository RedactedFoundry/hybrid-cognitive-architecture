#!/usr/bin/env python3
"""
Orchestrator Processing Nodes - Modular Cognitive Processing

This module provides a unified interface to the modular cognitive processing nodes.
Each cognitive layer is implemented in separate, focused modules for better maintainability.

The 3-layer cognitive architecture is now cleanly separated:
- Smart Router: Intent classification and routing
- Pheromind: Ambient pattern detection
- Council: Multi-agent deliberation
- KIP: Direct action execution
- Support: Infrastructure and error handling
"""

from typing import TYPE_CHECKING

from .nodes import (
    SmartRouterNode, 
    PheromindNode, 
    CouncilNode, 
    KIPNode, 
    SupportNode,
    SimpleGeneratorVerifierNode
)
from .models import OrchestratorState

# Type-only imports to avoid circular dependencies  
if TYPE_CHECKING:
    from .orchestrator import UserFacingOrchestrator


class ProcessingNodes:
    """
    Processing nodes coordinator for the orchestrator state machine.
    
    This class provides a unified interface to all cognitive processing layers
    while delegating to specialized, modular node implementations.
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize modular processing nodes.
        
        Args:
            orchestrator: The parent orchestrator instance
        """
        self.orchestrator = orchestrator
        
        # Initialize specialized cognitive processing nodes
        self.smart_router = SmartRouterNode(orchestrator)
        self.pheromind = PheromindNode(orchestrator)
        self.council = CouncilNode(orchestrator)
        self.simple_generator_verifier = SimpleGeneratorVerifierNode(orchestrator)  # Constitution v5.4 compliant
        self.kip = KIPNode(orchestrator)
        self.support = SupportNode(orchestrator)
    
    # Delegation methods to maintain API compatibility
    
    async def initialize_node(self, state: OrchestratorState) -> OrchestratorState:
        """Initialize the processing pipeline and validate input."""
        return await self.support.initialize_node(state)
    
    async def smart_triage_node(self, state: OrchestratorState) -> OrchestratorState:
        """Smart Router - Central Nervous System for Intent Classification."""
        return await self.smart_router.smart_triage_node(state)
    
    async def pheromind_scan_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute Pheromind ambient pattern detection."""
        return await self.pheromind.pheromind_scan_node(state)
    
    async def council_deliberation_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute Council-layer multi-agent deliberation."""
        return await self.council.council_deliberation_node(state)
    
    async def kip_execution_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute KIP agent tasks based on Council decisions."""
        return await self.kip.kip_execution_node(state)
    
    async def error_handler_node(self, state: OrchestratorState) -> OrchestratorState:
        """Handle errors and provide graceful degradation."""
        return await self.support.error_handler_node(state)
    
    async def fast_response_node(self, state: OrchestratorState) -> OrchestratorState:
        """Fast Response Path - Direct answers for simple queries."""
        return await self.support.fast_response_node(state)
    
    # Direct access to specialized processors for advanced use cases
    
    async def process_smart_router(self, state: OrchestratorState) -> OrchestratorState:
        """Direct access to Smart Router processing."""
        return await self.smart_router.process(state)
    
    async def process_pheromind(self, state: OrchestratorState) -> OrchestratorState:
        """Direct access to Pheromind processing."""
        return await self.pheromind.process(state)
    
    async def process_council(self, state: OrchestratorState) -> OrchestratorState:
        """Direct access to Council processing."""
        return await self.council.process(state)
    
    async def process_kip(self, state: OrchestratorState) -> OrchestratorState:
        """Direct access to KIP processing."""
        return await self.kip.process(state)