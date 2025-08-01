# config/__init__.py
"""
Configuration module for Hybrid AI Council.

This module provides centralized configuration management for the entire system.
"""

# Import the main Config class from the parent directory
import sys
import os

# Add parent directory to path to import config.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from config import Config as _Config
    Config = _Config
except ImportError:
    # Fallback for complex import scenarios
    import importlib.util
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
    spec = importlib.util.spec_from_file_location('config_module', config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    Config = config_module.Config

# Import model configurations
from .models import (
    CouncilModels,
    ModelRole,
    ANALYTICAL_MODEL,
    CREATIVE_MODEL,
    COORDINATOR_MODEL,
    ALL_MODELS,
    MODEL_MAPPING
)

__all__ = [
    # Main configuration class
    "Config",
    # Model configurations
    "CouncilModels",
    "ModelRole", 
    "ANALYTICAL_MODEL",
    "CREATIVE_MODEL",
    "COORDINATOR_MODEL",
    "ALL_MODELS",
    "MODEL_MAPPING"
]