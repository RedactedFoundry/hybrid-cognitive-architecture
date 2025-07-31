# config.py
# Configuration file for Hybrid AI Council
# This shows how environment variables work with our database clients

import os
import warnings
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

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
    tigergraph_password: str = Field(default_factory=lambda: Config._get_secure_password())
    tigergraph_graph_name: str = Field(default_factory=lambda: os.getenv("TIGERGRAPH_GRAPH_NAME", "HybridAICouncil"))
    
    # Environment detection
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    
    @staticmethod
    def _get_secure_password() -> str:
        """
        Get TigerGraph password with security validation.
        
        Returns:
            str: Password from environment variable
            
        Raises:
            ValueError: If no password provided in production environment
        """
        password = os.getenv("TIGERGRAPH_PASSWORD")
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if password is None:
            if environment in ["production", "prod", "staging"]:
                raise ValueError(
                    "❌ SECURITY ERROR: TIGERGRAPH_PASSWORD environment variable is required in production. "
                    "Set TIGERGRAPH_PASSWORD=your_secure_password in your environment."
                )
            else:
                # Development fallback with security warning
                warnings.warn(
                    "🔒 SECURITY WARNING: Using default TigerGraph password in development. "
                    "Set TIGERGRAPH_PASSWORD environment variable for better security. "
                    "This is NOT allowed in production!",
                    UserWarning,
                    stacklevel=2
                )
                return "tigergraph"  # Development fallback only
        
        # Validate password strength
        if len(password) < 8:
            if environment in ["production", "prod", "staging"]:
                raise ValueError("❌ SECURITY ERROR: TigerGraph password must be at least 8 characters in production")
            else:
                warnings.warn(
                    "🔒 SECURITY WARNING: TigerGraph password is less than 8 characters. "
                    "Consider using a stronger password.",
                    UserWarning
                )
        
        if password == "tigergraph" and environment in ["production", "prod", "staging"]:
            raise ValueError(
                "❌ SECURITY ERROR: Default 'tigergraph' password is not allowed in production. "
                "Use a strong, unique password."
            )
        
        return password
    
    @field_validator('tigergraph_password')
    @classmethod
    def validate_password_security(cls, v):
        """Additional password validation at class level."""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if environment in ["production", "prod", "staging"]:
            if v == "tigergraph":
                raise ValueError("Default password 'tigergraph' is not allowed in production")
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters in production")
                
        return v
    
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
# Legacy password variable - use Config class for secure password handling
TIGERGRAPH_PASSWORD = Config._get_secure_password()

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