# core/pheromind.py
"""
Pheromind Layer - The Ambient Intelligence System

This module implements the "ambient intelligence" layer of the Hybrid AI Council.
Pheromines are short-lived signals (12s TTL) that capture patterns, insights, and
contextual information across agent interactions.

The Pheromind Layer enables:
- Pattern detection across conversations
- Ambient context awareness  
- Emergent intelligence from signal correlation
- Decision-making influenced by recent system activity
"""

import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Set
from contextlib import asynccontextmanager

import redis.asyncio as redis
from pydantic import BaseModel, Field
import structlog

# Clean config import
from config import Config


# Replicate the PheromindSignal from orchestrator.py for consistency
class PheromindSignal(BaseModel):
    """
    Represents a pheromone signal detected during ambient processing.
    
    Pheromones have a 12-second TTL and influence decision-making patterns
    across the cognitive architecture.
    """
    pattern_id: str = Field(description="Unique identifier for the detected pattern")
    strength: float = Field(ge=0.0, le=1.0, description="Signal strength (0-1)")
    source_agent: str = Field(description="Agent that generated this pheromone")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(description="When this pheromone expires (12s TTL)")
    content: str = Field(description="Pattern description or content")


class PheromindAnalytics(BaseModel):
    """Analytics data for pheromind system monitoring."""
    total_signals: int = 0
    active_signals: int = 0
    strongest_signal: Optional[float] = None
    most_active_agent: Optional[str] = None
    pattern_diversity: int = 0
    avg_signal_strength: float = 0.0


class PheromindLayer:
    """
    The Pheromind Layer manages ambient intelligence through pheromone signals.
    
    This layer provides:
    - Signal storage and retrieval with automatic TTL management
    - Pattern-based querying for context-aware decision making
    - Signal analytics for system observability
    - Connection pooling for high-performance Redis operations
    """
    
    PHEROMIND_TTL = 12  # seconds - critical timing for ambient intelligence
    PHEROMIND_PREFIX = "pheromind:signal:"
    ANALYTICS_KEY = "pheromind:analytics"
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Pheromind Layer.
        
        Args:
            config: Optional configuration object. If None, uses environment variables.
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("PheromindLayer")
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
        
    async def __aenter__(self):
        """Async context manager entry - establish Redis connection."""
        await self._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup Redis connection."""
        await self._disconnect()
        
    async def _connect(self) -> None:
        """Establish async Redis connection with connection pooling."""
        try:
            # Create connection pool for high performance
            self._redis_pool = redis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                decode_responses=True,
                max_connections=20,  # Pool for concurrent operations
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            self._redis = redis.Redis(connection_pool=self._redis_pool)
            
            # Verify connection
            await self._redis.ping()
            
            self.logger.info(
                "Pheromind Layer connected to Redis",
                redis_host=self.config.redis_host,
                redis_port=self.config.redis_port
            )
            
        except redis.ConnectionError as e:
            self.logger.error(
                "Failed to connect to Redis for Pheromind Layer",
                error=str(e),
                redis_host=self.config.redis_host,
                redis_port=self.config.redis_port
            )
            raise ConnectionError(f"Redis connection failed: {e}")
            
    async def _disconnect(self) -> None:
        """Clean shutdown of Redis connections."""
        if self._redis:
            await self._redis.close()
        if self._redis_pool:
            await self._redis_pool.disconnect()
            
    def _generate_signal_key(self, signal: PheromindSignal) -> str:
        """Generate Redis key for a pheromind signal."""
        return f"{self.PHEROMIND_PREFIX}{signal.pattern_id}:{signal.source_agent}:{int(signal.detected_at.timestamp())}"
        
    async def add_signal(self, signal: PheromindSignal) -> bool:
        """
        Add a pheromind signal to Redis with 12-second TTL.
        
        Args:
            signal: PheromindSignal object to store
            
        Returns:
            bool: True if signal was successfully stored, False otherwise
            
        Raises:
            ConnectionError: If Redis is unavailable
            ValueError: If signal data is invalid
        """
        if not self._redis:
            raise ConnectionError("Pheromind Layer not connected to Redis")
            
        try:
            # Set expires_at if not already set
            if not hasattr(signal, 'expires_at') or signal.expires_at is None:
                signal.expires_at = signal.detected_at + timedelta(seconds=self.PHEROMIND_TTL)
                
            # Generate unique key for this signal
            signal_key = self._generate_signal_key(signal)
            
            # Serialize signal to JSON
            signal_data = signal.model_dump(mode='json')
            signal_json = json.dumps(signal_data, default=str)
            
            # Store with TTL (simplified approach)
            success = await self._redis.setex(signal_key, self.PHEROMIND_TTL, signal_json)
            
            if success:
                self.logger.info(
                    "Pheromind signal stored",
                    pattern_id=signal.pattern_id,
                    source_agent=signal.source_agent,
                    strength=signal.strength,
                    ttl_seconds=self.PHEROMIND_TTL,
                    signal_key=signal_key
                )
                
                # Update analytics asynchronously
                asyncio.create_task(self._update_analytics(signal))
                
            return bool(success)
            
        except (redis.RedisError, json.JSONEncodeError, ValueError) as e:
            self.logger.error(
                "Failed to store pheromind signal",
                pattern_id=signal.pattern_id,
                source_agent=signal.source_agent,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    async def query_signals(self, pattern: str, min_strength: float = 0.0) -> List[PheromindSignal]:
        """
        Query Redis for active pheromind signals matching a pattern.
        
        Args:
            pattern: Pattern to search for (supports Redis KEYS pattern matching)
            min_strength: Minimum signal strength filter (0.0-1.0)
            
        Returns:
            List[PheromindSignal]: List of matching active signals, sorted by strength
            
        Raises:
            ConnectionError: If Redis is unavailable
        """
        if not self._redis:
            raise ConnectionError("Pheromind Layer not connected to Redis")
            
        try:
            # Build search pattern for Redis keys
            search_pattern = f"{self.PHEROMIND_PREFIX}*{pattern}*"
            
            # Get all matching keys
            matching_keys = await self._redis.keys(search_pattern)
            
            if not matching_keys:
                self.logger.debug(
                    "No pheromind signals found for pattern",
                    pattern=pattern,
                    search_pattern=search_pattern
                )
                return []
                
            # Retrieve all signals in parallel using pipeline
            signals = []
            async with self._redis.pipeline() as pipe:
                for key in matching_keys:
                    await pipe.get(key)
                signal_data_list = await pipe.execute()
                
            # Parse and filter signals
            for i, signal_data in enumerate(signal_data_list):
                if signal_data is None:  # Key expired between keys() and get()
                    continue
                    
                try:
                    signal_dict = json.loads(signal_data)
                    
                    # Parse datetime fields
                    signal_dict['detected_at'] = datetime.fromisoformat(signal_dict['detected_at'].replace('Z', '+00:00'))
                    signal_dict['expires_at'] = datetime.fromisoformat(signal_dict['expires_at'].replace('Z', '+00:00'))
                    
                    signal = PheromindSignal(**signal_dict)
                    
                    # Filter by strength and expiration
                    if (signal.strength >= min_strength and 
                        signal.expires_at > datetime.now(timezone.utc)):
                        signals.append(signal)
                        
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.warning(
                        "Failed to parse pheromind signal",
                        key=matching_keys[i],
                        error=str(e)
                    )
                    continue
                    
            # Sort by strength (strongest first)
            signals.sort(key=lambda s: s.strength, reverse=True)
            
            self.logger.info(
                "Pheromind query completed",
                pattern=pattern,
                signals_found=len(signals),
                min_strength=min_strength,
                strongest_signal=signals[0].strength if signals else None
            )
            
            return signals
            
        except redis.RedisError as e:
            self.logger.error(
                "Failed to query pheromind signals",
                pattern=pattern,
                error=str(e)
            )
            return []
            
    async def get_active_patterns(self) -> Set[str]:
        """
        Get all unique pattern IDs currently active in the pheromind.
        
        Returns:
            Set[str]: Set of unique pattern IDs with active signals
        """
        try:
            all_signals = await self.query_signals("*")  # Get all active signals
            return {signal.pattern_id for signal in all_signals}
        except Exception as e:
            self.logger.error("Failed to get active patterns", error=str(e))
            return set()
            
    async def get_agent_signals(self, agent_name: str) -> List[PheromindSignal]:
        """
        Get all active signals from a specific agent.
        
        Args:
            agent_name: Name of the agent to query
            
        Returns:
            List[PheromindSignal]: List of signals from the specified agent
        """
        return await self.query_signals(f"*:{agent_name}:*")
        
    async def cleanup_expired_signals(self) -> int:
        """
        Manually cleanup expired signals (Redis TTL should handle this automatically).
        
        Returns:
            int: Number of signals cleaned up
        """
        try:
            all_keys = await self._redis.keys(f"{self.PHEROMIND_PREFIX}*")
            expired_keys = []
            
            for key in all_keys:
                ttl = await self._redis.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_keys.append(key)
                    
            if expired_keys:
                await self._redis.delete(*expired_keys)
                
            self.logger.info(
                "Pheromind cleanup completed",
                expired_signals=len(expired_keys),
                total_keys_checked=len(all_keys)
            )
            
            return len(expired_keys)
            
        except redis.RedisError as e:
            self.logger.error("Failed to cleanup expired signals", error=str(e))
            return 0
            
    async def get_analytics(self) -> PheromindAnalytics:
        """
        Get analytics about current pheromind activity.
        
        Returns:
            PheromindAnalytics: Current system analytics
        """
        try:
            all_signals = await self.query_signals("*")
            
            if not all_signals:
                return PheromindAnalytics()
                
            # Calculate analytics
            agent_counts = {}
            pattern_ids = set()
            total_strength = 0.0
            max_strength = 0.0
            
            for signal in all_signals:
                agent_counts[signal.source_agent] = agent_counts.get(signal.source_agent, 0) + 1
                pattern_ids.add(signal.pattern_id)
                total_strength += signal.strength
                max_strength = max(max_strength, signal.strength)
                
            most_active_agent = max(agent_counts.items(), key=lambda x: x[1])[0] if agent_counts else None
            
            return PheromindAnalytics(
                total_signals=len(all_signals),
                active_signals=len(all_signals),
                strongest_signal=max_strength,
                most_active_agent=most_active_agent,
                pattern_diversity=len(pattern_ids),
                avg_signal_strength=total_strength / len(all_signals) if all_signals else 0.0
            )
            
        except Exception as e:
            self.logger.error("Failed to generate pheromind analytics", error=str(e))
            return PheromindAnalytics()
            
    async def _update_analytics(self, signal: PheromindSignal) -> None:
        """Update analytics counters (fire-and-forget)."""
        try:
            analytics_key = f"{self.ANALYTICS_KEY}:counters"
            async with self._redis.pipeline() as pipe:
                await pipe.hincrby(analytics_key, "total_signals", 1)
                await pipe.hincrby(analytics_key, f"agent:{signal.source_agent}", 1)
                await pipe.expire(analytics_key, 300)  # 5 minute analytics window
                await pipe.execute()
        except (ConnectionError, TimeoutError, RuntimeError, redis.exceptions.RedisError):
            pass  # Analytics updates are non-critical


# Convenience function for standalone usage
async def create_pheromind_layer(config: Optional[Config] = None) -> PheromindLayer:
    """
    Create and initialize a PheromindLayer instance.
    
    Args:
        config: Optional configuration object
        
    Returns:
        PheromindLayer: Ready-to-use pheromind layer instance
    """
    layer = PheromindLayer(config)
    await layer._connect()
    return layer


@asynccontextmanager
async def pheromind_session(config: Optional[Config] = None):
    """
    Async context manager for pheromind operations.
    
    Usage:
        async with pheromind_session() as pheromind:
            await pheromind.add_signal(signal)
            signals = await pheromind.query_signals("pattern*")
    """
    layer = PheromindLayer(config)
    try:
        await layer._connect()
        yield layer
    finally:
        await layer._disconnect()