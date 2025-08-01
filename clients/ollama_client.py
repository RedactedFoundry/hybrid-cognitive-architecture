"""
Ollama Client for Hybrid AI Council
Provides OpenAI-compatible API interface to Ollama models
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp

from config import Config

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
    
    def __init__(self, base_url: Optional[str] = None):
        # Use provided URL or get from configuration
        if base_url is None:
            config = Config()
            base_url = f"http://{config.ollama_host}:{config.ollama_port}"
        
        self.base_url = base_url.rstrip('/')
        self.session = None
        
        # Import centralized model configuration
        from config.models import CouncilModels
        
        # Model alias mapping from council names to actual Ollama model names
        self.model_mapping = CouncilModels.MODEL_MAPPING
        
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
    
    async def generate_response_stream(
        self,
        prompt: str,
        model_alias: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        timeout: float = 60.0
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the specified model.
        
        This method yields individual tokens as they are generated, enabling
        real-time streaming for voice interactions and responsive UIs.
        
        Args:
            prompt: The input prompt for the model
            model_alias: Alias of the model to use (e.g., 'qwen3-council')
            system_prompt: System prompt to set model behavior
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            timeout: Request timeout in seconds
            
        Yields:
            Individual tokens as they are generated by the model
            
        Raises:
            ValueError: If model alias is not found
            Exception: For network or API errors
        """
        start_time = datetime.now()
        
        if model_alias not in self.model_mapping:
            raise ValueError(f"Unknown model alias: {model_alias}")
        
        actual_model = self.model_mapping[model_alias]
        logger.debug(f"Streaming response with {actual_model} (alias: {model_alias})")
        
        try:
            # Prepare the request payload for Ollama's /api/generate endpoint with streaming
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
                "stream": True  # Enable streaming response
            }
            
            session = await self._get_session()
            
            # Make streaming request
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: HTTP {response.status} - {error_text}")
                    raise Exception(f"HTTP {response.status}: {error_text}")
                
                # Process streaming response line by line
                async for line in response.content:
                    if line:
                        try:
                            # Each line is a JSON object with the streaming data
                            line_text = line.decode('utf-8').strip()
                            if line_text:
                                data = json.loads(line_text)
                                
                                # Extract the token from the response
                                token = data.get("response", "")
                                if token:
                                    yield token
                                
                                # Check if this is the final response
                                if data.get("done", False):
                                    generation_time = (datetime.now() - start_time).total_seconds()
                                    eval_count = data.get("eval_count", 0)
                                    logger.info(f"Streaming completed: {eval_count} tokens in {generation_time:.2f}s with {actual_model}")
                                    break
                                    
                        except json.JSONDecodeError as e:
                            # Skip malformed JSON lines
                            logger.warning(f"Skipping malformed JSON line: {line_text[:100]}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing stream line: {str(e)}")
                            continue
                            
        except asyncio.TimeoutError:
            logger.error(f"Timeout during streaming with {model_alias} after {timeout}s")
            raise Exception(f"Streaming timeout after {timeout}s")
        except Exception as e:
            logger.error(f"Error during streaming with {model_alias}: {str(e)}")
            raise
    
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