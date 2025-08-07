#!/usr/bin/env python3
"""
🔍 Ollama Health Check Script

Comprehensive health check for Ollama LLM service including:
- Service availability
- Model loading status
- Performance metrics
- Resource usage

Usage:
    python scripts/check_ollama_health.py
"""

import sys
import os
import requests
import json
import time
from typing import Dict, List, Tuple, Optional

def check_ollama_service() -> Tuple[bool, Dict]:
    """Check if Ollama service is running and healthy"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            return True, {
                'status': 'healthy',
                'models_count': len(models),
                'models': models
            }
        else:
            return False, {
                'status': 'unhealthy',
                'error': f'HTTP {response.status_code}',
                'models_count': 0,
                'models': []
            }
    except requests.exceptions.ConnectionError:
        return False, {
            'status': 'not_running',
            'error': 'Connection refused - service not running',
            'models_count': 0,
            'models': []
        }
    except requests.exceptions.Timeout:
        return False, {
            'status': 'timeout',
            'error': 'Request timeout',
            'models_count': 0,
            'models': []
        }
    except Exception as e:
        return False, {
            'status': 'error',
            'error': str(e),
            'models_count': 0,
            'models': []
        }

def check_required_models() -> Tuple[bool, List[str]]:
    """Check if required models are loaded"""
    required_models = [
        "hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M",  # mistral-council
        "hf.co/lm-kit/qwen-3-14b-instruct-gguf:Q4_K_M",          # qwen3-council  
        "deepseek-coder:6.7b-instruct"                             # deepseek-council
    ]
    model_aliases = ["mistral-council", "qwen3-council", "deepseek-council"]
    
    is_healthy, data = check_ollama_service()
    if not is_healthy:
        return False, []
    
    available_models = [m.get('name') for m in data['models']]
    missing_models = []
    
    for i, model in enumerate(required_models):
        alias = model_aliases[i]
        if model not in available_models:
            missing_models.append(alias)
    
    return len(missing_models) == 0, missing_models

def test_model_response(model_name: str, test_prompt: str = "Hello, how are you?") -> Tuple[bool, float]:
    """Test a model's response capability"""
    try:
        start_time = time.time()
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": test_prompt}],
                "stream": False
            },
            timeout=60
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('message', {}).get('content', '')
            if response_text.strip():
                return True, end_time - start_time
            else:
                return False, end_time - start_time
        else:
            return False, end_time - start_time
    except Exception as e:
        return False, 0.0

def get_system_info() -> Dict:
    """Get system information for Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except:
        return {}

def main():
    """Main health check function"""
    print("🔍 Ollama Health Check")
    print("=" * 50)
    
    # Check service status
    print("\n📊 Service Status:")
    is_healthy, service_data = check_ollama_service()
    
    if is_healthy:
        print(f"✅ Ollama Service: {service_data['status']}")
        print(f"📦 Models Loaded: {service_data['models_count']}")
        
        if service_data['models']:
            print("\n📋 Loaded Models:")
            for model in service_data['models']:
                print(f"   • {model.get('name', 'Unknown')}")
    else:
        print(f"❌ Ollama Service: {service_data['status']}")
        print(f"💡 Error: {service_data.get('error', 'Unknown error')}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if Ollama is installed: ollama --version")
        print("   2. Start Ollama service: ollama serve")
        print("   3. Check if port 11434 is available")
        return False
    
    # Check required models
    print("\n🎯 Required Models Check:")
    all_models_available, missing_models = check_required_models()
    
    if all_models_available:
        print("✅ All required models are available")
    else:
        print(f"❌ Missing models: {', '.join(missing_models)}")
        print("\n📥 To install missing models:")
        print("   ollama pull hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M")
        print("   ollama pull hf.co/lm-kit/qwen-3-14b-instruct-gguf:Q4_K_M")
        print("   ollama pull deepseek-coder:6.7b-instruct")
    
    # Test model responses
    print("\n🧪 Model Response Tests:")
    test_models = [
        ("hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M", "Mistral"),
        ("hf.co/lm-kit/qwen-3-14b-instruct-gguf:Q4_K_M", "Qwen3"),
        ("deepseek-coder:6.7b-instruct", "DeepSeek")
    ]
    
    for model_name, model_alias in test_models:
        if any(m.get('name') == model_name for m in service_data['models']):
            success, response_time = test_model_response(model_name)
            if success:
                print(f"✅ {model_alias}: Responding ({response_time:.2f}s)")
            else:
                print(f"❌ {model_alias}: No response ({response_time:.2f}s)")
        else:
            print(f"⚠️ {model_alias}: Not loaded")
    
    # System information
    print("\nℹ️ System Information:")
    system_info = get_system_info()
    if system_info:
        print(f"   Version: {system_info.get('version', 'Unknown')}")
        print(f"   Git Commit: {system_info.get('git_commit', 'Unknown')}")
    else:
        print("   Unable to get system information")
    
    # Summary
    print("\n📊 Health Check Summary:")
    if is_healthy and all_models_available:
        print("🎉 Ollama is healthy and ready for use!")
        return True
    else:
        print("⚠️ Ollama needs attention")
        if not is_healthy:
            print("   - Service is not running properly")
        if not all_models_available:
            print("   - Some required models are missing")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Health check interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
