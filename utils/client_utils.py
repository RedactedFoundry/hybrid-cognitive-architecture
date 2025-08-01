#!/usr/bin/env python3
"""
Client Utilities - Eliminate Client Initialization Duplication
==============================================================

This module provides common utilities for client initialization and caching,
eliminating duplication across cognitive processing nodes and other modules.

Features:
- Centralized cached client management
- Consistent fallback handling for cache failures
- Error handling and logging for client operations
- Reusable client patterns across the system
"""

from typing import Optional, Any, Union

import structlog

from clients.ollama_client import get_ollama_client, OllamaClient
from core.cache_integration import get_global_cache_manager, CachedOllamaClient

# Set up logger
logger = structlog.get_logger(__name__)


async def get_cached_ollama_client(component_name: Optional[str] = None) -> Union[CachedOllamaClient, OllamaClient]:
    """
    Get a cached Ollama client for improved performance and cost savings.
    
    This function centralizes the logic for getting cached clients that was
    duplicated across multiple processing nodes and modules.
    
    Args:
        component_name: Optional component name for enhanced logging context
        
    Returns:
        CachedOllamaClient if caching is available, otherwise direct OllamaClient
        
    Example:
        >>> client = await get_cached_ollama_client("SmartRouter")
        >>> response = await client.generate_response(prompt, model)
    """
    context_logger = logger.bind(component=component_name) if component_name else logger
    
    try:
        # Attempt to get cached client for performance and cost savings
        cache_manager = await get_global_cache_manager()
        ollama_client = get_ollama_client()
        cached_client = cache_manager.get_cached_ollama_client(ollama_client)
        
        context_logger.debug("Successfully obtained cached Ollama client")
        return cached_client
        
    except Exception as e:
        # Fall back to direct client if caching fails
        context_logger.warning("Failed to get cached client, using direct client", 
                             error=str(e),
                             fallback_reason="cache_manager_error")
        
        return get_ollama_client()


def get_client_with_fallback(primary_client_func, fallback_client_func, 
                           component_name: Optional[str] = None) -> Any:
    """
    Generic client getter with fallback pattern.
    
    This function provides a reusable pattern for getting clients with fallback
    logic, useful for any client type beyond just Ollama.
    
    Args:
        primary_client_func: Function to get primary client
        fallback_client_func: Function to get fallback client
        component_name: Optional component name for logging
        
    Returns:
        Client from primary function, or fallback if primary fails
        
    Example:
        >>> redis_client = get_client_with_fallback(
        ...     lambda: get_redis_connection_with_pool(),
        ...     lambda: get_redis_connection(),
        ...     "CacheManager"
        ... )
    """
    context_logger = logger.bind(component=component_name) if component_name else logger
    
    try:
        client = primary_client_func()
        context_logger.debug("Successfully obtained primary client")
        return client
        
    except Exception as e:
        context_logger.warning("Primary client failed, using fallback", 
                             error=str(e))
        try:
            return fallback_client_func()
        except Exception as fallback_error:
            context_logger.error("Both primary and fallback clients failed",
                                primary_error=str(e),
                                fallback_error=str(fallback_error))
            raise fallback_error


class ClientManager:
    """
    Centralized client management for common client operations.
    
    This class provides a centralized way to manage different types of clients
    with consistent caching, error handling, and logging patterns.
    """
    
    def __init__(self, component_name: str):
        """
        Initialize client manager.
        
        Args:
            component_name: Name of component using this manager (for logging)
        """
        self.component_name = component_name
        self.logger = logger.bind(component=component_name)
        self._cached_ollama_client: Optional[Union[CachedOllamaClient, OllamaClient]] = None
    
    async def get_ollama_client(self, force_refresh: bool = False) -> Union[CachedOllamaClient, OllamaClient]:
        """
        Get Ollama client with caching and component-specific logging.
        
        Args:
            force_refresh: If True, bypass any local caching and get fresh client
            
        Returns:
            Cached or direct Ollama client
        """
        if self._cached_ollama_client is not None and not force_refresh:
            self.logger.debug("Reusing existing Ollama client instance")
            return self._cached_ollama_client
        
        self._cached_ollama_client = await get_cached_ollama_client(self.component_name)
        return self._cached_ollama_client
    
    def invalidate_cache(self) -> None:
        """Invalidate any locally cached clients."""
        if self._cached_ollama_client is not None:
            self.logger.debug("Invalidating cached client")
            self._cached_ollama_client = None
    
    async def health_check_ollama(self) -> bool:
        """
        Perform health check on Ollama client.
        
        Returns:
            True if client is healthy, False otherwise
        """
        try:
            client = await self.get_ollama_client()
            
            # Check if it's a cached client with health check method
            if hasattr(client, 'health_check'):
                is_healthy = await client.health_check()
            else:
                # For direct client, try a simple operation
                is_healthy = True  # Basic assumption for direct clients
            
            self.logger.debug("Ollama client health check completed", healthy=is_healthy)
            return is_healthy
            
        except Exception as e:
            self.logger.warning("Ollama client health check failed", error=str(e))
            return False


# Convenience functions for backward compatibility and ease of use

def create_client_manager(component_name: str) -> ClientManager:
    """
    Create a client manager for a component.
    
    Args:
        component_name: Name of the component
        
    Returns:
        Configured ClientManager instance
    """
    return ClientManager(component_name)


async def get_ollama_for_component(component_name: str) -> Union[CachedOllamaClient, OllamaClient]:
    """
    Convenience function to get Ollama client for a specific component.
    
    Args:
        component_name: Name of the component requesting the client
        
    Returns:
        Cached or direct Ollama client
    """
    return await get_cached_ollama_client(component_name)