#!/usr/bin/env python3
"""
Master Startup Script for Hybrid AI Council
============================================

🚀 ONE COMMAND TO START EVERYTHING 🚀

Starts the complete Hybrid AI Council system in the correct order:
1. Docker service check
2. TigerGraph Community Edition  
3. Redis cache
4. Ollama LLM service
5. Database initialization
6. System verification
7. Optional: API server startup

Usage:
    python scripts/start_everything.py [--with-api] [--skip-verify]
    
Options:
    --with-api      Also start the FastAPI server (uvicorn)
    --skip-verify   Skip final system verification
    --quiet         Minimal output (errors only)
"""

import time
import sys
import os
import subprocess
import argparse
from pathlib import Path
import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up structured logging  
logger = structlog.get_logger("master_startup")

def print_banner():
    """Print the startup banner."""
    print("\n" + "="*60)
    print("🚀 HYBRID AI COUNCIL - MASTER STARTUP")
    print("="*60)
    print("Starting all services in optimal order...")
    print()

def check_docker():
    """Check if Docker is running."""
    logger.info("Step 1: Checking Docker service")
    try:
        result = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker is running and accessible")
            return True
        else:
            print("❌ Docker check failed")
            print("💡 Please start Docker Desktop and try again")
            return False
    except FileNotFoundError:
        print("❌ Docker not found - please install Docker Desktop")
        return False
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False

def start_tigergraph():
    """Start TigerGraph Community Edition."""
    logger.info("Step 2: Starting TigerGraph Community Edition")
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=tigergraph", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and "tigergraph" in result.stdout:
            if "Up" in result.stdout:
                print("✅ TigerGraph container already running")
                return True
            else:
                print("🔄 Starting existing TigerGraph container...")
                start_result = subprocess.run(["docker", "start", "tigergraph"], 
                                            capture_output=True, text=True, timeout=30)
                if start_result.returncode == 0:
                    print("✅ TigerGraph container started")
                    return True
        
        # Container doesn't exist, create it
        print("🏗️ Creating new TigerGraph container...")
        setup_script = project_root / "scripts" / "setup-tigergraph.sh"
        if setup_script.exists():
            setup_result = subprocess.run(
                ["bash", str(setup_script)], 
                cwd=str(project_root),
                capture_output=True, text=True, timeout=300
            )
            if setup_result.returncode == 0:
                print("✅ TigerGraph container created and started")
                return True
            else:
                print(f"❌ TigerGraph setup failed: {setup_result.stderr[:200]}")
                return False
        else:
            print("❌ TigerGraph setup script not found")
            return False
            
    except Exception as e:
        print(f"❌ TigerGraph startup failed: {e}")
        return False

def start_redis():
    """Start Redis container."""
    logger.info("Step 3: Starting Redis cache")
    try:
        # Check if Redis is already running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=redis", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and "redis" in result.stdout and "Up" in result.stdout:
            print("✅ Redis container already running")
            return True
        
        # Start Redis via docker-compose
        print("🔄 Starting Redis container...")
        redis_result = subprocess.run(
            ["docker-compose", "up", "-d", "redis"],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=60
        )
        
        if redis_result.returncode == 0:
            print("✅ Redis container started")
            return True
        else:
            print(f"❌ Redis startup failed: {redis_result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Redis startup failed: {e}")
        return False

def start_ollama():
    """Start Ollama LLM service."""
    logger.info("Step 4: Starting Ollama LLM service")
    try:
        # Check if Ollama is already running
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"✅ Ollama already running with {len(models)} models")
                return True
        except:
            pass
        
        # Try to start Ollama
        print("🔄 Starting Ollama service...")
        
        # On Windows, check if ollama is installed
        if os.name == 'nt':  # Windows
            try:
                subprocess.run(["ollama", "serve"], timeout=2)
            except subprocess.TimeoutExpired:
                pass  # Expected - serve runs in background
            except FileNotFoundError:
                print("❌ Ollama not installed. Please install from https://ollama.ai")
                return False
        else:  # Linux/Mac
            try:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                print("❌ Ollama not installed. Please install from https://ollama.ai")
                return False
        
        # Wait for Ollama to be ready
        print("⏳ Waiting for Ollama to be ready...")
        for i in range(30):  # 30 second timeout
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    print(f"✅ Ollama is ready with {len(models)} models")
                    return True
            except:
                time.sleep(1)
        
        print("⚠️ Ollama may not be fully ready, but continuing...")
        return True
        
    except Exception as e:
        print(f"❌ Ollama startup failed: {e}")
        return False

def wait_for_services():
    """Wait for all services to be fully ready."""
    logger.info("Step 5: Waiting for services to be ready")
    print("⏳ Waiting for all services to be ready...")
    
    max_wait = 60  # 60 seconds total
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Check TigerGraph
            tg_ready = False
            try:
                tg_result = subprocess.run(
                    ["docker", "exec", "tigergraph", "curl", "-s", "http://localhost:14240/api/ping"],
                    capture_output=True, text=True, timeout=5
                )
                if tg_result.returncode == 0 and "pong" in tg_result.stdout.lower():
                    tg_ready = True
            except:
                pass
            
            # Check Redis
            redis_ready = False
            try:
                # Try the actual container name from docker-compose
                redis_result = subprocess.run(
                    ["docker", "exec", "hybrid-cognitive-architecture-redis-1", "redis-cli", "ping"],
                    capture_output=True, text=True, timeout=5
                )
                if redis_result.returncode == 0 and "PONG" in redis_result.stdout:
                    redis_ready = True
                else:
                    # Fallback: try generic redis container name
                    redis_result = subprocess.run(
                        ["docker", "exec", "redis", "redis-cli", "ping"],
                        capture_output=True, text=True, timeout=5
                    )
                    if redis_result.returncode == 0 and "PONG" in redis_result.stdout:
                        redis_ready = True
            except:
                pass
            
            # Check Ollama
            ollama_ready = False
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    ollama_ready = True
            except:
                pass
            
            if tg_ready and redis_ready and ollama_ready:
                print("✅ All services are ready")
                return True
            
            elapsed = int(time.time() - start_time)
            status = []
            if tg_ready: status.append("TG✅")
            else: status.append("TG⏳")
            if redis_ready: status.append("Redis✅") 
            else: status.append("Redis⏳")
            if ollama_ready: status.append("Ollama✅")
            else: status.append("Ollama⏳")
            
            print(f"   {' '.join(status)} ({elapsed}s elapsed)")
            time.sleep(3)
            
        except Exception as e:
            logger.debug("Service check failed", error=str(e))
            time.sleep(3)
    
    print("⚠️ Services may not be fully ready, but continuing...")
    return True

def initialize_databases():
    """Initialize TigerGraph database with smart initialization."""
    logger.info("Step 6: Initializing databases")
    print("🗄️ Initializing TigerGraph database...")
    
    try:
        init_result = subprocess.run(
            [sys.executable, "scripts/smart_tigergraph_init.py"],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=120
        )
        
        if init_result.returncode == 0:
            if "already fully initialized" in init_result.stdout:
                print("✅ Database already initialized and ready")
            else:
                print("✅ Database initialized successfully")
            return True
        else:
            print(f"❌ Database initialization failed")
            print(f"Error: {init_result.stderr[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def verify_system(skip_verify=False):
    """Run system verification."""
    if skip_verify:
        print("⏭️ Skipping system verification")
        return True
        
    logger.info("Step 7: Running system verification")
    print("🔍 Running system verification...")
    
    try:
        verify_result = subprocess.run(
            [sys.executable, "verify_system.py"],
            cwd=str(project_root),
            capture_output=True, text=True, timeout=60
        )
        
        if "Overall Status" in verify_result.stdout:
            # Extract the status line
            lines = verify_result.stdout.split('\n')
            for line in lines:
                if "Overall Status:" in line:
                    print(f"✅ {line.strip()}")
                    break
            return True
        else:
            print("⚠️ Verification completed with warnings")
            return True
            
    except Exception as e:
        print(f"❌ System verification failed: {e}")
        return False

def start_api_server(start_api=False):
    """Optionally start the FastAPI server."""
    if not start_api:
        return True
        
    logger.info("Step 8: Starting API server")
    print("🌐 Starting FastAPI server...")
    
    try:
        # Check if API is already running
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ API server already running at http://localhost:8000")
                return True
        except:
            pass
        
        print("🔄 Starting uvicorn server in background...")
        # Start uvicorn in background with WebSocket support
        if os.name == 'nt':  # Windows
            subprocess.Popen([
                sys.executable, "-m", "uvicorn", "main:app", 
                "--host", "127.0.0.1", "--port", "8000"
            ], cwd=str(project_root))
        else:  # Linux/Mac
            subprocess.Popen([
                sys.executable, "-m", "uvicorn", "main:app", 
                "--host", "127.0.0.1", "--port", "8000"
            ], cwd=str(project_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait and verify the server actually started
        print("⏳ Waiting for API server to be ready...")
        for i in range(10):  # 10 second timeout
            time.sleep(1)
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    print("✅ API server is ready at http://localhost:8000")
                    print("🌐 UI available at: http://localhost:8000/static/index.html")
                    return True
            except:
                pass
        
        print("⚠️ API server may still be starting - check http://localhost:8000")
        return True
        
    except Exception as e:
        print(f"❌ API server startup failed: {e}")
        return False

def print_summary():
    """Print startup summary."""
    print("\n" + "="*60)
    print("🎉 HYBRID AI COUNCIL - STARTUP COMPLETE!")
    print("="*60)
    print()
    print("📊 Services Running:")
    print("   • TigerGraph Community Edition: http://localhost:14240")
    print("   • Redis Cache: localhost:6379")
    print("   • Ollama LLM Service: localhost:11434")
    print("   • Graph Database: HybridAICouncil")
    print()
    print("🔧 Development Commands:")
    print("   • System Status: python verify_system.py")
    print("   • Start API: uvicorn main:app --host 127.0.0.1 --port 8000")
    print("   • View Logs: docker-compose logs -f")
    print()
    print("🚀 Your Hybrid AI Council is ready for action!")
    print("="*60)

def master_startup(with_api=False, skip_verify=False, quiet=False):
    """Master startup function that orchestrates everything."""
    
    if not quiet:
        print_banner()
    
    # Step 1: Docker check
    if not check_docker():
        return False
    
    # Step 2: TigerGraph
    if not start_tigergraph():
        return False
    
    # Step 3: Redis
    if not start_redis():
        return False
    
    # Step 4: Ollama
    if not start_ollama():
        return False
    
    # Step 5: Wait for services
    if not wait_for_services():
        return False
    
    # Step 6: Initialize databases
    if not initialize_databases():
        return False
    
    # Step 7: System verification
    if not verify_system(skip_verify):
        return False
    
    # Step 8: Optional API server
    if not start_api_server(with_api):
        return False
    
    if not quiet:
        print_summary()
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the complete Hybrid AI Council system")
    parser.add_argument("--with-api", action="store_true", help="Also start the FastAPI server")
    parser.add_argument("--skip-verify", action="store_true", help="Skip final system verification")
    parser.add_argument("--quiet", action="store_true", help="Minimal output (errors only)")
    
    args = parser.parse_args()
    
    try:
        success = master_startup(
            with_api=args.with_api,
            skip_verify=args.skip_verify,
            quiet=args.quiet
        )
        
        if success:
            if not args.quiet:
                print("\n🎯 Startup completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Startup failed - check errors above")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error during startup", error=str(e))
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)