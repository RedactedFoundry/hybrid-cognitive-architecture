# config/models.py
"""
Model Configuration - Centralized AI Council Model Definitions

This module contains all model configurations for the Hybrid AI Council system.
Centralizing model names and mappings makes it easier to manage deployments
across different environments (local development vs cloud production).
"""

from typing import Dict, List, Literal
from enum import Enum


class ModelRole(str, Enum):
    """AI Council model roles for different cognitive functions."""
    ANALYTICAL = "analytical"     # Data analysis and logical reasoning
    CREATIVE = "creative"         # Creative thinking and ideation  
    COORDINATOR = "coordinator"   # Synthesis and final decisions (verifier)


class CouncilModels:
    """Centralized model definitions for the AI Council."""
    
    # Model aliases used throughout the system (llm-experiment branch)
    GENERATOR_MODEL = "huihui-generator"      # HuiHui GPT-OSS 20B (analytical reasoning)
    CREATIVE_MODEL = "huihui-creative"        # HuiHui GPT-OSS 20B (creative thinking) 
    VERIFIER_MODEL = "mistral-verifier"       # Mistral 7B (coordination + verification)
    
    # Model routing: which service handles each model
    MODEL_PROVIDERS: Dict[str, Literal["ollama", "llamacpp"]] = {
        # Both generator roles use llama.cpp for HuiHui GPT-OSS 20B MXFP4_MOE
        GENERATOR_MODEL: "llamacpp",
        CREATIVE_MODEL: "llamacpp", 
        # Verifier/coordinator uses Ollama for Mistral 7B
        VERIFIER_MODEL: "ollama"
    }
    
    # Model to actual model name mapping
    MODEL_MAPPING: Dict[str, str] = {
        # Generator models route to llama.cpp server (HuiHui GPT-OSS 20B)
        GENERATOR_MODEL: "huihui-oss20b-llamacpp",
        CREATIVE_MODEL: "huihui-oss20b-llamacpp",
        # Verifier model routes to Ollama (Mistral 7B)
        VERIFIER_MODEL: "hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M"
    }
    
    # Role assignments for council deliberation
    MODEL_ROLES: Dict[str, ModelRole] = {
        GENERATOR_MODEL: ModelRole.ANALYTICAL,   # HuiHui: Analytical reasoning
        CREATIVE_MODEL: ModelRole.CREATIVE,      # HuiHui: Creative thinking  
        VERIFIER_MODEL: ModelRole.COORDINATOR    # Mistral: Coordination + verification
    }
    
    # Default models for each role (allows easy swapping)
    ROLE_DEFAULTS: Dict[ModelRole, str] = {
        ModelRole.ANALYTICAL: GENERATOR_MODEL,
        ModelRole.CREATIVE: CREATIVE_MODEL,
        ModelRole.COORDINATOR: VERIFIER_MODEL
    }
    
    @classmethod
    def get_all_models(cls) -> List[str]:
        """Get list of all configured model aliases."""
        return list(cls.MODEL_MAPPING.keys())
    
    @classmethod
    def get_model_name(cls, alias: str) -> str:
        """Get the actual model name from alias."""
        return cls.MODEL_MAPPING.get(alias, alias)
    
    @classmethod
    def get_model_provider(cls, alias: str) -> Literal["ollama", "llamacpp"]:
        """Get the provider (ollama or llamacpp) for a model alias."""
        return cls.MODEL_PROVIDERS.get(alias, "ollama")
    
    @classmethod
    def get_ollama_model_name(cls, alias: str) -> str:
        """Get the actual Ollama model name from alias (backward compatibility)."""
        return cls.MODEL_MAPPING.get(alias, alias)
    
    @classmethod
    def get_model_role(cls, alias: str) -> ModelRole:
        """Get the role assigned to a model alias."""
        return cls.MODEL_ROLES.get(alias, ModelRole.ANALYTICAL)
    
    @classmethod
    def get_model_for_role(cls, role: ModelRole) -> str:
        """Get the default model alias for a given role."""
        return cls.ROLE_DEFAULTS.get(role, cls.GENERATOR_MODEL)


# Convenience constants for import (llm-experiment branch)
ANALYTICAL_MODEL = CouncilModels.GENERATOR_MODEL    # HuiHui for analytical reasoning
CREATIVE_MODEL = CouncilModels.CREATIVE_MODEL       # HuiHui for creative thinking
COORDINATOR_MODEL = CouncilModels.VERIFIER_MODEL    # Mistral for coordination

# For backward compatibility
ALL_MODELS = CouncilModels.get_all_models()
MODEL_MAPPING = CouncilModels.MODEL_MAPPING