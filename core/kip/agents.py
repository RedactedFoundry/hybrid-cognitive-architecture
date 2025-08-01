# core/kip/agents.py
"""
KIP Agent Management

This module handles agent lifecycle management, genome loading,
and caching for the KIP (Knowledge-Incentive Protocol) Layer.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import pyTigerGraph as tg
import structlog

# Clean config import
from config import Config
from clients.tigervector_client import get_tigergraph_connection
from .models import KIPAgent, AgentStatus, AgentFunction, ToolCapability, KIPAnalytics


class AgentManager:
    """
    Manages KIP agent lifecycle, genome loading, and performance analytics.
    
    This class provides:
    - Agent genome loading from TigerGraph
    - Agent lifecycle monitoring and control
    - Performance analytics and optimization
    - Caching for optimal performance
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Agent Manager.
        
        Args:
            config: Optional configuration object. If None, uses environment variables.
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("AgentManager")
        self._connection: Optional[tg.TigerGraphConnection] = None
        self._agent_cache: Dict[str, KIPAgent] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._last_cache_update: Optional[datetime] = None
        
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
                "Agent Manager connected to TigerGraph",
                graph_name=self.config.tigergraph_graph_name,
                host=self.config.tigergraph_host
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to connect to TigerGraph for Agent Manager",
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
            raise ConnectionError("Agent Manager not connected to TigerGraph")
            
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
                return KIPAnalytics(
                    total_agents=0,
                    active_agents=0,
                    busy_agents=0,
                    total_tools=0,
                    most_used_tool=None,
                    total_tool_executions=0,
                    average_execution_time=0.0,
                    success_rate=0.0,
                    most_active_agent=None
                )
                
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
                total_tools=total_tools,
                most_used_tool=None,  # This will be populated by tool analytics
                total_tool_executions=total_executions,
                average_execution_time=sum(agent.average_execution_time for agent in agents) / len(agents),
                success_rate=total_success_rates / len(agents) if agents else 0.0,
                most_active_agent=most_active
            )
            
        except Exception as e:
            self.logger.error("Failed to generate KIP analytics", error=str(e))
            return KIPAnalytics(
                total_agents=0,
                active_agents=0,
                busy_agents=0,
                total_tools=0,
                most_used_tool=None,
                total_tool_executions=0,
                average_execution_time=0.0,
                success_rate=0.0,
                most_active_agent=None
            )
            
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


# Convenience functions for standalone usage
async def create_agent_manager(config: Optional[Config] = None) -> AgentManager:
    """
    Create and initialize an AgentManager instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        AgentManager: Ready-to-use agent manager instance
    """
    manager = AgentManager(config)
    await manager._connect()
    return manager