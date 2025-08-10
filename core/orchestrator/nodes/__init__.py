"""
Cognitive Processing Nodes - Modular Architecture

This package contains the modular cognitive processing nodes for the Hybrid AI Council.
Each module represents a different layer of the 3-layer cognitive architecture.
"""

from .base import BaseProcessingNode, CognitiveProcessingNode
from .smart_router_nodes import SmartRouterNode
from .pheromind_nodes import PheromindNode
from .council_nodes import CouncilNode
from .simple_generator_verifier_node import SimpleGeneratorVerifierNode
from .kip_nodes import KIPNode
from .support_nodes import SupportNode

__all__ = [
    'BaseProcessingNode',
    'CognitiveProcessingNode', 
    'SmartRouterNode',
    'PheromindNode',
    'CouncilNode',
    'SimpleGeneratorVerifierNode',
    'KIPNode',
    'SupportNode'
]