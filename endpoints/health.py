"""
Health and Cache Endpoints for Hybrid AI Council
================================================

Health monitoring and cache management endpoints.
Extracted from main.py for better modularity and maintainability.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter
import structlog

from clients.llama_cpp_client import get_llama_cpp_client
from clients.redis_client import get_redis_connection
from clients.tigergraph_client import get_tigergraph_connection
from models.api_models import HealthStatus

# Set up logger
logger = structlog.get_logger(__name__)

# Create router for health endpoints
router = APIRouter(tags=["health"])

# These will be set by main.py after startup
_app_start_time: Optional[datetime] = None
_orchestrator = None


def set_health_dependencies(app_start_time: datetime, orchestrator):
    """Set dependencies for health endpoints after app startup."""
    global _app_start_time, _orchestrator
    _app_start_time = app_start_time
    _orchestrator = orchestrator


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Checks the status of all core services and returns detailed health information.
    This endpoint is used by monitoring systems and load balancers.
    """
    logger.debug("Health check requested")
    
    # Use default start time if not set
    start_time = _app_start_time or datetime.now(timezone.utc)
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "services": {},
        "uptime": (datetime.now(timezone.utc) - start_time).total_seconds()
    }
    
    # Check llama.cpp services
    try:
        llamacpp_client = await get_llama_cpp_client()
        huihui_healthy = await llamacpp_client.health_check("huihui-oss20b-llamacpp")
        mistral_healthy = await llamacpp_client.health_check("mistral-7b-llamacpp")
        
        health_status["services"]["llamacpp_huihui"] = {
            "status": "healthy" if huihui_healthy else "unhealthy",
            "message": "HuiHui OSS20B inference server (port 8081)",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
        health_status["services"]["llamacpp_mistral"] = {
            "status": "healthy" if mistral_healthy else "unhealthy", 
            "message": "Mistral 7B inference server (port 8082)",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
        if not (huihui_healthy and mistral_healthy):
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["llamacpp_huihui"] = {
            "status": "error",
            "message": f"Failed to check HuiHui server: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        health_status["services"]["llamacpp_mistral"] = {
            "status": "error",
            "message": f"Failed to check Mistral server: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        health_status["status"] = "degraded"
    
    # Check Redis service
    try:
        redis_client = get_redis_connection()
        if redis_client:
            redis_client.ping()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "message": "Pheromind working memory",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            health_status["services"]["redis"] = {
                "status": "error", 
                "message": "Redis connection failed",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "error", 
            "message": f"Redis unavailable: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        # Redis failure doesn't make system unhealthy, just degrades Pheromind
    
    # Check TigerGraph service
    try:
        tg_client = get_tigergraph_connection()
        if tg_client:
            health_status["services"]["tigergraph"] = {
                "status": "healthy",
                "message": "Persistent knowledge store",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            health_status["services"]["tigergraph"] = {
                "status": "error",
                "message": "TigerGraph connection failed",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        health_status["services"]["tigergraph"] = {
            "status": "error",
            "message": f"TigerGraph unavailable: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        # TigerGraph failure doesn't immediately break the system
    
    # Check orchestrator
    if _orchestrator and _orchestrator._initialized:
        health_status["services"]["orchestrator"] = {
            "status": "healthy", 
            "message": "AI Council orchestrator ready",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        health_status["services"]["orchestrator"] = {
            "status": "error",
            "message": "Orchestrator not initialized",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        health_status["status"] = "unhealthy"
    
    logger.debug("Health check completed", status=health_status["status"], services_count=len(health_status["services"]))
    
    return HealthStatus(**health_status)
    
    @router.get("/cache-stats")
    async def get_cache_stats():
        """
        Get prompt cache performance statistics.
        
        Returns detailed information about cache hit rates, cost savings,
        and performance metrics for monitoring and optimization.
        """
        try:
            from core.cache_integration import get_global_cache_manager
            
            cache_manager = await get_global_cache_manager()
            if cache_manager:
                stats = await cache_manager.get_orchestrator_cache_stats()
                
                logger.info("Cache stats requested", 
                           cache_enabled=stats.get("cache_enabled", False),
                           hit_rate=stats.get("cache_stats", {}).get("hit_rate", 0))
                
                return {
                    "status": "success",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cache_configuration": {
                        "enabled": stats.get("cache_enabled", False),
                        "ttl_hours": stats.get("cache_ttl_hours", 0),
                        "clients_cached": stats.get("clients_cached", 0)
                    },
                    "performance_stats": stats.get("cache_stats", {}),
                    "actions": {
                        "clear_cache": "/cache-clear",
                        "cleanup_cache": "/cache-cleanup"
                    }
                }
            else:
                return {
                    "status": "disabled",
                    "message": "Cache manager not initialized or caching disabled",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error("Error retrieving cache stats", error=str(e))
            return {
                "status": "error",
                "message": f"Failed to retrieve cache statistics: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    @router.post("/cache-clear")
    async def clear_cache(pattern: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            pattern: Optional pattern to match keys for selective clearing
        """
        try:
            from core.cache_integration import get_global_cache_manager
            
            cache_manager = await get_global_cache_manager()
            if cache_manager:
                # Clear cache on all cached clients
                total_cleared = 0
                for client in cache_manager._cached_clients.values():
                    if hasattr(client, 'clear_cache'):
                        cleared = await client.clear_cache(pattern)
                        total_cleared += cleared
                        
                logger.info("Cache cleared", pattern=pattern, entries_cleared=total_cleared)
                
                return {
                    "status": "success",
                    "message": f"Cache cleared successfully",
                    "entries_cleared": total_cleared,
                    "pattern": pattern,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "status": "disabled", 
                    "message": "Cache manager not available"
                }
                
        except Exception as e:
            logger.error("Error clearing cache", error=str(e), pattern=pattern)
            return {
                "status": "error",
                "message": f"Failed to clear cache: {str(e)}"
            }
    
    @router.post("/cache-cleanup")
    async def cleanup_cache():
        """
        Perform cache cleanup to remove expired entries and optimize storage.
        """
        try:
            from core.cache_integration import get_global_cache_manager
            
            cache_manager = await get_global_cache_manager()
            if cache_manager:
                cleanup_results = await cache_manager.perform_cache_cleanup()
                
                logger.info("Cache cleanup performed", results=cleanup_results)
                
                return {
                    "status": "success",
                    "message": "Cache cleanup completed successfully",
                    "cleanup_results": cleanup_results,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "status": "disabled",
                    "message": "Cache manager not available"
                }
                
        except Exception as e:
            logger.error("Error during cache cleanup", error=str(e))
            return {
                "status": "error", 
                "message": f"Cache cleanup failed: {str(e)}"
            }
    
# Router is exported directly as 'router'