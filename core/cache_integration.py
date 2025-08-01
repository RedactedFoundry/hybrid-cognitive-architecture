#!/usr/bin/env python3
"""
Cache Integration - LLM Response Caching for Orchestrator
=========================================================

This module provides caching integration for the orchestrator,
automatically caching and retrieving LLM responses to reduce costs
and improve performance.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, Tuple

import structlog

from clients.ollama_client import LLMResponse, OllamaClient
from config import Config

from .prompt_cache import CacheHit, CacheStrategy, PromptCache, PromptCacheConfig


class CachedOllamaClient:
    """
    Ollama client wrapper with intelligent prompt caching.
    
    This wrapper transparently adds caching to Ollama LLM calls,
    providing significant cost savings and performance improvements.
    """
    
    def __init__(self, ollama_client: OllamaClient, config: Optional[Config] = None):
        """
        Initialize the cached Ollama client.
        
        Args:
            ollama_client: The underlying Ollama client
            config: System configuration
        """
        self.ollama_client = ollama_client
        self.config = config or Config()
        self.logger = structlog.get_logger("CachedOllamaClient")
        
        # Initialize cache configuration from main config
        self.cache_config = PromptCacheConfig(
            enabled=self.config.cache_enabled,
            default_ttl_hours=self.config.cache_ttl_hours,
            max_prompt_length=self.config.cache_max_prompt_length,
            similarity_threshold=self.config.cache_similarity_threshold,
            max_cache_size_mb=self.config.cache_max_size_mb,
            cleanup_interval_hours=self.config.cache_cleanup_interval_hours,
            cost_per_token=self.config.cache_cost_per_token
        )
        
        self._cache: Optional[PromptCache] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        if self.cache_config.enabled:
            self._cache = PromptCache(self.config, self.cache_config)
            await self._cache._connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._cache:
            await self._cache._disconnect()
            
    def _create_cache_context(self, model_alias: str, **kwargs) -> str:
        """
        Create cache context from request parameters.
        
        Args:
            model_alias: The model being used
            **kwargs: Additional parameters that affect the response
            
        Returns:
            Context string for cache key generation
        """
        context_parts = [f"model:{model_alias}"]
        
        # Include relevant parameters that affect response generation
        for key in ["temperature", "top_p", "top_k", "max_tokens", "system_prompt"]:
            if key in kwargs and kwargs[key] is not None:
                context_parts.append(f"{key}:{kwargs[key]}")
                
        return "|".join(context_parts)
        
    async def generate_response(
        self,
        prompt: str,
        model_alias: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response with intelligent caching.
        
        This method checks the cache first and falls back to the actual LLM
        if no suitable cached response is found.
        
        Args:
            prompt: The user prompt
            model_alias: Model to use for generation
            system_prompt: Optional system prompt
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResponse with generated text and metadata
        """
        start_time = time.time()
        
        # Create cache context
        context = self._create_cache_context(
            model_alias=model_alias,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Check cache first
        cache_hit = None
        if self._cache and self.cache_config.enabled:
            try:
                cache_hit = await self._cache.get_cached_response(
                    prompt=prompt,
                    context=context,
                    strategy=CacheStrategy.EXACT_MATCH
                )
                
                if cache_hit:
                    # Return cached response
                    cache_time = time.time() - start_time
                    
                    self.logger.info(
                        "Using cached LLM response",
                        model_alias=model_alias,
                        cache_key=cache_hit.cache_key[:12],
                        hit_count=cache_hit.hit_count,
                        cache_time_ms=cache_time * 1000,
                        similarity_score=cache_hit.similarity_score
                    )
                    
                    return LLMResponse(
                        text=cache_hit.response,
                        model=model_alias,
                        tokens_generated=len(cache_hit.response.split()),  # Rough estimate
                        generation_time=cache_time,
                        success=True,
                        error=None
                    )
                    
            except Exception as e:
                self.logger.warning("Cache lookup failed, proceeding with LLM call", error=str(e))
                
        # Cache miss - generate response using actual LLM
        try:
            llm_response = await self.ollama_client.generate_response(
                prompt=prompt,
                model_alias=model_alias,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Cache the response if successful and caching is enabled
            if (llm_response.success and self._cache and 
                self.cache_config.enabled and llm_response.text):
                
                try:
                    cache_metadata = {
                        "model_alias": model_alias,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "tokens_generated": llm_response.tokens_generated,
                        "generation_time": llm_response.generation_time,
                        "system_prompt": system_prompt
                    }
                    
                    await self._cache.cache_response(
                        prompt=prompt,
                        response=llm_response.text,
                        context=context,
                        metadata=cache_metadata
                    )
                    
                    self.logger.info(
                        "LLM response cached successfully",
                        model_alias=model_alias,
                        response_length=len(llm_response.text),
                        generation_time_ms=llm_response.generation_time * 1000,
                        tokens_generated=llm_response.tokens_generated
                    )
                    
                except Exception as e:
                    self.logger.warning("Failed to cache LLM response", error=str(e))
                    
            return llm_response
            
        except Exception as e:
            self.logger.error("LLM generation failed", error=str(e))
            raise
            
    async def generate_response_stream(self, *args, **kwargs):
        """
        Generate streaming response.
        
        Note: Streaming responses are not cached by design since they're
        real-time and caching would defeat the purpose of streaming.
        """
        # Pass through to underlying client - no caching for streaming
        async for event in self.ollama_client.generate_response_stream(*args, **kwargs):
            yield event
            
    async def health_check(self) -> bool:
        """Check health of underlying Ollama client."""
        return await self.ollama_client.health_check()
        
    async def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache performance statistics."""
        if self._cache:
            stats = await self._cache.get_cache_stats()
            return stats.model_dump()
        return None
        
    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries."""
        if self._cache:
            return await self._cache.clear_cache(pattern)
        return 0


class OrchestratorCacheManager:
    """
    Manages caching for the entire orchestrator system.
    
    This class provides cache management capabilities for different
    types of prompts and responses within the cognitive architecture.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the cache manager.
        
        Args:
            config: System configuration
        """
        self.config = config or Config()
        self.logger = structlog.get_logger("OrchestratorCacheManager")
        self._cache: Optional[PromptCache] = None
        self._cached_clients: Dict[str, CachedOllamaClient] = {}
        
    async def __aenter__(self):
        """Async context manager entry."""
        if self.config.cache_enabled:
            cache_config = PromptCacheConfig(
                enabled=self.config.cache_enabled,
                default_ttl_hours=self.config.cache_ttl_hours,
                max_prompt_length=self.config.cache_max_prompt_length,
                similarity_threshold=self.config.cache_similarity_threshold,
                max_cache_size_mb=self.config.cache_max_size_mb,
                cleanup_interval_hours=self.config.cache_cleanup_interval_hours,
                cost_per_token=self.config.cache_cost_per_token
            )
            
            self._cache = PromptCache(self.config, cache_config)
            await self._cache._connect()
            
            self.logger.info(
                "Orchestrator cache manager initialized",
                cache_enabled=self.config.cache_enabled,
                ttl_hours=self.config.cache_ttl_hours
            )
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._cache:
            await self._cache._disconnect()
            
        for client in self._cached_clients.values():
            if hasattr(client, '_cache') and client._cache:
                await client._cache._disconnect()
                
    def get_cached_ollama_client(self, ollama_client: OllamaClient) -> CachedOllamaClient:
        """
        Get a cached wrapper for an Ollama client.
        
        Args:
            ollama_client: The underlying Ollama client
            
        Returns:
            CachedOllamaClient wrapper
        """
        client_id = id(ollama_client)
        
        if client_id not in self._cached_clients:
            self._cached_clients[client_id] = CachedOllamaClient(ollama_client, self.config)
            
        return self._cached_clients[client_id]
        
    async def get_orchestrator_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics for the orchestrator."""
        stats = {
            "cache_enabled": self.config.cache_enabled,
            "cache_ttl_hours": self.config.cache_ttl_hours,
            "clients_cached": len(self._cached_clients),
            "cache_stats": None
        }
        
        if self._cache:
            cache_stats = await self._cache.get_cache_stats()
            stats["cache_stats"] = cache_stats.model_dump()
            
        return stats
        
    async def perform_cache_cleanup(self) -> Dict[str, int]:
        """Perform cache cleanup across all cache instances."""
        cleanup_results = {"main_cache": 0, "client_caches": 0}
        
        if self._cache:
            cleanup_results["main_cache"] = await self._cache.cleanup_expired()
            
        for client in self._cached_clients.values():
            if hasattr(client, '_cache') and client._cache:
                client_cleanup = await client._cache.cleanup_expired()
                cleanup_results["client_caches"] += client_cleanup
                
        self.logger.info("Cache cleanup completed", results=cleanup_results)
        return cleanup_results


# Global cache manager instance
_global_cache_manager: Optional[OrchestratorCacheManager] = None


async def get_global_cache_manager(config: Optional[Config] = None) -> OrchestratorCacheManager:
    """Get or create the global cache manager instance."""
    global _global_cache_manager
    
    if _global_cache_manager is None:
        _global_cache_manager = OrchestratorCacheManager(config)
        await _global_cache_manager.__aenter__()
        
    return _global_cache_manager


async def cleanup_global_cache_manager() -> None:
    """Clean up the global cache manager instance."""
    global _global_cache_manager
    
    if _global_cache_manager:
        await _global_cache_manager.__aexit__(None, None, None)
        _global_cache_manager = None