# **Hybrid AI Council - Project Structure**

## 📁 **Root Directory Structure**

```
hybrid-cognitive-architecture/
├── .cursorrules                    # Cursor AI instructions
├── .env                           # Environment variables
├── .gitignore                     # Git ignore rules (includes .cursor-logs/ and dev-logs/)
├── docker-compose.yaml            # Docker services (Redis, TigerGraph, Ollama)
├── main.py                        # Main FastAPI application
├── pyproject.toml                 # Main project dependencies (Python 3.13)
├── README.md                      # Project overview
├── start_all.py                   # Single command to start all services
├── verify_system.py               # System verification script
│
├── .cursor-logs/                  # 🔗 SYMBOLIC LINK to external storage
│   └── *.md                      # Conversation history (moved to D:\Council-Project\.cursor-logs)
│
├── config/                        # Configuration management
│   ├── __init__.py
│   └── models.py                  # Model definitions and aliases
│
├── core/                          # Core AI system components
│   ├── orchestrator/              # LangGraph orchestrator
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # Main orchestrator
│   │   ├── models.py             # Orchestrator models
│   │   ├── nodes/                # Processing nodes
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── council_nodes.py
│   │   │   ├── kip_nodes.py
│   │   │   ├── pheromind_nodes.py
│   │   │   ├── smart_router_nodes.py
│   │   │   └── support_nodes.py
│   │   ├── processing_nodes.py
│   │   ├── state_machine.py
│   │   ├── streaming.py
│   │   └── synthesis.py
│   ├── pheromind.py              # Pheromone-based memory system
│   ├── kip/                      # Knowledge Investment Protocol
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── budget_manager.py
│   │   ├── economic_analyzer.py
│   │   ├── exceptions.py
│   │   ├── models.py
│   │   ├── tools.py
│   │   ├── transaction_processor.py
│   │   ├── treasury_core.py
│   │   └── treasury.py
│   ├── logging_config.py         # Structured logging setup
│   ├── cache_integration.py      # Redis cache integration
│   ├── error_boundaries.py       # Error handling patterns
│   └── prompt_cache.py           # LLM prompt caching
│
├── clients/                       # External service clients
│   ├── __init__.py
│   ├── redis_client.py           # Redis connection and operations
│   ├── tigervector_client.py     # TigerGraph client
│   └── ollama_client.py          # Ollama LLM client
│
├── endpoints/                     # FastAPI endpoints
│   ├── __init__.py
│   ├── chat.py                   # Chat endpoints
│   ├── health.py                 # Health check endpoints
│   └── voice.py                  # Voice processing endpoints
│
├── middleware/                    # FastAPI middleware
│   ├── __init__.py
│   ├── rate_limiting.py
│   ├── request_validation.py
│   └── security_headers.py
│
├── schemas/                       # Database schemas
│   └── schema.gsql               # TigerGraph schema
│
├── scripts/                       # Utility scripts
│   ├── __init__.py
│   ├── start_everything.py       # Service orchestration
│   ├── init_tigergraph.py        # Database initialization
│   ├── setup-tigergraph.sh       # TigerGraph setup (Linux/Mac)
│   ├── setup-tigergraph.ps1      # TigerGraph setup (Windows)
│   ├── start_tigergraph_safe.py  # Safe TigerGraph startup
│   ├── smart_tigergraph_init.py  # Smart database initialization
│   ├── check_financial_status.py # KIP status checker
│   └── check-file-sizes.py       # File size monitoring
│
├── static/                        # Web interface files
│   ├── index.html                # Main dashboard
│   ├── realtime-voice.html       # Voice chat interface
│   ├── voice-test.html           # Voice testing interface
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── client.js
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_initial.py           # Basic system tests
│   ├── test_api_endpoints.py     # API endpoint tests
│   ├── test_cognitive_nodes.py   # Cognitive system tests
│   ├── test_configuration.py     # Configuration tests
│   ├── test_economic_behaviors.py # KIP economic tests
│   ├── test_end_to_end_workflows.py # End-to-end tests
│   ├── test_kip_tools.py         # KIP tool tests
│   ├── test_production_readiness.py # Production tests
│   ├── test_prompt_cache.py      # Cache tests
│   ├── test_security_middleware.py # Security tests
│   ├── test_setup.py             # Setup tests
│   ├── test_smart_router.py      # Router tests
│   ├── test_voice_foundation.py  # Voice integration tests
│   ├── test_websocket_streaming.py # WebSocket tests
│   └── voice_foundation/         # Voice-specific tests
│       ├── test_kyutai_tts_only.py
│       ├── test_pipeline.py
│       └── test_production_voice.py
│
├── tools/                         # External tool integrations
│   ├── __init__.py
│   ├── web_tools.py              # Web scraping tools
│   └── marketing_tools_plan.md   # Marketing tools roadmap
│
├── utils/                         # Utility functions
│   ├── __init__.py
│   ├── client_utils.py           # Client utilities
│   ├── error_utils.py            # Error handling utilities
│   └── websocket_utils.py        # WebSocket utilities
│
├── voice_foundation/              # Voice processing integration
│   ├── __init__.py
│   ├── voice_client.py           # Voice service client
│   ├── production_voice_engines.py # Voice foundation wrapper
│   ├── simple_voice_pipeline.py  # Simple voice pipeline
│   ├── orchestrator_integration.py # Voice orchestrator
│   ├── create_test_audio.py      # Test audio generation
│   ├── integration_test_output.wav # Test audio file
│   ├── test_audio.wav            # Test audio file
│   ├── test_output.wav           # Test audio file
│   ├── requirements.txt           # Voice dependencies (legacy)
│   ├── README.md                  # Voice foundation docs
│   ├── production_voice_engines.py # Production voice engines
│   ├── simple_voice_pipeline.py  # Simple voice pipeline
│   ├── orchestrator_integration.py # Voice orchestrator integration
│   └── outputs/                  # Generated audio files
│       ├── kyutai_test.wav
│       ├── realtime_*.wav        # Real-time voice outputs
│       └── test_*.wav            # Test audio outputs
│
├── websocket_handlers/            # WebSocket message handlers
│   ├── __init__.py
│   ├── handlers.py               # Base handlers
│   ├── chat_handlers.py          # Chat message handlers
│   └── voice_handlers.py         # Voice message handlers
│
├── docs/                          # Documentation
│   ├── Hybrid AI Council_ Architectural Blueprint v3.8 (Final).md
│   ├── Unified Implementation Plan v2.3 (Final).md
│   ├── dev-log-Hybrid-AI-Council.md # 🔗 SYMBOLIC LINK to external storage
│   ├── AUTONOMOUS_TRADING_SYSTEM.md
│   ├── CODE_PATTERNS.md
│   ├── DEBUGGING_GUIDE.md
│   ├── ENVIRONMENT_VARIABLES.md
│   ├── INTEGRATION_MAP.md
│   ├── KIP_AUTONOMOUS_AGENTS_EXPLAINED.md
│   ├── MIDDLEWARE_FIX_DOCUMENTATION.md
│   ├── MULTI_MODEL_TEST_GUIDE.md
│   ├── REST_API_FIX_DOCUMENTATION.md
│   ├── SECURITY.md
│   ├── SYSTEM_VERIFICATION_GUIDE.md
│   └── TigerGraph_Community_Edition_Setup.md
│
├── decisions/                     # Architecture decisions
│   ├── template.md               # Decision template
│   ├── 001-why-ollama-over-vllm.md
│   ├── 002-why-tigergraph-over-postgres.md
│   ├── 003-why-smart-router-architecture.md
│   └── 004-coqui-xtts-v2-for-council-voices.md
│
└── python311-services/            # 🚀 **Python 3.11 Microservices (NEW ARCHITECTURE)**
    ├── pyproject.toml            # Python 3.11 dependencies (voice/ML)
    ├── README.md                  # Service overview & purpose
    ├── SETUP_GUIDE.md            # Complete setup instructions
    ├── setup.py                   # Automated dependency installer
    ├── voice/                     # Voice processing microservice
    │   ├── __init__.py
    │   ├── main.py               # FastAPI voice service
    │   ├── engines/              # Voice processing engines
    │   │   ├── __init__.py
    │   │   └── voice_engines.py  # STT (Parakeet) + TTS (XTTS v2)
    │   └── outputs/              # Generated audio files
    ├── shared/                    # Shared utilities (future expansion)
    └── tests/                     # Voice service tests
        ├── __init__.py
        ├── test_voice_engines.py # Voice engine unit tests
        ├── test_voice_service.py # Voice service integration tests
        └── README.md             # Test documentation
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
└── shared/                             # Shared utilities (future expansion)
```

**Purpose**: Handles Python 3.11-only dependencies (voice/ML) as microservice

## 📊 **External Storage (Performance Optimization)**

```
D:\Council-Project\
├── .cursor-logs/                      # Conversation history (18MB+)
│   ├── 1-cursor-ai-hybrid-build-chat-7-28-25.md
│   ├── 2-cursor-ai-hybrid-build-chat-7-28-25.md
│   ├── ...
│   └── 12-cursor-ai-hybrid-build-chat-8-5-25.md
└── dev-logs/                          # Development logs
    └── dev-log-Hybrid-AI-Council.md   # Historical development progress
```

**Purpose**: Stores large historical files to improve main repo performance

## 🔧 **Recently Modified**

| File | Action | Reason | Session |
|------|--------|--------|---------|
| .gitignore | ✅ Updated | Added .cursor-logs/ and dev-logs/ exclusions | Aug 5 |
| docs/dev-log-Hybrid-AI-Council.md | 🔄 Moved | Moved to external storage for performance | Aug 5 |
| docs/SYSTEM_PERFECTION_ROADMAP.md | ❌ Removed | Outdated roadmap with old TODO items | Aug 5 |
| archive/ | ❌ Removed | Old handoff files no longer needed | Aug 5 |
| sentencepiece-0.2.1-cp313-cp313-win_amd64.whl | ❌ Removed | Temporary wheel file | Aug 5 |
| server.log | ❌ Removed | Temporary log file | Aug 5 |

## 🎯 **Key Architectural Decisions**

1. **Python Version Split**: Main project (3.13) + Voice microservice (3.11)
2. **External Storage**: Large historical files moved to `D:\Council-Project\`
3. **Microservices**: Voice processing isolated in separate service
4. **Performance**: Main repo optimized to ~35K lines (was 476K+)

## 🚀 **Quick Start Commands**

```bash
# Start everything with one command
python start_all.py

# Or use the script
python scripts/start_everything.py --with-api

# Access the system
# Main Dashboard: http://localhost:8001/static/index.html
# Voice Chat: http://localhost:8001/static/realtime-voice.html
# Voice Service: http://localhost:8011/health
```

## 📈 **Performance Metrics**

- **Main Repo**: ~35K lines (down from 476K+)
- **External Storage**: ~437K lines moved to `D:\Council-Project\`
- **Performance Gain**: ~92% reduction in main repo size
- **Accessibility**: All files still accessible via symbolic links