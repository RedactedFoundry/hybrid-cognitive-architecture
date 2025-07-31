# config/__init__.py
"""
Configuration module for Hybrid AI Council.

This module provides centralized configuration management for the entire system.
"""

# Import the main Config class from the root config.py
import sys
import os
import importlib.util

# Get path to root config.py
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
config_path = os.path.join(parent_dir, 'config.py')

# Import Config from the root config.py
spec = importlib.util.spec_from_file_location("root_config", config_path)
root_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_config)
Config = root_config.Config

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
    "Config",  # Export the main Config class
    "CouncilModels",
    "ModelRole", 
    "ANALYTICAL_MODEL",
    "CREATIVE_MODEL",
    "COORDINATOR_MODEL",
    "ALL_MODELS",
    "MODEL_MAPPING"
]