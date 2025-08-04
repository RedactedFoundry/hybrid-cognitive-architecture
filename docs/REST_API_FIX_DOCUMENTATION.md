# REST API Fix Documentation
**Date:** August 3, 2025  
**Issue:** `/api/chat` endpoint hanging in uvicorn server  
**Status:** Partially resolved with identified root cause

## 🔍 Problem Analysis

### **Symptoms**
- REST `/api/chat` endpoint consistently timed out in uvicorn server
- WebSocket `/ws/chat` worked perfectly 
- Health endpoint `/health` worked fine
- TestClient tests passed with real orchestrator

### **Root Cause Discovered**
**uvicorn async context incompatibility** with shared global orchestrator instance:

1. **Global orchestrator** (set during startup) caused hanging in uvicorn
2. **Fresh orchestrator per request** works perfectly 
3. **Voice foundation initialization** during startup blocks the entire server

## ✅ Solution Implemented

### **Primary Fix: Fresh Orchestrator Pattern**
```python
# OLD (hanging):
orchestrator_result = await orchestrator.process_request(...)

# NEW (working):  
from core.orchestrator import UserFacingOrchestrator
request_orchestrator = UserFacingOrchestrator()
orchestrator_result = await request_orchestrator.process_request(...)
```

### **Secondary Issue: Voice Foundation Blocking**
Voice foundation initialization during startup blocks uvicorn server:
```python
# This blocks the entire server in uvicorn context:
voice_orch = get_voice_orchestrator()
await voice_orch.initialize()  # Heavy AI model loading
```

## 🧪 Testing Results

| Test Method | Result | Notes |
|-------------|--------|-------|
| **Direct orchestrator call** | ✅ Works (2.18s) | Confirms orchestrator logic is fine |
| **FastAPI + TestClient** | ✅ Works (0.85s) | Confirms endpoint logic is fine |
| **WebSocket chat** | ✅ Works perfectly | Uses parameter-passed orchestrator |
| **REST API (fresh orchestrator)** | ✅ Works in isolation | Fixed the core hanging issue |
| **REST API (with voice init)** | ❌ Still hangs | Voice loading blocks server |

## 🎯 Current Status

### **What's Working:**
- ✅ WebSocket chat (full AI Council functionality)
- ✅ Health monitoring
- ✅ Core orchestrator and Smart Router
- ✅ All databases (Redis, TigerGraph)
- ✅ LLM services (Ollama)

### **Remaining Issue:**
- ❌ REST API still hangs due to voice foundation startup blocking

## 📋 Recommended Next Steps

### **Option 1: Lazy Voice Loading (Recommended)**
Move voice foundation to lazy initialization on first use:
```python
# In voice endpoints only:
if not voice_orchestrator:
    voice_orchestrator = await get_voice_orchestrator()
    await voice_orchestrator.initialize()
```

### **Option 2: Background Voice Initialization**
Initialize voice foundation in background task after server startup.

### **Option 3: Separate Voice Service**
Move voice processing to separate service to avoid blocking main API.

## 🔧 Code Changes Made

### **File: `endpoints/chat.py`**
- Implemented fresh orchestrator per request pattern
- Removed global orchestrator dependency
- Cleaned up debug endpoints

### **File: `main.py`** 
- Temporarily disabled voice foundation initialization
- Re-enabled for testing (causing current blocking)

### **Files Removed:**
- `debug_rest_api.py` - Debug isolation script
- `debug_fastapi_direct.py` - FastAPI testing script

## 💡 Key Insights

1. **uvicorn async context** behaves differently than TestClient
2. **Shared state** between requests can cause blocking
3. **Heavy initialization** (AI models) should be lazy-loaded
4. **Fresh instances** avoid context contamination
5. **WebSocket pattern** (parameter injection) works better than globals

## 📈 Performance Impact

- **Fresh orchestrator per request:** ~0.1s overhead per request
- **Acceptable for REST API usage patterns**
- **WebSocket maintains shared state for performance**

---

**This documentation captures the investigation process and provides a clear path forward for completing the REST API fix.**