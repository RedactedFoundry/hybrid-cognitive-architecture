"""
Ollama Client for Hybrid AI Council
Provides OpenAI-compatible API interface to Ollama models
"""

import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Response from LLM generation"""
    text: str
    model: str
    tokens_generated: int
    generation_time: float
    success: bool
    error: Optional[str] = None

class OllamaClient:
    """Client for Ollama using OpenAI-compatible API"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        
        # Model alias mapping from council names to actual Ollama model names
        self.model_mapping = {
            "qwen3-council": "hf.co/lm-kit/qwen-3-14b-instruct-gguf:Q4_K_M",
            "deepseek-council": "deepseek-coder:6.7b-instruct", 
            "mistral-council": "hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M"
        }
        
    async def _get_session(self):
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Ollama health check successful. Found {len(data.get('models', []))} models.")
                    return True
                else:
                    logger.error(f"Ollama health check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Ollama health check error: {e}")
            return False
    
    async def generate_response(
        self,
        prompt: str,
        model_alias: str,
        system_prompt: str = "",
        max_tokens: int = 800,
        temperature: float = 0.7,
        timeout: float = 45.0
    ) -> LLMResponse:
        """Generate response using Ollama model"""
        start_time = datetime.now()
        
        try:
            # Map model alias to actual Ollama model name
            actual_model = self.model_mapping.get(model_alias, model_alias)
            logger.info(f"Generating response with {actual_model} (alias: {model_alias})")
            
            # Prepare the request payload for Ollama's /api/generate endpoint
            payload = {
                "model": actual_model,
                "prompt": prompt,
                "system": system_prompt,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40
                },
                "stream": False  # Get complete response, not streaming
            }
            
            session = await self._get_session()
            
            # Make request with custom timeout
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: HTTP {response.status} - {error_text}")
                    return LLMResponse(
                        text="",
                        model=actual_model,
                        tokens_generated=0,
                        generation_time=0.0,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}"
                    )
                
                data = await response.json()
                generated_text = data.get("response", "")
                
                # Calculate generation time
                generation_time = (datetime.now() - start_time).total_seconds()
                
                # Extract token count (if available)
                eval_count = data.get("eval_count", 0)
                
                logger.info(f"Generated {eval_count} tokens in {generation_time:.2f}s with {actual_model}")
                
                return LLMResponse(
                    text=generated_text,
                    model=actual_model,
                    tokens_generated=eval_count,
                    generation_time=generation_time,
                    success=True
                )
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout generating response with {model_alias} after {timeout}s")
            return LLMResponse(
                text="",
                model=model_alias,
                tokens_generated=0,
                generation_time=timeout,
                success=False,
                error=f"Request timeout after {timeout} seconds"
            )
            
        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error generating response with {model_alias}: {e}")
            return LLMResponse(
                text="",
                model=model_alias,
                tokens_generated=0,
                generation_time=generation_time,
                success=False,
                error=str(e)
            )
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global client instance
_ollama_client = None

def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
        logger.info("Created new Ollama client instance")
    return _ollama_client

async def close_ollama_client():
    """Close global Ollama client"""
    global _ollama_client
    if _ollama_client:
        await _ollama_client.close()
        _ollama_client = None
        logger.info("Closed Ollama client")