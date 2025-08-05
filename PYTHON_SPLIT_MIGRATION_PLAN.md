# 🔄 Python 3.13/3.11 Split Migration Plan

## 📋 Executive Summary

Split the Hybrid AI Council into two complementary projects:
- **Main Project** (Python 3.13): Core AI orchestration, web services, council logic
- **Legacy Voice Service** (Python 3.11): Voice processing, TTS/STT, audio handling

## 🎯 Project Architecture

```
hybrid-cognitive-architecture/
├── 📁 core/                    ← Python 3.13 (MAIN PROJECT)
├── 📁 clients/                 ← Python 3.13 
├── 📁 endpoints/               ← Python 3.13
├── 📁 websocket_handlers/      ← Python 3.13
├── 📁 middleware/              ← Python 3.13
├── 📁 utils/                   ← Python 3.13
├── 📁 tests/                   ← Python 3.13
├── 📁 scripts/                 ← Python 3.13
├── 📁 static/                  ← Python 3.13
├── 📁 tools/                   ← Python 3.13
├── 📁 schemas/                 ← Python 3.13
├── 📁 config/                  ← Python 3.13
└── 📁 legacy-voice-service/    ← Python 3.11 (NEW MICROSERVICE)
    ├── pyproject.toml          ← python = "^3.11"
    ├── voice_server.py         ← FastAPI service
    ├── voice_engines.py        ← Coqui TTS, Parakeet, etc.
    ├── audio_processing.py     ← All audio utilities
    └── tests/                  ← Voice-specific tests
```

## 📊 Component Migration Matrix

### 🚀 **STAYS in Python 3.13 (Main Project)**

| Component | Reason | Benefits from 3.13 |
|-----------|---------|-------------------|
| **Core AI Orchestration** | ✅ Modern AI libs support 3.13 | Free-threading, JIT |
| **Council Logic** | ✅ LangGraph, LangChain work | Async performance |
| **WebSocket Handlers** | ✅ FastAPI/Uvicorn support 3.13 | Enhanced async |
| **Database Clients** | ✅ Redis, TigerGraph compatible | Memory optimizations |
| **REST API Endpoints** | ✅ Core business logic | Better error handling |
| **KIP (Economic System)** | ✅ Pure Python/pandas | Computational speedup |
| **Pheromind** | ✅ Memory/cache system | GIL-free performance |
| **Smart Router** | ✅ Request routing logic | Faster dispatching |

### 📼 **MOVES to Python 3.11 (Legacy Voice Service)**

| Component | Reason | Current Issues |
|-----------|---------|----------------|
| **Coqui TTS** | ❌ No Python 3.13 support | `TTS>=0.22.0` requires <3.12 |
| **Parakeet (NeMo)** | ❌ NeMo toolkit compatibility | Heavy NVIDIA dependencies |
| **Audio Processing** | ❌ Some audio libs lag behind | Safer in 3.11 environment |
| **Voice Foundation** | ❌ Depends on above | Currently returning None |
| **STT/TTS Engines** | ❌ Ecosystem stability | Better library support |

## 🔗 Communication Architecture

### **HTTP API Communication**
```python
# Main Project (3.13) calls Legacy Voice Service (3.11)
POST http://localhost:8001/transcribe
POST http://localhost:8001/synthesize
GET  http://localhost:8001/health
```

### **Service Ports**
- **Main Project**: `:8000` (FastAPI + WebSockets)
- **Voice Service**: `:8001` (FastAPI audio processing)

## 📋 Implementation Checklist

### Phase 1: Environment Setup ✅
- [ ] **1.1** Create `legacy-voice-service/` directory
- [ ] **1.2** Set up Python 3.11 virtual environment for voice service
- [ ] **1.3** Create separate `pyproject.toml` for voice service
- [ ] **1.4** Update main project to Python 3.13 in `pyproject.toml`

### Phase 2: Voice Service Creation 🔧
- [ ] **2.1** Create `legacy-voice-service/voice_server.py` (FastAPI app)
- [ ] **2.2** Move voice-related dependencies to voice service
- [ ] **2.3** Install Coqui TTS in Python 3.11 environment
- [ ] **2.4** Create voice processing endpoints:
  - [ ] `/transcribe` - Audio to text
  - [ ] `/synthesize` - Text to audio  
  - [ ] `/health` - Service health check
- [ ] **2.5** Implement multi-voice support for council members

### Phase 3: Main Project Updates 🚀
- [ ] **3.1** Update main `pyproject.toml` to `python = "^3.13"`
- [ ] **3.2** Remove voice-related dependencies from main project:
  - [ ] Remove: `torch`, `torchaudio`, `silero-vad`
  - [ ] Remove: `nemo-toolkit`, `transformers` (unless needed for other AI)
  - [ ] Remove: `lhotse`, `jiwer`
- [ ] **3.3** Create HTTP client for voice service communication
- [ ] **3.4** Update `voice_foundation/production_voice_engines.py`
- [ ] **3.5** Test all non-voice functionality

### Phase 4: Integration Testing 🧪
- [ ] **4.1** Test voice service independently
- [ ] **4.2** Test main project without voice dependencies
- [ ] **4.3** Test end-to-end voice workflow
- [ ] **4.4** Verify WebSocket voice handlers work
- [ ] **4.5** Performance testing both services

### Phase 5: Deployment Configuration 🚀
- [ ] **5.1** Update Docker configuration for dual services
- [ ] **5.2** Update `docker-compose.yaml` 
- [ ] **5.3** Configure service discovery/health checks
- [ ] **5.4** Update deployment scripts
- [ ] **5.5** Document service communication

## 📁 New File Structure

### **Legacy Voice Service** (`legacy-voice-service/`)

```
legacy-voice-service/
├── pyproject.toml              # Python 3.11 dependencies
├── voice_server.py             # FastAPI app
├── voice_engines.py            # Coqui TTS, Parakeet, etc.
├── audio_processing.py         # Audio utilities
├── models.py                   # Pydantic models
├── config.py                   # Voice service config
├── tests/
│   ├── test_voice_endpoints.py
│   └── test_audio_processing.py
└── README.md                   # Service documentation
```

### **Updated Main Project** (Python 3.13)

```python
# New voice client in main project
clients/voice_client.py         # HTTP client for voice service
```

## 🔧 Key Dependencies Split

### **Main Project (3.13) - Core Dependencies**
```toml
[tool.poetry.dependencies]
python = "^3.13"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
langgraph = "^0.2.0"
langchain-core = "^0.3.0"
redis = "^5.0.0"
pytigergraph = "^1.9.0"
httpx = "^0.25.0"  # For calling voice service
# ... other compatible deps
```

### **Voice Service (3.11) - Audio Dependencies**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
TTS = "^0.22.0"                 # Coqui TTS
torch = "^2.7.1"
torchaudio = "^2.7.1"
nemo-toolkit = "^2.4.0"
transformers = "^4.54.1"
# ... other audio/ML deps
```

## 🎯 Benefits of This Approach

### **Python 3.13 Benefits (Main Project)**
- ✅ **Free-threaded mode**: Multi-agent parallelism
- ✅ **JIT compilation**: Faster AI inference  
- ✅ **Enhanced async**: Better WebSocket performance
- ✅ **Modern features**: Latest language improvements

### **Python 3.11 Benefits (Voice Service)**
- ✅ **Full TTS compatibility**: Coqui TTS works perfectly
- ✅ **Stable audio ecosystem**: Proven voice processing stack
- ✅ **Isolated concerns**: Voice issues don't break core AI
- ✅ **Easy maintenance**: Separate deployments and scaling

## ⚠️ Potential Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| **Service latency** | Keep voice service local, optimize HTTP calls |
| **Dependency management** | Clear separation, automated testing |
| **Deployment complexity** | Docker Compose orchestration |
| **Debugging across services** | Structured logging with correlation IDs |

## 🚦 Success Criteria

- [ ] **Voice chat fully functional** with Coqui TTS
- [ ] **Main project leverages Python 3.13** performance features  
- [ ] **All tests passing** in both projects
- [ ] **Sub-200ms voice response time** maintained
- [ ] **Easy deployment** with single command

---

## 🤝 Next Steps

1. **Review this plan** and confirm the split makes sense
2. **Start with Phase 1**: Set up the environments
3. **Implement incrementally**: One phase at a time
4. **Test thoroughly**: Each phase before proceeding

**Estimated Timeline**: 2-3 days for full migration

---

*This plan balances cutting-edge performance (Python 3.13) with practical compatibility (Python 3.11) while maintaining the project's innovative architecture.*