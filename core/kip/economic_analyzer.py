# core/kip/economic_analyzer.py
"""
Economic Analysis Module - KIP Treasury

Handles ROI calculations, performance analytics, and economic insights.
Extracted from Treasury for better modularity and maintainability.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import redis.asyncio as redis
import structlog

from config import Config
from .models import AgentBudget, EconomicAnalytics
from .budget_manager import BudgetManager
from .transaction_processor import TransactionProcessor


class EconomicAnalyzer:
    """
    Analyzes economic performance and calculates ROI adjustments.
    
    Responsibilities:
    - ROI calculation and budget adjustments
    - Performance scoring and ranking
    - Economic analytics and insights
    - Agent performance recommendations
    """
    
    # Performance thresholds
    EXCELLENT_PERFORMANCE_THRESHOLD = 2.0  # 200% ROI
    GOOD_PERFORMANCE_THRESHOLD = 1.5       # 150% ROI
    POOR_PERFORMANCE_THRESHOLD = 0.5       # 50% ROI
    CRITICAL_PERFORMANCE_THRESHOLD = 0.2   # 20% ROI
    
    # Adjustment multipliers
    EXCELLENT_MULTIPLIER = 1.5  # 50% budget increase
    GOOD_MULTIPLIER = 1.2       # 20% budget increase
    NEUTRAL_MULTIPLIER = 1.0    # No change
    POOR_MULTIPLIER = 0.8       # 20% budget decrease
    CRITICAL_MULTIPLIER = 0.5   # 50% budget decrease
    
    def __init__(
        self,
        redis_client: redis.Redis,
        budget_manager: BudgetManager,
        transaction_processor: TransactionProcessor,
        config: Optional[Config] = None
    ):
        """
        Initialize the Economic Analyzer.
        
        Args:
            redis_client: Connected Redis client
            budget_manager: Budget manager for balance updates
            transaction_processor: Transaction processor for history
            config: Optional configuration object
        """
        self.redis = redis_client
        self.budget_manager = budget_manager
        self.transaction_processor = transaction_processor
        self.config = config or Config()
        self.logger = structlog.get_logger("EconomicAnalyzer")
        
    async def calculate_roi_adjustment(
        self,
        agent_id: str,
        performance_period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate ROI-based budget adjustment for an agent.
        
        Args:
            agent_id: Agent identifier
            performance_period_days: Days to analyze for performance
            
        Returns:
            Dict with ROI analysis and adjustment recommendations
        """
        agent_id = agent_id.lower().replace(" ", "_")
        
        try:
            # Get current budget
            budget = await self.budget_manager.get_budget(agent_id)
            if not budget:
                return {
                    "agent_id": agent_id,
                    "error": "Agent budget not found",
                    "adjustment_applied": False
                }
                
            # Calculate performance metrics
            performance = await self._calculate_performance_metrics(agent_id, performance_period_days)
            
            if performance["total_spent"] == 0:
                # No spending to analyze
                return {
                    "agent_id": agent_id,
                    "roi": 0.0,
                    "performance_score": budget.performance_score,
                    "adjustment_multiplier": self.NEUTRAL_MULTIPLIER,
                    "adjustment_applied": False,
                    "reason": "No spending activity to analyze"
                }
                
            # Calculate ROI
            roi = performance["total_earned"] / max(performance["total_spent"], 1)
            
            # Determine adjustment multiplier
            multiplier = self._get_adjustment_multiplier(roi)
            
            # Calculate new budget amounts
            new_daily_limit = int(budget.daily_limit * multiplier)
            new_action_limit = int(budget.action_limit * multiplier)
            
            # Apply reasonable bounds
            new_daily_limit = max(1000, min(50000, new_daily_limit))  # $10-$500 range
            new_action_limit = max(100, min(10000, new_action_limit))  # $1-$100 range
            
            # Update budget with new limits and performance score
            budget.daily_limit = new_daily_limit
            budget.action_limit = new_action_limit
            budget.performance_score = roi
            budget.updated_at = datetime.now(timezone.utc)
            
            # Store updated budget
            await self.budget_manager._store_budget_redis(budget)
            
            self.logger.info(
                "ROI adjustment applied",
                agent_id=agent_id,
                roi=roi,
                multiplier=multiplier,
                old_daily_limit=int(budget.daily_limit / multiplier),
                new_daily_limit=new_daily_limit,
                performance_period_days=performance_period_days
            )
            
            return {
                "agent_id": agent_id,
                "roi": roi,
                "performance_score": roi,
                "adjustment_multiplier": multiplier,
                "old_daily_limit": int(budget.daily_limit / multiplier),
                "new_daily_limit": new_daily_limit,
                "old_action_limit": int(budget.action_limit / multiplier),
                "new_action_limit": new_action_limit,
                "adjustment_applied": True,
                "performance_tier": self._get_performance_tier(roi),
                "analysis_period_days": performance_period_days,
                **performance
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate ROI adjustment",
                agent_id=agent_id,
                error=str(e),
                exc_info=True
            )
            return {
                "agent_id": agent_id,
                "error": f"ROI calculation failed: {str(e)}",
                "adjustment_applied": False
            }
            
    async def get_economic_analytics(self) -> EconomicAnalytics:
        """
        Generate comprehensive economic analytics for the KIP system.
        
        Returns:
            EconomicAnalytics: System-wide economic insights
        """
        try:
            # Get all agent budget keys
            budget_keys = await self.redis.keys("budget:*")
            
            if not budget_keys:
                return EconomicAnalytics(
                    total_agents=0,
                    active_agents=0,
                    total_balance=0,
                    total_earned=0,
                    total_spent=0,
                    frozen_agents=0,
                    total_transactions=0,
                    average_transaction_amount=0.0,
                    system_roi=0.0,
                    top_performers=[],
                    poor_performers=[],
                    average_performance=0.0
                )
                
            # Analyze each agent
            total_balance = 0
            total_earned = 0
            total_spent = 0
            performance_scores = []
            agent_performances = []
            
            for key in budget_keys:
                try:
                    budget_data = await self.redis.get(key)
                    if budget_data:
                        import json
                        budget_dict = json.loads(budget_data)
                        
                        total_balance += budget_dict.get("current_balance", 0)
                        total_earned += budget_dict.get("total_earned", 0)
                        total_spent += budget_dict.get("total_spent", 0)
                        
                        performance_score = budget_dict.get("performance_score", 0.0)
                        performance_scores.append(performance_score)
                        
                        agent_performances.append({
                            "agent_id": budget_dict.get("agent_id", "unknown"),
                            "performance_score": performance_score,
                            "current_balance": budget_dict.get("current_balance", 0),
                            "is_active": budget_dict.get("is_active", False)
                        })
                        
                except Exception as agent_error:
                    self.logger.warning(
                        "Failed to process agent budget for analytics",
                        key=key,
                        error=str(agent_error)
                    )
                    continue
                    
            # Calculate derived metrics
            total_agents = len(budget_keys)
            active_agents = sum(1 for agent in agent_performances if agent["is_active"])
            average_performance = sum(performance_scores) / max(len(performance_scores), 1)
            
            # Identify top and poor performers
            sorted_agents = sorted(agent_performances, key=lambda x: x["performance_score"], reverse=True)
            top_performers = [agent["agent_id"] for agent in sorted_agents[:5] if agent["performance_score"] > 1.0]
            poor_performers = [agent["agent_id"] for agent in sorted_agents[-5:] if agent["performance_score"] < 0.5]
            
            # Calculate additional required fields
            frozen_agents = 0  # TODO: Implement frozen agent tracking
            total_transactions = len(budget_keys)  # Approximate based on agents
            average_transaction_amount = (total_spent / total_transactions) if total_transactions > 0 else 0.0
            system_roi = (total_earned / total_spent) if total_spent > 0 else 0.0
            
            analytics = EconomicAnalytics(
                total_agents=total_agents,
                active_agents=active_agents,
                total_balance=total_balance,
                total_earned=total_earned,
                total_spent=total_spent,
                frozen_agents=frozen_agents,
                total_transactions=total_transactions,
                average_transaction_amount=average_transaction_amount,
                system_roi=system_roi,
                top_performers=top_performers,
                poor_performers=poor_performers,
                average_performance=average_performance
            )
            
            self.logger.info(
                "Economic analytics generated",
                total_agents=total_agents,
                active_agents=active_agents,
                total_balance=total_balance,
                average_performance=average_performance
            )
            
            return analytics
            
        except Exception as e:
            self.logger.error(
                "Failed to generate economic analytics",
                error=str(e),
                exc_info=True
            )
            
            # Return empty analytics on error
            return EconomicAnalytics(
                total_agents=0,
                active_agents=0,
                total_balance=0,
                total_earned=0,
                total_spent=0,
                frozen_agents=0,
                total_transactions=0,
                average_transaction_amount=0.0,
                system_roi=0.0,
                top_performers=[],
                poor_performers=[],
                average_performance=0.0
            )
            
    async def _calculate_performance_metrics(
        self,
        agent_id: str,
        period_days: int
    ) -> Dict[str, Any]:
        """Calculate performance metrics for specified period."""
        try:
            # Get transaction history
            transactions = await self.transaction_processor.get_transaction_history(
                agent_id, 
                limit=500
            )
            
            # Filter by time period
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)
            recent_transactions = [
                t for t in transactions 
                if t.timestamp >= cutoff_date
            ]
            
            total_earned = sum(t.amount for t in recent_transactions if t.amount > 0)
            total_spent = sum(abs(t.amount) for t in recent_transactions if t.amount < 0)
            transaction_count = len(recent_transactions)
            
            return {
                "total_earned": total_earned,
                "total_spent": total_spent,
                "transaction_count": transaction_count,
                "analysis_period_days": period_days
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate performance metrics",
                agent_id=agent_id,
                period_days=period_days,
                error=str(e)
            )
            return {
                "total_earned": 0,
                "total_spent": 0,
                "transaction_count": 0,
                "analysis_period_days": period_days
            }
            
    def _get_adjustment_multiplier(self, roi: float) -> float:
        """Get budget adjustment multiplier based on ROI."""
        if roi >= self.EXCELLENT_PERFORMANCE_THRESHOLD:
            return self.EXCELLENT_MULTIPLIER
        elif roi >= self.GOOD_PERFORMANCE_THRESHOLD:
            return self.GOOD_MULTIPLIER
        elif roi >= self.POOR_PERFORMANCE_THRESHOLD:
            return self.NEUTRAL_MULTIPLIER
        elif roi >= self.CRITICAL_PERFORMANCE_THRESHOLD:
            return self.POOR_MULTIPLIER
        else:
            return self.CRITICAL_MULTIPLIER
            
    def _get_performance_tier(self, roi: float) -> str:
        """Get human-readable performance tier."""
        if roi >= self.EXCELLENT_PERFORMANCE_THRESHOLD:
            return "excellent"
        elif roi >= self.GOOD_PERFORMANCE_THRESHOLD:
            return "good"
        elif roi >= self.POOR_PERFORMANCE_THRESHOLD:
            return "neutral"
        elif roi >= self.CRITICAL_PERFORMANCE_THRESHOLD:
            return "poor"
        else:
            return "critical"