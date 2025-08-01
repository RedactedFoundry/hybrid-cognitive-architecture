"""
Ollama Client for Hybrid AI Council
Provides OpenAI-compatible API interface to Ollama models

Now with comprehensive error boundaries and circuit breaker protection.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp
import structlog

from config import Config
from utils.error_utils import (
    ConnectionError,
    TimeoutError,
    ValidationError,
    ProcessingError,
    error_boundary,
    ollama_circuit_breaker,
    handle_ollama_error,
    validate_user_input
)

# Set up structured logging
logger = structlog.get_logger("ollama_client")

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
        """Get or create HTTP session with event loop safety"""
        try:
            # Check if session exists and is valid for current event loop
            if (self.session is None or 
                self.session.closed or 
                self.session._loop != asyncio.get_running_loop()):
                
                # Close old session if it exists but is from different loop
                if self.session and not self.session.closed:
                    try:
                        await self.session.close()
                    except Exception:
                        pass  # Ignore errors when closing stale session
                
                # Create new session for current event loop
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                self.session = aiohttp.ClientSession(timeout=timeout)
                
        except RuntimeError:
            # No event loop running, create session anyway
            if self.session is None or self.session.closed:
                timeout = aiohttp.ClientTimeout(total=300)
                self.session = aiohttp.ClientSession(timeout=timeout)
                
        return self.session
    
    @error_boundary(component="ollama_health_check")
    async def health_check(self) -> bool:
        """Check if Ollama service is available with circuit breaker protection."""
        try:
            async def _health_check_impl():
                session = await self._get_session()
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        response_data = await response.json()
                        model_count = len(response_data.get('models', []))
                        logger.info("Ollama health check successful", model_count=model_count)
                        return True
                    else:
                        raise ConnectionError(
                            service="ollama",
                            message=f"Health check failed with HTTP {response.status}",
                            details={"status_code": response.status}
                        )
            
            return await ollama_circuit_breaker.call(_health_check_impl)
            
        except (ConnectionError, ProcessingError):
            # These are already handled by error_boundary
            return False
        except Exception as e:
            await handle_ollama_error(e, {"operation": "health_check"})
            return False
    
    @error_boundary(component="ollama_generate")
    async def generate_response(
        self,
        prompt: str,
        model_alias: str,
        system_prompt: str = "",
        max_tokens: int = 800,
        temperature: float = 0.7,
        timeout: float = 45.0
    ) -> LLMResponse:
        """Generate response using Ollama model with comprehensive error handling."""
        start_time = datetime.now()
        
        # Input validation
        validate_user_input(prompt)
        if not model_alias:
            raise ValidationError("model_alias", "Model alias cannot be empty")
        
        try:
            # Map model alias to actual Ollama model name
            actual_model = self.model_mapping.get(model_alias, model_alias)
            logger.info(
                "Generating response with Ollama",
                model=actual_model,
                alias=model_alias,
                prompt_length=len(prompt),
                max_tokens=max_tokens
            )
            
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
                
                response_data = await response.json()
                generated_text = response_data.get("response", "")
                
                # Calculate generation time
                generation_time = (datetime.now() - start_time).total_seconds()
                
                # Extract token count (if available)
                eval_count = response_data.get("eval_count", 0)
                
                logger.info(f"Generated {eval_count} tokens in {generation_time:.2f}s with {actual_model}")
                
                return LLMResponse(
                    text=generated_text,
                    model=actual_model,
                    tokens_generated=eval_count,
                    generation_time=generation_time,
                    success=True
                )
                
        except asyncio.TimeoutError as e:
            generation_time = timeout
            timeout_error = TimeoutError(
                operation=f"generate_response_{model_alias}",
                timeout_seconds=timeout,
                details={"model": model_alias, "prompt_length": len(prompt)}
            )
            await handle_ollama_error(timeout_error, {
                "operation": "generate_response",
                "model_alias": model_alias,
                "timeout": timeout
            })
            return LLMResponse(
                text="",
                model=model_alias,
                tokens_generated=0,
                generation_time=generation_time,
                success=False,
                error=str(timeout_error)
            )
            
        except aiohttp.ClientError as e:
            generation_time = (datetime.now() - start_time).total_seconds()
            connection_error = ConnectionError(
                service="ollama",
                message=f"Network error generating response: {str(e)}",
                retryable=True,
                details={"model": model_alias, "error_type": type(e).__name__}
            )
            await handle_ollama_error(connection_error, {
                "operation": "generate_response",
                "model_alias": model_alias
            })
            return LLMResponse(
                text="",
                model=model_alias,
                tokens_generated=0,
                generation_time=generation_time,
                success=False,
                error=str(connection_error)
            )
            
        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds()
            processing_error = ProcessingError(
                message=f"Error generating response with {model_alias}: {str(e)}",
                component="ollama_generate",
                details={"model": model_alias, "error_type": type(e).__name__}
            )
            await handle_ollama_error(processing_error, {
                "operation": "generate_response",
                "model_alias": model_alias
            })
            return LLMResponse(
                text="",
                model=model_alias,
                tokens_generated=0,
                generation_time=generation_time,
                success=False,
                error=str(processing_error)
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
                                response_chunk = json.loads(line_text)
                                
                                # Extract the token from the response
                                token = response_chunk.get("response", "")
                                if token:
                                    yield token
                                
                                # Check if this is the final response
                                if response_chunk.get("done", False):
                                    generation_time = (datetime.now() - start_time).total_seconds()
                                    eval_count = response_chunk.get("eval_count", 0)
                                    logger.info(f"Streaming completed: {eval_count} tokens in {generation_time:.2f}s with {actual_model}")
                                    break
                                    
                        except json.JSONDecodeError as e:
                            # Skip malformed JSON lines
                            logger.warning(f"Skipping malformed JSON line: {line_text[:100]}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing stream line: {str(e)}")
                            continue
                            
        except asyncio.TimeoutError as e:
            timeout_error = TimeoutError(
                operation=f"generate_response_stream_{model_alias}",
                timeout_seconds=timeout,
                details={"model": model_alias, "prompt_length": len(prompt)}
            )
            await handle_ollama_error(timeout_error, {
                "operation": "generate_response_stream",
                "model_alias": model_alias,
                "timeout": timeout
            })
            raise timeout_error
            
        except aiohttp.ClientError as e:
            connection_error = ConnectionError(
                service="ollama",
                message=f"Network error during streaming: {str(e)}",
                retryable=True,
                details={"model": model_alias, "error_type": type(e).__name__}
            )
            await handle_ollama_error(connection_error, {
                "operation": "generate_response_stream",
                "model_alias": model_alias
            })
            raise connection_error
            
        except Exception as e:
            processing_error = ProcessingError(
                message=f"Error during streaming with {model_alias}: {str(e)}",
                component="ollama_stream",
                details={"model": model_alias, "error_type": type(e).__name__}
            )
            await handle_ollama_error(processing_error, {
                "operation": "generate_response_stream",
                "model_alias": model_alias
            })
            raise processing_error
    
    @error_boundary(component="ollama_close")
    async def close(self):
        """Close the HTTP session with proper error handling."""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                logger.debug("Ollama client session closed successfully")
        except Exception as e:
            await handle_ollama_error(e, {"operation": "close_session"})
            # Don't re-raise - closing should be best effort

# Global client instance with event loop tracking
_ollama_client = None
_client_event_loop = None

def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client instance with event loop safety"""
    global _ollama_client, _client_event_loop
    
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create without loop tracking
        current_loop = None
    
    # Reset client if event loop changed (fixes "Event loop is closed" errors)
    if _client_event_loop != current_loop:
        if _ollama_client is not None:
            # Schedule cleanup of old client if it exists
            try:
                if _ollama_client.session and not _ollama_client.session.closed:
                    # Best effort cleanup - don't await in sync function
                    _ollama_client.session._connector = None
            except Exception:
                pass  # Ignore cleanup errors
        
        _ollama_client = OllamaClient()
        _client_event_loop = current_loop
        logger.info("Created new Ollama client instance", 
                   event_loop_id=id(current_loop) if current_loop else None)
    
    return _ollama_client

async def close_ollama_client():
    """Close global Ollama client"""
    global _ollama_client
    if _ollama_client:
        await _ollama_client.close()
        _ollama_client = None
        logger.info("Closed Ollama client")