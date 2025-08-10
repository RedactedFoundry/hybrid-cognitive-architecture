"""
llama.cpp HTTP client for HuiHui GPT-OSS 20B MXFP4_MOE model.
Provides compatibility with our existing Ollama-based architecture.
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

class LlamaCppClient:
    """HTTP client for llama.cpp server."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8081"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if llama.cpp server is responsive."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(f"{self.base_url}/health", timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.warning("llama.cpp health check failed", error=str(e))
            return False
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate completion from llama.cpp server using chat completions API.
        
        Args:
            prompt: Input text
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Dict with 'content' key containing generated text
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Use chat completions format for proper gpt-oss template handling
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "top_k": kwargs.get("top_k", 40),
            "stream": False
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=60
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"llama.cpp server error {response.status}: {error_text}")
                
                result = await response.json()
                
                # Extract generated text from chat completions format
                choices = result.get("choices", [])
                if not choices:
                    raise Exception("No choices returned from llama.cpp")
                
                message = choices[0].get("message", {})
                content = message.get("content", "").strip()
                
                # Clean up the GPT-OSS format tags if present
                if content.startswith("<|channel|>"):
                    # Extract just the final message part
                    parts = content.split("<|message|>")
                    if len(parts) > 1:
                        content = parts[-1].strip()
                
                logger.info("llama.cpp generation completed", 
                          prompt_length=len(prompt),
                          response_length=len(content),
                          usage=result.get("usage", {}))
                
                return {
                    "content": content,
                    "model": "huihui-oss20b-llamacpp",
                    "usage": result.get("usage", {}),
                    "finish_reason": choices[0].get("finish_reason", "unknown")
                }
                
        except Exception as e:
            logger.error("llama.cpp generation failed", error=str(e), prompt_preview=prompt[:100])
            raise

# Global client instance for easy usage
_client_instance = None

async def get_llama_cpp_client() -> LlamaCppClient:
    """Get shared llama.cpp client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LlamaCppClient()
    return _client_instance

async def quick_test():
    """Quick test function to verify llama.cpp connectivity."""
    async with LlamaCppClient() as client:
        health = await client.health_check()
        print(f"Health check: {'✅ PASS' if health else '❌ FAIL'}")
        
        if health:
            try:
                result = await client.generate("Say hello briefly.", max_tokens=32)
                print(f"Generation test: ✅ PASS")
                print(f"Response: {result['content']}")
                return True
            except Exception as e:
                print(f"Generation test: ❌ FAIL - {e}")
                return False
        return False

if __name__ == "__main__":
    asyncio.run(quick_test())
