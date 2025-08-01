# core/kip/budget_manager.py
"""
Budget Management Module - KIP Treasury

Handles agent budget allocation, daily limits, spending validation, and cache management.
Extracted from Treasury for better modularity and maintainability.
"""

import json
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any

import redis.asyncio as redis
import structlog

from config import Config
from .models import AgentBudget


class BudgetManager:
    """
    Manages agent budgets, daily limits, and spending validation.
    
    Responsibilities:
    - Agent budget initialization and retrieval
    - Daily spending limit enforcement
    - Budget caching for performance
    - Daily reset logic
    """
    
    # Economic constants
    DEFAULT_SEED_AMOUNT = 5000  # $50.00 in cents
    DEFAULT_DAILY_LIMIT = 10000  # $100.00 in cents
    DEFAULT_ACTION_LIMIT = 1000  # $10.00 in cents
    BUDGET_CACHE_TTL = 60  # 1 minute for balance caching
    
    def __init__(self, redis_client: redis.Redis, config: Optional[Config] = None):
        """
        Initialize the Budget Manager.
        
        Args:
            redis_client: Connected Redis client for speed layer
            config: Optional configuration object
        """
        self.redis = redis_client
        self.config = config or Config()
        self.logger = structlog.get_logger("BudgetManager")
        
        # Budget cache for performance
        self._budget_cache: Dict[str, AgentBudget] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
    async def initialize_agent_budget(
        self,
        agent_id: str,
        seed_amount: Optional[int] = None,
        daily_limit: Optional[int] = None,
        action_limit: Optional[int] = None
    ) -> AgentBudget:
        """
        Create initial budget for a new agent.
        
        Args:
            agent_id: Agent identifier
            seed_amount: Initial budget in USD cents
            daily_limit: Daily spending limit in USD cents
            action_limit: Per-action spending limit in USD cents
            
        Returns:
            AgentBudget: Newly created budget
        """
        agent_id = agent_id.lower().replace(" ", "_")
        
        # Check if budget already exists
        existing_budget = await self.get_budget(agent_id)
        if existing_budget:
            self.logger.warning(
                "Agent budget already exists, returning existing budget",
                agent_id=agent_id,
                current_balance=existing_budget.current_balance
            )
            return existing_budget
        
        # Create new budget with defaults
        now = datetime.now(timezone.utc)
        budget = AgentBudget(
            agent_id=agent_id,
            current_balance=seed_amount or self.DEFAULT_SEED_AMOUNT,
            daily_limit=daily_limit or self.DEFAULT_DAILY_LIMIT,
            action_limit=action_limit or self.DEFAULT_ACTION_LIMIT,
            daily_spent=0,
            total_earned=seed_amount or self.DEFAULT_SEED_AMOUNT,
            total_spent=0,
            is_active=True,
            is_frozen=False,
            last_reset_date=now.date(),
            performance_score=1.0,
            created_at=now,
            updated_at=now
        )
        
        # Store in Redis speed layer
        await self._store_budget_redis(budget)
        
        # Update cache
        self._budget_cache[agent_id] = budget
        self._cache_timestamps[agent_id] = now
        
        self.logger.info(
            "Agent budget initialized successfully",
            agent_id=agent_id,
            seed_amount=budget.current_balance,
            daily_limit=budget.daily_limit
        )
        
        return budget
        
    async def get_budget(self, agent_id: str) -> Optional[AgentBudget]:
        """
        Retrieve agent budget with caching and daily reset logic.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentBudget: Current budget or None if not found
        """
        agent_id = agent_id.lower().replace(" ", "_")
        
        # Check cache first
        if self._is_budget_cached(agent_id):
            return self._budget_cache[agent_id]
            
        try:
            # Load from Redis speed layer
            budget_key = f"budget:{agent_id}"
            budget_data = await self.redis.get(budget_key)
            
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
        action_description: str = "unknown action",
        emergency_freeze_active: bool = False
    ) -> Dict[str, Any]:
        """
        Check if agent has sufficient funds for a transaction.
        
        Args:
            agent_id: Agent identifier
            amount_to_spend: Amount in USD cents
            action_description: Description of the intended action
            emergency_freeze_active: Whether emergency freeze is active
            
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
        if emergency_freeze_active:
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
                "deficit": amount_to_spend - budget.current_balance
            }
            
        # Check daily spending limit
        if budget.daily_spent + amount_to_spend > budget.daily_limit:
            return {
                "approved": False,
                "reason": "Daily spending limit would be exceeded",
                "amount_cents": amount_to_spend,
                "daily_limit": budget.daily_limit,
                "daily_spent": budget.daily_spent,
                "daily_remaining": budget.daily_limit - budget.daily_spent
            }
            
        # Check per-action limit
        if amount_to_spend > budget.action_limit:
            return {
                "approved": False,
                "reason": "Amount exceeds per-action limit",
                "amount_cents": amount_to_spend,
                "action_limit": budget.action_limit
            }
            
        # All checks passed
        return {
            "approved": True,
            "amount_cents": amount_to_spend,
            "current_balance": budget.current_balance,
            "daily_spent": budget.daily_spent,
            "daily_remaining": budget.daily_limit - budget.daily_spent,
            "action_description": action_description
        }
        
    async def update_budget_balance(self, agent_id: str, amount_change: int) -> Optional[AgentBudget]:
        """
        Update agent budget balance (positive for earnings, negative for spending).
        
        Args:
            agent_id: Agent identifier
            amount_change: Amount to add/subtract (in cents)
            
        Returns:
            Updated AgentBudget or None if agent not found
        """
        budget = await self.get_budget(agent_id)
        if not budget:
            return None
            
        # Update balances
        budget.current_balance += amount_change
        
        if amount_change > 0:
            budget.total_earned += amount_change
        else:
            budget.total_spent += abs(amount_change)
            budget.daily_spent += abs(amount_change)
            
        budget.updated_at = datetime.now(timezone.utc)
        
        # Store updated budget
        await self._store_budget_redis(budget)
        
        # Update cache
        self._budget_cache[agent_id] = budget
        self._cache_timestamps[agent_id] = budget.updated_at
        
        return budget
        
    def _is_budget_cached(self, agent_id: str) -> bool:
        """Check if budget is cached and still valid."""
        if agent_id not in self._budget_cache:
            return False
            
        cache_time = self._cache_timestamps.get(agent_id)
        if not cache_time:
            return False
            
        age_seconds = (datetime.now(timezone.utc) - cache_time).total_seconds()
        return age_seconds < self.BUDGET_CACHE_TTL
        
    async def _check_daily_reset(self, budget: AgentBudget) -> AgentBudget:
        """Check if daily spending should be reset and handle it."""
        today = datetime.now(timezone.utc).date()
        
        if budget.last_reset_date < today:
            budget.daily_spent = 0
            budget.last_reset_date = today
            budget.updated_at = datetime.now(timezone.utc)
            
            # Store the updated budget
            await self._store_budget_redis(budget)
            
            self.logger.info(
                "Daily spending reset for agent",
                agent_id=budget.agent_id,
                reset_date=today.isoformat()
            )
            
        return budget
        
    async def _store_budget_redis(self, budget: AgentBudget) -> None:
        """Store budget in Redis speed layer."""
        try:
            budget_key = f"budget:{budget.agent_id}"
            budget_data = budget.model_dump_json()
            await self.redis.set(budget_key, budget_data)
            
        except Exception as e:
            self.logger.error(
                "Failed to store budget in Redis",
                agent_id=budget.agent_id,
                error=str(e)
            )
            raise