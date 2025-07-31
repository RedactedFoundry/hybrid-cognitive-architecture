# core/kip/treasury.py
"""
KIP Treasury - Economic Engine and Financial Management

This module implements the core economic engine that manages agent budgets,
transactions, and ROI-based survival mechanics for the KIP layer.
"""

import json
import uuid
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import pyTigerGraph as tg
import redis.asyncio as redis
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
from clients.tigervector_client import get_tigergraph_connection
from .models import AgentBudget, Transaction, TransactionType, EconomicAnalytics


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
            last_reset_date=datetime.now(timezone.utc).date(),
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
                total_balance=total_balance,
                total_spent=total_spent,
                total_earned=total_earned,
                total_transactions=total_transactions,
                average_transaction_amount=total_spent / total_transactions if total_transactions > 0 else 0.0,
                system_roi=((total_earned - total_spent) / total_spent * 100) if total_spent > 0 else 0.0,
                top_performer=most_profitable
            )
            
        except Exception as e:
            self.logger.error("Failed to generate economic analytics", error=str(e))
            return EconomicAnalytics(
                total_agents=0,
                active_agents=0,
                frozen_agents=0,
                total_balance=0,
                total_spent=0,
                total_earned=0,
                total_transactions=0,
                average_transaction_amount=0.0,
                system_roi=0.0,
                top_performer=None
            )
            
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
            
            # Store in TigerGraph for persistence
            await self._store_budget_tigergraph(budget)
            
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
            
            # Store in TigerGraph for permanent audit trail
            await self._store_transaction_tigergraph(transaction)
            
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

    async def _store_budget_tigergraph(self, budget: AgentBudget) -> None:
        """Store agent budget in TigerGraph for persistence."""
        try:
            if self._tg_connection is None:
                self.logger.warning("TigerGraph connection not available, skipping budget persistence")
                return
            
            # Prepare budget data for TigerGraph vertex
            budget_data = {
                "agent_id": budget.agent_id,
                "current_balance": budget.current_balance,
                "total_spent": budget.total_spent,
                "total_earned": budget.total_earned,
                "daily_limit": budget.daily_limit,
                "per_action_limit": budget.per_action_limit,
                "last_reset_date": budget.last_reset_date.isoformat() if hasattr(budget.last_reset_date, 'isoformat') else str(budget.last_reset_date),
                "is_frozen": budget.is_frozen,
                "total_transactions": budget.total_transactions,
                "roi_score": budget.roi_score,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Use TigerGraph upsert functionality to create or update agent budget
            vertex_type = "AgentBudget"
            vertex_id = budget.agent_id
            
            # TigerGraph upsert operation
            result = self._tg_connection.upsertVertex(vertex_type, vertex_id, budget_data)
            
            self.logger.info(
                "Agent budget stored in TigerGraph",
                agent_id=budget.agent_id,
                balance_cents=budget.current_balance,
                total_transactions=budget.total_transactions,
                tigergraph_result=result
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to store budget in TigerGraph",
                agent_id=budget.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Don't raise - TigerGraph failures shouldn't break the main flow
    
    async def _store_transaction_tigergraph(self, transaction: Transaction) -> None:
        """Store transaction in TigerGraph for permanent audit trail."""
        try:
            if self._tg_connection is None:
                self.logger.warning("TigerGraph connection not available, skipping transaction persistence")
                return
            
            # Prepare transaction data for TigerGraph vertex
            transaction_data = {
                "transaction_id": transaction.transaction_id,
                "agent_id": transaction.agent_id,
                "amount_cents": transaction.amount_cents,
                "description": transaction.description,
                "timestamp": transaction.timestamp.isoformat(),
                "transaction_type": transaction.transaction_type,
                "related_kpi": transaction.roi_data.get("action_description") if transaction.roi_data else None,
                "roi_impact": transaction.roi_data.get("roi_percentage") if transaction.roi_data else 0.0
            }
            
            # Create transaction vertex
            vertex_type = "Transaction"
            vertex_id = transaction.transaction_id
            
            # TigerGraph upsert operation for transaction
            result = self._tg_connection.upsertVertex(vertex_type, vertex_id, transaction_data)
            
            # Create relationship between agent and transaction
            try:
                edge_result = self._tg_connection.upsertEdge(
                    sourceVertexType="AgentBudget",
                    sourceVertexId=transaction.agent_id,
                    targetVertexType="Transaction", 
                    targetVertexId=transaction.transaction_id,
                    edgeType="HAS_TRANSACTION",
                    attributes={"created_at": datetime.now(timezone.utc).isoformat()}
                )
                
                self.logger.info(
                    "Transaction stored in TigerGraph with agent relationship",
                    transaction_id=transaction.transaction_id,
                    agent_id=transaction.agent_id,
                    amount_cents=transaction.amount_cents,
                    tigergraph_vertex_result=result,
                    tigergraph_edge_result=edge_result
                )
                
            except Exception as edge_error:
                self.logger.warning(
                    "Transaction vertex created but failed to create agent relationship",
                    transaction_id=transaction.transaction_id,
                    agent_id=transaction.agent_id,
                    error=str(edge_error)
                )
            
        except Exception as e:
            self.logger.error(
                "Failed to store transaction in TigerGraph",
                transaction_id=transaction.transaction_id,
                agent_id=transaction.agent_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Don't raise - TigerGraph failures shouldn't break the main flow


# Convenience functions for standalone usage
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