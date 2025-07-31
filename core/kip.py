# core/kip.py
"""
KIP (Knowledge-Incentive Protocol) Layer - Agent Execution System

This module implements the final layer of the Hybrid AI Council's 3-layer architecture.
The KIP Layer manages autonomous agents that execute specific functions based on their
"genome" (configuration stored in TigerGraph).

The KIP Layer enables:
- Agent lifecycle management (loading, execution, monitoring)
- Tool authorization and capability management
- Action execution with structured results
- Integration with TigerGraph for persistent agent configurations
- Dynamic agent deployment and scaling

Architecture:
KIPAgent (genome in TigerGraph) → Tool Authorization → Action Execution → Result Capture
"""

import json
import asyncio
import uuid
import importlib
from datetime import datetime, timezone, timedelta, date
from typing import List, Optional, Dict, Any, Set, Union, Callable, Awaitable
from enum import Enum
from contextlib import asynccontextmanager
from decimal import Decimal

import pyTigerGraph as tg
import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator
import structlog

from config import Config
from clients.tigervector_client import get_tigergraph_connection


class AgentStatus(str, Enum):
    """Enumeration of KIP Agent statuses."""
    INACTIVE = "inactive"        # Agent exists but not running
    ACTIVE = "active"           # Agent is ready and available  
    BUSY = "busy"               # Agent is currently executing
    ERROR = "error"             # Agent encountered an error
    MAINTENANCE = "maintenance"  # Agent is under maintenance
    RETIRED = "retired"         # Agent is permanently disabled


class AgentFunction(str, Enum):
    """Enumeration of standard KIP Agent functions."""
    DATA_ANALYST = "data_analyst"           # Data analysis and processing
    CONTENT_CREATOR = "content_creator"     # Content generation and editing
    RESEARCHER = "researcher"               # Information gathering and synthesis
    COORDINATOR = "coordinator"             # Multi-agent coordination
    MONITOR = "monitor"                     # System monitoring and alerting
    EXECUTOR = "executor"                   # Task and workflow execution
    SPECIALIST = "specialist"               # Domain-specific expertise
    CUSTOM = "custom"                       # User-defined function


class ToolCapability(BaseModel):
    """Represents a tool that an agent is authorized to use."""
    tool_name: str = Field(description="Name of the tool")
    description: str = Field(description="Tool description and purpose")
    tool_type: str = Field(description="Category/type of tool")
    version: str = Field(description="Tool version")
    authorization_level: str = Field(description="Agent's authorization level for this tool")
    granted_at: datetime = Field(description="When authorization was granted")


class KIPAgent(BaseModel):
    """
    Represents a KIP (Knowledge-Incentive Protocol) Agent.
    
    KIP Agents are autonomous entities with specific functions, stored in TigerGraph
    as their "genome" - the persistent configuration that defines their capabilities,
    authorizations, and operational parameters.
    """
    
    # Core Identity (from TigerGraph KIPAgent vertex)
    agent_id: str = Field(description="Unique identifier for the agent")
    function: AgentFunction = Field(description="Primary function/role of the agent")
    status: AgentStatus = Field(description="Current operational status")
    created_at: datetime = Field(description="When the agent was created")
    
    # Extended Capabilities (enriched from relationships)
    authorized_tools: List[ToolCapability] = Field(default_factory=list, description="Tools this agent can use")
    
    # Operational Metadata
    last_active: Optional[datetime] = Field(default=None, description="Last activity timestamp")
    execution_count: int = Field(default=0, description="Number of times agent has executed")
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Success rate (0-1)")
    average_execution_time: float = Field(default=0.0, description="Average execution time in seconds")
    
    # Configuration Parameters (genome data)
    max_concurrent_tasks: int = Field(default=1, description="Maximum concurrent task execution")
    timeout_seconds: int = Field(default=300, description="Default task timeout in seconds")
    priority_level: int = Field(default=5, ge=1, le=10, description="Agent priority (1=low, 10=high)")
    
    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Ensure agent_id follows naming conventions."""
        if not v or len(v) < 3:
            raise ValueError("agent_id must be at least 3 characters long")
        return v.lower().replace(" ", "_")
        
    @property
    def is_available(self) -> bool:
        """Check if agent is available for task execution."""
        return self.status == AgentStatus.ACTIVE
        
    @property
    def capabilities_summary(self) -> str:
        """Get a summary of agent capabilities."""
        tool_count = len(self.authorized_tools)
        tool_types = set(tool.tool_type for tool in self.authorized_tools)
        return f"{self.function.value} with {tool_count} tools across {len(tool_types)} categories"


class AgentBudget(BaseModel):
    """
    Represents an agent's financial status in the KIP Economic Engine.
    
    This is the core financial state for each autonomous agent, tracking their
    economic performance and enforcing spending constraints to ensure sustainable
    operations.
    """
    agent_id: str = Field(description="Unique identifier for the agent")
    current_balance: int = Field(description="Current balance in USD cents", ge=0)
    total_spent: int = Field(default=0, description="Total amount spent in USD cents", ge=0)
    total_earned: int = Field(default=0, description="Total amount earned in USD cents", ge=0)
    daily_spent: int = Field(default=0, description="Amount spent today in USD cents", ge=0)
    
    # Spending limits and controls
    daily_limit: int = Field(default=10000, description="Daily spending limit in USD cents (default: $100)", gt=0)
    per_action_limit: int = Field(default=1000, description="Maximum spend per action in USD cents (default: $10)", gt=0)
    
    # State management
    last_reset_date: Union[datetime, Any] = Field(default_factory=lambda: datetime.now(timezone.utc).date())
    is_frozen: bool = Field(default=False, description="Whether spending is frozen for this agent")
    
    # Performance tracking
    total_transactions: int = Field(default=0, description="Total number of transactions", ge=0)
    roi_score: float = Field(default=0.0, description="Current ROI performance score")
    
    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Ensure agent_id follows naming conventions."""
        if not v or len(v) < 3:
            raise ValueError("agent_id must be at least 3 characters long")
        return v.lower().replace(" ", "_")
        
    @property
    def available_daily_budget(self) -> int:
        """Calculate remaining daily budget in USD cents."""
        return max(0, self.daily_limit - self.daily_spent)
        
    @property
    def net_worth(self) -> int:
        """Calculate net worth (earnings - spending) in USD cents."""
        return self.total_earned - self.total_spent
        
    @property
    def can_spend(self) -> bool:
        """Check if agent can make any purchases."""
        return not self.is_frozen and self.current_balance > 0 and self.available_daily_budget > 0
        
    def to_usd(self, cents: int) -> str:
        """Convert cents to USD string representation."""
        return f"${cents / 100:.2f}"
        
    @property
    def balance_usd(self) -> str:
        """Get current balance as USD string."""
        return self.to_usd(self.current_balance)
        
    @property
    def daily_budget_usd(self) -> str:
        """Get daily budget as USD string."""
        return self.to_usd(self.daily_limit)


class TransactionType(str, Enum):
    """Types of financial transactions in the KIP economy."""
    SEED_FUNDING = "seed_funding"        # Initial budget allocation
    EARNING = "earning"                  # Revenue from successful actions
    SPENDING = "spending"                # Cost of actions/resources
    ROI_ADJUSTMENT = "roi_adjustment"    # Performance-based budget changes
    PENALTY = "penalty"                  # Performance penalties
    REFUND = "refund"                    # Reversed transactions
    EMERGENCY_FREEZE = "emergency_freeze" # Circuit breaker activation
    LIMIT_ADJUSTMENT = "limit_adjustment" # Spending limit changes


class Transaction(BaseModel):
    """Represents a financial transaction in the KIP economy."""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = Field(description="Agent involved in the transaction")
    amount_cents: int = Field(description="Transaction amount in USD cents (positive=credit, negative=debit)")
    transaction_type: TransactionType = Field(description="Type of transaction")
    description: str = Field(description="Human-readable transaction description")
    
    # Financial state tracking
    balance_before: int = Field(description="Agent balance before transaction in USD cents")
    balance_after: int = Field(description="Agent balance after transaction in USD cents")
    
    # Performance data
    roi_data: Optional[Dict[str, Any]] = Field(default=None, description="ROI attribution data")
    
    # Audit trail
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_by: str = Field(default="treasury_system", description="System/user that processed transaction")
    
    @property
    def amount_usd(self) -> str:
        """Get transaction amount as USD string."""
        return f"${abs(self.amount_cents) / 100:.2f}"
        
    @property
    def is_credit(self) -> bool:
        """Check if transaction is a credit (positive amount)."""
        return self.amount_cents > 0
        
    @property
    def is_debit(self) -> bool:
        """Check if transaction is a debit (negative amount)."""
        return self.amount_cents < 0


class Tool(BaseModel):
    """
    Represents a tool that KIP agents can use to perform actions.
    
    Tools are the primary interface between agents and external systems,
    enabling agents to gather data, perform calculations, and interact
    with the real world.
    """
    name: str = Field(description="Unique name for the tool")
    description: str = Field(description="Human-readable description of what the tool does")
    cost_cents: int = Field(description="Cost to use this tool in USD cents")
    category: str = Field(default="general", description="Tool category (web, data, calculation, etc.)")
    
    # Authorization and limits
    min_authorization_level: str = Field(default="basic", description="Minimum authorization level required")
    max_daily_uses: int = Field(default=100, description="Maximum daily uses per agent")
    timeout_seconds: int = Field(default=30, description="Tool execution timeout")
    
    # Function reference
    function_name: str = Field(description="Name of the function to execute")
    module_path: str = Field(description="Python module path containing the function")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True, description="Whether the tool is available for use")
    
    async def execute(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the tool function with the given parameters.
        
        Args:
            params: Optional parameters to pass to the function
            
        Returns:
            Any: Result from the tool function
            
        Raises:
            ImportError: If the module or function cannot be imported
            Exception: If the tool execution fails
        """
        try:
            # Import the module dynamically
            module = importlib.import_module(self.module_path)
            
            # Get the function from the module
            if not hasattr(module, self.function_name):
                raise ImportError(f"Function {self.function_name} not found in module {self.module_path}")
                
            func = getattr(module, self.function_name)
            
            # Execute the function
            if params:
                if asyncio.iscoroutinefunction(func):
                    result = await func(**params)
                else:
                    result = func(**params)
            else:
                if asyncio.iscoroutinefunction(func):
                    result = await func()
                else:
                    result = func()
                    
            return result
            
        except Exception as e:
            raise Exception(f"Tool execution failed: {e}")
            
    @property
    def cost_usd(self) -> str:
        """Get tool cost as USD string."""
        return f"${self.cost_cents / 100:.2f}"


class ActionResult(BaseModel):
    """Represents the result of a KIP agent action execution."""
    action_id: str = Field(description="Unique identifier for this action")
    agent_id: str = Field(description="ID of the agent that executed the action")
    tool_name: str = Field(description="Name of the tool that was executed")
    status: str = Field(description="Execution status (success, error, timeout)")
    result_data: Any = Field(default=None, description="Action result data")
    execution_time: float = Field(description="Time taken to execute in seconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Economic data
    cost_cents: int = Field(default=0, description="Cost of action in USD cents")
    revenue_cents: int = Field(default=0, description="Revenue generated in USD cents")
    roi_percentage: float = Field(default=0.0, description="ROI percentage for this action")
    
    # Transaction tracking
    transaction_id: Optional[str] = Field(default=None, description="Treasury transaction ID")
    
    @property
    def cost_usd(self) -> str:
        """Get action cost as USD string."""
        return f"${self.cost_cents / 100:.2f}"
        
    @property
    def was_successful(self) -> bool:
        """Check if action was successful."""
        return self.status == "success"


class EconomicAnalytics(BaseModel):
    """Analytics data for the KIP Economic Engine."""
    total_agents: int = 0
    active_agents: int = 0
    frozen_agents: int = 0
    total_balance_cents: int = 0
    total_spent_cents: int = 0
    total_earned_cents: int = 0
    total_transactions: int = 0
    avg_roi_score: float = 0.0
    most_profitable_agent: Optional[str] = None
    emergency_freeze_active: bool = False
    
    @property
    def total_balance_usd(self) -> str:
        """Get total balance as USD string."""
        return f"${self.total_balance_cents / 100:.2f}"
        
    @property
    def total_spent_usd(self) -> str:
        """Get total spent as USD string."""
        return f"${self.total_spent_cents / 100:.2f}"
        
    @property
    def total_earned_usd(self) -> str:
        """Get total earned as USD string."""
        return f"${self.total_earned_cents / 100:.2f}"


class KIPAnalytics(BaseModel):
    """Analytics data for KIP layer monitoring."""
    total_agents: int = 0
    active_agents: int = 0
    busy_agents: int = 0
    error_agents: int = 0
    total_tools: int = 0
    avg_success_rate: float = 0.0
    total_executions: int = 0
    most_active_agent: Optional[str] = None


class KIPLayer:
    """
    The KIP (Knowledge-Incentive Protocol) Layer manages autonomous agent execution.
    
    This layer provides:
    - Agent genome loading from TigerGraph
    - Tool capability management and authorization
    - Agent lifecycle monitoring and control
    - Action execution coordination
    - Performance analytics and optimization
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the KIP Layer.
        
        Args:
            config: Optional configuration object. If None, uses environment variables.
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("KIPLayer")
        self._connection: Optional[tg.TigerGraphConnection] = None
        self._agent_cache: Dict[str, KIPAgent] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._last_cache_update: Optional[datetime] = None
        
        # Tool registry for action execution
        self.tool_registry: Dict[str, Tool] = {}
        self._tool_usage_tracking: Dict[str, Dict[str, int]] = {}  # agent_id -> {tool_name: daily_count}
        
        # Initialize built-in tools
        self._register_default_tools()
        
    async def __aenter__(self):
        """Async context manager entry - establish TigerGraph connection."""
        await self._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup connection."""
        await self._disconnect()
        
    async def _connect(self) -> None:
        """Establish TigerGraph connection for agent data access."""
        try:
            # Use synchronous connection (pyTigerGraph doesn't support async)
            self._connection = get_tigergraph_connection(self.config.tigergraph_graph_name)
            
            if not self._connection:
                raise ConnectionError("Failed to establish TigerGraph connection")
                
            self.logger.info(
                "KIP Layer connected to TigerGraph",
                graph_name=self.config.tigergraph_graph_name,
                host=self.config.tigergraph_host
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to connect to TigerGraph for KIP Layer",
                error=str(e),
                graph_name=self.config.tigergraph_graph_name
            )
            raise ConnectionError(f"TigerGraph connection failed: {e}")
            
    async def _disconnect(self) -> None:
        """Clean shutdown of TigerGraph connections."""
        # pyTigerGraph connections don't need explicit cleanup
        self._connection = None
        
    async def load_agent(self, agent_id: str, force_refresh: bool = False) -> Optional[KIPAgent]:
        """
        Load a KIP agent's genome from TigerGraph.
        
        This method queries TigerGraph for agent configuration and tool authorizations,
        building a complete KIPAgent object representing the agent's capabilities.
        
        Args:
            agent_id: Unique identifier for the agent to load
            force_refresh: If True, bypass cache and reload from database
            
        Returns:
            KIPAgent: Fully loaded agent object, or None if agent not found
            
        Raises:
            ConnectionError: If TigerGraph is unavailable
            ValueError: If agent_id is invalid
        """
        if not self._connection:
            raise ConnectionError("KIP Layer not connected to TigerGraph")
            
        # Validate agent_id
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("agent_id must be a non-empty string")
            
        agent_id = agent_id.lower().replace(" ", "_")
        
        # Check cache first (unless force refresh)
        if not force_refresh and self._is_cache_valid():
            cached_agent = self._agent_cache.get(agent_id)
            if cached_agent:
                self.logger.debug(
                    "Agent loaded from cache",
                    agent_id=agent_id,
                    function=cached_agent.function.value
                )
                return cached_agent
                
        try:
            # For MVP demo, create mock agents for known IDs
            # In production, this would query TigerGraph via _query_agent_genome
            agent = await self._create_demo_agent(agent_id)
            
            if not agent:
                self.logger.warning(
                    "Agent not found",
                    agent_id=agent_id
                )
                return None
            
            # Cache the agent
            self._agent_cache[agent_id] = agent
            self._last_cache_update = datetime.now(timezone.utc)
            
            self.logger.info(
                "Agent genome loaded successfully",
                agent_id=agent_id,
                function=agent.function.value,
                status=agent.status.value,
                tool_count=len(agent.authorized_tools)
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(
                "Failed to load agent genome",
                agent_id=agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
            
    async def _query_agent_genome(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Query TigerGraph for agent's core data.
        
        Args:
            agent_id: Agent identifier to query
            
        Returns:
            Dict containing agent data or None if not found
        """
        try:
            # Use TigerGraph's getVertex method to query agent
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._connection.getVertex("KIPAgent", agent_id)
            )
            
            if result:
                return {
                    "id": result.get("id", agent_id),
                    "function": result.get("function", "custom"),
                    "status": result.get("status", "inactive"),
                    "created_at": result.get("created_at", datetime.now(timezone.utc))
                }
                
            return None
            
        except Exception as e:
            # Agent doesn't exist - this is normal for our demo
            self.logger.debug(
                "Agent not found in TigerGraph (this is expected for demo)",
                agent_id=agent_id,
                error=str(e)
            )
            return None
            
    async def _load_agent_tools(self, agent_id: str) -> List[ToolCapability]:
        """
        Load agent's authorized tools from TigerGraph.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of ToolCapability objects
        """
        try:
            # For MVP, return mock tools since we don't have tools in the graph yet
            # In production, this would query via getEdges() for CAN_USE relationships
            mock_tools = [
                ToolCapability(
                    tool_name="data_processor",
                    description="Processes and analyzes data",
                    tool_type="analysis",
                    version="1.0",
                    authorization_level="full",
                    granted_at=datetime.now(timezone.utc)
                ),
                ToolCapability(
                    tool_name="report_generator",
                    description="Generates reports and summaries",
                    tool_type="reporting",
                    version="1.2",
                    authorization_level="basic",
                    granted_at=datetime.now(timezone.utc)
                )
            ]
            
            # Return different tools based on agent function
            if "analyst" in agent_id:
                # Data analyst gets web tools for market analysis
                web_tools = [
                    ToolCapability(
                        tool_name="get_bitcoin_price",
                        description="Access to Bitcoin price data",
                        tool_type="web",
                        version="1.0",
                        authorization_level="full",
                        granted_at=datetime.now(timezone.utc)
                    ),
                    ToolCapability(
                        tool_name="get_ethereum_price",
                        description="Access to Ethereum price data",
                        tool_type="web", 
                        version="1.0",
                        authorization_level="full",
                        granted_at=datetime.now(timezone.utc)
                    ),
                    ToolCapability(
                        tool_name="get_crypto_summary",
                        description="Access to comprehensive crypto data",
                        tool_type="web",
                        version="1.0", 
                        authorization_level="full",
                        granted_at=datetime.now(timezone.utc)
                    )
                ]
                return mock_tools + web_tools
            elif "creator" in agent_id:
                # Content creator gets reporting tools and some web access
                web_tools = [
                    ToolCapability(
                        tool_name="get_bitcoin_price",
                        description="Access to Bitcoin price data",
                        tool_type="web",
                        version="1.0",
                        authorization_level="basic",
                        granted_at=datetime.now(timezone.utc)
                    )
                ]
                return [mock_tools[1]] + web_tools  # Just report generator + basic web access
            else:
                return mock_tools
                
        except Exception as e:
            self.logger.warning(
                "Failed to load agent tools",
                agent_id=agent_id,
                error=str(e)
            )
            return []
            
    async def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[KIPAgent]:
        """
        List all agents in the KIP layer.
        
        Args:
            status_filter: Optional status filter
            
        Returns:
            List of KIPAgent objects
        """
        try:
            # For MVP demo, return mock agents since we don't have agents in the graph yet
            # In production, this would use getVertices("KIPAgent") 
            mock_agents = [
                await self._create_mock_agent("data_analyst_01", AgentFunction.DATA_ANALYST, AgentStatus.ACTIVE),
                await self._create_mock_agent("content_creator_01", AgentFunction.CONTENT_CREATOR, AgentStatus.ACTIVE),
                await self._create_mock_agent("researcher_01", AgentFunction.RESEARCHER, AgentStatus.INACTIVE),
                await self._create_mock_agent("coordinator_01", AgentFunction.COORDINATOR, AgentStatus.BUSY),
            ]
            
            # Apply status filter if provided
            if status_filter:
                mock_agents = [agent for agent in mock_agents if agent.status == status_filter]
                
            self.logger.info(
                "Agents listed",
                total_count=len(mock_agents),
                status_filter=status_filter.value if status_filter else "all"
            )
            
            return mock_agents
            
        except Exception as e:
            self.logger.error(
                "Failed to list agents",
                error=str(e)
            )
            return []
            
    async def _create_demo_agent(self, agent_id: str) -> Optional[KIPAgent]:
        """Create a demo agent for known agent IDs."""
        # Map known agent IDs to their configurations
        agent_configs = {
            "data_analyst_01": (AgentFunction.DATA_ANALYST, AgentStatus.ACTIVE),
            "content_creator_01": (AgentFunction.CONTENT_CREATOR, AgentStatus.ACTIVE),
            "researcher_01": (AgentFunction.RESEARCHER, AgentStatus.INACTIVE),
            "coordinator_01": (AgentFunction.COORDINATOR, AgentStatus.BUSY),
        }
        
        if agent_id not in agent_configs:
            return None
            
        function, status = agent_configs[agent_id]
        return await self._create_mock_agent(agent_id, function, status)
        
    async def _create_mock_agent(self, agent_id: str, function: AgentFunction, status: AgentStatus) -> KIPAgent:
        """Create a mock agent for demo purposes."""
        tools = await self._load_agent_tools(agent_id)
        return KIPAgent(
            agent_id=agent_id,
            function=function,
            status=status,
            created_at=datetime.now(timezone.utc) - timedelta(days=30),
            authorized_tools=tools,
            last_active=datetime.now(timezone.utc) - timedelta(hours=2),
            execution_count=42 if "analyst" in agent_id else 15,
            success_rate=0.95 if status == AgentStatus.ACTIVE else 0.80,
            average_execution_time=2.5
        )
            
    async def get_analytics(self) -> KIPAnalytics:
        """
        Get analytics about the KIP layer performance.
        
        Returns:
            KIPAnalytics: Current system analytics
        """
        try:
            agents = await self.list_agents()
            
            if not agents:
                return KIPAnalytics()
                
            # Calculate analytics
            status_counts = {}
            total_executions = 0
            total_success_rates = 0.0
            total_tools = 0
            most_active = None
            max_executions = 0
            
            for agent in agents:
                status = agent.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                total_executions += agent.execution_count
                total_success_rates += agent.success_rate
                total_tools += len(agent.authorized_tools)
                
                if agent.execution_count > max_executions:
                    max_executions = agent.execution_count
                    most_active = agent.agent_id
                    
            return KIPAnalytics(
                total_agents=len(agents),
                active_agents=status_counts.get("active", 0),
                busy_agents=status_counts.get("busy", 0),
                error_agents=status_counts.get("error", 0),
                total_tools=total_tools,
                avg_success_rate=total_success_rates / len(agents) if agents else 0.0,
                total_executions=total_executions,
                most_active_agent=most_active
            )
            
        except Exception as e:
            self.logger.error("Failed to generate KIP analytics", error=str(e))
            return KIPAnalytics()
            
    def _is_cache_valid(self) -> bool:
        """Check if agent cache is still valid."""
        if not self._last_cache_update:
            return False
        age = datetime.now(timezone.utc) - self._last_cache_update
        return age.total_seconds() < self._cache_ttl
        
    async def invalidate_cache(self) -> None:
        """Invalidate the agent cache."""
        self._agent_cache.clear()
        self._last_cache_update = None
        self.logger.info("Agent cache invalidated")
        
    def _register_default_tools(self) -> None:
        """
        Register the default tools available to all agents.
        """
        # Web tools for real-time data
        bitcoin_tool = Tool(
            name="get_bitcoin_price",
            description="Get current Bitcoin price in USD from CoinGecko API",
            cost_cents=100,  # $1.00 per call
            category="web",
            function_name="get_current_bitcoin_price",
            module_path="tools.web_tools",
            timeout_seconds=15
        )
        
        ethereum_tool = Tool(
            name="get_ethereum_price", 
            description="Get current Ethereum price in USD from CoinGecko API",
            cost_cents=100,  # $1.00 per call
            category="web",
            function_name="get_current_ethereum_price",
            module_path="tools.web_tools",
            timeout_seconds=15
        )
        
        crypto_summary_tool = Tool(
            name="get_crypto_summary",
            description="Get summary of major cryptocurrency prices with 24h changes",
            cost_cents=200,  # $2.00 per call (more comprehensive data)
            category="web",
            function_name="get_crypto_market_summary",
            module_path="tools.web_tools",
            timeout_seconds=20,
            max_daily_uses=50  # More expensive, so lower daily limit
        )
        
        # Register tools
        self.tool_registry[bitcoin_tool.name] = bitcoin_tool
        self.tool_registry[ethereum_tool.name] = ethereum_tool
        self.tool_registry[crypto_summary_tool.name] = crypto_summary_tool
        
        self.logger.info(
            "Default tools registered",
            tool_count=len(self.tool_registry),
            tools=list(self.tool_registry.keys())
        )
        
    async def register_tool(self, tool: Tool) -> bool:
        """
        Register a new tool in the KIP layer.
        
        Args:
            tool: Tool instance to register
            
        Returns:
            bool: True if successfully registered, False if tool name conflicts
        """
        if tool.name in self.tool_registry:
            self.logger.warning(
                "Tool registration failed - name conflict",
                tool_name=tool.name,
                existing_tool=self.tool_registry[tool.name].description
            )
            return False
            
        self.tool_registry[tool.name] = tool
        
        self.logger.info(
            "Tool registered successfully",
            tool_name=tool.name,
            description=tool.description,
            cost=tool.cost_usd,
            category=tool.category
        )
        
        return True
        
    async def get_available_tools(self, agent_id: str) -> List[Tool]:
        """
        Get all tools that an agent is authorized to use.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List[Tool]: List of tools the agent can use
        """
        # Load agent to check authorization levels
        agent = await self.load_agent(agent_id)
        if not agent:
            return []
            
        available_tools = []
        
        for tool in self.tool_registry.values():
            if not tool.is_active:
                continue
                
            # Check if agent has a tool capability that matches this tool
            authorized = False
            for capability in agent.authorized_tools:
                if (capability.tool_name == tool.name or 
                    capability.tool_type == tool.category):
                    
                    # Check authorization level
                    auth_levels = ["basic", "intermediate", "advanced", "full"]
                    agent_level_idx = auth_levels.index(capability.authorization_level) if capability.authorization_level in auth_levels else 0
                    required_level_idx = auth_levels.index(tool.min_authorization_level) if tool.min_authorization_level in auth_levels else 0
                    
                    if agent_level_idx >= required_level_idx:
                        authorized = True
                        break
                        
            if authorized:
                available_tools.append(tool)
                
        return available_tools
        
    async def execute_action(
        self,
        agent_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        treasury: Optional['Treasury'] = None
    ) -> ActionResult:
        """
        Execute an agent action using a specified tool.
        
        This is the core method that enables agents to interact with the world.
        It handles authorization, cost tracking, execution, and result recording.
        
        Args:
            agent_id: Agent executing the action
            tool_name: Name of the tool to execute
            params: Optional parameters for the tool
            treasury: Treasury instance for cost tracking
            
        Returns:
            ActionResult: Result of the action execution
        """
        action_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(
            "Agent action execution started",
            agent_id=agent_id,
            action_id=action_id,
            tool_name=tool_name,
            params=params or {}
        )
        
        try:
            # 1. Validate tool exists
            if tool_name not in self.tool_registry:
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="error",
                    error_message=f"Tool '{tool_name}' not found",
                    execution_time=0.0
                )
                
            tool = self.tool_registry[tool_name]
            
            # 2. Check if tool is active
            if not tool.is_active:
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="error",
                    error_message=f"Tool '{tool_name}' is currently inactive",
                    execution_time=0.0
                )
                
            # 3. Check agent authorization
            available_tools = await self.get_available_tools(agent_id)
            if tool not in available_tools:
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="error",
                    error_message=f"Agent not authorized to use tool '{tool_name}'",
                    execution_time=0.0
                )
                
            # 4. Check daily usage limits
            daily_usage = self._get_daily_tool_usage(agent_id, tool_name)
            if daily_usage >= tool.max_daily_uses:
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="error",
                    error_message=f"Daily usage limit exceeded for tool '{tool_name}' ({daily_usage}/{tool.max_daily_uses})",
                    execution_time=0.0
                )
                
            # 5. Check agent funds (if Treasury provided)
            transaction_id = None
            if treasury and tool.cost_cents > 0:
                funds_check = await treasury.check_funds(
                    agent_id=agent_id,
                    amount_to_spend=tool.cost_cents,
                    action_description=f"Tool execution: {tool_name}"
                )
                
                if not funds_check["approved"]:
                    return ActionResult(
                        action_id=action_id,
                        agent_id=agent_id,
                        tool_name=tool_name,
                        status="error",
                        error_message=f"Insufficient funds: {funds_check['reason']}",
                        execution_time=0.0,
                        cost_cents=tool.cost_cents
                    )
                    
            # 6. Execute the tool
            try:
                # Record the cost transaction before execution
                if treasury and tool.cost_cents > 0:
                    transaction = await treasury.record_transaction(
                        agent_id=agent_id,
                        amount_cents=-tool.cost_cents,  # Negative for spending
                        description=f"Tool execution: {tool_name}",
                        transaction_type=TransactionType.SPENDING
                    )
                    transaction_id = transaction.transaction_id if transaction else None
                    
                # Execute with timeout
                execution_result = await asyncio.wait_for(
                    tool.execute(params),
                    timeout=tool.timeout_seconds
                )
                
                # Update usage tracking
                self._increment_tool_usage(agent_id, tool_name)
                
                # Calculate execution time
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # Create successful result
                result = ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="success",
                    result_data=execution_result,
                    execution_time=execution_time,
                    cost_cents=tool.cost_cents,
                    transaction_id=transaction_id
                )
                
                self.logger.info(
                    "Agent action executed successfully",
                    agent_id=agent_id,
                    action_id=action_id,
                    tool_name=tool_name,
                    execution_time=execution_time,
                    cost=tool.cost_usd,
                    transaction_id=transaction_id
                )
                
                return result
                
            except asyncio.TimeoutError:
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                self.logger.warning(
                    "Agent action timed out",
                    agent_id=agent_id,
                    action_id=action_id,
                    tool_name=tool_name,
                    timeout_seconds=tool.timeout_seconds
                )
                
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="timeout",
                    error_message=f"Tool execution timed out after {tool.timeout_seconds} seconds",
                    execution_time=execution_time,
                    cost_cents=tool.cost_cents,
                    transaction_id=transaction_id
                )
                
            except Exception as e:
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                self.logger.error(
                    "Agent action execution failed",
                    agent_id=agent_id,
                    action_id=action_id,
                    tool_name=tool_name,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    status="error",
                    error_message=str(e),
                    execution_time=execution_time,
                    cost_cents=tool.cost_cents,
                    transaction_id=transaction_id
                )
                
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "Agent action validation failed",
                agent_id=agent_id,
                action_id=action_id,
                tool_name=tool_name,
                error=str(e)
            )
            
            return ActionResult(
                action_id=action_id,
                agent_id=agent_id,
                tool_name=tool_name,
                status="error",
                error_message=f"Action validation failed: {e}",
                execution_time=execution_time
            )
            
    def _get_daily_tool_usage(self, agent_id: str, tool_name: str) -> int:
        """
        Get the daily usage count for a specific tool by an agent.
        
        Args:
            agent_id: Agent identifier
            tool_name: Tool name
            
        Returns:
            int: Number of times the tool was used today
        """
        today = datetime.now(timezone.utc).date()
        usage_key = f"{agent_id}:{today}"
        
        if usage_key not in self._tool_usage_tracking:
            return 0
            
        return self._tool_usage_tracking[usage_key].get(tool_name, 0)
        
    def _increment_tool_usage(self, agent_id: str, tool_name: str) -> None:
        """
        Increment the daily usage count for a tool.
        
        Args:
            agent_id: Agent identifier
            tool_name: Tool name
        """
        today = datetime.now(timezone.utc).date()
        usage_key = f"{agent_id}:{today}"
        
        if usage_key not in self._tool_usage_tracking:
            self._tool_usage_tracking[usage_key] = {}
            
        if tool_name not in self._tool_usage_tracking[usage_key]:
            self._tool_usage_tracking[usage_key][tool_name] = 0
            
        self._tool_usage_tracking[usage_key][tool_name] += 1
        
        # Clean up old usage data (keep only last 7 days)
        cutoff_date = today - timedelta(days=7)
        keys_to_remove = []
        
        for key in self._tool_usage_tracking.keys():
            try:
                key_date = datetime.strptime(key.split(':')[1], '%Y-%m-%d').date()
                if key_date < cutoff_date:
                    keys_to_remove.append(key)
            except (ValueError, IndexError):
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self._tool_usage_tracking[key]
            
    async def get_tool_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about tool usage across all agents.
        
        Returns:
            Dict[str, Any]: Tool usage analytics
        """
        total_tools = len(self.tool_registry)
        active_tools = len([t for t in self.tool_registry.values() if t.is_active])
        
        # Calculate usage statistics
        today = datetime.now(timezone.utc).date()
        today_usage = {}
        total_usage = {}
        
        for usage_key, usage_data in self._tool_usage_tracking.items():
            key_date_str = usage_key.split(':')[1]
            try:
                key_date = datetime.strptime(key_date_str, '%Y-%m-%d').date()
                
                for tool_name, count in usage_data.items():
                    if tool_name not in total_usage:
                        total_usage[tool_name] = 0
                    total_usage[tool_name] += count
                    
                    if key_date == today:
                        if tool_name not in today_usage:
                            today_usage[tool_name] = 0
                        today_usage[tool_name] += count
                        
            except ValueError:
                continue
                
        most_used_tool = max(total_usage.items(), key=lambda x: x[1]) if total_usage else None
        
        return {
            "total_tools": total_tools,
            "active_tools": active_tools,
            "tool_categories": list(set(t.category for t in self.tool_registry.values())),
            "today_usage": today_usage,
            "total_usage": total_usage,
            "most_used_tool": most_used_tool[0] if most_used_tool else None,
            "most_used_count": most_used_tool[1] if most_used_tool else 0
        }


class Treasury:
    """
    The KIP Economic Engine - Core Financial Management System.
    
    This class implements the "make-or-break" economic foundation that determines
    agent survival through ROI-driven budget management. It provides:
    
    - Agent budget allocation and tracking
    - Real-time ROI-based rewards and penalties
    - Spending limits and circuit breaker protection
    - Dual-storage: TigerGraph audit trail + Redis speed layer
    - Complete transaction history for compliance
    
    Economic Principles:
    - Agents receive seed funding to start operations
    - Performance (ROI) determines budget increases/decreases
    - Poor performers lose budget and become INACTIVE
    - Safeguards prevent runaway spending
    """
    
    # Economic constants
    DEFAULT_SEED_AMOUNT = 5000  # $50.00 in cents
    DEFAULT_DAILY_LIMIT = 10000  # $100.00 in cents
    DEFAULT_ACTION_LIMIT = 1000  # $10.00 in cents
    
    # Cache TTL
    BUDGET_CACHE_TTL = 60  # 1 minute for balance caching
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Treasury economic engine.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("Treasury")
        
        # TigerGraph connection for audit trail
        self._tg_connection: Optional[tg.TigerGraphConnection] = None
        
        # Redis connection for speed layer
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
        
        # Circuit breaker state
        self._emergency_freeze_active = False
        
        # Budget cache
        self._budget_cache: Dict[str, AgentBudget] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
    async def __aenter__(self):
        """Async context manager entry - establish connections."""
        await self._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup connections."""
        await self._disconnect()
        
    async def _connect(self) -> None:
        """Establish TigerGraph and Redis connections."""
        try:
            # TigerGraph connection for audit trail
            self._tg_connection = get_tigergraph_connection(self.config.tigergraph_graph_name)
            if not self._tg_connection:
                raise ConnectionError("Failed to connect to TigerGraph")
                
            # Redis connection for speed layer
            self._redis_pool = redis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                decode_responses=True,
                max_connections=20
            )
            self._redis = redis.Redis(connection_pool=self._redis_pool)
            await self._redis.ping()
            
            self.logger.info(
                "Treasury connected to financial infrastructure",
                tigergraph_host=self.config.tigergraph_host,
                redis_host=self.config.redis_host
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to connect Treasury to financial infrastructure",
                error=str(e)
            )
            raise ConnectionError(f"Treasury connection failed: {e}")
            
    async def _disconnect(self) -> None:
        """Clean shutdown of connections."""
        if self._redis:
            await self._redis.aclose()
        if self._redis_pool:
            await self._redis_pool.disconnect()
            
    async def initialize_agent_budget(
        self, 
        agent_id: str, 
        seed_amount: Optional[int] = None,
        daily_limit: Optional[int] = None,
        action_limit: Optional[int] = None
    ) -> AgentBudget:
        """
        Initialize a new agent's budget with seed funding.
        
        Args:
            agent_id: Unique agent identifier
            seed_amount: Initial budget in USD cents (default: $50)
            daily_limit: Daily spending limit in USD cents (default: $100)
            action_limit: Per-action spending limit in USD cents (default: $10)
            
        Returns:
            AgentBudget: Newly created budget
            
        Raises:
            ValueError: If agent already has a budget
            ConnectionError: If financial infrastructure unavailable
        """
        if not self._tg_connection or not self._redis:
            raise ConnectionError("Treasury not connected to financial infrastructure")
            
        agent_id = agent_id.lower().replace(" ", "_")
        
        # Check if agent already has budget
        existing_budget = await self.get_budget(agent_id)
        if existing_budget:
            raise ValueError(f"Agent {agent_id} already has a budget")
            
        # Create initial budget
        seed_amount = seed_amount or self.DEFAULT_SEED_AMOUNT
        daily_limit = daily_limit or self.DEFAULT_DAILY_LIMIT
        action_limit = action_limit or self.DEFAULT_ACTION_LIMIT
        
        budget = AgentBudget(
            agent_id=agent_id,
            current_balance=seed_amount,
            total_earned=seed_amount,  # Seed funding counts as earnings
            daily_limit=daily_limit,
            per_action_limit=action_limit,
            total_transactions=1  # Seed transaction
        )
        
        # Record seed funding transaction
        transaction = Transaction(
            agent_id=agent_id,
            amount_cents=seed_amount,
            transaction_type=TransactionType.SEED_FUNDING,
            description=f"Seed funding for agent {agent_id}",
            balance_before=0,
            balance_after=seed_amount
        )
        
        # Store in TigerGraph and Redis
        await self._store_budget(budget)
        await self._store_transaction(transaction)
        
        self.logger.info(
            "Agent budget initialized with seed funding",
            agent_id=agent_id,
            seed_amount_cents=seed_amount,
            seed_amount_usd=budget.to_usd(seed_amount),
            daily_limit_usd=budget.to_usd(daily_limit)
        )
        
        return budget
        
    async def get_budget(self, agent_id: str) -> Optional[AgentBudget]:
        """
        Retrieve an agent's current budget with high-speed caching.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentBudget: Current budget or None if not found
        """
        if not self._redis:
            raise ConnectionError("Treasury not connected to Redis")
            
        agent_id = agent_id.lower().replace(" ", "_")
        
        # Check cache first
        if self._is_budget_cached(agent_id):
            return self._budget_cache[agent_id]
            
        try:
            # Load from Redis speed layer
            budget_key = f"budget:{agent_id}"
            budget_data = await self._redis.get(budget_key)
            
            if budget_data:
                budget_dict = json.loads(budget_data)
                
                # Fix date deserialization issue
                if 'last_reset_date' in budget_dict and isinstance(budget_dict['last_reset_date'], str):
                    try:
                        budget_dict['last_reset_date'] = datetime.fromisoformat(budget_dict['last_reset_date']).date()
                    except:
                        budget_dict['last_reset_date'] = datetime.now(timezone.utc).date()
                
                budget = AgentBudget(**budget_dict)
                
                # Reset daily spending if new day
                budget = await self._check_daily_reset(budget)
                
                # Update cache
                self._budget_cache[agent_id] = budget
                self._cache_timestamps[agent_id] = datetime.now(timezone.utc)
                
                return budget
                
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve agent budget",
                agent_id=agent_id,
                error=str(e)
            )
            return None
            
    async def check_funds(
        self, 
        agent_id: str, 
        amount_to_spend: int,
        action_description: str = "unknown action"
    ) -> Dict[str, Any]:
        """
        Check if agent has sufficient funds for a transaction.
        
        Args:
            agent_id: Agent identifier
            amount_to_spend: Amount in USD cents
            action_description: Description of the intended action
            
        Returns:
            Dict with approval status and details
        """
        if amount_to_spend <= 0:
            return {
                "approved": False,
                "reason": "Invalid amount - must be positive",
                "amount_cents": amount_to_spend
            }
            
        # Check emergency freeze
        if self._emergency_freeze_active:
            return {
                "approved": False,
                "reason": "Emergency freeze active - all spending suspended",
                "amount_cents": amount_to_spend
            }
            
        budget = await self.get_budget(agent_id)
        if not budget:
            return {
                "approved": False,
                "reason": "Agent budget not found",
                "amount_cents": amount_to_spend
            }
            
        # Check individual agent freeze
        if budget.is_frozen:
            return {
                "approved": False,
                "reason": "Agent spending is frozen",
                "amount_cents": amount_to_spend,
                "current_balance": budget.current_balance
            }
            
        # Check current balance
        if budget.current_balance < amount_to_spend:
            return {
                "approved": False,
                "reason": "Insufficient balance",
                "amount_cents": amount_to_spend,
                "current_balance": budget.current_balance,
                "shortfall": amount_to_spend - budget.current_balance
            }
            
        # Check per-action limit
        if amount_to_spend > budget.per_action_limit:
            return {
                "approved": False,
                "reason": "Exceeds per-action spending limit",
                "amount_cents": amount_to_spend,
                "per_action_limit": budget.per_action_limit
            }
            
        # Check daily limit
        if budget.daily_spent + amount_to_spend > budget.daily_limit:
            return {
                "approved": False,
                "reason": "Would exceed daily spending limit",
                "amount_cents": amount_to_spend,
                "daily_spent": budget.daily_spent,
                "daily_limit": budget.daily_limit,
                "available_daily": budget.available_daily_budget
            }
            
        # All checks passed
        return {
            "approved": True,
            "amount_cents": amount_to_spend,
            "balance_after": budget.current_balance - amount_to_spend,
            "daily_remaining": budget.available_daily_budget - amount_to_spend
        }
        
    async def record_transaction(
        self,
        agent_id: str,
        amount_cents: int,
        description: str,
        transaction_type: TransactionType = TransactionType.SPENDING,
        roi_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Transaction]:
        """
        Record a financial transaction and update agent budget.
        
        Args:
            agent_id: Agent identifier
            amount_cents: Amount in USD cents (positive=credit, negative=debit)
            description: Transaction description
            transaction_type: Type of transaction
            roi_data: Optional ROI attribution data
            
        Returns:
            Transaction: Recorded transaction or None if failed
        """
        if not self._tg_connection or not self._redis:
            raise ConnectionError("Treasury not connected to financial infrastructure")
            
        agent_id = agent_id.lower().replace(" ", "_")
        
        try:
            # Get current budget
            budget = await self.get_budget(agent_id)
            if not budget:
                self.logger.error(
                    "Cannot record transaction - agent budget not found",
                    agent_id=agent_id
                )
                return None
                
            # For spending transactions, validate funds first
            if amount_cents < 0 and transaction_type == TransactionType.SPENDING:
                funds_check = await self.check_funds(agent_id, abs(amount_cents), description)
                if not funds_check["approved"]:
                    self.logger.warning(
                        "Transaction rejected - insufficient funds",
                        agent_id=agent_id,
                        amount_cents=amount_cents,
                        reason=funds_check["reason"]
                    )
                    return None
                    
            # Create transaction record
            balance_before = budget.current_balance
            balance_after = balance_before + amount_cents
            
            transaction = Transaction(
                agent_id=agent_id,
                amount_cents=amount_cents,
                transaction_type=transaction_type,
                description=description,
                balance_before=balance_before,
                balance_after=balance_after,
                roi_data=roi_data
            )
            
            # Update budget
            budget.current_balance = balance_after
            budget.total_transactions += 1
            
            if amount_cents > 0:
                budget.total_earned += amount_cents
            else:
                budget.total_spent += abs(amount_cents)
                budget.daily_spent += abs(amount_cents)
                
            # Store transaction and updated budget
            await self._store_transaction(transaction)
            await self._store_budget(budget)
            
            self.logger.info(
                "Transaction recorded successfully",
                agent_id=agent_id,
                transaction_id=transaction.transaction_id,
                amount_cents=amount_cents,
                amount_usd=transaction.amount_usd,
                transaction_type=transaction_type.value,
                balance_after=balance_after
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(
                "Failed to record transaction",
                agent_id=agent_id,
                amount_cents=amount_cents,
                error=str(e)
            )
            return None
            
    async def calculate_roi_adjustment(
        self, 
        agent_id: str, 
        revenue_cents: int, 
        cost_cents: int,
        action_description: str
    ) -> Optional[Transaction]:
        """
        Calculate and apply ROI-based budget adjustment.
        
        Args:
            agent_id: Agent identifier
            revenue_cents: Revenue generated in USD cents
            cost_cents: Cost incurred in USD cents
            action_description: Description of the action that generated ROI
            
        Returns:
            Transaction: ROI adjustment transaction or None
        """
        if cost_cents <= 0:
            self.logger.warning(
                "Cannot calculate ROI - invalid cost",
                agent_id=agent_id,
                cost_cents=cost_cents
            )
            return None
            
        # Calculate ROI
        profit_cents = revenue_cents - cost_cents
        roi_percentage = (profit_cents / cost_cents) * 100
        
        # ROI-based reward calculation
        # Positive ROI: agent gets 50% of profit as bonus
        # Negative ROI: agent loses 25% of loss as penalty (Darwinian pressure)
        if roi_percentage > 0:
            adjustment_cents = int(profit_cents * 0.5)  # 50% of profit as reward
            transaction_type = TransactionType.ROI_ADJUSTMENT
        else:
            adjustment_cents = int(profit_cents * 0.25)  # 25% of loss as penalty
            transaction_type = TransactionType.PENALTY
            
        roi_data = {
            "revenue_cents": revenue_cents,
            "cost_cents": cost_cents,
            "profit_cents": profit_cents,
            "roi_percentage": roi_percentage,
            "action_description": action_description
        }
        
        description = (
            f"ROI adjustment: {roi_percentage:.1f}% ROI from {action_description}. "
            f"Revenue: ${revenue_cents/100:.2f}, Cost: ${cost_cents/100:.2f}"
        )
        
        return await self.record_transaction(
            agent_id=agent_id,
            amount_cents=adjustment_cents,
            description=description,
            transaction_type=transaction_type,
            roi_data=roi_data
        )
        
    async def emergency_freeze_all(self, reason: str = "Emergency stop activated") -> int:
        """
        Activate emergency circuit breaker - freeze all agent spending.
        
        Args:
            reason: Reason for emergency freeze
            
        Returns:
            int: Number of agents frozen
        """
        self._emergency_freeze_active = True
        
        # Get all agent IDs from Redis
        agent_keys = await self._redis.keys("budget:*")
        frozen_count = 0
        
        for key in agent_keys:
            agent_id = key.replace("budget:", "")
            budget = await self.get_budget(agent_id)
            if budget and not budget.is_frozen:
                budget.is_frozen = True
                await self._store_budget(budget)
                frozen_count += 1
                
        self.logger.critical(
            "Emergency freeze activated",
            reason=reason,
            agents_frozen=frozen_count
        )
        
        return frozen_count
        
    async def emergency_unfreeze_all(self, reason: str = "Emergency cleared") -> int:
        """
        Deactivate emergency circuit breaker - unfreeze all agent spending.
        
        Args:
            reason: Reason for lifting freeze
            
        Returns:
            int: Number of agents unfrozen
        """
        self._emergency_freeze_active = False
        
        # Get all agent IDs from Redis
        agent_keys = await self._redis.keys("budget:*")
        unfrozen_count = 0
        
        for key in agent_keys:
            agent_id = key.replace("budget:", "")
            budget = await self.get_budget(agent_id)
            if budget and budget.is_frozen:
                budget.is_frozen = False
                await self._store_budget(budget)
                unfrozen_count += 1
                
        self.logger.info(
            "Emergency freeze lifted",
            reason=reason,
            agents_unfrozen=unfrozen_count
        )
        
        return unfrozen_count
        
    async def get_economic_analytics(self) -> EconomicAnalytics:
        """
        Generate comprehensive economic analytics.
        
        Returns:
            EconomicAnalytics: Current economic state
        """
        try:
            agent_keys = await self._redis.keys("budget:*")
            
            total_balance = 0
            total_spent = 0
            total_earned = 0
            total_transactions = 0
            active_agents = 0
            frozen_agents = 0
            roi_scores = []
            most_profitable = None
            max_net_worth = float('-inf')
            
            for key in agent_keys:
                agent_id = key.replace("budget:", "")
                budget = await self.get_budget(agent_id)
                
                if budget:
                    total_balance += budget.current_balance
                    total_spent += budget.total_spent
                    total_earned += budget.total_earned
                    total_transactions += budget.total_transactions
                    
                    if budget.is_frozen:
                        frozen_agents += 1
                    elif budget.current_balance > 0:
                        active_agents += 1
                        
                    roi_scores.append(budget.roi_score)
                    
                    if budget.net_worth > max_net_worth:
                        max_net_worth = budget.net_worth
                        most_profitable = agent_id
                        
            return EconomicAnalytics(
                total_agents=len(agent_keys),
                active_agents=active_agents,
                frozen_agents=frozen_agents,
                total_balance_cents=total_balance,
                total_spent_cents=total_spent,
                total_earned_cents=total_earned,
                total_transactions=total_transactions,
                avg_roi_score=sum(roi_scores) / len(roi_scores) if roi_scores else 0.0,
                most_profitable_agent=most_profitable,
                emergency_freeze_active=self._emergency_freeze_active
            )
            
        except Exception as e:
            self.logger.error("Failed to generate economic analytics", error=str(e))
            return EconomicAnalytics()
            
    async def _store_budget(self, budget: AgentBudget) -> None:
        """Store budget in Redis and TigerGraph."""
        try:
            # Store in Redis for speed
            budget_key = f"budget:{budget.agent_id}"
            
            # Custom serialization to handle date properly
            budget_dict = budget.model_dump()
            # Ensure last_reset_date is stored as ISO string
            if isinstance(budget_dict['last_reset_date'], (datetime, type(datetime.now().date()))):
                if hasattr(budget_dict['last_reset_date'], 'isoformat'):
                    budget_dict['last_reset_date'] = budget_dict['last_reset_date'].isoformat()
                else:
                    budget_dict['last_reset_date'] = str(budget_dict['last_reset_date'])
            
            budget_data = json.dumps(budget_dict, default=str)
            await self._redis.setex(budget_key, self.BUDGET_CACHE_TTL, budget_data)
            
            # Update local cache
            self._budget_cache[budget.agent_id] = budget
            self._cache_timestamps[budget.agent_id] = datetime.now(timezone.utc)
            
            # TODO: Store in TigerGraph for persistence
            # This would create/update an AgentBudget vertex
            
        except Exception as e:
            self.logger.error(
                "Failed to store budget",
                agent_id=budget.agent_id,
                error=str(e)
            )
            
    async def _store_transaction(self, transaction: Transaction) -> None:
        """Store transaction in TigerGraph audit trail."""
        try:
            # Store transaction in Redis for recent history
            tx_key = f"transaction:{transaction.transaction_id}"
            tx_data = transaction.model_dump_json()
            await self._redis.setex(tx_key, 86400, tx_data)  # 24 hour TTL
            
            # TODO: Store in TigerGraph for permanent audit trail
            # This would create a Transaction vertex and relationships
            
        except Exception as e:
            self.logger.error(
                "Failed to store transaction",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            
    async def _check_daily_reset(self, budget: AgentBudget) -> AgentBudget:
        """Reset daily spending if new day."""
        today = datetime.now(timezone.utc).date()
        
        # Handle both date and datetime objects
        last_reset = budget.last_reset_date
        if isinstance(last_reset, datetime):
            last_reset = last_reset.date()
            
        if last_reset < today:
            budget.daily_spent = 0
            budget.last_reset_date = today
            await self._store_budget(budget)
            
        return budget
        
    def _is_budget_cached(self, agent_id: str) -> bool:
        """Check if budget is in cache and still valid."""
        if agent_id not in self._budget_cache:
            return False
            
        cache_time = self._cache_timestamps.get(agent_id)
        if not cache_time:
            return False
            
        age = datetime.now(timezone.utc) - cache_time
        return age.total_seconds() < self.BUDGET_CACHE_TTL


# Convenience functions for standalone usage
async def create_kip_layer(config: Optional[Config] = None) -> KIPLayer:
    """
    Create and initialize a KIPLayer instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        KIPLayer: Ready-to-use KIP layer instance
    """
    layer = KIPLayer(config)
    await layer._connect()
    return layer


async def create_treasury(config: Optional[Config] = None) -> Treasury:
    """
    Create and initialize a Treasury instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        Treasury: Ready-to-use economic engine
    """
    treasury = Treasury(config)
    await treasury._connect()
    return treasury


@asynccontextmanager
async def kip_session(config: Optional[Config] = None):
    """
    Async context manager for KIP operations.
    
    Usage:
        async with kip_session() as kip:
            agent = await kip.load_agent("data_analyst_01")
            agents = await kip.list_agents()
    """
    layer = KIPLayer(config)
    try:
        await layer._connect()
        yield layer
    finally:
        await layer._disconnect()


@asynccontextmanager
async def treasury_session(config: Optional[Config] = None):
    """
    Async context manager for Treasury operations.
    
    Usage:
        async with treasury_session() as treasury:
            budget = await treasury.get_budget("data_analyst_01")
            await treasury.record_transaction(agent_id, -500, "LLM API call")
    """
    treasury = Treasury(config)
    try:
        await treasury._connect()
        yield treasury
    finally:
        await treasury._disconnect()