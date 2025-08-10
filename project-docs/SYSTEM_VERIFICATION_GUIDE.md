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

## 📄 Environment Configuration Files

**Quick Answer to "Do I need both .env and ENVIRONMENT_VARIABLES.md?"**

- **`.env`** - Your actual local environment variables (used by the system)
- **`ENVIRONMENT_VARIABLES.md`** - Documentation reference (explains all possible variables)

You only **need** the `.env` file for the system to work. The `.md` file is just documentation.

```bash
# Check if you have a .env file
if [ -f .env ]; then
    echo "✅ .env file exists (GOOD - system will use these values)"
    echo "📄 Contents:"
    grep -v "^#" .env | grep -v "^$" | head -5
else
    echo "ℹ️  No .env file (OK - system will use defaults from config.py)"
    echo "💡 You can create one with: touch .env"
fi
```

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
# Should show: huihui-oss20b (generator), mistral-council (verifier)

# Quick status summary
echo "🔍 Service Status Summary:"
redis_running=$(docker ps --filter "name=redis" --format "{{.Names}}" | grep redis)
tigergraph_running=$(docker ps --filter "name=tigergraph" --format "{{.Names}}" | grep tigergraph)

if [ -n "$redis_running" ]; then
    echo "   ✅ Redis: Running"
else
    echo "   ❌ Redis: Not running"
fi

if [ -n "$tigergraph_running" ]; then
    echo "   ✅ TigerGraph: Running"
else
    echo "   ❌ TigerGraph: Not running"
fi

if ollama list >/dev/null 2>&1; then
    models_count=$(ollama list | wc -l)
    if [ $models_count -gt 1 ]; then
        echo "   ✅ Ollama: Running with models"
    else
        echo "   ⚠️  Ollama: Running but no models"
    fi
else
    echo "   ❌ Ollama: Not running or not accessible"
fi
```

### 2. Environment Variables
```bash
# Verify required environment variables
echo "REDIS_HOST: ${REDIS_HOST:-localhost (default)}"
echo "TIGERGRAPH_HOST: ${TIGERGRAPH_HOST:-http://localhost (default)}"
echo "ENVIRONMENT: ${ENVIRONMENT:-development (default)}"

# Alternative: Check if .env file exists
if [ -f .env ]; then
    echo "✅ .env file found"
    echo "📄 Contents:"
    grep -v "^#" .env | head -10
else
    echo "ℹ️  No .env file - using defaults from config.py"
fi
```

---

## 🔍 Database Verification

### Redis Verification

#### Step 1: Basic Connectivity
```bash
# Check Redis connectivity and data
docker exec hybrid-cognitive-architecture-redis-1 redis-cli ping
# Expected: PONG

# Check Redis info and memory usage
docker exec hybrid-cognitive-architecture-redis-1 redis-cli INFO memory | grep "used_memory_human"
# Expected: used_memory_human:X.XXM
```

#### Step 2: Check Existing Data
```bash
# Count total keys
docker exec hybrid-cognitive-architecture-redis-1 redis-cli DBSIZE
# Expected: (integer) X (where X > 0 after system use)

# Check existing keys by pattern
echo "Total keys: $(docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "*" | wc -l)"
# Expected: Various keys including rate_limit:*, prompt_cache:*, pheromind:*

# View key patterns
echo "Key patterns:"
docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "*" | cut -d: -f1 | sort | uniq -c | sort -nr
```

#### Step 3: Inspect Actual Data
```bash
# View rate limiting data (if any requests made)
echo "Rate limit keys:"
docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "rate_limit:*"

# View actual rate limit values
docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "rate_limit:*" | while read key; do
    if [ -n "$key" ]; then
        value=$(docker exec hybrid-cognitive-architecture-redis-1 redis-cli GET "$key")
        echo "$key = $value"
    fi
done

# View pheromind signals (after system use)
echo "Pheromind keys:"
docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "pheromind:*"

# View prompt cache (after system use)  
echo "Prompt cache keys:"
docker exec hybrid-cognitive-architecture-redis-1 redis-cli KEYS "prompt_cache:*"

# Test Redis operations
docker exec hybrid-cognitive-architecture-redis-1 redis-cli SET test_key "verification_value" EX 60
docker exec hybrid-cognitive-architecture-redis-1 redis-cli GET test_key
# Expected: "verification_value"
```

#### Step 4: Monitor Redis in Real-Time (Optional)
```bash
# Monitor Redis commands in real-time (run in separate terminal)
docker exec hybrid-cognitive-architecture-redis-1 redis-cli MONITOR
# Then use your system and watch Redis activity live
```

### TigerGraph Verification

#### Step 1: Initialize TigerGraph (First Time Setup)
```bash
# IMPORTANT: Initialize the graph schema first (required for first use)
python scripts/init_tigergraph.py

# Expected output:
# ✅ TigerGraph connection successful
# ✅ Graph 'HybridAICouncil' created
# ✅ Schema installed successfully
# ✅ Data source created
```

#### Step 2: Verify TigerGraph Connection
```bash
# Check TigerGraph status
curl http://localhost:14240/api/ping
# Expected: {"error":false,"message":"pong","results":"hello"}

# Check TigerGraph login and credentials
curl -X POST http://localhost:14240/gsqlserver/gsql/login -d "tigergraph"
# Expected: {"error":false,"message":"Login successfully",...}
```

#### Step 3: Verify Graph Schema and Data
```python
# Run this Python script to check schema and data
python -c "
from clients.tigervector_client import get_tigergraph_connection
try:
    conn = get_tigergraph_connection()
    print('✅ TigerGraph Connection: SUCCESS')
    
    # Check schema
    schema = conn.getSchema()
    print(f'📊 Graph Schema: {len(schema.vertexTypes)} vertex types, {len(schema.edgeTypes)} edge types')
    
    # Check vertex counts
    vertices = conn.getVertexTypes()
    for vertex_type in vertices:
        count = conn.getVertexCount(vertex_type)
        print(f'   {vertex_type}: {count} vertices')
    
    # Check edge counts  
    edges = conn.getEdgeTypes()
    for edge_type in edges:
        count = conn.getEdgeCount(edge_type)
        print(f'   {edge_type}: {count} edges')
        
except Exception as e:
    print(f'❌ TigerGraph Error: {e}')
    print('💡 Try running: python scripts/init_tigergraph.py')
"
```

#### Step 4: View Actual Data in TigerGraph
```python
# See real conversation data stored in TigerGraph
python -c "
from clients.tigervector_client import get_tigergraph_connection
conn = get_tigergraph_connection()

# Get recent conversations
conversations = conn.getVertices('Conversation', limit=5)
print('📝 Recent Conversations:')
for conv in conversations:
    print(f'   ID: {conv[0]}, Data: {conv[1]}')

# Get knowledge nodes
knowledge = conn.getVertices('KnowledgeNode', limit=5)
print('🧠 Recent Knowledge Nodes:')
for node in knowledge:
    print(f'   ID: {node[0]}, Content: {node[1].get(\"content\", \"N/A\")[:100]}...')
"
```

#### Credentials Configuration (Optional)
```bash
# Default TigerGraph credentials are tigergraph/tigergraph
# To change them (optional), update your .env file:
echo 'TIGERGRAPH_USERNAME=your_username' >> .env
echo 'TIGERGRAPH_PASSWORD=your_password' >> .env

# Then restart TigerGraph:
docker restart tigergraph
# Wait 30 seconds for startup
sleep 30
python scripts/init_tigergraph.py  # Re-initialize with new credentials
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
ollama create huihui-oss20b -f ollama/Modelfile.huihui-oss20b
ollama pull hf.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M
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

### 🔬 Live Data Inspection

**To actually see data being written, follow these steps:**

1. **Start the system**: `uvicorn main:app --host 0.0.0.0 --port 8000`
2. **Open two terminal windows** for monitoring:
   
   **Terminal 1 - Monitor Redis:**
   ```bash
   docker exec hybrid-cognitive-architecture-redis-1 redis-cli MONITOR
   ```
   
   **Terminal 2 - Monitor TigerGraph (optional):**
   ```bash
   # Run this periodically to see vertex counts increase
   python -c "
   from clients.tigervector_client import get_tigergraph_connection
   conn = get_tigergraph_connection()
   print(f'Conversations: {conn.getVertexCount(\"Conversation\")}')
   print(f'Knowledge Nodes: {conn.getVertexCount(\"KnowledgeNode\")}')
   "
   ```

3. **Use the system** - Make some requests:
   ```bash
   # Simple API request
   curl -X POST "http://localhost:8000/api/chat" -H "Content-Type: application/json" -d '{"message": "Hello, test data storage", "conversation_id": "data_test_123"}'
   
   # Or use the web interface at http://localhost:8000
   ```

4. **Verify data was written:**
   ```bash
   # Check Redis keys increased
   docker exec hybrid-cognitive-architecture-redis-1 redis-cli DBSIZE
   
   # Check TigerGraph vertices increased  
   python -c "
   from clients.tigervector_client import get_tigergraph_connection
   conn = get_tigergraph_connection()
   conversations = conn.getVertices('Conversation', limit=3)
   print('Latest conversations:', conversations)
   "
   ```

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