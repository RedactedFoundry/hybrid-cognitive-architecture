#!/usr/bin/env python3
"""
Setup script for Python 3.11 Voice Service

This script sets up the voice processing service with all required dependencies.
Run this after ensuring you have Python 3.11 installed.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if we're running Python 3.11"""
    version = sys.version_info
    if version.major != 3 or version.minor != 11:
        print(f"❌ Error: This service requires Python 3.11, found {version.major}.{version.minor}")
        print("Please install Python 3.11 and run this script with python3.11")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    # Core dependencies
    deps = [
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "aiohttp>=3.9.0",
        "pydantic>=2.0.0",
        "structlog>=23.0.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.25.0",
        "numpy>=1.25.0",
    ]
    
    # Voice processing dependencies (heavy ML)
    voice_deps = [
        "TTS>=0.22.0",           # Coqui XTTS v2
        "torch>=2.7.1",          # PyTorch  
        "torchaudio>=2.7.1",     # Audio processing
        "transformers>=4.54.1",  # HuggingFace
        "nemo-toolkit>=2.4.0",   # NVIDIA NeMo
# "silero-vad>=5.1.2" removed - Parakeet handles non-speech segments

    ]
    
    all_deps = deps + voice_deps
    
    for dep in all_deps:
        try:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Failed to install {dep}: {e}")
            print("Some dependencies may require manual installation")

def create_directories():
    """Create required directories"""
    dirs = ["voice/outputs"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {dir_path}")

def test_imports():
    """Test if critical imports work"""
    print("🔍 Testing imports...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")
    except ImportError:
        print("❌ PyTorch not available")
    
    try:
        import transformers
        print(f"✅ Transformers {transformers.__version__}")
    except ImportError:
        print("❌ Transformers not available")
    
    try:
        from TTS.api import TTS
        print("✅ Coqui TTS available")
    except ImportError:
        print("❌ Coqui TTS not available")
    
    try:
        import nemo.collections.asr as nemo_asr
        print("✅ NeMo ASR available")
    except ImportError:
        print("❌ NeMo ASR not available")

def main():
    """Main setup function"""
    print("🚀 Setting up Python 3.11 Voice Service")
    print("=" * 50)
    
    if not check_python_version():
        sys.exit(1)
    
    create_directories()
    install_dependencies()
    test_imports()
    
    print("\n✅ Setup complete!")
    print("\nTo start the service:")
    print("python -m uvicorn voice.main:app --host 0.0.0.0 --port 8011 --reload")

if __name__ == "__main__":
    main()