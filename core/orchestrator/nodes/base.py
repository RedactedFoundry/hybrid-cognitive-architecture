#!/usr/bin/env python3
"""
Base Processing Node Class - Shared Infrastructure

This module provides the base class and shared utilities for all cognitive processing nodes.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import structlog

from utils.client_utils import get_cached_ollama_client

from ..models import OrchestratorState

# Type-only imports to avoid circular dependencies  
if TYPE_CHECKING:
    from ..orchestrator import UserFacingOrchestrator


class BaseProcessingNode(ABC):
    """
    Base class for all cognitive processing nodes.
    
    Provides shared infrastructure and utilities used across all cognitive layers.
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize base processing node.
        
        Args:
            orchestrator: The parent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(self.__class__.__name__)
        
    async def _get_cached_ollama_client(self):
        """Get a cached Ollama client for improved performance and cost savings."""
        return await get_cached_ollama_client(self.__class__.__name__)


class CognitiveProcessingNode(BaseProcessingNode):
    """
    Base class for cognitive layer processing nodes.
    
    Provides specialized functionality for nodes that perform LLM-based reasoning.
    """
    
    @abstractmethod
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """
        Process the orchestrator state through this cognitive layer.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            Updated orchestrator state
        """
        pass