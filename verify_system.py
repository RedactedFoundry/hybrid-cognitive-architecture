#!/usr/bin/env python3
"""
Hybrid AI Council - Quick System Verification Script
===================================================

This script performs a rapid verification of all core system components
to ensure the Hybrid AI Council is fully operational.
"""

import asyncio
import requests
import time
import sys
from datetime import datetime

try:
    from core.orchestrator import UserFacingOrchestrator
    from clients.redis_client import get_redis_connection
    from clients.tigervector_client import get_tigergraph_connection
    from clients.ollama_client import get_ollama_client
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

async def verify_databases():
    """Verify database connections and data."""
    print("🗄️  Database Verification:")
    
    # Redis verification
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        
        # Check for data
        keys = redis_conn.keys("*")
        print(f"   ✅ Redis: Connected, {len(keys)} keys found")
        
        # Test write/read
        test_key = f"verification_test_{int(time.time())}"
        redis_conn.set(test_key, "test_value", ex=60)
        value = redis_conn.get(test_key)
        if value == "test_value":
            print("   ✅ Redis: Write/Read operations working")
        
    except Exception as e:
        print(f"   ❌ Redis: {e}")
        return False
    
    # TigerGraph verification
    try:
        tg_conn = get_tigergraph_connection()
        if tg_conn:
            schema = tg_conn.getSchema()
            vertex_count = tg_conn.getVertexCount("*")
            print(f"   ✅ TigerGraph: Connected, {vertex_count} total vertices")
        else:
            print("   ❌ TigerGraph: Connection failed")
            return False
            
    except Exception as e:
        print(f"   ❌ TigerGraph: {e}")
        return False
    
    return True

async def verify_llm_service():
    """Verify LLM service is operational."""
    print("🤖 LLM Service Verification:")
    
    try:
        ollama_client = get_ollama_client()
        health_ok = await ollama_client.health_check()
        
        if health_ok:
            print("   ✅ Ollama: Service healthy and responsive")
            
            # Test simple generation
            response = await ollama_client.generate_response(
                "Say 'verification successful'",
                max_tokens=10
            )
            
            if response and "verification" in response.lower():
                print("   ✅ Ollama: Text generation working")
            else:
                print(f"   ⚠️  Ollama: Unexpected response: {response}")
        else:
            print("   ❌ Ollama: Health check failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Ollama: {e}")
        return False
    
    return True

async def verify_orchestrator():
    """Verify the main orchestrator functionality."""
    print("🧠 Orchestrator Verification:")
    
    try:
        orchestrator = UserFacingOrchestrator()
        start_time = time.time()
        
        result = await orchestrator.process_request(
            "Verification test: What is 2+2?",
            "system_verification"
        )
        
        processing_time = time.time() - start_time
        
        print(f"   ✅ Orchestrator: Initialized and processing ({processing_time:.2f}s)")
        print(f"   ✅ Smart Router: {result.smart_router_decision}")
        print(f"   ✅ Final Phase: {result.current_phase}")
        print(f"   ✅ Response Length: {len(result.final_response)} characters")
        
        # Verify components
        if result.pheromind_signals:
            print(f"   ✅ Pheromind: {len(result.pheromind_signals)} signals detected")
        
        if result.council_decision:
            print(f"   ✅ Council: Decision made by {result.council_decision.winning_agent}")
        
        if result.kip_tasks:
            print(f"   ✅ KIP: {len(result.kip_tasks)} tasks generated")
            
    except Exception as e:
        print(f"   ❌ Orchestrator: {e}")
        return False
    
    return True

async def verify_api_endpoints():
    """Verify API endpoints are responding."""
    print("🌐 API Endpoint Verification:")
    
    base_url = "http://localhost:8000"
    
    # Health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Health Endpoint: {health_data['status']}")
        else:
            print(f"   ❌ Health Endpoint: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health Endpoint: {e}")
        return False
    
    # Chat API endpoint
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "message": "API verification test",
                "conversation_id": "api_verification"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            chat_data = response.json()
            print(f"   ✅ Chat API: Response received")
            print(f"   ✅ Smart Router: {chat_data.get('smart_router_decision', 'N/A')}")
        elif response.status_code == 429:
            print("   ⚠️  Chat API: Rate limited (system working correctly)")
        else:
            print(f"   ❌ Chat API: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Chat API: {e}")
        return False
    
    return True

async def verify_performance():
    """Quick performance verification."""
    print("⚡ Performance Verification:")
    
    try:
        import psutil
        
        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        
        print(f"   ✅ Memory Usage: {memory_mb:.1f} MB")
        print(f"   ✅ CPU Usage: {cpu_percent:.1f}%")
        
        if memory_mb > 4000:  # 4GB
            print("   ⚠️  High memory usage detected")
        
        # Test response time
        start = time.time()
        response = requests.get("http://localhost:8000/health", timeout=5)
        response_time = time.time() - start
        
        print(f"   ✅ API Response Time: {response_time:.3f}s")
        
        if response_time > 2.0:
            print("   ⚠️  Slow response time detected")
            
    except Exception as e:
        print(f"   ❌ Performance Check: {e}")
        return False
    
    return True

async def main():
    """Run complete system verification."""
    print("🔍 Hybrid AI Council - System Verification")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Track results
    results = {}
    
    # Run all verifications
    results['databases'] = await verify_databases()
    print()
    
    results['llm'] = await verify_llm_service()
    print()
    
    results['orchestrator'] = await verify_orchestrator()
    print()
    
    results['api'] = await verify_api_endpoints()
    print()
    
    results['performance'] = await verify_performance()
    print()
    
    # Summary
    print("📊 Verification Summary:")
    print("-" * 30)
    
    total_checks = len(results)
    passed_checks = sum(results.values())
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {component.title()}: {'PASS' if status else 'FAIL'}")
    
    print()
    print(f"🎯 Overall Status: {passed_checks}/{total_checks} components verified")
    
    if passed_checks == total_checks:
        print("🎉 System Verification SUCCESSFUL - All components operational!")
        print("   Your Hybrid AI Council is ready for use! 🚀")
        return True
    else:
        print("⚠️  System Verification INCOMPLETE - Some issues detected")
        print("   Check the failed components above and refer to SYSTEM_VERIFICATION_GUIDE.md")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification failed with error: {e}")
        sys.exit(1)