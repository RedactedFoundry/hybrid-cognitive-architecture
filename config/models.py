# config/models.py
"""
Model Configuration - Centralized AI Council Model Definitions

This module contains all model configurations for the Hybrid AI Council system.
Centralizing model names and mappings makes it easier to manage deployments
across different environments (local development vs cloud production).
"""

from typing import Dict, List
from enum import Enum


class ModelRole(str, Enum):
    """AI Council model roles for different cognitive functions."""
    ANALYTICAL = "analytical"     # Data analysis and logical reasoning
    CREATIVE = "creative"         # Creative thinking and ideation  
    COORDINATOR = "coordinator"   # Synthesis and final decisions (verifier)


class CouncilModels:
    """Centralized model definitions for the AI Council."""
    
    # Model aliases used throughout the system
    QWEN3_COUNCIL = "qwen3-council"
    DEEPSEEK_COUNCIL = "deepseek-council" 
    MISTRAL_COUNCIL = "mistral-council"
    
    # Model to actual Ollama model name mapping (experimental generator+verifier)
    MODEL_MAPPING: Dict[str, str] = {
        # Generator (HuiHui GPT-OSS 20B MXFP4_MOE) registered locally as 'huihui-oss20b'
        QWEN3_COUNCIL: "huihui-oss20b",
        # We collapse creative role to same generator for the 2-model experiment
        DEEPSEEK_COUNCIL: "huihui-oss20b",
        # Verifier / coordinator stays Mistral 7B Instruct via Bartowski GGUF
        MISTRAL_COUNCIL: "hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M"
    }
    
    # Role assignments for council deliberation
    MODEL_ROLES: Dict[str, ModelRole] = {
        QWEN3_COUNCIL: ModelRole.ANALYTICAL,     # Qwen3: Analytical agent
        DEEPSEEK_COUNCIL: ModelRole.CREATIVE,    # DeepSeek: Creative agent  
        MISTRAL_COUNCIL: ModelRole.COORDINATOR   # Mistral: Coordinator agent
    }
    
    # Default models for each role (allows easy swapping)
    ROLE_DEFAULTS: Dict[ModelRole, str] = {
        ModelRole.ANALYTICAL: QWEN3_COUNCIL,
        ModelRole.CREATIVE: DEEPSEEK_COUNCIL,
        ModelRole.COORDINATOR: MISTRAL_COUNCIL
    }
    
    @classmethod
    def get_all_models(cls) -> List[str]:
        """Get list of all configured model aliases."""
        return list(cls.MODEL_MAPPING.keys())
    
    @classmethod
    def get_ollama_model_name(cls, alias: str) -> str:
        """Get the actual Ollama model name from alias."""
        return cls.MODEL_MAPPING.get(alias, alias)
    
    @classmethod
    def get_model_role(cls, alias: str) -> ModelRole:
        """Get the role assigned to a model alias."""
        return cls.MODEL_ROLES.get(alias, ModelRole.ANALYTICAL)
    
    @classmethod
    def get_model_for_role(cls, role: ModelRole) -> str:
        """Get the default model alias for a given role."""
        return cls.ROLE_DEFAULTS.get(role, cls.QWEN3_COUNCIL)


# Convenience constants for import
ANALYTICAL_MODEL = CouncilModels.QWEN3_COUNCIL
CREATIVE_MODEL = CouncilModels.DEEPSEEK_COUNCIL
COORDINATOR_MODEL = CouncilModels.MISTRAL_COUNCIL

# For backward compatibility
ALL_MODELS = CouncilModels.get_all_models()
MODEL_MAPPING = CouncilModels.MODEL_MAPPING