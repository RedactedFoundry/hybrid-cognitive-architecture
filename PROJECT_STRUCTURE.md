# **Hybrid AI Council - Project Structure**

## 📁 **Root Directory Structure**

```text
hybrid-cognitive-architecture/
├── .cursorrules                    # Cursor AI instructions
├── .env                           # Environment variables
├── .gitignore                     # Git ignore rules (includes .cursor-logs/ and dev-logs/)
├── docker-compose.yaml            # Docker services (Redis, TigerGraph)
├── main.py                        # Main FastAPI application
├── pyproject.toml                 # Main project dependencies (Python 3.13)
├── README.md                      # Project overview
├── start_all.py                   # Single command to start all services
├── add_sample_data.py             # TigerGraph sample data loader  
├── comprehensive_baseline_review.py # Quality analysis framework
├── detailed_quality_comparison.py # Response comparison tool
├── show_response_differences.py   # Side-by-side response viewer
├── test_json_ab.py               # A/B testing framework
├── manual_tigergraph_examples.gsql # TigerGraph GSQL examples
├── Perplexity JSON-Prompt-v1.3.json # JSON prompting reference
│
├── .cursor-logs/                  # 🔗 SYMBOLIC LINK to external storage
│   └── *.md                      # Conversation history (moved to D:\Council-Project\.cursor-logs)
│
├── project-docs/                  # 🔗 SYMBOLIC LINK to external storage
│   ├── CODE_PATTERNS.md          # Code patterns and conventions
│   ├── DEBUGGING_GUIDE.md        # Debugging and troubleshooting
│   ├── SYSTEM_VERIFICATION_GUIDE.md # System verification procedures
│   └── code-audit-prompt.md      # IDE/AI coding issues guide
│
├── config/                        # Configuration management
│   ├── __init__.py
│   ├── models.py                  # Model definitions and aliases
│   └── llama_cpp_models.py        # llama.cpp model paths and ports (env-driven)
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
│   │   │   ├── simple_generator_verifier_node.py  # Constitution v5.4 main flow
│   │   │   └── support_nodes.py
│   │   ├── processing_nodes.py
│   │   ├── state_machine.py
│   │   ├── streaming.py
│   │   └── synthesis.py
│   ├── pheromind.py              # Pheromone-based memory system
│   ├── verifier.py               # Constitution v5.4 verifier system
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
│   ├── error_boundaries.py       # Error handling patterns
│   └── prompt_cache.py           # LLM prompt caching
│
├── clients/                       # External service clients  
│   ├── __init__.py
│   ├── redis_client.py           # Redis connection and operations
│   ├── tigervector_client.py     # TigerGraph client
│   ├── llama_cpp_client.py       # llama.cpp HTTP client for models
│   └── model_router.py           # Model routing (llama.cpp only)
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
│   ├── init_tigergraph.py        # Database initialization
│   ├── setup-tigergraph.sh       # TigerGraph setup (Linux/Mac)
│   ├── setup-tigergraph.ps1      # TigerGraph setup (Windows)
│   ├── start_tigergraph_safe.py  # Safe TigerGraph startup
│   ├── smart_tigergraph_init.py  # Smart database initialization
│   ├── check_financial_status.py # KIP status checker
│   ├── start_llamacpp_servers.py # Start and monitor llama.cpp servers (multi-model)
│   ├── quick_db_check.py         # Quick database status check
│   ├── verify_system.py          # Complete system verification
│   └── check-file-sizes.py       # File size monitoring
│
├── static/                        # Web interface files
│   ├── index.html                # Main dashboard
│   ├── realtime-voice.html       # Voice chat interface
│   ├── voice-test.html           # Voice testing interface
│   ├── claude-ui-mockup.html     # Standalone interactive UI mockup (no backend)
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
```text

## 🚀 **Python 3.11 Microservices (NEW ARCHITECTURE)**

```text
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

```text
D:\Council-Project\
├── .cursor-logs/                      # Conversation history (18MB+)
│   ├── 1-cursor-ai-hybrid-build-chat-7-28-25.md
│   ├── 2-cursor-ai-hybrid-build-chat-7-28-25.md
│   ├── ...
│   └── 12-cursor-ai-hybrid-build-chat-8-5-25.md
│   
└── Project Docs/                      # Project documentation
    ├── CODE_PATTERNS.md               # Code patterns and conventions
    ├── DEBUGGING_GUIDE.md             # Debugging and troubleshooting
    ├── SYSTEM_VERIFICATION_GUIDE.md   # System verification procedures
    └── code-audit-prompt.md           # IDE/AI coding issues guide
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
| **CLEANUP COMPLETED** | 🔄 **Aug 5** | **Comprehensive codebase cleanup** | **Aug 5** |
| clients/tigervector_client.py | 🔄 Updated | Added is_graph_initialized() for smart schema detection | Aug 10 |
| scripts/init_tigergraph.py | 🔄 Updated | Smart initialization: handles existing graphs without errors | Aug 10 |
| start_all.py | 🔄 Updated | Modular architecture: delegates TigerGraph logic to client | Aug 10 |
| **TIGERGRAPH SMART INIT** | ✅ **Aug 10** | **Bulletproof TigerGraph initialization system** | **Aug 10** |
| start_main_api.py | ❌ Removed | Superseded by start_all.py | Aug 5 |
| start_voice_service.py | ❌ Removed | Superseded by start_all.py | Aug 5 |
| start_voice.sh | ❌ Removed | Superseded by start_all.py | Aug 5 |
| quick_start.py | ❌ Removed | Superseded by start_all.py | Aug 5 |
| start_manual.py | ❌ Removed | Superseded by start_all.py | Aug 5 |
| test_voice_complete.py | ❌ Removed | Temporary debug test | Aug 5 |
| test_voice_fix.py | ❌ Removed | Temporary debug test | Aug 5 |
| test_audio_conversion.py | ❌ Removed | Temporary debug test | Aug 5 |
| test_integration.py | ❌ Removed | Temporary debug test | Aug 5 |
| SYSTEMATIC_DEBUG_PLAN.md | ❌ Removed | Temporary debug plan | Aug 5 |
| STARTUP_COMMAND_GUIDE.md | ❌ Removed | Superseded by Makefile | Aug 5 |
| main_project_deps.txt | ❌ Removed | Redundant with pyproject.toml | Aug 5 |
| code-audit-prompt.md | 🔄 Moved | Moved to external storage | Aug 5 |
| docs/CODE_PATTERNS.md | 🔄 Moved | Large doc moved to external storage | Aug 5 |
| docs/SYSTEM_VERIFICATION_GUIDE.md | 🔄 Moved | Large doc moved to external storage | Aug 5 |
| docs/DEBUGGING_GUIDE.md | 🔄 Moved | Large doc moved to external storage | Aug 5 |
| test_voice_foundation.py | 🔄 Moved | Moved from root to tests/ directory | Aug 5 |
| quick_db_check.py | 🔄 Moved | Moved from root to scripts/ directory | Aug 5 |
| verify_system.py | 🔄 Moved | Moved from root to scripts/ directory | Aug 5 |
| project-docs/ | ✅ Created | Symbolic link to external Project Docs | Aug 6 |
| ollama/Modelfile.huihui-oss20b | ✅ Created | Register local HuiHui GPT-OSS 20B (MXFP4_MOE) with Ollama | Aug 6 |
| config/models.py | 🔄 Updated | Route generator to HuiHui OSS20B, keep Mistral 7B for verifier/pheromind | Aug 6 |
| start_all.py | 🔧 Refactored | Unified llama.cpp startup/health, Windows UTF-8 logs, removed Ollama | Aug 14 |
| core/orchestrator/synthesis.py | 🔄 Updated | Conversational tone; no preambles or headings | Aug 14 |
| core/orchestrator/nodes/smart_router_nodes.py | 🔄 Updated | Classification via llama.cpp ModelRouter | Aug 14 |
| core/orchestrator/nodes/simple_generator_verifier_node.py | 🔄 Updated | Conversational generator prompt; safer rewrite prompt | Aug 14 |
| core/orchestrator/nodes/support_nodes.py | 🔄 Updated | Fast path yields 1–2 natural sentences | Aug 14 |
| clients/model_router.py | 🔄 Updated | llama.cpp-only routing; removed Ollama branch | Aug 14 |
| clients/llama_cpp_client.py | 🔄 Updated | Host+port from env; fixed base URL | Aug 14 |
| config/llama_cpp_models.py | ✅ Created/Updated | Env-driven model dir/host/ports; validation helpers | Aug 14 |
| scripts/start_llamacpp_servers.py | 🔄 Updated | Config-safe import; explicit binary; Windows UTF-8 logs | Aug 14 |
| Makefile | 🔄 Updated | Replaced Ollama checks with llama.cpp health targets | Aug 14 |
| PROJECT_STRUCTURE.md | 🔄 Updated | Removed Ollama references and legacy utilities | Aug 14 |
| CURRENT_ISSUES.md | 🔄 Updated | Unified llama.cpp backend; voice/TTS notes | Aug 14 |
| clients/ollama_client.py | ❌ Removed | Legacy client no longer used | Aug 14 |
| core/cache_integration.py | ❌ Removed | Ollama cache wrapper removed | Aug 14 |
| utils/client_utils.py | ❌ Removed | Ollama client helpers removed | Aug 14 |
| scripts/check_ollama_health.py | ❌ Removed | Legacy health script removed | Aug 14 |
| scripts/generate_modelfile.py | ❌ Removed | Legacy Ollama Modelfile generator removed | Aug 14 |
| ollama/Modelfile.huihui-oss20b | ❌ Removed | Legacy model definition | Aug 14 |
| schemas/schema.gsql | 🔄 Updated | Fixed function→agent_role reserved word conflict | Aug 12 |
| scripts/generate_modelfile.py | ✅ Created | Dynamic Ollama Modelfile generation for cloud deployment | Aug 12 |
| comprehensive_baseline_review.py | ✅ Created | Quality analysis framework for response evaluation | Aug 12 |
| test_json_ab.py | ✅ Created | A/B testing framework for prompting strategies | Aug 12 |
| detailed_quality_comparison.py | ✅ Created | Multi-metric response comparison tool | Aug 12 |
| show_response_differences.py | ✅ Created | Side-by-side response comparison viewer | Aug 12 |
| .cursorrules | 🔄 Updated | MCP server integration guidance and debugging loop prevention | Aug 12 |
| project-docs/HANDOFF_AUG_11_2025_LATE_EVENING.md | ✅ Created | Session handoff documentation | Aug 12 |
| CURRENT_ISSUES.md | 🔄 Updated | Production-ready status and accomplishments | Aug 12 |
| project-docs/dev-log-Hybrid-AI-Council.md | 🔄 Updated | Complete session documentation | Aug 12 |
| static/claude-ui-mockup.html | ✅ Created | Standalone Claude UI interactive mockup (no backend) | Aug 14 |
| project-docs/dev-log-Hybrid-AI-Council.md | 🔄 Updated | Logged llama.cpp migration, Ollama removal, UI mockup, OG.env purge | Aug 14 |

## 🎯 **Key Architectural Decisions**

1. **Python Version Split**: Main project (3.13) + Voice microservice (3.11)
2. **External Storage**: Large historical files moved to `D:\Council-Project\`
3. **Microservices**: Voice processing isolated in separate service
4. **Performance**: Main repo optimized to ~35K lines (was 476K+)

## 🚀 **Quick Start Commands**

```bash
# Start everything with one command
python start_all.py

# Access the system
# Main Dashboard: http://localhost:8001/static/index.html  
# Voice Chat: http://localhost:8001/static/realtime-voice.html
# Voice Service: http://localhost:8011/health
# TigerGraph GraphStudio: http://localhost:14240
```

## 📈 **Performance Metrics**

- **Main Repo**: ~35K lines (down from 476K+)
- **External Storage**: ~437K lines moved to `D:\Council-Project\`
- **Performance Gain**: ~92% reduction in main repo size

- **Accessibility**: All files still accessible via symbolic links
