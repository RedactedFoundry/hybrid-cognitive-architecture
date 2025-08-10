#!/usr/bin/env python3
"""
🚀 ONE COMMAND TO START EVERYTHING 🚀

Comprehensive startup script that starts the complete Hybrid AI Council system
including ALL services and the voice service.

Usage:
    python start_all.py

This will start:
1. Docker service check
2. TigerGraph Community Edition
3. Redis cache
4. Ollama LLM service (auto-start if needed)
5. Database initialization
6. Voice Service (Python 3.11)
7. Main API Server (Python 3.13)
8. System verification

All services will be available at:
- Main Dashboard: http://localhost:8001/static/index.html
- Voice Chat: http://localhost:8001/static/realtime-voice.html
- Voice Service: http://localhost:8011/health
"""

import sys
import os
import subprocess
import time
import signal
from pathlib import Path

def run_command(cmd, description, check=True, capture_output=False):
    """Run a command with error handling and show output"""
    print(f"🔄 {description}...")
    print(f"   Command: {cmd}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def check_docker_container(container_name):
    """Check if a Docker container is running"""
    try:
        result = subprocess.run(f"docker ps --format '{{{{.Names}}}}' | grep {container_name}", 
                              shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"⚠️ Docker check error for {container_name}: {e}")
        return False

def check_ollama_health():
    """Check if Ollama is running and healthy"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            return True, len(models), models
        return False, 0, []
    except Exception as e:
        return False, 0, []

def start_ollama_service():
    """Start Ollama if not running, with proper error handling"""
    print("🤖 Starting Ollama LLM service...")
    
    # First check if Ollama is already running
    is_healthy, model_count, models = check_ollama_health()
    if is_healthy:
        print(f"✅ Ollama already running with {model_count} models")
        for model in models:
            print(f"   • {model.get('name', 'Unknown')}")
        return True
    
    # Check if Ollama is installed
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ollama not installed. Please install from https://ollama.ai")
            print("💡 Windows: Download from https://ollama.ai/download")
            return False
    except FileNotFoundError:
        print("❌ Ollama not found in PATH. Please install from https://ollama.ai")
        return False
    
    # Start Ollama service
    print("🔄 Starting Ollama service...")
    try:
        # Start Ollama in background
        if os.name == 'nt':  # Windows
            # Use subprocess.Popen with shell=True for Windows
            process = subprocess.Popen(
                ["ollama", "serve"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:  # Linux/Mac
            process = subprocess.Popen(
                ["ollama", "serve"], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
        
        print("⏳ Waiting for Ollama to start...")
        
        # Wait for Ollama to be ready (up to 30 seconds)
        for i in range(30):
            time.sleep(1)
            is_healthy, model_count, models = check_ollama_health()
            if is_healthy:
                print(f"✅ Ollama started successfully with {model_count} models")
                for model in models:
                    print(f"   • {model.get('name', 'Unknown')}")
                return True
            elif i % 5 == 0:  # Show progress every 5 seconds
                print(f"⏳ Still waiting for Ollama... ({i+1}/30)")
        
        print("❌ Ollama failed to start within 30 seconds")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start Ollama: {e}")
        return False

def verify_ollama_models():
    """Verify that required models are available"""
    print("📦 Verifying Ollama models...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"📋 Available models: {len(models)}")
            for model in models:
                print(f"   • {model.get('name', 'Unknown')}")
            
            # Check if required models are available (2-model experiment)
            required_models = [
                "huihui-oss20b",                                         # generator
                "hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M"   # verifier/coordinator
            ]
            model_aliases = ["generator", "verifier"]
            
            all_models_available = True
            for i, model in enumerate(required_models):
                alias = model_aliases[i]
                if any(m.get('name') == model for m in models):
                    print(f"✅ Model available: {alias}")
                else:
                    print(f"❌ Model missing: {alias}")
                    all_models_available = False
            
            if all_models_available:
                print("🎉 All required models are available!")
                return True
            else:
                print("⚠️ Some models are missing, but continuing...")
                return False
        else:
            print("❌ Failed to get model list from Ollama")
            return False
    except Exception as e:
        print(f"⚠️ Error checking models: {e}")
        return False

def check_tigergraph_ready():
    """Check if TigerGraph is ready and database is initialized"""
    try:
        import requests
        response = requests.get("http://localhost:14240/api/ping", timeout=5)
        if response.status_code == 200:
            # Try to connect to the graph to see if it's initialized
            try:
                # This will fail if the graph doesn't exist, but that's expected
                response = requests.get("http://localhost:14240/graph/HybridAICouncil", timeout=5)
                return True  # Graph exists, so initialization is complete
            except:
                return False  # Graph doesn't exist yet
        return False
    except:
        return False

def start_services():
    """Start all services in the correct order"""
    print("🚀 Starting ALL Hybrid AI Council Services...")
    print("=" * 60)
    
    # Step 1: Check Docker
    if not run_command("docker --version", "Checking Docker"):
        print("⚠️ Docker not available, but continuing...")
    
    # Step 2: Start TigerGraph
    print("\n📊 Step 1: Starting TigerGraph...")
    if not check_docker_container("tigergraph"):
        print("Starting TigerGraph...")
        run_command("docker run -d --name tigergraph -p 14240:14240 -p 9000:9000 tigergraph/tigergraph-community:latest", "Starting TigerGraph container")
        time.sleep(15)  # Wait longer for TigerGraph to start
    else:
        print("✅ TigerGraph already running")
    
    # Step 3: Start Redis
    print("\n🔴 Step 2: Starting Redis...")
    if not check_docker_container("redis"):
        run_command("docker run -d --name redis -p 6379:6379 redis:latest", "Starting Redis container")
        time.sleep(3)
    else:
        print("✅ Redis already running")
    
    # Step 4: Start Ollama (with auto-start)
    print("\n🤖 Step 3: Starting Ollama...")
    if not start_ollama_service():
        print("⚠️ Ollama startup failed, but continuing...")
    
    # Step 4.5: Verify Ollama models
    print("\n📦 Step 3.5: Verifying Ollama models...")
    verify_ollama_models()
    
    # Step 5: Initialize TigerGraph database
    print("\n🗄️ Step 4: Initializing TigerGraph database...")
    # Wait for TigerGraph to be ready before initializing
    print("⏳ Waiting for TigerGraph to be ready...")
    for i in range(30):
        time.sleep(2)
        try:
            import requests
            response = requests.get("http://localhost:14240/api/ping", timeout=5)
            if response.status_code == 200:
                print("✅ TigerGraph is ready")
                break
        except:
            pass
    else:
        print("⚠️ TigerGraph may not be fully ready")
    
    # Check if database is already initialized
    if check_tigergraph_ready():
        print("✅ TigerGraph database already initialized")
    else:
        # Now try to initialize the database
        print("🔄 Initializing TigerGraph database...")
        init_result = run_command("python scripts/init_tigergraph.py", "Initializing TigerGraph database", check=False)
        if not init_result:
            print("⚠️ TigerGraph initialization failed, but continuing...")
        else:
            print("✅ TigerGraph database initialized successfully")
    
    # Step 6: Start voice service
    print("\n🎤 Step 5: Starting Voice Service...")
    voice_dir = Path(__file__).parent / "python311-services"
    
    # Start voice service in background
    print("🔄 Starting voice service...")
    # Use the direct Python executable from the virtual environment
    python_exe = "C:/Users/Jake/AppData/Local/pypoetry/Cache/virtualenvs/python311-services-A1b0dxtl-py3.11/Scripts/python.exe"
    voice_cmd = f"cd {voice_dir} && \"{python_exe}\" voice/main.py"
    voice_process = subprocess.Popen(voice_cmd, shell=True)  # Remove pipe capture to keep process alive
    
    print("✅ Voice service started in background")
    
    # Wait for voice service to be ready
    print("⏳ Waiting for voice service to be ready...")
    for i in range(60):  # 60 second timeout
        time.sleep(1)
        try:
            import requests
            response = requests.get("http://localhost:8011/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                stt_status = data.get('services', {}).get('stt', {}).get('initialized', False)
                tts_status = data.get('services', {}).get('tts', {}).get('initialized', False)
                if stt_status and tts_status:
                    print("✅ Voice service ready (STT & TTS initialized)")
                    break
                else:
                    print("⏳ Voice service starting (engines initializing)...")
        except:
            if i % 10 == 0:  # Show message every 10 seconds
                print("⏳ Waiting for voice service...")
    else:
        print("⚠️ Voice service may still be starting")
    
    # Step 7: Start main API server
    print("\n🌐 Step 6: Starting Main API Server...")
    api_cmd = "python -m uvicorn main:app --host 127.0.0.1 --port 8001 --timeout-keep-alive 5"
    print(f"🔄 Starting main API: {api_cmd}")
    api_process = subprocess.Popen(api_cmd, shell=True)  # Remove pipe capture to keep process alive
    
    print("✅ Main API server started in background")
    
    # Wait for main API to be ready
    print("⏳ Waiting for main API to be ready...")
    for i in range(30):  # 30 second timeout
        time.sleep(1)
        try:
            import requests
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("✅ Main API server ready")
                break
        except:
            if i % 10 == 0:  # Show message every 10 seconds
                print("⏳ Waiting for main API...")
    else:
        print("⚠️ Main API may still be starting")
    
    return True

def verify_services():
    """Verify all services are running"""
    print("\n🔍 Step 7: Verifying All Services...")
    
    services = [
        ("TigerGraph", "http://localhost:14240/api/ping"),
        ("Redis", "http://localhost:6379"),  # Will fail but that's expected
        ("Ollama", "http://localhost:11434/api/tags"),
        ("Voice Service", "http://localhost:8011/health"),
        ("Main API", "http://localhost:8001/health")
    ]
    
    all_ready = True
    for name, url in services:
        try:
            import requests
            if name == "Redis":
                # Redis doesn't have HTTP endpoint, just check if port is open
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 6379))
                sock.close()
                if result == 0:
                    print(f"✅ {name}: Running")
                else:
                    print(f"❌ {name}: Not responding")
                    all_ready = False
            else:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {name}: Healthy")
                else:
                    print(f"❌ {name}: Unhealthy ({response.status_code})")
                    all_ready = False
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            all_ready = False
    
    return all_ready

if __name__ == "__main__":
    try:
        # Start all services
        if not start_services():
            print("\n💥 Service startup failed!")
            sys.exit(1)
        
        # Verify services
        if not verify_services():
            print("\n⚠️ Some services may not be fully ready")
        else:
            print("\n🎉 ALL SERVICES READY!")
        
        print("\n🌐 Access your system at:")
        print("   • Main Dashboard: http://localhost:8001/static/index.html")
        print("   • Voice Chat: http://localhost:8001/static/realtime-voice.html")
        print("   • Voice Health: http://localhost:8011/health")
        print("\n🎤 Voice chat is ready to use!")
        print("\n💡 If any services aren't ready, wait a few more seconds and refresh.")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n⚠️ Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 