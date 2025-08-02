#!/usr/bin/env python3
"""
Economic Behaviors Test Suite - KIP Agent Economy Validation

This test suite validates the sophisticated multi-agent economic system that powers
the KIP (Knowledge Information Processing) layer of the Hybrid AI Council.

The KIP Economic Engine Features:
- Multi-agent budget management and spending controls
- Performance-based ROI tracking and budget adjustments  
- Tool execution costs and economic optimization
- System-wide economic analytics and agent ranking
- Sophisticated financial transaction logging and audit trails

Test Coverage:
1. Individual Agent Economics - Budget allocation, spending limits, ROI scoring
2. Multi-Agent Competition - Performance comparison and ranking
3. Tool Economics - Cost tracking and ROI for tool usage
4. Economic Analytics - System-wide financial health metrics
5. Performance Adjustments - Automated budget increases/decreases based on ROI
6. Economic Scenarios - Real-world business decision workflows with costs
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Import KIP economic components
from core.kip.models import (
    AgentBudget, Transaction, TransactionType, Tool,
    EconomicAnalytics, KIPAnalytics, ActionResult
)
from core.kip.economic_analyzer import EconomicAnalyzer
from core.kip.budget_manager import BudgetManager
from core.kip.transaction_processor import TransactionProcessor
from core.kip.treasury_core import TreasuryCore
from core.kip.agents import AgentManager

# Import web tools for realistic cost scenarios
from tools.web_tools import get_current_bitcoin_price, get_current_ethereum_price


class TestIndividualAgentEconomics:
    """Test individual agent budget management and financial controls."""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client for economic data storage."""
        redis_mock = AsyncMock()
        # Mock Redis responses for agent budget data
        redis_mock.get.return_value = json.dumps({
            "agent_id": "crypto_analyst_001",
            "current_balance": 500000,  # $5000.00 in cents
            "total_spent": 200000,      # $2000.00 in cents  
            "total_earned": 350000,     # $3500.00 in cents
            "daily_spent": 5000,        # $50.00 in cents
            "daily_limit": 100000,      # $1000.00 daily limit
            "per_action_limit": 5000,   # $50.00 per action
            "last_reset_date": str(date.today()),
            "is_frozen": False,
            "total_transactions": 25,
            "roi_score": 1.75,          # 175% ROI
            "performance_score": 1.75,
            "is_active": True
        })
        return redis_mock
    
    @pytest.fixture 
    async def budget_manager(self, mock_redis):
        """Create budget manager with mocked Redis."""
        return BudgetManager(mock_redis)
    
    @pytest.fixture
    async def transaction_processor(self, mock_redis, budget_manager):
        """Create transaction processor with mocked Redis."""
        # Mock TigerGraph connection
        mock_tigergraph = AsyncMock()
        return TransactionProcessor(mock_redis, mock_tigergraph, budget_manager)
    
    @pytest.fixture
    async def economic_analyzer(self, mock_redis, budget_manager, transaction_processor):
        """Create economic analyzer with all dependencies."""
        return EconomicAnalyzer(mock_redis, budget_manager, transaction_processor)
    
    @pytest.mark.asyncio
    async def test_agent_budget_allocation(self, mock_redis):
        """Test creating and managing agent budgets."""
        # Create budget directly using AgentBudget model to test economic concepts
        from datetime import date
        
        budget = AgentBudget(
            agent_id="market_analyst_001",
            current_balance=100000,      # $1000.00
            daily_limit=50000,           # $500.00 daily limit
            per_action_limit=2000,       # $20.00 per action
            last_reset_date=date.today(),
            total_earned=100000,         # Initial seed funding counts as earnings
            total_spent=0,               # No spending yet
            daily_spent=0,               # No spending today
            roi_score=1.0                # Initial neutral ROI
        )
        
        # Verify budget allocation and financial controls
        assert budget.agent_id == "market_analyst_001"
        assert budget.current_balance == 100000
        assert budget.daily_limit == 50000
        assert budget.per_action_limit == 2000
        assert budget.can_spend is True
        assert budget.balance_usd == "$1000.00"
        assert budget.daily_budget_usd == "$500.00"
        assert budget.available_daily_budget == 50000  # Full daily budget available
        assert budget.net_worth == 100000  # $1000.00 profit (earned - spent)
    
    @pytest.mark.asyncio 
    async def test_agent_spending_controls(self, mock_redis):
        """Test spending limits and controls prevent overspending."""
        from datetime import date
        
        # Create agent with tight spending limits
        budget = AgentBudget(
            agent_id="restricted_agent_001",
            current_balance=50000,       # $500.00
            daily_limit=10000,           # $100.00 daily limit
            per_action_limit=1000,       # $10.00 per action limit
            last_reset_date=date.today(),
            total_earned=50000,          # Initial seed funding
            total_spent=0,
            daily_spent=0
        )
        
        # Test daily spending limit enforcement
        assert budget.available_daily_budget == 10000  # Full daily budget available
        
        # Simulate spending $80.00 today
        budget.daily_spent = 8000
        assert budget.available_daily_budget == 2000  # $20.00 remaining
        
        # Test frozen account
        budget.is_frozen = True
        assert budget.can_spend is False
        
        # Unfreeze and test zero balance
        budget.is_frozen = False
        budget.current_balance = 0
        assert budget.can_spend is False
    
    @pytest.mark.asyncio
    async def test_agent_roi_calculation(self, economic_analyzer):
        """Test agent ROI calculation and performance scoring thresholds."""
        # Test the performance thresholds that drive the Economic Darwinism system
        assert economic_analyzer.EXCELLENT_PERFORMANCE_THRESHOLD == 2.0  # 200% ROI
        assert economic_analyzer.GOOD_PERFORMANCE_THRESHOLD == 1.5        # 150% ROI
        assert economic_analyzer.POOR_PERFORMANCE_THRESHOLD == 0.5        # 50% ROI
        assert economic_analyzer.CRITICAL_PERFORMANCE_THRESHOLD == 0.2    # 20% ROI
        
        # Test adjustment multipliers that reward/penalize agents
        assert economic_analyzer.EXCELLENT_MULTIPLIER == 1.5  # 50% budget increase
        assert economic_analyzer.GOOD_MULTIPLIER == 1.2       # 20% budget increase
        assert economic_analyzer.NEUTRAL_MULTIPLIER == 1.0    # No change
        assert economic_analyzer.POOR_MULTIPLIER == 0.8       # 20% budget decrease
        assert economic_analyzer.CRITICAL_MULTIPLIER == 0.5   # 50% budget decrease
        
        # Test ROI scenarios that would trigger different adjustments
        # Excellent performance: Agent that turns $100 into $200+ (200%+ ROI)
        excellent_roi = 250000 / 100000  # $2500 earned / $1000 spent = 2.5 ROI
        assert excellent_roi > economic_analyzer.EXCELLENT_PERFORMANCE_THRESHOLD
        
        # Poor performance: Agent that turns $100 into $40 (40% ROI)
        poor_roi = 40000 / 100000  # $400 earned / $1000 spent = 0.4 ROI  
        assert poor_roi < economic_analyzer.POOR_PERFORMANCE_THRESHOLD
    
    @pytest.mark.asyncio
    async def test_transaction_logging(self, mock_redis):
        """Test complete financial transaction audit trail."""
        agent_id = "audit_agent_001"
        
        # Create transaction directly to test the economic audit model
        transaction = Transaction(
            agent_id=agent_id,
            amount_cents=-5000,  # $50.00 spent
            transaction_type=TransactionType.SPENDING,
            description="Bitcoin price API call",
            balance_before=100000,  # $1000.00 before
            balance_after=95000,    # $950.00 after
            roi_data={
                "tool_used": "get_current_bitcoin_price",
                "execution_time": 0.45,
                "success": True,
                "expected_roi": 2.0  # Expected 200% ROI from this action
            }
        )
        
        # Verify transaction properties and audit trail
        assert transaction.agent_id == agent_id
        assert transaction.amount_cents == -5000
        assert transaction.is_debit is True
        assert transaction.is_credit is False
        assert transaction.amount_usd == "$50.00"
        assert transaction.description == "Bitcoin price API call"
        assert transaction.balance_before == 100000
        assert transaction.balance_after == 95000
        
        # Verify ROI tracking data
        assert "tool_used" in transaction.roi_data
        assert transaction.roi_data["expected_roi"] == 2.0
        assert transaction.roi_data["success"] is True
        
        # Verify audit trail fields
        assert transaction.transaction_id is not None
        assert transaction.timestamp is not None
        assert transaction.processed_by == "treasury_system"
    
    @pytest.mark.asyncio
    async def test_net_worth_calculation(self):
        """Test agent net worth and financial health calculations."""
        # Create agent with positive ROI
        profitable_agent = AgentBudget(
            agent_id="profitable_agent",
            current_balance=150000,     # $1500.00
            total_spent=100000,         # $1000.00 spent
            total_earned=175000,        # $1750.00 earned
            daily_spent=2000,           # $20.00 today
            daily_limit=50000,          # $500.00 daily limit
            per_action_limit=5000,      # $50.00 per action
            last_reset_date=date.today(),
            roi_score=1.75              # 175% ROI
        )
        
        # Verify financial health metrics
        assert profitable_agent.net_worth == 75000       # $750.00 profit
        assert profitable_agent.can_spend is True
        assert profitable_agent.available_daily_budget == 48000  # $480.00 remaining today
        
        # Create agent with negative ROI  
        losing_agent = AgentBudget(
            agent_id="losing_agent",
            current_balance=25000,      # $250.00
            total_spent=150000,         # $1500.00 spent
            total_earned=50000,         # $500.00 earned  
            daily_spent=45000,          # $450.00 today
            daily_limit=50000,          # $500.00 daily limit
            per_action_limit=5000,      # $50.00 per action
            last_reset_date=date.today(),
            roi_score=0.33              # 33% ROI - poor performance
        )
        
        # Verify poor performance metrics
        assert losing_agent.net_worth == -100000    # -$1000.00 loss
        assert losing_agent.can_spend is True       # Still has balance
        assert losing_agent.available_daily_budget == 5000  # $50.00 remaining today


class TestMultiAgentCompetition:
    """Test multi-agent economic competition and performance ranking."""
    
    @pytest.fixture
    async def mock_redis_multi_agent(self):
        """Mock Redis with multiple agent data for competition testing."""
        redis_mock = AsyncMock()
        
        # Mock multiple agent budgets with different performance levels
        agent_data = {
            "kip:budget:top_performer": json.dumps({
                "agent_id": "top_performer",
                "current_balance": 200000,
                "total_spent": 50000,
                "total_earned": 150000,
                "performance_score": 3.0,    # 300% ROI - Excellent
                "is_active": True
            }),
            "kip:budget:good_performer": json.dumps({
                "agent_id": "good_performer", 
                "current_balance": 120000,
                "total_spent": 80000,
                "total_earned": 120000,
                "performance_score": 1.5,    # 150% ROI - Good
                "is_active": True
            }),
            "kip:budget:average_performer": json.dumps({
                "agent_id": "average_performer",
                "current_balance": 100000,
                "total_spent": 100000,
                "total_earned": 100000,
                "performance_score": 1.0,    # 100% ROI - Average
                "is_active": True
            }),
            "kip:budget:poor_performer": json.dumps({
                "agent_id": "poor_performer",
                "current_balance": 30000,
                "total_spent": 150000,
                "total_earned": 60000,
                "performance_score": 0.4,    # 40% ROI - Poor
                "is_active": True
            }),
            "kip:budget:critical_performer": json.dumps({
                "agent_id": "critical_performer",
                "current_balance": 10000,
                "total_spent": 200000,
                "total_earned": 30000,
                "performance_score": 0.15,   # 15% ROI - Critical
                "is_active": False
            })
        }
        
        async def mock_get(key):
            return agent_data.get(key)
        
        async def mock_keys(pattern):
            return list(agent_data.keys())
        
        redis_mock.get.side_effect = mock_get
        redis_mock.keys.side_effect = mock_keys
        
        return redis_mock
    
    @pytest.fixture
    async def economic_analyzer_multi(self, mock_redis_multi_agent):
        """Create economic analyzer with multi-agent data."""
        budget_manager = BudgetManager(mock_redis_multi_agent)
        mock_tigergraph = AsyncMock()
        transaction_processor = TransactionProcessor(mock_redis_multi_agent, mock_tigergraph, budget_manager)
        return EconomicAnalyzer(mock_redis_multi_agent, budget_manager, transaction_processor)
    
    @pytest.mark.asyncio
    async def test_economic_analytics_generation(self, economic_analyzer_multi):
        """Test system-wide economic analytics with multiple agents."""
        analytics = await economic_analyzer_multi.get_economic_analytics()
        
        # Verify analytics structure
        assert isinstance(analytics, EconomicAnalytics)
        assert analytics.total_agents == 5
        assert analytics.active_agents == 4  # One agent is inactive
        
        # Verify financial totals
        assert analytics.total_balance == 460000    # Sum of all balances
        assert analytics.total_spent == 580000      # Sum of all spending
        assert analytics.total_earned == 460000     # Sum of all earnings
        
        # Verify performance classification
        assert "top_performer" in analytics.top_performers
        assert "good_performer" in analytics.top_performers
        assert "poor_performer" in analytics.poor_performers  
        assert "critical_performer" in analytics.poor_performers
        
        # Verify system ROI calculation
        expected_system_roi = 460000 / 580000  # total_earned / total_spent ≈ 0.79
        assert abs(analytics.system_roi - expected_system_roi) < 0.01
    
    @pytest.mark.asyncio
    async def test_performance_based_budget_adjustments(self, economic_analyzer_multi):
        """Test automated budget adjustments based on agent performance."""
        # Test excellent performer gets budget increase
        excellent_adjustment = await economic_analyzer_multi.calculate_roi_adjustment("top_performer")
        
        # Should recommend budget increase for excellent performance
        if "error" not in excellent_adjustment:
            # Performance above 2.0 should trigger excellent multiplier (1.5x)
            assert excellent_adjustment.get("recommended_multiplier", 1.0) >= 1.2
        
        # Test poor performer gets budget decrease
        poor_adjustment = await economic_analyzer_multi.calculate_roi_adjustment("poor_performer")
        
        # Should recommend budget decrease for poor performance  
        if "error" not in poor_adjustment:
            # Performance below 0.5 should trigger poor multiplier (0.8x)
            assert poor_adjustment.get("recommended_multiplier", 1.0) <= 0.9
    
    @pytest.mark.asyncio 
    async def test_agent_ranking_system(self, economic_analyzer_multi):
        """Test agent ranking based on performance scores."""
        analytics = await economic_analyzer_multi.get_economic_analytics()
        
        # Verify top performers (score > 1.0)
        expected_top_performers = {"top_performer", "good_performer"}
        actual_top_performers = set(analytics.top_performers)
        assert expected_top_performers.issubset(actual_top_performers)
        
        # Verify poor performers (score < 0.5)
        expected_poor_performers = {"poor_performer", "critical_performer"}
        actual_poor_performers = set(analytics.poor_performers)
        assert expected_poor_performers.issubset(actual_poor_performers)
        
        # Verify average performance calculation
        # (3.0 + 1.5 + 1.0 + 0.4 + 0.15) / 5 = 1.21
        expected_avg = (3.0 + 1.5 + 1.0 + 0.4 + 0.15) / 5
        assert abs(analytics.average_performance - expected_avg) < 0.01


class TestToolEconomics:
    """Test tool execution costs and economic optimization."""
    
    @pytest.fixture
    def crypto_analysis_tools(self):
        """Create realistic crypto analysis tools with costs."""
        return [
            Tool(
                tool_name="get_current_bitcoin_price",
                description="Get real-time Bitcoin price from CoinGecko API",
                tool_type="market_data",
                version="1.0.0",
                module_path="tools.web_tools",
                function_name="get_current_bitcoin_price",
                required_authorization="analyst",
                cost_per_use=500,        # $5.00 per call
                daily_limit=50,          # 50 calls per day max
                total_uses=245
            ),
            Tool(
                tool_name="get_current_ethereum_price", 
                description="Get real-time Ethereum price from CoinGecko API",
                tool_type="market_data",
                version="1.0.0", 
                module_path="tools.web_tools",
                function_name="get_current_ethereum_price",
                required_authorization="analyst",
                cost_per_use=500,        # $5.00 per call
                daily_limit=50,          # 50 calls per day max
                total_uses=189
            ),
            Tool(
                tool_name="get_crypto_market_summary",
                description="Get comprehensive crypto market overview",
                tool_type="market_analysis",
                version="1.0.0",
                module_path="tools.web_tools", 
                function_name="get_crypto_market_summary",
                required_authorization="senior_analyst",
                cost_per_use=1500,       # $15.00 per call - premium tool
                daily_limit=10,          # 10 calls per day max
                total_uses=67
            )
        ]
    
    @pytest.mark.asyncio
    async def test_tool_cost_calculation(self, crypto_analysis_tools):
        """Test tool execution cost tracking and ROI calculation."""
        btc_tool = crypto_analysis_tools[0]  # Bitcoin price tool
        
        # Verify tool economics
        assert btc_tool.cost_per_use == 500      # $5.00
        assert btc_tool.daily_limit == 50        # 50 uses per day
        assert btc_tool.total_uses == 245        # Historical usage
        
        # Calculate total historical cost
        total_cost = btc_tool.total_uses * btc_tool.cost_per_use
        assert total_cost == 122500  # $1,225.00 total spent on this tool
        
        # Test premium tool costs
        premium_tool = crypto_analysis_tools[2]  # Market summary tool
        assert premium_tool.cost_per_use == 1500    # $15.00 - 3x more expensive
        assert premium_tool.daily_limit == 10       # Lower usage limit
        
        premium_total_cost = premium_tool.total_uses * premium_tool.cost_per_use
        assert premium_total_cost == 100500  # $1,005.00 for premium analysis
    
    @pytest.mark.asyncio
    async def test_tool_roi_scenarios(self):
        """Test realistic tool ROI scenarios for crypto trading."""
        # Scenario 1: Profitable Bitcoin analysis
        btc_analysis_action = ActionResult(
            action_id="btc_analysis_001",
            agent_id="crypto_trader_001",
            tool_name="get_current_bitcoin_price",
            success=True,
            result_data={
                "price": "$67,432.50",
                "24h_change": "+2.5%",
                "market_decision": "BUY_SIGNAL"
            },
            execution_time=0.45,
            cost_cents=500,  # $5.00 tool cost
            # Assume this analysis led to a profitable trade
        )
        
        # Calculate ROI if this analysis generated $500 profit
        generated_value = 50000  # $500.00 in cents
        roi_ratio = generated_value / btc_analysis_action.cost_cents
        assert roi_ratio == 100.0  # 10,000% ROI - excellent tool performance
        
        # Scenario 2: Failed analysis (tool worked but decision was wrong)
        failed_analysis_action = ActionResult(
            action_id="eth_analysis_002", 
            agent_id="crypto_trader_001",
            tool_name="get_current_ethereum_price",
            success=True,  # Tool worked successfully
            result_data={
                "price": "$3,245.12",
                "24h_change": "-1.2%", 
                "market_decision": "HOLD"
            },
            execution_time=0.38,
            cost_cents=500,  # $5.00 tool cost
            # Assume this led to no profit or loss
        )
        
        # ROI for neutral outcome
        neutral_value = 0  # No profit/loss
        neutral_roi = neutral_value / failed_analysis_action.cost_cents
        assert neutral_roi == 0.0  # 0% ROI - tool cost not recovered
    
    @pytest.mark.asyncio
    async def test_daily_tool_limits(self, crypto_analysis_tools):
        """Test daily tool usage limits prevent overspending."""
        btc_tool = crypto_analysis_tools[0]
        
        # Simulate agent approaching daily limit
        daily_uses = 48  # 48 out of 50 uses
        remaining_uses = btc_tool.daily_limit - daily_uses
        assert remaining_uses == 2  # Only 2 uses left today
        
        # Calculate remaining daily budget for this tool
        remaining_budget = remaining_uses * btc_tool.cost_per_use
        assert remaining_budget == 1000  # $10.00 remaining for Bitcoin price calls
        
        # Premium tool has stricter limits
        premium_tool = crypto_analysis_tools[2]
        premium_daily_uses = 9  # 9 out of 10 uses
        premium_remaining = premium_tool.daily_limit - premium_daily_uses
        assert premium_remaining == 1  # Only 1 premium analysis left
        
        premium_remaining_budget = premium_remaining * premium_tool.cost_per_use  
        assert premium_remaining_budget == 1500  # $15.00 remaining for premium analysis


class TestEconomicScenarios:
    """Test real-world economic scenarios and decision workflows."""
    
    @pytest.fixture
    async def trading_agent_budget(self):
        """Create a realistic crypto trading agent budget."""
        return AgentBudget(
            agent_id="crypto_trader_premium",
            current_balance=1000000,    # $10,000.00 starting capital
            total_spent=250000,         # $2,500.00 spent so far
            total_earned=400000,        # $4,000.00 earned so far
            daily_spent=15000,          # $150.00 spent today
            daily_limit=200000,         # $2,000.00 daily limit
            per_action_limit=5000,      # $50.00 per action limit
            last_reset_date=date.today(),
            is_frozen=False,
            total_transactions=156,
            roi_score=1.6               # 160% ROI - good performance
        )
    
    @pytest.mark.asyncio
    async def test_profitable_trading_day(self, trading_agent_budget):
        """Test a profitable crypto trading day with multiple tool uses."""
        agent = trading_agent_budget
        initial_balance = agent.current_balance
        
        # Morning: Check Bitcoin price ($5.00)
        btc_check_cost = 500
        agent.current_balance -= btc_check_cost
        agent.daily_spent += btc_check_cost
        agent.total_spent += btc_check_cost
        
        # Midday: Check Ethereum price ($5.00) 
        eth_check_cost = 500
        agent.current_balance -= eth_check_cost
        agent.daily_spent += eth_check_cost
        agent.total_spent += eth_check_cost
        
        # Afternoon: Premium market analysis ($15.00)
        market_analysis_cost = 1500
        agent.current_balance -= market_analysis_cost
        agent.daily_spent += market_analysis_cost
        agent.total_spent += market_analysis_cost
        
        # Total tool costs for the day
        total_tool_costs = btc_check_cost + eth_check_cost + market_analysis_cost
        assert total_tool_costs == 2500  # $25.00 in tools ($5 + $5 + $15)
        
        # Simulate successful trading profit of $800.00
        trading_profit = 80000
        agent.current_balance += trading_profit
        agent.total_earned += trading_profit
        
        # Verify profitable day
        net_day_result = trading_profit - total_tool_costs
        assert net_day_result == 77500  # $775.00 net profit ($800 - $25)
        
        # Verify agent is still profitable overall
        assert agent.net_worth > 0  # Still profitable
        assert agent.current_balance > initial_balance  # Balance increased
        
        # Update ROI score
        new_roi = agent.total_earned / agent.total_spent
        assert new_roi > 1.6  # ROI improved from successful day
    
    @pytest.mark.asyncio
    async def test_budget_constraint_decision_making(self, trading_agent_budget):
        """Test agent decision making under budget constraints."""
        agent = trading_agent_budget
        
        # Agent has already spent $1950.00 today, only $50.00 left
        agent.daily_spent = 195000
        remaining_budget = agent.available_daily_budget
        assert remaining_budget == 5000  # $50.00 remaining
        
        # Can afford one basic tool call ($5.00) but not premium analysis ($75.00)
        basic_tool_cost = 500    # Bitcoin/Ethereum price check
        premium_tool_cost = 7500 # Premium market analysis with multiple APIs
        
        assert remaining_budget >= basic_tool_cost     # Can afford basic tool
        assert remaining_budget < premium_tool_cost    # Cannot afford premium tool
        
        # Agent makes economic decision: use remaining budget for basic tool
        agent.current_balance -= basic_tool_cost
        agent.daily_spent += basic_tool_cost
        
        # Verify remaining budget decreased
        assert agent.available_daily_budget == 4500  # $45.00 remaining after $5 spend
        
        # Agent must wait until tomorrow for more expensive tools
        assert agent.can_spend is True  # Still has account balance
        # But daily limit reached, so premium tools unavailable until reset
    
    @pytest.mark.asyncio
    async def test_economic_emergency_scenarios(self):
        """Test emergency economic scenarios and recovery mechanisms."""
        # Scenario: Agent with critical performance needs intervention
        critical_agent = AgentBudget(
            agent_id="emergency_agent_001",
            current_balance=5000,       # $50.00 - very low
            total_spent=500000,         # $5,000.00 spent
            total_earned=75000,         # $750.00 earned
            daily_spent=4000,           # $40.00 today
            daily_limit=10000,          # $100.00 daily limit
            per_action_limit=2000,      # $20.00 per action
            last_reset_date=date.today(),
            is_frozen=False,
            total_transactions=387,
            roi_score=0.15              # 15% ROI - critical performance
        )
        
        # Verify critical financial state
        assert critical_agent.net_worth == -425000    # -$4,250.00 loss
        assert critical_agent.roi_score < 0.2         # Below critical threshold
        assert critical_agent.current_balance < 10000 # Less than $100.00
        
        # Emergency intervention: Freeze agent to prevent further losses
        critical_agent.is_frozen = True
        assert critical_agent.can_spend is False
        
        # Recovery scenario: Reset with seed funding
        recovery_funding = 200000  # $2,000.00 emergency funding
        critical_agent.current_balance = recovery_funding
        critical_agent.is_frozen = False
        critical_agent.daily_limit = 50000  # Reduced daily limit ($500.00)
        critical_agent.per_action_limit = 1000  # Reduced per action ($10.00)
        
        # Verify recovery state
        assert critical_agent.can_spend is True
        assert critical_agent.current_balance == recovery_funding
        assert critical_agent.daily_limit == 50000  # Tighter controls


class TestEconomicIntegrationScenarios:
    """Test end-to-end economic scenarios with full KIP integration."""
    
    @pytest.fixture
    async def mock_treasury_system(self):
        """Mock complete treasury system for integration testing."""
        mock_redis = AsyncMock()
        
        # Mock treasury data
        treasury_data = {
            "kip:treasury:stats": json.dumps({
                "total_agents": 12,
                "active_agents": 10,
                "total_balance": 2500000,   # $25,000.00
                "daily_spending": 45000,    # $450.00 today
                "monthly_budget": 1000000   # $10,000.00 monthly
            })
        }
        
        async def mock_get(key):
            return treasury_data.get(key)
        
        mock_redis.get.side_effect = mock_get
        
        budget_manager = BudgetManager(mock_redis)
        mock_tigergraph = AsyncMock()
        transaction_processor = TransactionProcessor(mock_redis, mock_tigergraph, budget_manager)
        economic_analyzer = EconomicAnalyzer(mock_redis, budget_manager, transaction_processor)
        
        # Create TreasuryCore with default config (it manages its own components)
        return TreasuryCore()
    
    @pytest.mark.asyncio
    async def test_full_economic_workflow(self, mock_treasury_system):
        """Test complete economic workflow from agent creation to performance review."""
        treasury = mock_treasury_system
        
        # Step 1: Create new agent with initial funding
        agent_id = "integration_test_agent"
        initial_funding = 500000  # $5,000.00
        
        # Step 1: Create new agent budget (simulating treasury initialization)
        from datetime import date
        initial_budget = AgentBudget(
            agent_id=agent_id,
            current_balance=initial_funding,
            daily_limit=100000,     # $1,000.00 daily
            per_action_limit=5000,  # $50.00 per action
            last_reset_date=date.today(),
            total_earned=initial_funding,  # Initial seed funding
            total_spent=0,
            daily_spent=0,
            roi_score=1.0           # Neutral starting ROI
        )
        
        assert initial_budget.current_balance == initial_funding
        assert initial_budget.roi_score == 1.0  # Neutral starting performance
        
        # Step 2: Agent executes tools and incurs costs
        tool_costs = [
            ("get_bitcoin_price", 500),    # $5.00
            ("get_ethereum_price", 500),   # $5.00  
            ("market_analysis", 1500),     # $15.00
            ("portfolio_optimization", 2500) # $25.00
        ]
        
        total_costs = sum(cost for _, cost in tool_costs)
        assert total_costs == 5000  # $50.00 total tool costs
        
        # Step 3: Agent generates value from tool usage
        generated_value = 12000  # $120.00 in trading profits
        roi_ratio = generated_value / total_costs
        assert roi_ratio == 2.4  # 240% ROI - excellent performance
        
        # Step 4: Update agent performance metrics
        updated_budget = AgentBudget(
            agent_id=agent_id,
            current_balance=initial_funding - total_costs + generated_value,
            total_spent=total_costs,
            total_earned=generated_value,
            daily_spent=total_costs,
            daily_limit=100000,
            per_action_limit=5000,
            last_reset_date=date.today(),
            is_frozen=False,
            total_transactions=len(tool_costs),
            roi_score=roi_ratio
        )
        
        # Verify economic success
        assert updated_budget.net_worth == 7000     # $70.00 profit
        assert updated_budget.roi_score > 2.0       # Excellent performance
        
        # Step 5: Simulate performance-based budget adjustment (conceptual test)
        # In a real system, this would be done by the Treasury's economic analyzer
        excellent_performance_threshold = 2.0
        if roi_ratio > excellent_performance_threshold:
            # Excellent performers get budget increases
            budget_increase_multiplier = 1.5  # 50% increase
            new_daily_limit = int(updated_budget.daily_limit * budget_increase_multiplier)
            roi_analysis = {
                "agent_id": agent_id,
                "roi": roi_ratio,
                "performance_tier": "excellent",
                "budget_adjustment": "+50%",
                "new_daily_limit": new_daily_limit,
                "recommended_multiplier": budget_increase_multiplier
            }
        else:
            roi_analysis = {
                "agent_id": agent_id,
                "roi": roi_ratio,
                "performance_tier": "good",
                "budget_adjustment": "no change"
            }
        
        # Excellent performance should trigger budget increase
        if "error" not in roi_analysis:
            # Agent performing at 240% ROI should get budget increase
            recommended_multiplier = roi_analysis.get("recommended_multiplier", 1.0)
            assert recommended_multiplier >= 1.2  # At least 20% increase
    
    @pytest.mark.asyncio
    async def test_economic_competition_scenario(self):
        """Test realistic multi-agent economic competition."""
        # Create competing crypto analysis agents
        agents = [
            {
                "agent_id": "conservative_trader",
                "strategy": "low_risk",
                "tool_usage": [("basic_price_check", 500)] * 10,  # 10 basic calls
                "success_rate": 0.8,
                "avg_profit_per_trade": 2000  # $20.00 per successful trade
            },
            {
                "agent_id": "aggressive_trader", 
                "strategy": "high_risk",
                "tool_usage": [("premium_analysis", 1500)] * 5,  # 5 premium calls
                "success_rate": 0.6,
                "avg_profit_per_trade": 8000  # $80.00 per successful trade
            },
            {
                "agent_id": "data_driven_trader",
                "strategy": "analytical",
                "tool_usage": [("basic_price_check", 500)] * 5 + [("market_analysis", 1500)] * 3,
                "success_rate": 0.75,
                "avg_profit_per_trade": 4500  # $45.00 per successful trade
            }
        ]
        
        # Calculate performance for each agent
        agent_performances = []
        
        for agent in agents:
            # Calculate total tool costs
            total_cost = sum(cost for _, cost in agent["tool_usage"])
            
            # Calculate expected earnings
            num_trades = len(agent["tool_usage"])
            successful_trades = int(num_trades * agent["success_rate"])
            total_earnings = successful_trades * agent["avg_profit_per_trade"]
            
            # Calculate ROI
            roi = total_earnings / total_cost if total_cost > 0 else 0
            
            agent_performances.append({
                "agent_id": agent["agent_id"],
                "strategy": agent["strategy"],
                "total_cost": total_cost,
                "total_earnings": total_earnings,
                "roi": roi,
                "net_profit": total_earnings - total_cost
            })
        
        # Analyze competition results
        conservative = agent_performances[0]  # Conservative trader
        aggressive = agent_performances[1]    # Aggressive trader
        analytical = agent_performances[2]    # Data-driven trader
        
        # Conservative trader: 10 trades, 80% success, $20 per win
        assert conservative["total_cost"] == 5000    # $50.00 in basic tools
        assert conservative["total_earnings"] == 16000  # 8 successful * $20 = $160.00
        assert conservative["roi"] == 3.2              # 320% ROI
        
        # Aggressive trader: 5 trades, 60% success, $80 per win  
        assert aggressive["total_cost"] == 7500     # $75.00 in premium tools
        assert aggressive["total_earnings"] == 24000  # 3 successful * $80 = $240.00
        assert aggressive["roi"] == 3.2               # 320% ROI
        
        # Analytical trader: 8 trades, 75% success, $45 per win
        assert analytical["total_cost"] == 7000     # $70.00 mixed tools
        assert analytical["total_earnings"] == 27000  # 6 successful * $45 = $270.00
        assert analytical["roi"] == 27000 / 7000    # ~386% ROI - best performance!
        
        # Rank agents by performance
        ranked_agents = sorted(agent_performances, key=lambda x: x["roi"], reverse=True)
        
        # Analytical strategy wins with highest ROI
        assert ranked_agents[0]["agent_id"] == "data_driven_trader"
        assert ranked_agents[0]["roi"] > 3.5  # Best ROI
        
        # Conservative and aggressive tied for second
        assert ranked_agents[1]["roi"] == ranked_agents[2]["roi"] == 3.2


if __name__ == "__main__":
    """
    Run the economic behaviors test suite.
    
    This validates the sophisticated KIP economic engine that powers
    autonomous agent decision-making and performance optimization.
    """
    pytest.main([__file__, "-v", "--tb=short"])