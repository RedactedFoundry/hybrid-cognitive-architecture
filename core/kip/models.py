# core/kip/models.py
"""
KIP Layer Data Models and Enums

This module contains all Pydantic models, enums, and data structures
used throughout the KIP (Knowledge-Incentive Protocol) Layer.
"""

import json
import asyncio
import importlib
import uuid
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


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
        return self.status in [AgentStatus.ACTIVE, AgentStatus.INACTIVE]
    
    @property
    def capabilities_summary(self) -> str:
        """Get a summary of agent capabilities."""
        return f"{self.function.value} agent with {len(self.authorized_tools)} tools"


class AgentBudget(BaseModel):
    """
    Represents an agent's financial status and spending limits.
    
    All monetary values are stored in USD cents to avoid floating-point precision issues.
    """
    
    # Identity
    agent_id: str = Field(description="Agent identifier")
    
    # Financial Status (in USD cents)
    current_balance: int = Field(description="Current available balance in USD cents")
    total_spent: int = Field(default=0, description="Total amount spent (lifetime) in USD cents")
    total_earned: int = Field(default=0, description="Total amount earned (lifetime) in USD cents")
    daily_spent: int = Field(default=0, description="Amount spent today in USD cents", ge=0)
    
    # Spending Controls (in USD cents)
    daily_limit: int = Field(description="Maximum spending per day in USD cents")
    per_action_limit: int = Field(description="Maximum spending per single action in USD cents")
    
    # Operational Controls
    last_reset_date: date = Field(description="Date of last daily limit reset")
    is_frozen: bool = Field(default=False, description="Whether spending is frozen")
    
    # Analytics
    total_transactions: int = Field(default=0, description="Total number of transactions")
    roi_score: float = Field(default=0.0, description="Return on investment score")
    
    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Ensure agent_id follows naming conventions."""
        if not v or len(v) < 3:
            raise ValueError("agent_id must be at least 3 characters long")
        return v.lower().replace(" ", "_")
    
    @property
    def available_daily_budget(self) -> int:
        """Calculate remaining daily budget in cents."""
        return max(0, self.daily_limit - self.daily_spent)
    
    @property
    def net_worth(self) -> int:
        """Calculate net worth (earnings - spending) in USD cents."""
        return self.total_earned - self.total_spent
    
    @property
    def can_spend(self) -> bool:
        """Check if agent can make purchases."""
        return not self.is_frozen and self.current_balance > 0
    
    def to_usd(self, cents: int) -> str:
        """Convert cents to USD string representation."""
        return f"${cents / 100:.2f}"
    
    @property
    def balance_usd(self) -> str:
        """Get current balance as USD string."""
        return self.to_usd(self.current_balance)
    
    @property
    def daily_budget_usd(self) -> str:
        """Get daily limit as USD string.""" 
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
        """Check if this is a credit transaction."""
        return self.amount_cents > 0
    
    @property
    def is_debit(self) -> bool:
        """Check if this is a debit transaction."""
        return self.amount_cents < 0


class Tool(BaseModel):
    """
    Represents an executable tool that agents can use.
    
    Tools are dynamically loaded modules with specific capabilities
    and cost structures for agent execution.
    """
    
    # Tool Identity
    tool_name: str = Field(description="Unique tool identifier")
    description: str = Field(description="What this tool does")
    tool_type: str = Field(description="Category/classification of tool")
    version: str = Field(description="Tool version")
    
    # Execution Configuration
    module_path: str = Field(description="Python module path for dynamic import")
    function_name: str = Field(description="Function name to call within module")
    
    # Authorization & Limits
    required_authorization: str = Field(description="Minimum authorization level required")
    cost_per_use: int = Field(description="Cost per execution in USD cents")
    daily_limit: int = Field(default=100, description="Maximum daily uses per agent")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = Field(default=None)
    total_uses: int = Field(default=0)
    
    async def execute(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Dynamically execute the tool with provided parameters.
        
        Args:
            params: Optional parameters to pass to the tool function
            
        Returns:
            Result from tool execution
            
        Raises:
            ImportError: If module or function cannot be imported
            Exception: If tool execution fails
        """
        try:
            # Dynamic import of the tool module
            module = importlib.import_module(self.module_path)
            
            # Get the specific function
            if not hasattr(module, self.function_name):
                raise AttributeError(f"Function '{self.function_name}' not found in module '{self.module_path}'")
            
            func = getattr(module, self.function_name)
            
            # Execute with or without parameters
            if params:
                result = await func(**params) if asyncio.iscoroutinefunction(func) else func(**params)
            else:
                result = await func() if asyncio.iscoroutinefunction(func) else func()
            
            # Update usage statistics
            self.last_used = datetime.now(timezone.utc)
            self.total_uses += 1
            
            return result
            
        except Exception as e:
            raise Exception(f"Tool '{self.tool_name}' execution failed: {str(e)}")
    
    @property
    def cost_usd(self) -> str:
        """Get cost per use as USD string."""
        return f"${self.cost_per_use / 100:.2f}"


class ActionResult(BaseModel):
    """
    Represents the result of an agent action execution.
    
    Provides structured feedback on action success, performance,
    and economic impact.
    """
    
    # Execution Identity
    action_id: str = Field(description="Unique action execution identifier")
    agent_id: str = Field(description="Agent that executed the action")
    tool_name: str = Field(description="Tool that was used")
    
    # Execution Results
    success: bool = Field(description="Whether action completed successfully")
    result_data: Optional[Dict[str, Any]] = Field(default=None, description="Structured result data")
    error_message: Optional[str] = Field(default=None, description="Error message if action failed")
    
    # Performance Metrics
    execution_time: float = Field(description="Time taken to execute in seconds")
    cost_cents: int = Field(description="Actual cost of execution in USD cents")
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def cost_usd(self) -> str:
        """Get execution cost as USD string."""
        return f"${self.cost_cents / 100:.2f}"
    
    @property
    def was_successful(self) -> bool:
        """Check if action was successful."""
        return self.success and self.error_message is None


class EconomicAnalytics(BaseModel):
    """
    Aggregate economic analytics across all agents.
    
    Provides system-wide financial health metrics.
    """
    
    # Financial Totals (in USD cents)
    total_balance: int = Field(description="Sum of all agent balances")
    total_spent: int = Field(description="Total amount spent across all agents")
    total_earned: int = Field(description="Total amount earned across all agents")
    
    # Agent Statistics
    active_agents: int = Field(description="Number of active agents")
    total_agents: int = Field(description="Total number of agents")
    frozen_agents: int = Field(description="Number of frozen agents")
    
    # Transaction Statistics
    total_transactions: int = Field(description="Total number of transactions")
    average_transaction_amount: float = Field(description="Average transaction amount in USD cents")
    
    # Performance Metrics
    system_roi: float = Field(description="Overall system ROI")
    top_performer: Optional[str] = Field(default=None, description="Agent ID of top performer")
    
    @property
    def total_balance_usd(self) -> str:
        """Get total balance as USD string."""
        return f"${self.total_balance / 100:.2f}"
    
    @property
    def total_spent_usd(self) -> str:
        """Get total spent as USD string."""
        return f"${self.total_spent / 100:.2f}"
    
    @property
    def total_earned_usd(self) -> str:
        """Get total earned as USD string."""
        return f"${self.total_earned / 100:.2f}"


class KIPAnalytics(BaseModel):
    """
    KIP Layer analytics and performance metrics.
    """
    
    # Agent Statistics
    total_agents: int = Field(description="Total number of agents")
    active_agents: int = Field(description="Number of active agents") 
    busy_agents: int = Field(description="Number of busy agents")
    
    # Tool Usage Statistics
    total_tools: int = Field(description="Total number of available tools")
    most_used_tool: Optional[str] = Field(default=None, description="Most frequently used tool")
    total_tool_executions: int = Field(description="Total tool executions")
    
    # Performance Metrics
    average_execution_time: float = Field(description="Average tool execution time")
    success_rate: float = Field(description="Overall success rate")
    most_active_agent: Optional[str] = None