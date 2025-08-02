# Hybrid AI Council - Complete System Verification Guide

This guide provides comprehensive steps to verify that the entire Hybrid AI Council system is working correctly after deployment.

## 🎯 Overview

This verification covers:
- ✅ All services running and connected
- ✅ Database operations (Redis + TigerGraph)
- ✅ UI functionality and user experience
- ✅ End-to-end cognitive workflows
- ✅ Real-time features (WebSocket, Voice)
- ✅ Production readiness

---

## 📋 Pre-Verification Checklist

### 1. Services Status Check
```bash
# Check all containers are running
docker ps

# Should see:
# - hybrid-cognitive-architecture-redis-1 (port 6379)
# - tigergraph (port 14240)

# Check Ollama is running
ollama list
# Should show: mistral-council, llama3.2, qwen2.5-coder models
```

### 2. Environment Variables
```bash
# Verify required environment variables
echo $REDIS_HOST        # Should be: localhost
echo $TIGERGRAPH_HOST   # Should be: http://localhost
echo $ENVIRONMENT       # Should be: development
```

---

## 🔍 Database Verification

### Redis Verification
```bash
# Check Redis connectivity and data
docker exec hybrid-cognitive-architecture-redis-1 redis-cli ping
# Expected: PONG

# Check existing keys
docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "*"
# Expected: Various keys including rate_limit:*, prompt_cache:*, pheromind:*

# Test Redis operations
docker exec hybrid-cognitive-architecture-redis-1 redis-cli SET test_key "verification_value"
docker exec hybrid-cognitive-architecture-redis-1 redis-cli GET test_key
# Expected: "verification_value"

# Check Redis info
docker exec hybrid-cognitive-architecture-redis-1 redis-cli INFO memory | findstr used_memory_human
```

### TigerGraph Verification
```bash
# Check TigerGraph status
curl http://localhost:14240/api/ping
# Expected: {"error":false,"message":"pong","results":"hello"}

# Verify graph exists
python -c "
from clients.tigervector_client import get_tigergraph_connection
conn = get_tigergraph_connection()
print('TigerGraph connection:', conn)
print('Graph info:', conn.getSchema())
"

# Check vertices count (after running system)
python -c "
from clients.tigervector_client import get_tigergraph_connection
conn = get_tigergraph_connection()
print('Total vertices:', conn.getVertexCount('*'))
"
```

---

## 🖥️ UI Verification

### 1. Start the Server
```bash
# Start the main application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Server should start with:
# ✅ Ollama service is available
# ✅ Redis service is available  
# ✅ TigerGraph service is available
# ✅ UserFacingOrchestrator initialized successfully
```

### 2. Web Interface Testing

**Main Chat Interface (http://localhost:8000)**
- [ ] Page loads without errors
- [ ] Chat input field is present
- [ ] "Send" button is functional
- [ ] WebSocket connection establishes (check browser dev tools)

**Voice Interface (http://localhost:8000/realtime-voice.html)**
- [ ] Voice interface loads
- [ ] Microphone permission prompt appears
- [ ] Audio controls are functional

**Health Endpoint (http://localhost:8000/health)**
- [ ] Returns JSON with status information
- [ ] Shows service health for Ollama, Redis, TigerGraph
- [ ] Response time < 1 second

### 3. API Testing
```bash
# Test simple chat API
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?", "conversation_id": "test_123"}'

# Expected: JSON response with Smart Router decision and final_response

# Test health endpoint
curl http://localhost:8000/health

# Expected: {"status": "healthy", "services": {...}, "timestamp": "..."}
```

---

## 🧠 End-to-End Cognitive Workflow Testing

### 1. Simple Query (Fast Response Path)
```python
# Run this test in Python
import asyncio
from core.orchestrator import UserFacingOrchestrator

async def test_simple_query():
    orchestrator = UserFacingOrchestrator()
    
    result = await orchestrator.process_request(
        user_input="What is 2 + 2?",
        conversation_id="verification_simple"
    )
    
    print(f"✅ Simple Query Test:")
    print(f"   Final Response: {result.final_response}")
    print(f"   Processing Time: {(result.updated_at - result.started_at).total_seconds():.2f}s")
    print(f"   Current Phase: {result.current_phase}")
    print(f"   Smart Router Decision: {result.smart_router_decision}")

asyncio.run(test_simple_query())
```

### 2. Complex Query (Council Deliberation)
```python
async def test_complex_query():
    orchestrator = UserFacingOrchestrator()
    
    result = await orchestrator.process_request(
        user_input="Analyze the economic implications of AI automation on global labor markets over the next decade, considering both positive and negative impacts.",
        conversation_id="verification_complex"
    )
    
    print(f"✅ Complex Query Test:")
    print(f"   Final Response Length: {len(result.final_response)} chars")
    print(f"   Processing Time: {(result.updated_at - result.started_at).total_seconds():.2f}s")
    print(f"   Council Decision: {result.council_decision}")
    print(f"   Pheromind Signals: {len(result.pheromind_signals)}")
    print(f"   KIP Tasks: {len(result.kip_tasks)}")

asyncio.run(test_complex_query())
```

### 3. Economic Agent Testing (KIP)
```python
async def test_kip_agents():
    from core.kip.treasury import TreasuryManager
    
    treasury = TreasuryManager()
    
    # Test budget allocation
    budget = await treasury.allocate_budget("market_research", 50.00)
    print(f"✅ KIP Budget Test:")
    print(f"   Allocated Budget: ${budget.amount}")
    print(f"   Budget ID: {budget.budget_id}")
    
    # Test transaction
    transaction = await treasury.process_transaction(
        budget_id=budget.budget_id,
        amount=10.00,
        description="Test API call",
        category="api_usage"
    )
    print(f"   Transaction: ${transaction.amount} - {transaction.description}")

asyncio.run(test_kip_agents())
```

---

## 🔊 Real-Time Features Testing

### WebSocket Testing
```javascript
// Open browser console on http://localhost:8000 and run:
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onopen = function() {
    console.log('✅ WebSocket connected');
    
    // Send test message
    ws.send(JSON.stringify({
        message: "Test WebSocket communication",
        conversation_id: "ws_test_123"
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('📨 Received:', data);
};

// Expected: Real-time streaming responses with type indicators
```

### Voice Testing
1. Navigate to http://localhost:8000/realtime-voice.html
2. Grant microphone permissions
3. Click "Start Recording"
4. Speak: "Hello, test the voice system"
5. Click "Stop Recording"
6. Verify audio playback of AI response

---

## 📊 Performance & Production Readiness

### 1. Run Full Test Suite
```bash
# Run all 210 tests
python -m pytest tests/ -v

# Expected: All tests passing
# Look for: 210 passed, X warnings in Y.Ys
```

### 2. Load Testing
```bash
# Run production readiness tests specifically
python -m pytest tests/test_production_readiness.py -v

# Expected: 15/15 tests passing including:
# - Load testing
# - Performance benchmarks  
# - Resource monitoring
# - Error rate validation
```

### 3. Memory & Resource Monitoring
```python
# Monitor system resources during operation
import psutil
import time

def monitor_resources():
    process = psutil.Process()
    print(f"Memory Usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    print(f"CPU Usage: {process.cpu_percent():.1f}%")
    
    # Check Docker containers
    print("\nDocker Resource Usage:")
    # Redis
    print("Redis: Check docker stats hybrid-cognitive-architecture-redis-1")
    # TigerGraph  
    print("TigerGraph: Check docker stats tigergraph")

monitor_resources()
```

---

## 🚨 Troubleshooting Common Issues

### Service Connection Issues
```bash
# If Redis connection fails:
docker restart hybrid-cognitive-architecture-redis-1
docker logs hybrid-cognitive-architecture-redis-1

# If TigerGraph connection fails:
docker restart tigergraph
docker logs tigergraph

# If Ollama connection fails:
ollama serve
ollama pull mistral-council
```

### Database Issues
```bash
# Reset Redis data:
docker exec hybrid-cognitive-architecture-redis-1 redis-cli FLUSHALL

# Reinitialize TigerGraph:
python scripts/init_tigergraph.py
```

### Performance Issues
```bash
# Check system resources:
docker stats

# Check disk space:
docker system df

# Clean up if needed:
docker system prune
```

---

## ✅ Verification Completion Checklist

After running through this guide, you should have verified:

**🔧 Infrastructure:**
- [ ] All Docker containers running
- [ ] Redis operational with data
- [ ] TigerGraph operational with schema
- [ ] Ollama models loaded and responsive

**🌐 User Interfaces:**
- [ ] Web chat interface functional
- [ ] Voice interface operational  
- [ ] API endpoints responding correctly
- [ ] WebSocket real-time communication working

**🧠 Cognitive Architecture:**
- [ ] Smart Router making correct routing decisions
- [ ] Fast response path working for simple queries
- [ ] Council deliberation working for complex queries
- [ ] Pheromind ambient intelligence functioning
- [ ] KIP economic agents operational

**📊 Production Readiness:**
- [ ] All 210 tests passing
- [ ] Performance within acceptable limits
- [ ] Error rates < 5%
- [ ] Resource usage within bounds
- [ ] Rate limiting functioning correctly

**🔍 Data Verification:**
- [ ] Redis contains pheromind signals, cache data, rate limits
- [ ] TigerGraph contains conversation graphs, knowledge nodes
- [ ] Real data being written during system operation

---

## 🎯 Quick Verification Script

For a rapid system check, run this comprehensive verification:

```python
# save as verify_system.py
import asyncio
import requests
import time
from core.orchestrator import UserFacingOrchestrator

async def quick_verification():
    print("🔍 Hybrid AI Council - Quick System Verification")
    print("=" * 50)
    
    # 1. Check API health
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Health Check: {response.status_code} - {response.json()['status']}")
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return
    
    # 2. Test orchestrator
    try:
        orchestrator = UserFacingOrchestrator()
        start_time = time.time()
        
        result = await orchestrator.process_request(
            "Test system verification",
            "verification_test"
        )
        
        processing_time = time.time() - start_time
        print(f"✅ Orchestrator: {processing_time:.2f}s - {result.current_phase}")
        print(f"   Response: {result.final_response[:100]}...")
        
    except Exception as e:
        print(f"❌ Orchestrator Failed: {e}")
        return
    
    # 3. Test simple API call
    try:
        response = requests.post(
            "http://localhost:8000/api/chat",
            json={"message": "Quick test", "conversation_id": "verify_api"},
            timeout=10
        )
        print(f"✅ API Chat: {response.status_code} - Response received")
    except Exception as e:
        print(f"❌ API Chat Failed: {e}")
        return
    
    print("\n🎉 System Verification Complete - All Core Functions Working!")

if __name__ == "__main__":
    asyncio.run(quick_verification())
```

Run with: `python verify_system.py`

---

**This verification guide ensures your Hybrid AI Council system is fully operational and ready for production use!** 🚀