# core/kip/transaction_processor.py
"""
Transaction Processing Module - KIP Treasury

Handles transaction recording, validation, and storage for the economic engine.
Extracted from Treasury for better modularity and maintainability.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import pyTigerGraph as tg
import redis.asyncio as redis
import structlog

from config import Config
from .models import Transaction, TransactionType, AgentBudget
from .budget_manager import BudgetManager


class TransactionProcessor:
    """
    Processes and records financial transactions for KIP agents.
    
    Responsibilities:
    - Transaction validation and recording
    - Dual storage (Redis + TigerGraph)
    - Transaction history tracking
    - Integration with budget management
    """
    
    def __init__(
        self, 
        redis_client: redis.Redis,
        tigergraph_client: Optional[tg.TigerGraphConnection],
        budget_manager: BudgetManager,
        config: Optional[Config] = None
    ):
        """
        Initialize the Transaction Processor.
        
        Args:
            redis_client: Connected Redis client for speed layer
            tigergraph_client: Connected TigerGraph client for audit trail
            budget_manager: Budget manager for balance updates
            config: Optional configuration object
        """
        self.redis = redis_client
        self.tigergraph = tigergraph_client
        self.budget_manager = budget_manager
        self.config = config or Config()
        self.logger = structlog.get_logger("TransactionProcessor")
        
    async def record_transaction(
        self,
        agent_id: str,
        amount: int,
        description: str,
        transaction_type: TransactionType = TransactionType.SPENDING,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Transaction]:
        """
        Record a financial transaction for an agent.
        
        Args:
            agent_id: Agent identifier
            amount: Transaction amount in USD cents (negative for expenses)
            description: Human-readable transaction description
            transaction_type: Type of transaction (EXPENSE, REVENUE, ADJUSTMENT)
            metadata: Optional additional transaction data
            
        Returns:
            Transaction: Recorded transaction or None if failed
        """
        agent_id = agent_id.lower().replace(" ", "_")
        
        # Validate transaction amount
        if amount == 0:
            self.logger.warning(
                "Zero-amount transaction ignored",
                agent_id=agent_id,
                description=description
            )
            return None
            
        # Create transaction record
        now = datetime.now(timezone.utc)
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            agent_id=agent_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            metadata=metadata or {},
            timestamp=now
        )
        
        try:
            # Update agent budget first
            updated_budget = await self.budget_manager.update_budget_balance(agent_id, amount)
            if not updated_budget:
                self.logger.error(
                    "Failed to update budget for transaction",
                    agent_id=agent_id,
                    amount=amount,
                    transaction_id=transaction.transaction_id
                )
                return None
            
            # Store transaction in Redis speed layer
            await self._store_transaction_redis(transaction)
            
            # Store transaction in TigerGraph audit trail (best effort)
            if self.tigergraph:
                await self._store_transaction_tigergraph(transaction)
            
            self.logger.info(
                "Transaction recorded successfully",
                transaction_id=transaction.transaction_id,
                agent_id=agent_id,
                amount=amount,
                new_balance=updated_budget.current_balance,
                description=description
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(
                "Failed to record transaction",
                transaction_id=transaction.transaction_id,
                agent_id=agent_id,
                amount=amount,
                error=str(e),
                exc_info=True
            )
            return None
            
    async def get_transaction_history(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[Transaction]:
        """
        Retrieve transaction history for an agent.
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            
        Returns:
            List of transactions ordered by timestamp (newest first)
        """
        agent_id = agent_id.lower().replace(" ", "_")
        
        try:
            # Get from Redis (recent transactions)
            transaction_key = f"transactions:{agent_id}"
            transaction_data = await self.redis.lrange(transaction_key, offset, offset + limit - 1)
            
            transactions = []
            for data in transaction_data:
                try:
                    transaction_dict = json.loads(data)
                    transaction = Transaction(**transaction_dict)
                    transactions.append(transaction)
                except Exception as parse_error:
                    self.logger.warning(
                        "Failed to parse transaction data",
                        agent_id=agent_id,
                        error=str(parse_error)
                    )
                    continue
                    
            self.logger.debug(
                "Retrieved transaction history",
                agent_id=agent_id,
                count=len(transactions),
                limit=limit,
                offset=offset
            )
            
            return transactions
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve transaction history",
                agent_id=agent_id,
                error=str(e)
            )
            return []
            
    async def calculate_agent_totals(self, agent_id: str) -> Dict[str, Any]:
        """
        Calculate total earnings, spending, and transaction counts for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dict with financial totals and statistics
        """
        agent_id = agent_id.lower().replace(" ", "_")
        
        try:
            transactions = await self.get_transaction_history(agent_id, limit=1000)
            
            total_revenue = 0
            total_expenses = 0
            transaction_count = len(transactions)
            
            for transaction in transactions:
                if transaction.amount > 0:
                    total_revenue += transaction.amount
                else:
                    total_expenses += abs(transaction.amount)
                    
            net_earnings = total_revenue - total_expenses
            
            return {
                "agent_id": agent_id,
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_earnings": net_earnings,
                "transaction_count": transaction_count,
                "average_transaction": (total_revenue + total_expenses) // max(transaction_count, 1)
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to calculate agent totals",
                agent_id=agent_id,
                error=str(e)
            )
            return {
                "agent_id": agent_id,
                "total_revenue": 0,
                "total_expenses": 0,
                "net_earnings": 0,
                "transaction_count": 0,
                "average_transaction": 0
            }
            
    async def _store_transaction_redis(self, transaction: Transaction) -> None:
        """Store transaction in Redis speed layer."""
        try:
            transaction_key = f"transactions:{transaction.agent_id}"
            transaction_data = transaction.model_dump_json()
            
            # Store in list (newest first) with size limit
            pipe = self.redis.pipeline()
            pipe.lpush(transaction_key, transaction_data)
            pipe.ltrim(transaction_key, 0, 999)  # Keep last 1000 transactions
            pipe.expire(transaction_key, 86400 * 30)  # 30 day expiry
            await pipe.execute()
            
        except Exception as e:
            self.logger.error(
                "Failed to store transaction in Redis",
                transaction_id=transaction.transaction_id,
                agent_id=transaction.agent_id,
                error=str(e)
            )
            raise
            
    async def _store_transaction_tigergraph(self, transaction: Transaction) -> None:
        """Store transaction in TigerGraph audit trail (best effort)."""
        if not self.tigergraph:
            return
            
        try:
            # Create transaction vertex
            vertex_data = {
                "primary_id": transaction.transaction_id,
                "agent_id": transaction.agent_id,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type.value,
                "description": transaction.description,
                "metadata": json.dumps(transaction.metadata),
                "timestamp": transaction.timestamp.isoformat()
            }
            
            upsert_result = self.tigergraph.upsertVertex(
                "Transaction",
                transaction.transaction_id,
                vertex_data
            )
            
            if upsert_result.get("accepted_vertices", 0) > 0:
                self.logger.debug(
                    "Transaction stored in TigerGraph",
                    transaction_id=transaction.transaction_id,
                    agent_id=transaction.agent_id
                )
            else:
                self.logger.warning(
                    "Transaction vertex not accepted by TigerGraph",
                    transaction_id=transaction.transaction_id,
                    result=upsert_result
                )
                
            # Create relationship to agent if possible
            try:
                edge_result = self.tigergraph.upsertEdge(
                    "AgentBudget",
                    transaction.agent_id,
                    "HAS_TRANSACTION",
                    "Transaction",
                    transaction.transaction_id,
                    {"amount": transaction.amount}
                )
                
                if edge_result.get("accepted_edges", 0) == 0:
                    self.logger.warning(
                        "Transaction edge not accepted by TigerGraph",
                        transaction_id=transaction.transaction_id,
                        agent_id=transaction.agent_id
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