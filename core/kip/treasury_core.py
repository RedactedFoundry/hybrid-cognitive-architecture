# core/kip/treasury_core.py
"""
Treasury Core - KIP Economic Engine Coordinator

Main coordination module that integrates budget management, transaction processing,
and economic analysis. Handles emergency controls and provides unified interface.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import pyTigerGraph as tg
import redis.asyncio as redis
import structlog

from config import Config
from clients.tigergraph_client import get_tigergraph_connection
from .models import AgentBudget, Transaction, TransactionType, EconomicAnalytics
from .budget_manager import BudgetManager
from .transaction_processor import TransactionProcessor
from .economic_analyzer import EconomicAnalyzer


class TreasuryCore:
    """
    Main Treasury coordination class - provides unified interface to KIP economic engine.
    
    This class coordinates between focused modules:
    - BudgetManager: Budget allocation and limits
    - TransactionProcessor: Transaction recording and history
    - EconomicAnalyzer: ROI calculations and analytics
    
    Also handles:
    - Connection management
    - Emergency controls (freeze/unfreeze)
    - System-wide economic operations
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Treasury Core coordination system.
        
        Args:
            config: Optional configuration object
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("TreasuryCore")
        
        # Connection objects
        self._tg_connection: Optional[tg.TigerGraphConnection] = None
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
        
        # Focused module instances
        self.budget_manager: Optional[BudgetManager] = None
        self.transaction_processor: Optional[TransactionProcessor] = None
        self.economic_analyzer: Optional[EconomicAnalyzer] = None
        
        # Emergency controls
        self._emergency_freeze_active = False
        
    async def __aenter__(self):
        """Async context manager entry - establish connections and initialize modules."""
        await self._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup connections."""
        await self._disconnect()
        
    async def _connect(self) -> None:
        """Establish connections and initialize focused modules."""
        try:
            # TigerGraph connection for audit trail
            self._tg_connection = get_tigergraph_connection(self.config.tigergraph_graph_name)
            if not self._tg_connection:
                self.logger.warning("Failed to connect to TigerGraph - audit trail disabled")
                
            # Redis connection for speed layer
            self._redis_pool = redis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                decode_responses=True,
                max_connections=20
            )
            self._redis = redis.Redis(connection_pool=self._redis_pool)
            await self._redis.ping()
            
            # Initialize focused modules
            self.budget_manager = BudgetManager(self._redis, self.config)
            self.transaction_processor = TransactionProcessor(
                self._redis, 
                self._tg_connection,
                self.budget_manager,
                self.config
            )
            self.economic_analyzer = EconomicAnalyzer(
                self._redis,
                self.budget_manager,
                self.transaction_processor,
                self.config
            )
            
            self.logger.info(
                "Treasury Core connected to financial infrastructure",
                tigergraph_host=self.config.tigergraph_host,
                tigergraph_connected=self._tg_connection is not None,
                redis_host=self.config.redis_host
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to connect Treasury Core to financial infrastructure",
                error=str(e)
            )
            raise ConnectionError(f"Treasury Core connection failed: {e}")
            
    async def _disconnect(self) -> None:
        """Clean shutdown of connections."""
        if self._redis:
            await self._redis.aclose()
        self.logger.info("Treasury Core disconnected")
        
    # Unified interface methods - delegate to focused modules
    
    async def initialize_agent_budget(
        self,
        agent_id: str,
        seed_amount: Optional[int] = None,
        daily_limit: Optional[int] = None,
        action_limit: Optional[int] = None
    ) -> AgentBudget:
        """Initialize budget for a new agent."""
        return await self.budget_manager.initialize_agent_budget(
            agent_id, seed_amount, daily_limit, action_limit
        )
        
    async def get_budget(self, agent_id: str) -> Optional[AgentBudget]:
        """Get current budget for an agent."""
        return await self.budget_manager.get_budget(agent_id)
        
    async def check_funds(
        self, 
        agent_id: str, 
        amount_to_spend: int,
        action_description: str = "unknown action"
    ) -> Dict[str, Any]:
        """Check if agent has sufficient funds for a transaction."""
        return await self.budget_manager.check_funds(
            agent_id, amount_to_spend, action_description, self._emergency_freeze_active
        )
        
    async def record_transaction(
        self,
        agent_id: str,
        amount: int,
        description: str,
        transaction_type: TransactionType = TransactionType.SPENDING,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Transaction]:
        """Record a financial transaction."""
        return await self.transaction_processor.record_transaction(
            agent_id, amount, description, transaction_type, metadata
        )
        
    async def calculate_roi_adjustment(
        self,
        agent_id: str,
        performance_period_days: int = 7
    ) -> Dict[str, Any]:
        """Calculate and apply ROI-based budget adjustment."""
        return await self.economic_analyzer.calculate_roi_adjustment(
            agent_id, performance_period_days
        )
        
    async def get_economic_analytics(self) -> EconomicAnalytics:
        """Get system-wide economic analytics."""
        return await self.economic_analyzer.get_economic_analytics()
        
    # Emergency control methods
    
    async def emergency_freeze_all(self, reason: str = "Emergency stop activated") -> int:
        """
        Freeze all agent spending immediately.
        
        Args:
            reason: Reason for emergency freeze
            
        Returns:
            int: Number of agents frozen
        """
        self._emergency_freeze_active = True
        
        try:
            # Get all agent budget keys
            budget_keys = await self._redis.keys("budget:*")
            frozen_count = 0
            
            for key in budget_keys:
                try:
                    budget_data = await self._redis.get(key)
                    if budget_data:
                        import json
                        budget_dict = json.loads(budget_data)
                        budget_dict["is_frozen"] = True
                        budget_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
                        
                        await self._redis.set(key, json.dumps(budget_dict))
                        frozen_count += 1
                        
                except Exception as agent_error:
                    self.logger.warning(
                        "Failed to freeze individual agent",
                        key=key,
                        error=str(agent_error)
                    )
                    continue
                    
            self.logger.critical(
                "Emergency freeze activated - all spending suspended",
                reason=reason,
                agents_frozen=frozen_count
            )
            
            return frozen_count
            
        except Exception as e:
            self.logger.error(
                "Failed to execute emergency freeze",
                reason=reason,
                error=str(e)
            )
            raise
            
    async def emergency_unfreeze_all(self, reason: str = "Emergency cleared") -> int:
        """
        Unfreeze all agent spending.
        
        Args:
            reason: Reason for unfreezing
            
        Returns:
            int: Number of agents unfrozen
        """
        self._emergency_freeze_active = False
        
        try:
            # Get all agent budget keys
            budget_keys = await self._redis.keys("budget:*")
            unfrozen_count = 0
            
            for key in budget_keys:
                try:
                    budget_data = await self._redis.get(key)
                    if budget_data:
                        import json
                        budget_dict = json.loads(budget_data)
                        budget_dict["is_frozen"] = False
                        budget_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
                        
                        await self._redis.set(key, json.dumps(budget_dict))
                        unfrozen_count += 1
                        
                except Exception as agent_error:
                    self.logger.warning(
                        "Failed to unfreeze individual agent",
                        key=key,
                        error=str(agent_error)
                    )
                    continue
                    
            self.logger.info(
                "Emergency unfreeze completed - spending restored",
                reason=reason,
                agents_unfrozen=unfrozen_count
            )
            
            return unfrozen_count
            
        except Exception as e:
            self.logger.error(
                "Failed to execute emergency unfreeze",
                reason=reason,
                error=str(e)
            )
            raise
            
    @property
    def is_emergency_freeze_active(self) -> bool:
        """Check if emergency freeze is currently active."""
        return self._emergency_freeze_active
        
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall treasury system status."""
        try:
            analytics = await self.get_economic_analytics()
            
            return {
                "connected": True,
                "emergency_freeze_active": self._emergency_freeze_active,
                "tigergraph_connected": self._tg_connection is not None,
                "redis_connected": self._redis is not None,
                "total_agents": analytics.total_agents,
                "active_agents": analytics.active_agents,
                "total_balance": analytics.total_balance,
                "average_performance": analytics.average_performance,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get system status", error=str(e))
            return {
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Convenience functions for backward compatibility and standalone usage

async def create_treasury(config: Optional[Config] = None) -> TreasuryCore:
    """
    Create and initialize a Treasury Core instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        TreasuryCore: Ready-to-use economic engine
    """
    treasury = TreasuryCore(config)
    await treasury._connect()
    return treasury


@asynccontextmanager
async def treasury_session(config: Optional[Config] = None):
    """
    Async context manager for Treasury operations.
    
    Usage:
        async with treasury_session() as treasury:
            budget = await treasury.get_budget("data_analyst_01")
            await treasury.record_transaction(agent_id, -500, "LLM API call")
    """
    treasury = TreasuryCore(config)
    try:
        await treasury._connect()
        yield treasury
    finally:
        await treasury._disconnect()


# Alias for backward compatibility
Treasury = TreasuryCore