#!/usr/bin/env python3
"""
Test suite for the prompt caching system.
"""

import asyncio
import pytest
import redis.exceptions  # Add redis import for redis.exceptions.RedisError usage
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from core.prompt_cache import PromptCache, PromptCacheConfig, CacheStrategy
from core.cache_integration import CachedOllamaClient, OrchestratorCacheManager
from clients.ollama_client import LLMResponse
from config import Config


class TestPromptCache:
    """Test cases for the PromptCache class."""
    
    @pytest.fixture
    async def mock_redis(self):
        """Create a mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        redis_mock.delete.return_value = 1
        redis_mock.keys.return_value = []
        redis_mock.exists.return_value = True
        return redis_mock
    
    @pytest.fixture
    def cache_config(self):
        """Create test cache configuration."""
        return PromptCacheConfig(
            enabled=True,
            default_ttl_hours=1,
            max_prompt_length=1000,
            similarity_threshold=0.85,
            max_cache_size_mb=10,
            cleanup_interval_hours=1,
            cost_per_token=0.0001
        )
    
    @pytest.fixture
    async def prompt_cache(self, mock_redis, cache_config):
        """Create a PromptCache instance with mocked Redis."""
        cache = PromptCache(config=Config(), cache_config=cache_config)
        cache._redis = mock_redis
        return cache
    
    async def test_cache_response_and_retrieval(self, prompt_cache):
        """Test caching and retrieving a response."""
        prompt = "What is the capital of France?"
        response = "Paris is the capital of France."
        
        # Cache the response
        success = await prompt_cache.cache_response(prompt, response)
        assert success is True
        
        # Verify setex was called twice (response + stats)
        assert prompt_cache._redis.setex.call_count == 2
        
    async def test_cache_hit(self, prompt_cache):
        """Test successful cache hit."""
        prompt = "What is 2 + 2?"
        cached_response = "4"
        
        # Mock Redis to return cached data
        cache_data = {
            "response": cached_response,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "hit_count": 0,
            "metadata": {},
            "prompt_length": len(prompt),
            "response_length": len(cached_response)
        }
        
        import json
        prompt_cache._redis.get.return_value = json.dumps(cache_data)
        
        # Retrieve from cache
        cache_hit = await prompt_cache.get_cached_response(prompt)
        
        assert cache_hit is not None
        assert cache_hit.response == cached_response
        assert cache_hit.similarity_score == 1.0  # Exact match
        
    async def test_cache_miss(self, prompt_cache):
        """Test cache miss scenario."""
        prompt = "What is the meaning of life?"
        
        # Mock Redis to return None (cache miss)
        prompt_cache._redis.get.return_value = None
        
        # Attempt to retrieve from cache
        cache_hit = await prompt_cache.get_cached_response(prompt)
        
        assert cache_hit is None
        
    async def test_prompt_too_long(self, prompt_cache):
        """Test that overly long prompts are not cached."""
        prompt = "x" * 2000  # Exceeds max_prompt_length
        response = "This is a response."
        
        success = await prompt_cache.cache_response(prompt, response)
        assert success is False
        
    async def test_cache_stats(self, prompt_cache):
        """Test cache statistics functionality."""
        stats = await prompt_cache.get_cache_stats()
        
        assert stats.total_requests >= 0
        assert stats.cache_hits >= 0
        assert stats.cache_misses >= 0
        assert stats.hit_rate >= 0.0
        
    async def test_clear_cache(self, prompt_cache):
        """Test cache clearing functionality."""
        # Mock some keys
        prompt_cache._redis.keys.return_value = ["prompt_cache:exact:abc123", "prompt_cache:exact:def456"]
        prompt_cache._redis.delete.return_value = 2
        
        deleted = await prompt_cache.clear_cache()
        assert deleted == 2


class TestCachedOllamaClient:
    """Test cases for the CachedOllamaClient wrapper."""
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client."""
        client = AsyncMock()
        client.generate_response.return_value = LLMResponse(
            text="This is a test response.",
            model="test-model",
            tokens_generated=10,
            generation_time=0.5,
            success=True
        )
        client.health_check.return_value = True
        return client
    
    @pytest.fixture
    def mock_config(self):
        """Create test configuration."""
        config = Config()
        config.cache_enabled = True
        config.cache_ttl_hours = 1
        config.cache_max_prompt_length = 1000
        return config
    
    @pytest.fixture
    async def cached_client(self, mock_ollama_client, mock_config):
        """Create a CachedOllamaClient instance."""
        client = CachedOllamaClient(mock_ollama_client, mock_config)
        
        # Mock the cache
        client._cache = AsyncMock()
        client._cache.get_cached_response.return_value = None  # Cache miss by default
        client._cache.cache_response.return_value = True
        
        return client
    
    async def test_cache_miss_calls_llm(self, cached_client):
        """Test that cache miss results in LLM call."""
        prompt = "Test prompt"
        
        # Ensure cache miss
        cached_client._cache.get_cached_response.return_value = None
        
        response = await cached_client.generate_response(prompt, "test-model")
        
        # Verify LLM was called
        cached_client.ollama_client.generate_response.assert_called_once()
        
        # Verify response was cached
        cached_client._cache.cache_response.assert_called_once()
        
        assert response.success is True
        assert response.text == "This is a test response."
        
    async def test_cache_hit_skips_llm(self, cached_client):
        """Test that cache hit skips LLM call."""
        from core.prompt_cache import CacheHit
        
        prompt = "Test prompt"
        cached_response = "Cached response"
        
        # Mock cache hit
        cache_hit = CacheHit(
            response=cached_response,
            cached_at=datetime.now(timezone.utc),
            hit_count=1,
            metadata={},
            cache_key="test_key"
        )
        cached_client._cache.get_cached_response.return_value = cache_hit
        
        response = await cached_client.generate_response(prompt, "test-model")
        
        # Verify LLM was NOT called
        cached_client.ollama_client.generate_response.assert_not_called()
        
        assert response.success is True
        assert response.text == cached_response
        
    async def test_health_check_passthrough(self, cached_client):
        """Test that health check passes through to underlying client."""
        result = await cached_client.health_check()
        
        cached_client.ollama_client.health_check.assert_called_once()
        assert result is True


class TestOrchestratorCacheManager:
    """Test cases for the OrchestratorCacheManager."""
    
    @pytest.fixture
    def mock_config(self):
        """Create test configuration."""
        config = Config()
        config.cache_enabled = True
        return config
    
    @pytest.fixture
    async def cache_manager(self, mock_config):
        """Create an OrchestratorCacheManager instance."""
        manager = OrchestratorCacheManager(mock_config)
        
        # Mock the cache
        manager._cache = AsyncMock()
        # Return a proper CacheStats instance instead of AsyncMock to avoid coroutine warning
        from core.prompt_cache import CacheStats
        manager._cache.get_cache_stats.return_value = CacheStats(
            total_requests=10,
            cache_hits=5,
            cache_misses=5,
            hit_rate=0.5,
            avg_response_time_cached=0.1,
            avg_response_time_uncached=1.0,
            total_cost_saved=5.0,
            storage_used_mb=2.5
        )
        
        return manager
    
    async def test_get_cached_ollama_client(self, cache_manager):
        """Test getting a cached Ollama client."""
        mock_ollama_client = AsyncMock()
        
        cached_client = cache_manager.get_cached_ollama_client(mock_ollama_client)
        
        assert isinstance(cached_client, CachedOllamaClient)
        assert cached_client.ollama_client == mock_ollama_client
        
    async def test_cache_stats(self, cache_manager):
        """Test getting cache statistics."""
        stats = await cache_manager.get_orchestrator_cache_stats()
        
        assert "cache_enabled" in stats
        assert "cache_ttl_hours" in stats
        assert "clients_cached" in stats
        
    async def test_cache_cleanup(self, cache_manager):
        """Test cache cleanup functionality."""
        # Mock cleanup results
        cache_manager._cache.cleanup_expired.return_value = 5
        
        results = await cache_manager.perform_cache_cleanup()
        
        assert "main_cache" in results
        assert results["main_cache"] == 5


# Integration test
async def test_end_to_end_caching():
    """End-to-end test of the caching system."""
    # This test requires Redis to be running
    try:
        from core.cache_integration import get_global_cache_manager
        
        config = Config()
        config.cache_enabled = True
        
        async with OrchestratorCacheManager(config) as cache_manager:
            # Test that manager initializes correctly
            assert cache_manager.config.cache_enabled is True
            
            # Get cache stats
            stats = await cache_manager.get_orchestrator_cache_stats()
            assert stats["cache_enabled"] is True
            
    except (ConnectionError, ImportError, ModuleNotFoundError, redis.exceptions.RedisError):
        # Skip if Redis is not available
        pytest.skip("Redis not available for integration test")


if __name__ == "__main__":
    # Run a simple test
    async def simple_test():
        print("🧪 Running simple prompt cache test...")
        
        config = PromptCacheConfig(enabled=True, default_ttl_hours=1)
        
        # Mock Redis for testing
        cache = PromptCache(Config(), config)
        cache._redis = AsyncMock()
        cache._redis.ping.return_value = True
        cache._redis.get.return_value = None
        cache._redis.setex.return_value = True
        
        # Test caching
        success = await cache.cache_response("Test prompt", "Test response")
        print(f"✅ Cache response: {success}")
        
        # Test retrieval
        hit = await cache.get_cached_response("Test prompt")
        print(f"✅ Cache retrieval: {hit}")
        
        print("🎉 Simple test completed!")
    
    asyncio.run(simple_test())