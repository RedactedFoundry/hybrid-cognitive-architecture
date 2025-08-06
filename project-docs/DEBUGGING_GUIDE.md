# 🔧 Debugging Guide - Hybrid AI Council

> **Project-Specific Troubleshooting for Common Issues**

## 🚨 **Emergency Commands (When Everything Breaks)**

```bash
# Nuclear reset (last resort)
make clean-all && make dev-setup

# Emergency stop all spending
python -c "
import asyncio
from core.kip import create_treasury
asyncio.run(create_treasury().__aenter__().emergency_freeze_all('Manual emergency stop'))
"

# Quick health check
make health
```

---

## 🗄️ **Database Issues**

### **Redis Won't Connect**

**Symptoms:**
- `ConnectionError: Error 111 connecting to localhost:6379`
- Tests fail with Redis connection errors

**Diagnosis:**
```bash
# Check if Redis is running
docker ps | grep redis
redis-cli ping  # Should return "PONG"
```

**Solutions:**
```bash
# Start Redis if stopped
docker-compose up -d redis

# If port conflict (common on Windows)
docker-compose down
docker-compose up -d redis

# Check logs for detailed error
docker-compose logs redis
```

**Prevention:** Add Redis health check to startup scripts

---

### **TigerGraph 404 Errors**

**Symptoms:**
- `HTTP 404` on TigerGraph queries
- `Schema not found` errors
- Tests fail with TigerGraph connection issues

**Diagnosis:**
```bash
# Check if TigerGraph is running
curl http://localhost:14240/api/ping

# Check if schema is initialized
curl -s "http://localhost:14240/gsqlserver/gsql/schema?graph=HybridAICouncil"
```

**Solutions:**
```bash
# Start TigerGraph (manual setup required)
./scripts/setup-tigergraph.sh

# Initialize schema if missing
python scripts/init_tigergraph.py

# If schema corruption
make reset-db  # Nuclear option - rebuilds everything
```

**Common Causes:**
- Schema not initialized after fresh install
- TigerGraph service stopped unexpectedly
- Port conflicts with other services

---

### **Agent Genome Data Corruption**

**Symptoms:**
- Agents not found in TigerGraph
- Inconsistent agent behavior
- Missing transaction history

**Diagnosis:**
```bash
# Check agent data integrity
python quick_db_check.py

# Check specific agent
python -c "
import asyncio
from core.kip import create_treasury
async def check_agent():
    async with create_treasury() as treasury:
        agent = await treasury.agent_manager.load_agent('your_agent_id')
        print(f'Agent found: {agent is not None}')
asyncio.run(check_agent())
"
```

**Solutions:**
```bash
# Restore from backup (if available)
ls backups/
# Manually restore agent data

# Re-initialize specific agent
python -c "
# Custom agent restoration script here
"
```

---

## 🤖 **LLM & AI Issues**

### **Ollama Not Responding**

**Symptoms:**
- `ConnectionError` when calling LLM
- Timeouts on model requests
- Models not loading

**Diagnosis:**
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# Check model availability
docker exec ollama ollama list
```

**Solutions:**
```bash
# Start Ollama
docker-compose up -d ollama

# Pull required models
make models

# If model loading issues (memory)
docker exec ollama ollama ps  # Check loaded models
docker stats ollama           # Check memory usage
```

**Common Causes:**
- Insufficient RAM for models (need 16GB+ for Qwen3-14B)
- Models not pulled after fresh install
- Port conflicts

---

### **Model Responses Are Gibberish**

**Symptoms:**
- Incoherent responses
- JSON parsing errors
- Unexpected model behavior

**Diagnosis:**
```bash
# Test model directly
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:14b", "messages": [{"role": "user", "content": "Hello"}]}'
```

**Solutions:**
- Check model loading: `docker exec ollama ollama ps`
- Re-pull model: `docker exec ollama ollama pull qwen2.5:14b`
- Check system resources: `docker stats`

---

## 💰 **Financial & KIP Issues**

### **Agents Can't Spend Money**

**Symptoms:**
- `InsufficientFundsError` despite having budget
- `EmergencyFreezeError` when not in emergency
- Transactions failing silently

**Diagnosis:**
```bash
# Check emergency freeze status
python -c "
import asyncio
from core.kip import create_treasury
async def check_freeze():
    async with create_treasury() as treasury:
        print(f'Emergency freeze: {treasury.treasury_core.is_emergency_freeze_active()}')
asyncio.run(check_freeze())
"

# Check agent budget
python quick_db_check.py | grep -A 5 "Agent Budgets"
```

**Solutions:**
```bash
# Unfreeze if accidentally frozen
python -c "
import asyncio
from core.kip import create_treasury
asyncio.run(create_treasury().__aenter__().emergency_unfreeze_all('Manual unfreeze'))
"

# Reset daily limits (if daily limit exceeded)
# Check current date vs last_reset_date in budget data
```

---

### **Transaction History Missing**

**Symptoms:**
- No transaction records in TigerGraph
- Inconsistent financial reporting
- Audit trail gaps

**Diagnosis:**
```bash
# Check transaction data
python -c "
import asyncio
from core.kip import create_treasury
async def check_transactions():
    async with create_treasury() as treasury:
        analytics = await treasury.get_economic_analytics()
        print(f'Total transactions: {analytics.total_transactions}')
        print(f'Total spent: {analytics.total_spent}')
asyncio.run(check_transactions())
"
```

**Solutions:**
- Check TigerGraph schema integrity
- Verify transaction processor is working
- Review Redis-to-TigerGraph sync processes

---

## 🌐 **API & WebSocket Issues**

### **API Endpoints Not Responding**

**Symptoms:**
- `Connection refused` on localhost:8000
- 500 errors on API calls
- WebSocket connection failures

**Diagnosis:**
```bash
# Check FastAPI service
curl http://localhost:8000/health

# Check process
ps aux | grep uvicorn
```

**Solutions:**
```bash
# Start API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Check for port conflicts
lsof -i :8000
```

---

### **Voice Processing Failures**

**Symptoms:**
- Voice uploads fail
- TTS generation errors
- Audio file corruption

**Diagnosis:**
```bash
# Check voice dependencies
python -c "import kyutai_tts; print('TTS available')"

# Test voice pipeline
cd voice_foundation
python test_production_voice.py
```

**Solutions:**
- Verify audio dependencies installed
- Check file permissions in voice_foundation/outputs/
- Test with simpler audio files first

---

## 🧪 **Test Failures**

### **Tests Pass Locally But Fail in CI**

**Common Causes:**
- Docker service startup timing issues
- Environment variable differences
- Test database conflicts

**Solutions:**
```bash
# Add delays for service startup
sleep 10  # In test setup

# Check environment variables
env | grep -E "(REDIS|TIGERGRAPH|OLLAMA)"

# Run tests with verbose logging
pytest -v -s --log-cli-level=DEBUG
```

---

### **Flaky Tests (Pass Sometimes)**

**Common Patterns:**
- Redis connection timing
- TigerGraph query consistency
- LLM response variations

**Solutions:**
- Add retries with exponential backoff
- Use fixtures for consistent test data
- Mock external dependencies

---

## 📊 **Performance Issues**

### **System Running Slowly**

**Diagnosis:**
```bash
# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

**Common Solutions:**
- Restart resource-heavy containers
- Clear Redis cache: `redis-cli FLUSHALL`
- Check for memory leaks in long-running processes

---

### **High Memory Usage**

**Symptoms:**
- System freezing
- Out of memory errors
- Slow model responses

**Solutions:**
```bash
# Check model memory usage
docker exec ollama ollama ps

# Unload unused models
docker exec ollama ollama stop qwen2.5:14b

# Monitor memory over time
watch -n 2 "docker stats --no-stream"
```

---

## 🔍 **Monitoring Commands**

### **Quick System Health Check**
```bash
make health  # Full health check
make status  # System status overview
```

### **Live Monitoring**
```bash
# Service logs
make logs

# Financial monitoring
watch -n 5 "python quick_db_check.py | head -20"

# Resource monitoring  
watch -n 2 "docker stats --no-stream"
```

### **Backup & Recovery**
```bash
# Create backup
make backup

# List backups
ls -la backups/

# Manual data export
python quick_db_check.py > manual_backup_$(date +%Y%m%d_%H%M%S).txt
```

---

## 🚨 **When All Else Fails**

### **Nuclear Reset Process**
```bash
# 1. Save important data
make backup

# 2. Complete system reset
make clean-all

# 3. Fresh setup
make dev-setup

# 4. Verify everything works
make verify
```

### **Get Help**
1. Check this guide first
2. Review relevant error logs
3. Check GitHub issues for similar problems
4. Create detailed issue with error logs and reproduction steps

---

## 📋 **Common Error Codes**

| Error | Meaning | Quick Fix |
|-------|---------|-----------|
| `REDIS_001` | Connection failed | `docker-compose up -d redis` |
| `TG_002` | Schema not found | `python scripts/init_tigergraph.py` |
| `OLLAMA_003` | Model not loaded | `docker exec ollama ollama pull [model]` |
| `KIP_004` | Emergency freeze active | Run unfreeze command |
| `API_005` | Port conflict | Check `lsof -i :[port]` |

**Remember:** When in doubt, check the logs first: `make logs`