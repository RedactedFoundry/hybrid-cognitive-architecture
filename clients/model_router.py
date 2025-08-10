"""
Model Router - Routes requests to appropriate LLM backend (Ollama vs llama.cpp)
"""

import asyncio
from typing import Dict, Any, Optional
import structlog

from clients.ollama_client import OllamaClient
from clients.llama_cpp_client import LlamaCppClient, get_llama_cpp_client
from config.models import CouncilModels

logger = structlog.get_logger(__name__)

class ModelRouter:
    """Routes model requests to appropriate backend (Ollama or llama.cpp)."""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.llamacpp_client: Optional[LlamaCppClient] = None
    
    async def _get_llamacpp_client(self) -> LlamaCppClient:
        """Get or create llama.cpp client instance."""
        if self.llamacpp_client is None:
            self.llamacpp_client = await get_llama_cpp_client()
        return self.llamacpp_client
    
    async def generate(self, model_alias: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Route generation request to appropriate backend.
        
        Args:
            model_alias: Model alias from CouncilModels (e.g., "huihui-generator")
            prompt: Input text
            **kwargs: Additional parameters
            
        Returns:
            Dict with 'content' key containing generated text
        """
        provider = CouncilModels.get_model_provider(model_alias)
        model_name = CouncilModels.get_model_name(model_alias)
        
        logger.info("routing_model_request", 
                   model_alias=model_alias, 
                   provider=provider,
                   model_name=model_name,
                   prompt_length=len(prompt))
        
        try:
            if provider == "llamacpp":
                # Route to llama.cpp server
                client = await self._get_llamacpp_client()
                result = await client.generate(prompt, **kwargs)
                
                # Add routing metadata
                result["provider"] = "llamacpp"
                result["model_alias"] = model_alias
                return result
                
            elif provider == "ollama":
                # Route to Ollama
                response = await self.ollama_client.generate_response(
                    prompt=prompt,
                    model_alias=model_name,
                    **kwargs
                )
                
                # Normalize format to match llama.cpp
                content = response.text
                return {
                    "content": content,
                    "model": f"{model_name}-ollama",
                    "model_alias": model_alias,
                    "provider": "ollama",
                    "usage": {
                        "completion_tokens": response.tokens_generated,
                        "prompt_tokens": len(prompt.split()),  # Estimate from prompt
                        "total_tokens": response.tokens_generated + len(prompt.split())
                    }
                }
            
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
        except Exception as e:
            logger.error("model_routing_failed", 
                        model_alias=model_alias,
                        provider=provider,
                        error=str(e))
            raise
    
    async def health_check(self, model_alias: str) -> bool:
        """Check if the backend for a specific model is healthy."""
        provider = CouncilModels.get_model_provider(model_alias)
        
        try:
            if provider == "llamacpp":
                client = await self._get_llamacpp_client()
                return await client.health_check()
            elif provider == "ollama":
                # Simple check - OllamaClient doesn't have list_models, so basic ping
                # For now, assume healthy if client exists (TODO: implement proper health check)
                return self.ollama_client is not None
            else:
                return False
        except Exception as e:
            logger.warning("health_check_failed", 
                          model_alias=model_alias, 
                          provider=provider,
                          error=str(e))
            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all configured models."""
        results = {}
        for model_alias in CouncilModels.get_all_models():
            results[model_alias] = await self.health_check(model_alias)
        return results

# Global router instance
_router_instance: Optional[ModelRouter] = None

async def get_model_router() -> ModelRouter:
    """Get shared model router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance

async def quick_test():
    """Quick test of model routing."""
    router = await get_model_router()
    
    print("=== Model Router Test ===")
    
    # Test health checks
    health = await router.health_check_all()
    for model, status in health.items():
        provider = CouncilModels.get_model_provider(model)
        print(f"{model} ({provider}): {'✅ HEALTHY' if status else '❌ UNHEALTHY'}")
    
    # Test generation for each provider type
    models_to_test = [
        ("huihui-generator", "llamacpp"),  # HuiHui generator
        ("mistral-verifier", "ollama")     # Mistral verifier
    ]
    
    for model_alias, expected_provider in models_to_test:
        if health.get(model_alias, False):
            try:
                print(f"\n--- Testing {model_alias} ({expected_provider}) ---")
                result = await router.generate(
                    model_alias, 
                    "Say hello briefly.", 
                    max_tokens=32
                )
                print(f"✅ SUCCESS: {result['content'][:100]}...")
                print(f"Provider: {result['provider']}, Model: {result['model']}")
            except Exception as e:
                print(f"❌ FAILED: {e}")
        else:
            print(f"\n--- Skipping {model_alias} (unhealthy) ---")

if __name__ == "__main__":
    asyncio.run(quick_test())
