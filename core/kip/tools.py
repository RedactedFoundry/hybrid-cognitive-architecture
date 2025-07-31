# core/kip/tools.py
"""
KIP Tool Registry and Execution Engine

This module handles tool registration, authorization, execution,
and usage tracking for the KIP (Knowledge-Incentive Protocol) Layer.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, TYPE_CHECKING

import structlog

# Import Config from the root config module
try:
    import sys
    import os
    # Get path to root config.py
    current_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    config_path = os.path.join(parent_dir, 'config.py')
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    Config = config_module.Config
except ImportError:
    # Fallback for testing
    class Config:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
from .models import Tool, ActionResult, AgentStatus, TransactionType

if TYPE_CHECKING:
    from .treasury import Treasury
    from .agents import AgentManager


class ToolRegistry:
    """
    Manages tool registration, authorization, and execution for KIP agents.
    
    This class provides:
    - Tool registration and lifecycle management
    - Agent authorization checking
    - Tool execution with cost tracking
    - Usage analytics and limits
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Tool Registry.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("ToolRegistry")
        
        # Tool registry for action execution
        self.tool_registry: Dict[str, Tool] = {}
        self._tool_usage_tracking: Dict[str, Dict[str, int]] = {}  # agent_id:date -> {tool_name: daily_count}
        
        # Initialize built-in tools
        self._register_default_tools()
        
    def _register_default_tools(self) -> None:
        """
        Register the default tools available to all agents.
        """
        # Web tools for real-time data
        bitcoin_tool = Tool(
            tool_name="get_bitcoin_price",
            description="Get current Bitcoin price in USD from CoinGecko API",
            tool_type="web",
            version="1.0",
            module_path="tools.web_tools",
            function_name="get_current_bitcoin_price",
            required_authorization="basic",
            cost_per_use=100,  # $1.00 per call
            daily_limit=100
        )
        
        ethereum_tool = Tool(
            tool_name="get_ethereum_price", 
            description="Get current Ethereum price in USD from CoinGecko API",
            tool_type="web",
            version="1.0",
            module_path="tools.web_tools",
            function_name="get_current_ethereum_price",
            required_authorization="basic",
            cost_per_use=100,  # $1.00 per call
            daily_limit=100
        )
        
        crypto_summary_tool = Tool(
            tool_name="get_crypto_summary",
            description="Get summary of major cryptocurrency prices with 24h changes",
            tool_type="web",
            version="1.0",
            module_path="tools.web_tools",
            function_name="get_crypto_market_summary",
            required_authorization="full",
            cost_per_use=200,  # $2.00 per call (more comprehensive data)
            daily_limit=50  # More expensive, so lower daily limit
        )
        
        # Register tools
        self.tool_registry[bitcoin_tool.tool_name] = bitcoin_tool
        self.tool_registry[ethereum_tool.tool_name] = ethereum_tool
        self.tool_registry[crypto_summary_tool.tool_name] = crypto_summary_tool
        
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
        if tool.tool_name in self.tool_registry:
            self.logger.warning(
                "Tool registration failed - name conflict",
                tool_name=tool.tool_name,
                existing_tool=self.tool_registry[tool.tool_name].description
            )
            return False
            
        self.tool_registry[tool.tool_name] = tool
        
        self.logger.info(
            "Tool registered successfully",
            tool_name=tool.tool_name,
            description=tool.description,
            cost=tool.cost_usd,
            tool_type=tool.tool_type
        )
        
        return True
        
    async def get_available_tools(self, agent_manager: 'AgentManager', agent_id: str) -> List[Tool]:
        """
        Get all tools that an agent is authorized to use.
        
        Args:
            agent_manager: AgentManager instance for loading agent data
            agent_id: Agent identifier
            
        Returns:
            List[Tool]: List of tools the agent can use
        """
        # Load agent to check authorization levels
        agent = await agent_manager.load_agent(agent_id)
        if not agent:
            return []
            
        available_tools = []
        
        for tool in self.tool_registry.values():
            # Check if agent has a tool capability that matches this tool
            authorized = False
            for capability in agent.authorized_tools:
                if (capability.tool_name == tool.tool_name or 
                    capability.tool_type == tool.tool_type):
                    
                    # Check authorization level
                    auth_levels = ["basic", "intermediate", "advanced", "full"]
                    agent_level_idx = auth_levels.index(capability.authorization_level) if capability.authorization_level in auth_levels else 0
                    required_level_idx = auth_levels.index(tool.required_authorization) if tool.required_authorization in auth_levels else 0
                    
                    if agent_level_idx >= required_level_idx:
                        authorized = True
                        break
                        
            if authorized:
                available_tools.append(tool)
                
        return available_tools
        
    async def execute_action(
        self,
        agent_manager: 'AgentManager',
        treasury: Optional['Treasury'],
        agent_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """
        Execute an agent action using a specified tool.
        
        This is the core method that enables agents to interact with the world.
        It handles authorization, cost tracking, execution, and result recording.
        
        Args:
            agent_manager: AgentManager instance for authorization
            treasury: Treasury instance for cost tracking
            agent_id: Agent executing the action
            tool_name: Name of the tool to execute
            params: Optional parameters for the tool
            
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
                    success=False,
                    error_message=f"Tool '{tool_name}' not found",
                    execution_time=0.0,
                    cost_cents=0
                )
                
            tool = self.tool_registry[tool_name]
            
            # 2. Check agent authorization
            available_tools = await self.get_available_tools(agent_manager, agent_id)
            if tool not in available_tools:
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    success=False,
                    error_message=f"Agent not authorized to use tool '{tool_name}'",
                    execution_time=0.0,
                    cost_cents=0
                )
                
            # 3. Check daily usage limits
            daily_usage = self._get_daily_tool_usage(agent_id, tool_name)
            if daily_usage >= tool.daily_limit:
                return ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    success=False,
                    error_message=f"Daily usage limit exceeded for tool '{tool_name}' ({daily_usage}/{tool.daily_limit})",
                    execution_time=0.0,
                    cost_cents=tool.cost_per_use
                )
                
            # 4. Check agent funds (if Treasury provided)
            if treasury and tool.cost_per_use > 0:
                funds_check = await treasury.check_funds(
                    agent_id=agent_id,
                    amount_to_spend=tool.cost_per_use,
                    action_description=f"Tool execution: {tool_name}"
                )
                
                if not funds_check["approved"]:
                    return ActionResult(
                        action_id=action_id,
                        agent_id=agent_id,
                        tool_name=tool_name,
                        success=False,
                        error_message=f"Insufficient funds: {funds_check['reason']}",
                        execution_time=0.0,
                        cost_cents=tool.cost_per_use
                    )
                    
            # 5. Execute the tool
            try:
                # Record the cost transaction before execution
                if treasury and tool.cost_per_use > 0:
                    transaction = await treasury.record_transaction(
                        agent_id=agent_id,
                        amount_cents=-tool.cost_per_use,  # Negative for spending
                        description=f"Tool execution: {tool_name}",
                        transaction_type=TransactionType.SPENDING
                    )
                    
                # Execute the tool
                execution_result = await tool.execute(params)
                
                # Update usage tracking
                self._increment_tool_usage(agent_id, tool_name)
                
                # Calculate execution time
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # Create successful result
                result = ActionResult(
                    action_id=action_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    success=True,
                    result_data=execution_result,
                    execution_time=execution_time,
                    cost_cents=tool.cost_per_use
                )
                
                self.logger.info(
                    "Agent action executed successfully",
                    agent_id=agent_id,
                    action_id=action_id,
                    tool_name=tool_name,
                    execution_time=execution_time,
                    cost=tool.cost_usd
                )
                
                return result
                
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
                    success=False,
                    error_message=str(e),
                    execution_time=execution_time,
                    cost_cents=tool.cost_per_use
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
                success=False,
                error_message=f"Action validation failed: {e}",
                execution_time=execution_time,
                cost_cents=0
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
            "tool_categories": list(set(t.tool_type for t in self.tool_registry.values())),
            "today_usage": today_usage,
            "total_usage": total_usage,
            "most_used_tool": most_used_tool[0] if most_used_tool else None,
            "most_used_count": most_used_tool[1] if most_used_tool else 0
        }