# config.py
# Configuration file for Hybrid AI Council
# This shows how environment variables work with our database clients

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


class Config(BaseModel):
    """
    Configuration class for the Hybrid AI Council system.
    
    Centralizes all configuration management with proper validation
    and type safety using Pydantic.
    """
    
    # Redis Configuration
    redis_host: str = Field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = Field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    
    # TigerGraph Configuration  
    tigergraph_host: str = Field(default_factory=lambda: os.getenv("TIGERGRAPH_HOST", "http://localhost"))
    tigergraph_port: int = Field(default_factory=lambda: int(os.getenv("TIGERGRAPH_PORT", "14240")))
    tigergraph_username: str = Field(default_factory=lambda: os.getenv("TIGERGRAPH_USERNAME", "tigergraph"))
    tigergraph_password: str = Field(default_factory=lambda: os.getenv("TIGERGRAPH_PASSWORD", "tigergraph"))
    tigergraph_graph_name: str = Field(default_factory=lambda: os.getenv("TIGERGRAPH_GRAPH_NAME", "HybridAICouncil"))
    
    # Ollama Configuration
    ollama_host: str = Field(default_factory=lambda: os.getenv("OLLAMA_HOST", "localhost"))
    ollama_port: int = Field(default_factory=lambda: int(os.getenv("OLLAMA_PORT", "11434")))
    
    # Logging Configuration
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # API Configuration
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    
    # Pheromind Configuration
    pheromind_ttl: int = Field(default_factory=lambda: int(os.getenv("PHEROMIND_TTL", "12")))
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}"
        
    @property
    def tigergraph_url(self) -> str:
        """Get TigerGraph connection URL."""
        return f"{self.tigergraph_host}:{self.tigergraph_port}"
        
    @property
    def ollama_url(self) -> str:
        """Get Ollama API base URL."""
        return f"http://{self.ollama_host}:{self.ollama_port}"


# Legacy module-level variables for backwards compatibility
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

TIGERGRAPH_HOST = os.getenv("TIGERGRAPH_HOST", "http://localhost")
TIGERGRAPH_PASSWORD = os.getenv("TIGERGRAPH_PASSWORD", "tigergraph")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Print current config (for testing)
if __name__ == "__main__":
    config = Config()
    print("🔧 Current Configuration:")
    print(f"Redis: {config.redis_host}:{config.redis_port}")
    print(f"TigerGraph: {config.tigergraph_url}")
    print(f"Ollama: {config.ollama_url}")
    print(f"Log Level: {config.log_level}")
    print(f"Pheromind TTL: {config.pheromind_ttl}s") 