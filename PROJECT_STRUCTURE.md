# Hybrid AI Council - Project Structure

## 🏗️ **Architecture Overview**

This is a **hybrid cloud/local AI system** with a 3-layer cognitive architecture:
- **Pheromind**: Subconscious pattern recognition (Redis pheromones)
- **Council**: Conscious reasoning (LangGraph orchestrator)  
- **KIP**: Knowledge integration & persistence (TigerGraph)

## 📁 **Main Project Structure (Python 3.13)**

```
hybrid-cognitive-architecture/           # Main project (Python 3.13)
├── .cursorrules                        # Cursor AI instructions
├── .env                                # Environment variables
├── .gitignore
├── docker-compose.yaml                 # Docker services (Redis, TigerGraph)
├── render.yaml                         # Cloud deployment config
├── pyproject.toml                      # Main project dependencies (Python 3.13)
├── README.md                           # Project overview
├── start_all.py                        # 🚀 ONE COMMAND startup script
├── main.py                             # FastAPI main application
├── config.py                           # Centralized configuration
├── config/                             # Configuration modules
│   ├── __init__.py
│   └── models.py                       # Model definitions & aliases
├── core/                               # 🧠 Core AI components
│   ├── orchestrator/                   # LangGraph orchestrator
│   │   ├── __init__.py
│   │   ├── orchestrator.py             # Main orchestrator
│   │   ├── state_machine.py            # State management
│   │   ├── streaming.py                # Real-time streaming
│   │   ├── synthesis.py                # Response synthesis
│   │   ├── models.py                   # State models
│   │   └── nodes/                      # Processing nodes
│   │       ├── __init__.py
│   │       ├── base.py                 # Base node classes
│   │       ├── council_nodes.py        # Council reasoning nodes
│   │       ├── kip_nodes.py            # Knowledge integration nodes
│   │       ├── pheromind_nodes.py      # Pattern recognition nodes
│   │       ├── smart_router_nodes.py   # Smart routing nodes
│   │       └── support_nodes.py        # Utility nodes
│   ├── pheromind.py                    # Subconscious pattern recognition
│   ├── kip/                            # Knowledge Integration & Persistence
│   │   ├── __init__.py
│   │   ├── agents.py                   # Autonomous agents
│   │   ├── budget_manager.py           # Economic budget management
│   │   ├── economic_analyzer.py        # Economic analysis
│   │   ├── exceptions.py               # KIP-specific exceptions
│   │   ├── models.py                   # Economic models
│   │   ├── tools.py                    # Economic tools
│   │   ├── transaction_processor.py    # Transaction processing
│   │   ├── treasury_core.py            # Treasury core logic
│   │   └── treasury.py                 # Treasury management
│   ├── logging_config.py               # Structured logging setup
│   ├── cache_integration.py            # Cache management
│   ├── error_boundaries.py             # Error handling
│   └── prompt_cache.py                 # Prompt caching
├── clients/                            # External service clients
│   ├── __init__.py
│   ├── ollama_client.py                # Ollama LLM client
│   ├── redis_client.py                 # Redis cache client
│   └── tigervector_client.py           # TigerGraph client
├── voice_foundation/                   # 🎤 Voice system integration
│   ├── __init__.py                     # Voice foundation package
│   ├── voice_client.py                 # Voice service HTTP client
│   ├── production_voice_engines.py     # Production voice engines
│   ├── orchestrator_integration.py     # Voice orchestrator integration
│   └── simple_voice_pipeline.py        # Simple voice pipeline
├── endpoints/                          # API endpoints
│   ├── __init__.py
│   ├── chat.py                         # Chat endpoints
│   ├── health.py                       # Health check endpoints
│   └── voice.py                        # Voice endpoints
├── middleware/                         # Request middleware
│   ├── __init__.py
│   ├── rate_limiting.py                # Rate limiting
│   ├── request_validation.py           # Request validation
│   └── security_headers.py             # Security headers
├── websocket_handlers/                 # WebSocket handlers
│   ├── __init__.py
│   ├── handlers.py                     # Base handlers
│   ├── chat_handlers.py                # Chat WebSocket handlers
│   └── voice_handlers.py               # Voice WebSocket handlers
├── utils/                              # Utility functions
│   ├── __init__.py
│   ├── client_utils.py                 # Client utilities
│   ├── error_utils.py                  # Error handling utilities
│   └── websocket_utils.py              # WebSocket utilities
├── tools/                              # External tools
│   ├── __init__.py
│   ├── web_tools.py                    # Web scraping tools
│   └── marketing_tools_plan.md         # Marketing tools plan
├── static/                             # Static web assets
│   ├── css/
│   │   └── styles.css                  # Main stylesheet
│   ├── js/
│   │   └── client.js                   # Frontend JavaScript
│   ├── index.html                      # Main dashboard
│   ├── realtime-voice.html             # Voice chat interface
│   └── voice-test.html                 # Voice testing interface
├── schemas/                            # Database schemas
│   └── schema.gsql                     # TigerGraph schema
├── scripts/                            # Utility scripts
│   ├── README.md                       # Scripts documentation
│   ├── setup-tigergraph.sh             # TigerGraph setup (Linux/Mac)
│   ├── setup-tigergraph.ps1            # TigerGraph setup (Windows)
│   ├── init_tigergraph.py              # Database initialization
│   ├── smart_tigergraph_init.py        # Smart initialization
│   ├── start_everything.py             # Master startup script
│   ├── start_tigergraph_safe.py        # Safe TigerGraph startup
│   ├── check_financial_status.py       # Financial status checker
│   └── check-file-sizes.py             # File size checker
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── run_tests.py                    # Test runner
│   ├── test_initial.py                 # Initial tests
│   ├── test_api_endpoints.py           # API endpoint tests
│   ├── test_cognitive_nodes.py         # Cognitive node tests
│   ├── test_configuration.py           # Configuration tests
│   ├── test_economic_behaviors.py      # Economic behavior tests
│   ├── test_end_to_end_workflows.py    # End-to-end workflow tests
│   ├── test_kip_tools.py               # KIP tool tests
│   ├── test_production_readiness.py    # Production readiness tests
│   ├── test_prompt_cache.py            # Prompt cache tests
│   ├── test_security_middleware.py     # Security middleware tests
│   ├── test_setup.py                   # Setup tests
│   ├── test_smart_router.py            # Smart router tests
│   ├── test_voice_foundation.py        # Voice foundation tests
│   ├── test_websocket_streaming.py     # WebSocket streaming tests
│   └── voice_foundation/               # Voice-specific tests
│       ├── test_pipeline.py            # Voice pipeline tests
│       ├── test_kyutai_tts_only.py     # Kyutai TTS tests
│       └── test_production_voice.py    # Production voice tests
├── docs/                               # Documentation
│   ├── Hybrid AI Council_ Architectural Blueprint v3.8 (Final).md
│   ├── Unified Implementation Plan v2.3 (Final).md
│   ├── dev-log-Hybrid-AI-Council.md   # Development log
│   ├── ENVIRONMENT_VARIABLES.md        # Environment setup guide
│   ├── TigerGraph_Community_Edition_Setup.md
│   ├── SYSTEM_VERIFICATION_GUIDE.md    # System verification
│   ├── MULTI_MODEL_TEST_GUIDE.md      # Multi-model testing
│   ├── INTEGRATION_MAP.md             # Integration mapping
│   ├── KIP_AUTONOMOUS_AGENTS_EXPLAINED.md
│   ├── AUTONOMOUS_TRADING_SYSTEM.md   # Trading system docs
│   ├── CODE_PATTERNS.md               # Code patterns guide
│   ├── DEBUGGING_GUIDE.md             # Debugging guide
│   ├── SECURITY.md                    # Security guidelines
│   ├── SYSTEM_PERFECTION_ROADMAP.md   # System roadmap
│   ├── MIDDLEWARE_FIX_DOCUMENTATION.md
│   └── REST_API_FIX_DOCUMENTATION.md
├── decisions/                          # Architecture decisions
│   ├── template.md                     # Decision template
│   ├── 001-why-ollama-over-vllm.md    # Ollama decision
│   ├── 002-why-tigergraph-over-postgres.md
│   ├── 003-why-smart-router-architecture.md
│   └── 004-coqui-xtts-v2-for-council-voices.md
├── docker/                             # Docker configurations
│   └── vllm/                          # vLLM configurations
└── archive/                            # Archived files
    ├── CHAT_SESSION_HANDOFF.md
    ├── code_audit_progress.md
    ├── CODE_CLEANUP_AUDIT.md
    ├── REFACTORING_HANDOFF_V2.md
    ├── SESSION_SUMMARY_AUG_4_2025.md
    └── SMART_ROUTER_HANDOFF.md
```

## 🚀 **Python 3.11 Microservices (NEW ARCHITECTURE)**

```
python311-services/                     # Python 3.11 compatibility layer
├── pyproject.toml                      # Python 3.11 dependencies (voice/ML)
├── README.md                           # Service overview & purpose
├── SETUP_GUIDE.md                      # Complete setup instructions
├── setup.py                           # Automated dependency installer
├── voice/                              # Voice processing microservice
│   ├── __init__.py
│   ├── main.py                         # FastAPI voice service
│   ├── engines/                        # Voice processing engines
│   │   ├── __init__.py
│   │   └── voice_engines.py            # STT (Parakeet) + TTS (XTTS v2)
│   └── outputs/                        # Generated audio files
├── tests/                              # Voice service tests
│   ├── __init__.py
│   ├── test_voice_engines.py           # Voice engine unit tests
│   └── test_voice_service.py           # Voice service integration tests
└── shared/                             # Shared utilities (future expansion)
```

**Purpose**: Handles Python 3.11-only dependencies (voice/ML) as microservice

## 📊 **Recently Modified**

| File | Action | Reason | Session |
|------|--------|--------|---------|
| `start_all.py` | ✅ Created | One-command startup script for all services | Current |
| `python311-services/voice/main.py` | ✅ Created | FastAPI voice service with STT/TTS endpoints | Current |
| `python311-services/voice/engines/voice_engines.py` | ✅ Created | NeMo Parakeet STT + Coqui XTTS v2 TTS engines | Current |
| `voice_foundation/voice_client.py` | ✅ Created | HTTP client for voice service communication | Current |
| `voice_foundation/production_voice_engines.py` | 🔄 Updated | Updated to use voice service client instead of direct imports | Current |
| `pyproject.toml` | 🔄 Updated | Removed voice dependencies, updated to Python 3.13 | Current |
| `python311-services/pyproject.toml` | ✅ Created | Python 3.11 dependencies for voice microservice | Current |
| `websocket_handlers/voice_handlers.py` | 🔄 Updated | Updated to use initialized voice orchestrator | Current |
| `voice_foundation/orchestrator_integration.py` | 🔄 Updated | Added async initialization and retry logic | Current |
| `main.py` | 🔄 Updated | Updated to use async voice orchestrator initialization | Current |
| `tests/voice_foundation/test_pipeline.py` | ❌ Removed | Moved to python311-services/tests/ | Current |
| `tests/voice_foundation/test_kyutai_tts_only.py` | ❌ Removed | No longer needed (Kyutai removed) | Current |
| `tests/test_voice_foundation.py` | 🔄 Updated | Updated to test microservice integration | Current |
| `kyutai-tts/` | ❌ Removed | Entire directory removed (replaced with Coqui XTTS v2) | Current |
| `voice_foundation/requirements.txt` | ❌ Removed | No longer needed (using pyproject.toml) | Current |

## 🎯 **Key Components**

### **Voice System (NEW)**
- **STT**: NVIDIA NeMo Parakeet-TDT-0.6B-v2 (SOTA speech recognition)
- **TTS**: Coqui XTTS v2 (multi-voice, voice cloning, ~200ms latency)
- **Architecture**: Python 3.11 microservice communicating via HTTP
- **Integration**: HTTP client in main project for seamless communication

### **Core AI Components**
- **Orchestrator**: LangGraph-based state machine for cognitive workflows
- **Pheromind**: Redis-based subconscious pattern recognition
- **KIP**: TigerGraph-based knowledge integration with economic modeling
- **Smart Router**: Intelligent request routing and load balancing

### **External Services**
- **Ollama**: Local LLM inference (Mistral, Qwen3, DeepSeek)
- **TigerGraph**: Graph database for knowledge persistence
- **Redis**: Caching and pheromone storage
- **Docker**: Containerized services

## 🚀 **Quick Start**

```bash
# Start everything with one command
python start_all.py

# Access the system
# Main Dashboard: http://localhost:8001/static/index.html
# Voice Chat: http://localhost:8001/static/realtime-voice.html
# Voice Health: http://localhost:8011/health
```

## 📋 **Development Status**

- ✅ **Voice System**: Fully implemented and working
- ✅ **Core Architecture**: Complete with 3-layer cognitive system
- ✅ **Microservices**: Python 3.13/3.11 split working
- ✅ **One-Command Startup**: All services start with single command
- ✅ **Production Ready**: Error handling, logging, health checks
- 🔄 **Testing**: Comprehensive test suite in place
- 🔄 **Documentation**: Complete architectural documentation