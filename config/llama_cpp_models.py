"""
llama.cpp Model Configuration
============================

Defines model paths and server configurations for llama.cpp inference.
All models are stored in D:/Council-Project/models/llama-cpp/
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base directory for all models (configurable via env)
MODEL_BASE_DIR = Path(os.getenv("LLAMACPP_MODEL_DIR", "D:/Council-Project/models/llama-cpp"))

# Model file mappings
LLAMACPP_MODELS: Dict[str, Dict[str, Any]] = {
    "huihui-oss20b-llamacpp": {
        "file_path": MODEL_BASE_DIR / "huihui-oss-20b-mxfp4-moe.gguf",
        "port": int(os.getenv("LLAMACPP_PORT_HUIHUI", "8081")),
        "host": os.getenv("LLAMACPP_HOST_HUIHUI", os.getenv("LLAMACPP_HOST", "127.0.0.1")),
        "context_size": 4096,
        "batch_size": 512,
        "threads": 8,
        "gpu_layers": 35,  # Adjust based on your RTX 4090 VRAM
        "description": "HuiHui GPT-OSS 20B MXFP4_MOE - Analytical reasoning and creative thinking"
    },
    "mistral-7b-llamacpp": {
        "file_path": MODEL_BASE_DIR / "mistral-7b-instruct-v0.3-q4_k_m.gguf", 
        "port": int(os.getenv("LLAMACPP_PORT_MISTRAL", "8082")),
        "host": os.getenv("LLAMACPP_HOST_MISTRAL", os.getenv("LLAMACPP_HOST", "127.0.0.1")),
        "context_size": 4096,
        "batch_size": 512,
        "threads": 8,
        "gpu_layers": 32,  # Mistral 7B should fit entirely in VRAM
        "description": "Mistral 7B Instruct v0.3 Q4_K_M - Verification and coordination"
    }
}

def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get configuration for a specific model."""
    return LLAMACPP_MODELS.get(model_name, {})

def get_model_port(model_name: str) -> int:
    """Get the port for a specific model."""
    config = get_model_config(model_name)
    return int(config.get("port"))

def get_model_host(model_name: str) -> str:
    """Get the host for a specific model."""
    config = get_model_config(model_name)
    return str(config.get("host", "127.0.0.1"))

def get_model_path(model_name: str) -> Path:
    """Get the file path for a specific model."""
    config = get_model_config(model_name)
    return config.get("file_path", MODEL_BASE_DIR / "unknown.gguf")

def validate_model_files() -> Dict[str, bool]:
    """Validate that all model files exist."""
    results = {}
    for model_name, config in LLAMACPP_MODELS.items():
        file_path = config["file_path"]
        results[model_name] = file_path.exists()
    return results
