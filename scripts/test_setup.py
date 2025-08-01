#!/usr/bin/env python3
"""
Hybrid AI Council Setup Validation Script

Comprehensive test suite to validate all system components are working correctly.
Tests TigerGraph Community Edition, Redis, vLLM, and their integrations.

Usage:
    python scripts/test_setup.py
"""

import os
import sys
import requests
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def test_tigergraph():
    """Test TigerGraph Community Edition connectivity and functionality"""
    print("🔍 Testing TigerGraph Community Edition...")
    
    try:
        from clients.tigervector_client import test_connection, get_tigergraph_connection
        
        # Test basic connectivity
        if not test_connection():
            print("❌ TigerGraph connection failed")
            print("💡 Run: ./scripts/setup-tigergraph.sh")
            return False
        
        # Test graph operations
        conn = get_tigergraph_connection("HybridAICouncil")
        if not conn:
            print("❌ TigerGraph connection object failed")
            return False
        
        # Test basic operations
        try:
            version = conn.getVersion()
            print(f"✅ TigerGraph version: {version}")
        except Exception as e:
            print(f"⚠️  TigerGraph connected but limited functionality: {e}")
        
        print("✅ TigerGraph Community Edition: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install pyTigerGraph")
        return False
    except Exception as e:
        print(f"❌ TigerGraph test failed: {e}")
        return False

def test_redis():
    """Test Redis connectivity and basic operations"""
    print("\n🔍 Testing Redis...")
    
    try:
        from clients.redis_client import get_redis_connection
        
        redis_client = get_redis_connection()
        if not redis_client:
            print("❌ Redis connection failed")
            print("💡 Run: docker-compose up -d redis")
            return False
        
        # Test basic operations
        test_key = "hybrid_ai_test"
        test_value = "test_value"
        
        redis_client.set(test_key, test_value, ex=10)  # 10 second expiry
        retrieved_value = redis_client.get(test_key)
        
        # Handle both bytes and string returns from Redis
        if retrieved_value:
            if isinstance(retrieved_value, bytes):
                retrieved_value = retrieved_value.decode()
            
            if retrieved_value == test_value:
                print("✅ Redis read/write: PASSED")
            else:
                print("❌ Redis read/write: FAILED")
                return False
        else:
            print("❌ Redis read/write: FAILED - No value returned")
            return False
        
        # Test TTL functionality (important for Pheromind 12s TTL)
        ttl = redis_client.ttl(test_key)
        if ttl > 0:
            print(f"✅ Redis TTL functionality: PASSED ({ttl}s remaining)")
        else:
            print("❌ Redis TTL functionality: FAILED")
            return False
        
        # Cleanup
        redis_client.delete(test_key)
        print("✅ Redis: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def test_ollama():
    """Test Ollama local AI model service"""
    print("\n🔍 Testing Ollama...")
    
    try:
        # Get Ollama URL from environment
        ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        ollama_port = os.getenv("OLLAMA_PORT", "11434")
        ollama_url = f"http://{ollama_host}:{ollama_port}"
        
        # Test health endpoint
        health_response = requests.get(f"{ollama_url}/api/tags", timeout=10)
        if health_response.status_code == 200:
            print("✅ Ollama health check: PASSED")
        else:
            print(f"❌ Ollama health check failed: {health_response.status_code}")
            print("💡 Run: ollama serve")
            return False
        
        # Test models endpoint
        models_response = requests.get(f"{ollama_url}/api/tags", timeout=10)
        if models_response.status_code == 200:
            models = models_response.json()
            model_count = len(models.get('models', []))
            print(f"✅ Ollama models available: {model_count}")
            
            if model_count > 0:
                for model in models['models']:
                    model_id = model.get('name', 'unknown')
                    print(f"   📦 Model: {model_id}")
            else:
                print("⚠️  No models loaded in Ollama")
                print("💡 Pull models: ollama pull qwen2.5:14b-instruct")
        else:
            print(f"❌ Ollama models endpoint failed: {models_response.status_code}")
            return False
        
        print("✅ Ollama: PASSED")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Ollama connection failed - service not running")
        print("💡 Run: ollama serve")
        return False
    except requests.exceptions.Timeout:
        print("❌ Ollama connection timeout")
        print("💡 Ollama may still be starting up")
        return False
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        return False

def test_docker_services():
    """Test that required Docker services are running"""
    print("\n🔍 Testing Docker services...")
    
    import subprocess
    
    try:
        # Check if Docker is running
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        print("✅ Docker: Running")
        
        # Check container status
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        running_containers = result.stdout
        
        # Check for TigerGraph
        if "tigergraph" in running_containers:
            print("✅ TigerGraph container: Running")
        else:
            print("❌ TigerGraph container: Not running")
            print("💡 Run: ./scripts/setup-tigergraph.sh")
        
        # Check for Redis
        if "redis" in running_containers:
            print("✅ Redis container: Running")
        else:
            print("❌ Redis container: Not running")
            print("💡 Run: docker-compose up -d redis")
        
        # Note: Ollama runs natively on Windows, not in Docker
        
        return True
        
    except subprocess.CalledProcessError:
        print("❌ Docker: Not running")
        print("💡 Start Docker Desktop and try again")
        return False
    except FileNotFoundError:
        print("❌ Docker: Not installed")
        print("💡 Install Docker Desktop")
        return False

def test_environment():
    """Test Python environment and dependencies"""
    print("\n🔍 Testing Python environment...")
    
    required_packages = [
        ("pyTigerGraph", "pyTigerGraph"),  # (import_name, display_name)
        ("redis", "redis"), 
        ("requests", "requests"),
        ("structlog", "structlog"),
        ("typing_extensions", "typing_extensions")
    ]
    
    missing_packages = []
    
    for import_name, display_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {display_name}: Available")
        except ImportError:
            print(f"❌ {display_name}: Missing")
            missing_packages.append(display_name)
    
    if missing_packages:
        # Map display names to install names
        install_names = []
        for display_name in missing_packages:
            if display_name == "pyTigerGraph":
                install_names.append("pyTigerGraph")
            elif display_name == "typing_extensions":
                install_names.append("typing-extensions")
            else:
                install_names.append(display_name)
        
        print(f"💡 Install missing packages:")
        print(f"   pip install {' '.join(install_names)}")
        print(f"   OR")
        print(f"   poetry install  # if using Poetry")
        return False
    
    print("✅ Python environment: PASSED")
    return True

def test_file_structure():
    """Test that required files and directories exist"""
    print("\n🔍 Testing file structure...")
    
    required_paths = [
        "schemas/schema.gsql",
        "clients/tigervector_client.py",
        "clients/redis_client.py",
        "scripts/setup-tigergraph.sh",
        "scripts/setup-tigergraph.ps1",
        "docker-compose.yaml"
    ]
    
    missing_files = []
    
    for path in required_paths:
        file_path = project_root / path
        if file_path.exists():
            print(f"✅ {path}: Found")
        else:
            print(f"❌ {path}: Missing")
            missing_files.append(path)
    
    if missing_files:
        print("💡 Some required files are missing - check project structure")
        return False
    
    print("✅ File structure: PASSED")
    return True

def main():
    """Run comprehensive system validation"""
    print("🚀 Hybrid AI Council Setup Validation")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Environment", test_environment),
        ("Docker Services", test_docker_services),
        ("TigerGraph Community Edition", test_tigergraph),
        ("Redis", test_redis),
        ("Ollama", test_ollama)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except KeyboardInterrupt:
            print(f"\n⚠️  Test interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Your Hybrid AI Council is ready!")
        print("\n📚 Next steps:")
        tigergraph_host = os.getenv("TIGERGRAPH_HOST", "http://localhost")
        tigergraph_port = os.getenv("TIGERGRAPH_PORT", "14240")
        print(f"   1. Access TigerGraph GraphStudio: {tigergraph_host}:{tigergraph_port}")
        print("   2. Explore the knowledge graph schema")
        print("   3. Start developing your AI Council application")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed - please fix issues before proceeding")
        print("\n💡 Common fixes:")
        print("   • TigerGraph: ./scripts/setup-tigergraph.sh")
        print("   • Other services: docker-compose up -d")
        print("   • Dependencies: poetry install  # or pip install -e .")
        sys.exit(1)

if __name__ == "__main__":
    main() 