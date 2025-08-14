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
4. llama.cpp servers for HuiHui OSS20B and Mistral 7B (unified inference)
6. Database initialization
7. Voice Service (Python 3.11)
8. Main API Server (Python 3.13)
9. System verification

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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from pathlib import Path

# Ensure Unicode output works on Windows consoles
try:
	sys.stdout.reconfigure(encoding="utf-8")
	sys.stderr.reconfigure(encoding="utf-8")
except Exception:
	pass

def is_process_running(process_name):
    """Check if a process is running on Windows"""
    try:
        result = subprocess.run(f'tasklist | findstr /i "{process_name}"', 
                              shell=True, capture_output=True, text=True)
        return result.returncode == 0 and process_name.lower() in result.stdout.lower()
    except Exception:
        return False

def check_docker_actually_working():
    """Check if Docker Desktop is actually working by testing container operations"""
    try:
        # Try to run a simple docker command that requires the daemon
        result = subprocess.run("docker ps", shell=True, 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def start_docker_desktop():
    """Start Docker Desktop if not running"""
    print("🐳 Checking Docker Desktop...")
    
    # Check if Docker Desktop is actually working (not just CLI available)
    if check_docker_actually_working():
        print("✅ Docker Desktop is working properly")
        return True
    
    # Check if Docker Desktop process is running
    if is_process_running("Docker Desktop") or is_process_running("com.docker.service"):
        print("⚠️ Docker Desktop process found but not working properly")
        # Continue to restart it
    else:
        print("❌ Docker Desktop not running")
    
    print("🔄 Starting Docker Desktop...")
    
    # Get Docker Desktop path (cloud-ready)
    docker_exe = os.getenv("DOCKER_DESKTOP_PATH", "C:/Program Files/Docker/Docker/Docker Desktop.exe")
    
    if not os.path.exists(docker_exe):
        print(f"❌ Docker Desktop not found at: {docker_exe}")
        print("💡 Set DOCKER_DESKTOP_PATH environment variable for custom location")
        return False
    
    try:
        # Start Docker Desktop
        subprocess.Popen([docker_exe], shell=True)
        print("⏳ Waiting for Docker Desktop to start...")
        
        # Wait for Docker Desktop to be ready (up to 120 seconds)
        for i in range(120):
            time.sleep(2)
            try:
                # Test actual Docker functionality, not just CLI
                if check_docker_actually_working():
                    print("✅ Docker Desktop started successfully")
                    return True
            except:
                pass
            
            if i % 30 == 0 and i > 0:  # Show progress every 60 seconds
                print(f"⏳ Still waiting for Docker Desktop... ({i*2}/240 seconds)")
        
        print("❌ Docker Desktop failed to start within 4 minutes")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start Docker Desktop: {e}")
        return False

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
    """Check if a Docker container is running and start it if stopped"""
    try:
        # First check if running
        result = subprocess.run(f"docker ps --format '{{{{.Names}}}}' | grep {container_name}", 
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True  # Already running
        
        # Check if container exists but is stopped
        result = subprocess.run(f"docker ps -a --format '{{{{.Names}}}}' | grep {container_name}", 
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # Container exists but is stopped - start it
            print(f"🔄 Starting existing {container_name} container...")
            start_result = subprocess.run(f"docker start {container_name}", 
                                        shell=True, capture_output=True, text=True)
            if start_result.returncode == 0:
                print(f"✅ {container_name} container started successfully")
                return True
            else:
                print(f"❌ Failed to start {container_name}: {start_result.stderr}")
                return False
        
        # Container doesn't exist at all
        return False
        
    except Exception as e:
        print(f"⚠️ Docker check error for {container_name}: {e}")
        return False


def _load_llamacpp_config_module():
    """Load llama.cpp model config robustly despite config.py shadowing.
    Returns a module-like object with LLAMACPP_MODELS and validate_model_files.
    """
    try:
        import importlib
        return importlib.import_module("config.llama_cpp_models")
    except Exception:
        # Fallback: import directly from config/ folder
        cfg_dir = Path(__file__).parent / "config"
        if str(cfg_dir) not in sys.path:
            sys.path.insert(0, str(cfg_dir))
        import importlib
        return importlib.import_module("llama_cpp_models")


def check_llamacpp_health():
    """Check if llama.cpp servers are running and healthy"""
    llama_cfg = _load_llamacpp_config_module()
    healthy_servers = []
    total_servers = len(llama_cfg.LLAMACPP_MODELS)
    for model_name, config in llama_cfg.LLAMACPP_MODELS.items():
        port = int(config["port"])
        try:
            import requests
            host = str(config.get("host", "127.0.0.1"))
            response = requests.get(f"http://{host}:{port}/health", timeout=5)
            if response.status_code == 200:
                healthy_servers.append((model_name, port))
            else:
                print(f"   ⚠️ {model_name} server (port {port}) returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ {model_name} server (port {port}) connection refused")
        except requests.exceptions.Timeout:
            print(f"   ⏰ {model_name} server (port {port}) timeout")
        except Exception as e:
            print(f"   ❌ {model_name} server health check error: {e}")
    return len(healthy_servers) == total_servers, len(healthy_servers), healthy_servers

def _build_llamacpp_env() -> dict:
    """Build environment for starting llama.cpp servers on Windows."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "1"
    # Ensure child can import config/ modules even with config.py present
    project_root = str(Path(__file__).parent.resolve())
    config_dir = str(Path(__file__).parent.joinpath("config").resolve())
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    for p in (project_root, config_dir):
        if p not in parts:
            parts.append(p)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    # Best-effort resolve llama-server binary
    default_bin = Path("D:/llama.cpp/llama-server.exe")
    if "LLAMA_SERVER_BIN" not in env and default_bin.exists():
        env["LLAMA_SERVER_BIN"] = str(default_bin)
    return env


def start_llamacpp_servers():
    """Start llama.cpp servers for both HuiHui OSS20B and Mistral 7B"""
    print("🤖 Starting llama.cpp inference servers...")
    
    # First check if servers are already running
    all_healthy, healthy_count, healthy_servers = check_llamacpp_health()
    if all_healthy:
        print(f"✅ All {healthy_count} llama.cpp servers already running")
        for model_name, port in healthy_servers:
            print(f"   • {model_name} (port {port})")
        return True
    
    # Start the servers using our dedicated script
    print("🔄 Starting llama.cpp servers...")
    try:
        # Prepare log and environment
        log_dir = Path('.logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'llamacpp_servers_from_start_all.log'
        log_file = open(log_path, 'a', encoding='utf-8')
        env = _build_llamacpp_env()
        # Run the server manager script in background with robust env
        process = subprocess.Popen(
            [sys.executable, "scripts/start_llamacpp_servers.py"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            shell=False
        )
        
        # Wait for servers to start
        print("⏳ Waiting for llama.cpp servers to start...")
        for i in range(60):  # Wait up to 60 seconds
            time.sleep(2)
            all_healthy, healthy_count, healthy_servers = check_llamacpp_health()
            
            if all_healthy:
                print(f"✅ All {healthy_count} llama.cpp servers started successfully")
                for model_name, port in healthy_servers:
                    print(f"   • {model_name} (port {port})")
                return True
            elif i % 5 == 0:  # Show progress every 10 seconds
                print(f"⏳ Waiting for servers ({healthy_count}/2 ready)... ({i*2}/120s)")
        
        # Final check
        all_healthy, healthy_count, healthy_servers = check_llamacpp_health()
        if healthy_count > 0:
            print(f"✅ {healthy_count}/2 llama.cpp servers started")
            for model_name, port in healthy_servers:
                print(f"   • {model_name} (port {port})")
            return healthy_count > 0  # Partial success is okay
        else:
            print("❌ llama.cpp servers failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Error starting llama.cpp servers: {e}")
        return False

def verify_llamacpp_models_available():
    """Verify that required llama.cpp models are available"""
    print("📦 Verifying llama.cpp models are available...")
    
    from config.llama_cpp_models import validate_model_files, LLAMACPP_MODELS
    
    validation_results = validate_model_files()
    missing_models = [model for model, exists in validation_results.items() if not exists]
    
    if missing_models:
        print(f"❌ Missing model files: {missing_models}")
        print("💡 Please ensure all models are in D:/Council-Project/models/llama-cpp/")
        return False
    else:
        print(f"✅ All {len(LLAMACPP_MODELS)} model files found")
        for model_name, config in LLAMACPP_MODELS.items():
            print(f"   • {model_name}: {config['file_path'].name}")
        return True




def check_tigergraph_graph_exists():
    """Check if HybridAICouncil graph exists with proper schema"""
    try:
        # Import here to avoid circular imports
        sys.path.append('.')
        from clients.tigervector_client import get_tigergraph_connection, is_graph_initialized
        
        conn = get_tigergraph_connection()
        if conn is None:
            return False
            
        # Delegate to the TigerGraph client for proper schema checking
        return is_graph_initialized(conn)
            
    except Exception as e:
        print(f"   ⚠️ Error checking TigerGraph graph: {e}")
        return False

def start_services():
    """Start all services in the correct order"""
    print("🚀 Starting ALL Hybrid AI Council Services...")
    print("=" * 60)
    
    # Step 0: Auto-start dependencies
    print("\n🔧 Step 0: Starting Required Dependencies...")
    
    # Auto-start Docker Desktop
    if not start_docker_desktop():
        print("⚠️ Docker Desktop startup failed, but continuing...")
        print("💡 Some services (TigerGraph, Redis) may not work without Docker")
    
    # Auto-start llama.cpp servers
    if not start_llamacpp_servers():
        print("⚠️ llama.cpp servers startup failed, but continuing...")
        print("💡 LLM services will not work without llama.cpp servers")
    else:
        # Verify models are available
        verify_llamacpp_models_available()
    
    print("\n✅ Dependencies startup phase complete!")
    
    # Step 1: Check Docker (keeping original check)
    if not run_command("docker --version", "Checking Docker"):
        print("⚠️ Docker not available, but continuing...")
    
    # Step 2: Start TigerGraph (PRESERVE EXISTING DATA!)
    print("\n📊 Step 2: Starting TigerGraph...")
    if not check_docker_container("tigergraph"):
        # DO NOT cleanup - preserve existing data!
        print("🔄 Starting TigerGraph container...")
        run_command("docker run -d --name tigergraph -p 14240:14240 -p 9000:9000 -v tigergraph_data:/home/tigergraph/tigergraph/data tigergraph/community:4.2.0", "Starting TigerGraph container")
        time.sleep(15)  # Wait longer for TigerGraph to start
    else:
        print("✅ TigerGraph already running")
    
    # Step 3: Start Redis (PRESERVE EXISTING DATA!)
    print("\n🔴 Step 3: Starting Redis...")
    if not check_docker_container("redis"):
        # DO NOT cleanup - preserve existing data!
        print("🔄 Starting Redis container with persistent data...")
        run_command("docker run -d --name redis -p 6379:6379 -v redis_data:/data redis:8.0-alpine", "Starting Redis container")
        time.sleep(3)
    else:
        print("✅ Redis already running")
    
    # Step 4: Verify llama.cpp servers are ready (already started in Step 0)
    print("\n🤖 Step 4: Verifying llama.cpp servers...")
    all_healthy, healthy_count, healthy_servers = check_llamacpp_health()
    if all_healthy:
        print(f"✅ llama.cpp verified - {healthy_count} servers available")
        for model_name, port in healthy_servers:
            print(f"   • {model_name} (port {port})")
    else:
        print("⚠️ llama.cpp servers not fully responding, but continuing...")
    
    # Step 5: Verify llama.cpp models are loaded
    print("\n📦 Step 5: Verifying llama.cpp models...")
    verify_llamacpp_models_available()
    
    
    # Step 6: Initialize TigerGraph database
    print("\n🗄️ Step 6: Initializing TigerGraph database...")
    # Wait for TigerGraph GSQL service to be ready before initializing
    print("⏳ Waiting for TigerGraph GSQL service to be ready...")
    for i in range(60):  # Increased timeout for GSQL service
        time.sleep(2)
        try:
            import requests
            # Check GSQL API specifically (needed for database initialization)
            response = requests.get("http://localhost:14240/gsql/v1/statements", timeout=5)
            if response.status_code == 401:  # 401 = GSQL ready but needs auth (expected)
                print("✅ TigerGraph GSQL service is ready")
                break
            elif response.status_code == 502:  # 502 = GSQL not ready yet
                if i % 10 == 0:  # Show progress every 20 seconds
                    print(f"   ⏳ GSQL service starting... ({i+1}/60)")
        except:
            pass
    else:
        print("⚠️ TigerGraph GSQL service may not be fully ready (proceeding anyway)")
    
    # Check if HybridAICouncil graph exists
    if check_tigergraph_graph_exists():
        print("✅ TigerGraph HybridAICouncil graph already exists")
    else:
        # Now try to initialize the database
        print("🔄 Initializing TigerGraph database...")
        init_result = run_command("python scripts/init_tigergraph.py", "Initializing TigerGraph database", check=False)
        if not init_result:
            print("⚠️ TigerGraph initialization failed, but continuing...")
        else:
            print("✅ TigerGraph database initialized successfully")
    
    # Step 7: Start voice service
    print("\n🎤 Step 7: Starting Voice Service...")
    voice_dir = Path(__file__).parent / "python311-services"
    
    # Start voice service in background
    print("🔄 Starting voice service...")
    # Get Python executable (cloud-ready)
    username = os.getenv("USERNAME", "RedactedFoundry")
    python_exe = os.getenv("VOICE_PYTHON_PATH", 
        f"C:/Users/{username}/AppData/Local/pypoetry/Cache/virtualenvs/python311-services-A1b0dxtl-py3.11/Scripts/python.exe")
    
    if not os.path.exists(python_exe):
        print(f"❌ Python executable not found at: {python_exe}")
        print("💡 Set VOICE_PYTHON_PATH environment variable for custom location")
        return False
        
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
    
    # Step 8: Start main API server
    print("\n🌐 Step 8: Starting Main API Server...")
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
    print("\n🔍 Step 9: Verifying All Services...")
    
    services = [
        ("TigerGraph", "http://localhost:14240/api/ping"),
        ("Redis", "socket:6379"),  # Special case - use socket check
        ("llama.cpp HuiHui", "http://localhost:8081/health"),
        ("llama.cpp Mistral", "http://localhost:8082/health"),
        ("Voice Service", "http://localhost:8011/health"),
        ("Main API", "http://localhost:8001/health")
    ]
    
    all_ready = True
    for name, url in services:
        try:
            if url.startswith("socket:"):
                # Socket check for Redis
                import socket
                port = int(url.split(":")[1])
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                if result == 0:
                    print(f"✅ {name}: Running")
                else:
                    print(f"❌ {name}: Not responding")
                    all_ready = False
            else:
                # HTTP check for other services
                import requests
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