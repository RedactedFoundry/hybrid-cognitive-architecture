# core/kip/__init__.py
"""
KIP (Knowledge-Incentive Protocol) Layer

This package implements the autonomous agent execution layer of the Hybrid AI Council.
It provides economic incentives, tool management, and performance tracking for AI agents.

The KIP Layer consists of:
- Models: Data structures and enums
- Treasury: Economic engine and financial management  
- Agents: Agent lifecycle and genome management
- Tools: Tool registry and execution engine
- Exceptions: Custom error handling
"""

from contextlib import asynccontextmanager
from typing import Optional

# Clean config import
from config import Config

# Import all models and data structures
from .models import (
    # Enums
    AgentStatus,
    AgentFunction,
    TransactionType,
    
    # Core Models
    KIPAgent,
    AgentBudget, 
    Transaction,
    Tool,
    ToolCapability,
    ActionResult,
    
    # Analytics Models
    EconomicAnalytics,
    KIPAnalytics
)

# Import main classes
from .treasury import Treasury, treasury_session, create_treasury
from .agents import AgentManager, create_agent_manager
from .tools import ToolRegistry

# Import exceptions
from .exceptions import (
    KIPLayerError,
    AgentNotFoundError,
    AgentAuthorizationError,
    ToolNotFoundError,
    ToolExecutionError,
    InsufficientFundsError,
    UsageLimitExceededError,
    TreasuryError,
    BudgetNotFoundError,
    TransactionError,
    EmergencyFreezeError,
    ConfigurationError,
    ConnectionError
)


class KIPLayer:
    """
    Main KIP Layer interface that coordinates agents, tools, and treasury.
    
    This class provides a unified interface to the KIP subsystems:
    - Agent management via AgentManager
    - Tool execution via ToolRegistry  
    - Economic tracking via Treasury
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the KIP Layer.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or Config()
        
        # Initialize subsystems
        self.agent_manager = AgentManager(config)
        self.tool_registry = ToolRegistry(config)
        self.treasury = Treasury(config)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.agent_manager._connect()
        await self.treasury._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.agent_manager._disconnect()
        await self.treasury._disconnect()
        
    async def load_agent(self, agent_id: str, force_refresh: bool = False) -> Optional[KIPAgent]:
        """Load an agent's genome."""
        return await self.agent_manager.load_agent(agent_id, force_refresh)
        
    async def list_agents(self, status_filter: Optional[AgentStatus] = None) -> list[KIPAgent]:
        """List all agents."""
        return await self.agent_manager.list_agents(status_filter)
        
    async def execute_action(
        self,
        agent_id: str,
        tool_name: str,
        params: Optional[dict] = None
    ) -> ActionResult:
        """Execute an agent action with economic tracking."""
        return await self.tool_registry.execute_action(
            agent_manager=self.agent_manager,
            treasury=self.treasury,
            agent_id=agent_id,
            tool_name=tool_name,
            params=params
        )
        
    async def get_agent_budget(self, agent_id: str) -> Optional[AgentBudget]:
        """Get an agent's current budget."""
        return await self.treasury.get_budget(agent_id)
        
    async def initialize_agent_budget(
        self,
        agent_id: str,
        seed_amount: Optional[int] = None
    ) -> AgentBudget:
        """Initialize an agent's budget with seed funding."""
        return await self.treasury.initialize_agent_budget(agent_id, seed_amount)
        
    async def get_analytics(self) -> KIPAnalytics:
        """Get comprehensive KIP analytics."""
        return await self.agent_manager.get_analytics()
        
    async def get_economic_analytics(self) -> EconomicAnalytics:
        """Get economic analytics."""
        return await self.treasury.get_economic_analytics()


# Convenience functions
async def create_kip_layer(config: Optional[Config] = None) -> KIPLayer:
    """
    Create and initialize a KIPLayer instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        KIPLayer: Ready-to-use KIP layer instance
    """
    layer = KIPLayer(config)
    await layer.__aenter__()
    return layer


@asynccontextmanager
async def kip_session(config: Optional[Config] = None):
    """
    Async context manager for KIP operations.
    
    Usage:
        async with kip_session() as kip:
            agent = await kip.load_agent("data_analyst_01")
            result = await kip.execute_action("data_analyst_01", "get_bitcoin_price")
    """
    layer = KIPLayer(config)
    try:
        await layer.__aenter__()
        yield layer
    finally:
        await layer.__aexit__(None, None, None)


# Export everything that external modules need
__all__ = [
    # Main Classes
    "KIPLayer",
    "Treasury", 
    "AgentManager",
    "ToolRegistry",
    
    # Models
    "KIPAgent",
    "AgentBudget",
    "Transaction", 
    "Tool",
    "ToolCapability",
    "ActionResult",
    "EconomicAnalytics",
    "KIPAnalytics",
    
    # Enums
    "AgentStatus",
    "AgentFunction", 
    "TransactionType",
    
    # Context Managers
    "kip_session",
    "treasury_session",
    
    # Factory Functions
    "create_kip_layer",
    "create_treasury",
    "create_agent_manager",
    
    # Exceptions
    "KIPLayerError",
    "AgentNotFoundError",
    "AgentAuthorizationError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "InsufficientFundsError",
    "UsageLimitExceededError",
    "TreasuryError",
    "BudgetNotFoundError",
    "TransactionError",
    "EmergencyFreezeError",
    "ConfigurationError",
    "ConnectionError"
]