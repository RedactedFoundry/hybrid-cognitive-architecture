# 🏗️ Hybrid AI Council - Project Structure

> **Living Document**: Updated as we add/modify files during development
> 
> **Purpose**: Complete reference for file organization, preventing duplication and ensuring proper placement of new code

## 📁 Root Directory Structure

```
hybrid-cognitive-architecture/
├── 📋 Project Management & Docs
├── ⚙️  Configuration Files  
├── 🧠 Core AI System
├── 🔌 External Integrations
├── 🌐 API Endpoints
├── 🛡️  Security & Middleware
├── 🗄️  Data & Schemas
├── 🔧 Development Tools
├── 🧪 Testing Suite
├── 🎤 Voice Foundation
├── 📡 WebSocket Handlers
├── 🖥️  Static Assets (UI)
└── 🐳 Containerization
```

## 📋 Project Management & Documentation

```
├── CHAT_SESSION_HANDOFF.md           # Session continuity & status
├── SYSTEM_PERFECTION_ROADMAP.md      # Testing journey & milestones  
├── CODE_CLEANUP_AUDIT.md             # Code quality tracking
├── code_audit_progress.md            # Audit progress log
├── code-audit-prompt.md              # Audit methodology
├── REFACTORING_HANDOFF_V2.md         # Refactoring documentation
├── SMART_ROUTER_HANDOFF.md           # Smart router implementation
├── ENVIRONMENT_VARIABLES.md          # Environment setup guide
├── SECURITY.md                       # Security policies
├── LICENSE                           # Project license
├── README.md                         # Main project documentation
├── PROJECT_STRUCTURE.md              # 👈 THIS FILE
├── CURSOR_BASH_SETUP.md              # Cursor terminal setup
├── SYSTEM_VERIFICATION_GUIDE.md      # Complete system testing guide
├── CURRENT_ISSUES.md                 # ✅ Active priorities & blockers tracker
├── verify_system.py                  # Quick system health check
├── quick_db_check.py                 # Database inspection tool
├── find_git_bash.ps1                 # Git Bash path finder
├── Makefile                          # ✅ One-command operations (dev-setup, test-all, etc.)
└── decisions/                        # ✅ Architecture Decision Records
    ├── 001-why-ollama-over-vllm.md
    ├── 002-why-tigergraph-over-postgres.md
    ├── 003-why-smart-router-architecture.md
    └── template.md
```

## ⚙️ Configuration Files

```
├── config.py                         # Main configuration loader
├── config/
│   ├── __init__.py
│   └── models.py                      # Pydantic config models
├── pyproject.toml                     # Dependencies & project metadata
├── poetry.lock                        # Locked dependency versions
├── .cursorrules                       # Cursor AI assistant rules
├── .env                              # Local environment variables (gitignored)
├── .gitignore                        # Git ignore patterns
└── .vscode/
    └── settings.json                  # Workspace terminal settings
```

## 🧠 Core AI System (The Brain)

```
core/
├── __init__.py
├── orchestrator.py                    # Legacy orchestrator (being phased out)
├── pheromind.py                       # Subconscious pattern discovery
├── logging_config.py                  # Structured logging setup
├── cache_integration.py               # Caching layer integration
├── error_boundaries.py                # Error handling patterns
├── prompt_cache.py                    # LLM prompt caching
│
├── orchestrator/                      # 🎯 NEW: Smart Router System
│   ├── __init__.py
│   ├── orchestrator.py                # Main orchestrator logic
│   ├── models.py                      # Data models & state
│   ├── state_machine.py               # State management
│   ├── streaming.py                   # Real-time response streaming
│   ├── synthesis.py                   # Response synthesis
│   ├── processing_nodes.py            # Legacy processing nodes
│   └── nodes/                         # Smart routing nodes
│       ├── __init__.py
│       ├── base.py                    # Base node classes
│       ├── council_nodes.py           # Multi-agent deliberation
│       ├── kip_nodes.py               # Economic action nodes
│       ├── pheromind_nodes.py         # Pattern discovery nodes
│       ├── smart_router_nodes.py      # Intent classification
│       └── support_nodes.py           # Utility nodes
│
└── kip/                               # 💰 Knowledge-Incentive Protocol (Economic Engine)
    ├── __init__.py
    ├── treasury.py                    # Main treasury interface
    ├── treasury_core.py               # Core treasury operations
    ├── budget_manager.py              # Budget allocation & tracking
    ├── transaction_processor.py       # Transaction handling
    ├── economic_analyzer.py           # ROI & performance analysis
    ├── agents.py                      # Autonomous economic agents
    ├── tools.py                       # KIP agent tools
    ├── models.py                      # KIP data models
    └── exceptions.py                  # KIP-specific exceptions
```

## 🔌 External Integrations (Database & AI Clients)

```
clients/
├── __init__.py
├── redis_client.py                    # Redis connection & operations
├── tigervector_client.py              # TigerGraph connection & queries  
└── ollama_client.py                   # Local LLM client (Qwen, DeepSeek, Mistral)
```

## 🌐 API Endpoints

```
├── main.py                            # FastAPI application entry point
└── endpoints/
    ├── __init__.py
    ├── chat.py                        # Chat completion endpoints
    ├── health.py                      # Health check endpoints
    └── voice.py                       # Voice processing endpoints
```

## 🛡️ Security & Middleware

```
middleware/
├── __init__.py
├── rate_limiting.py                   # API rate limiting
├── request_validation.py              # Input validation & sanitization
└── security_headers.py                # Security header injection
```

## 🗄️ Data & Schemas

```
├── schemas/
│   └── schema.gsql                    # TigerGraph database schema
└── models/                            # (Currently empty - data models in core/)
```

## 🔧 Development Tools & Scripts

```
├── scripts/
│   ├── README.md                      # Script documentation
│   ├── init_tigergraph.py             # TigerGraph database initialization
│   ├── setup-tigergraph.sh            # TigerGraph setup (Linux/Mac)
│   ├── setup-tigergraph.ps1           # TigerGraph setup (Windows)
│   ├── test_setup.py                  # Development environment test
│   └── check-file-sizes.py            # File size compliance check
├── tools/
│   ├── __init__.py
│   ├── web_tools.py                   # Web scraping & research tools
│   └── marketing_tools_plan.md        # Future marketing tools plan
├── utils/
│   ├── __init__.py
│   ├── client_utils.py                # Client utility functions
│   ├── error_utils.py                 # Error handling utilities
│   └── websocket_utils.py             # WebSocket utility functions
└── run_tests.py                       # Test runner script
```

## 🧪 Testing Suite (6 Critical Test Categories)

```
tests/
├── __init__.py
├── test_initial.py                    # Basic functionality tests
├── test_configuration.py              # Configuration validation tests
├── test_api_endpoints.py              # API endpoint tests
├── test_security_middleware.py        # Security & middleware tests
├── test_cognitive_nodes.py            # Core AI system tests
├── test_smart_router.py               # Smart router tests
├── test_kip_tools.py                  # KIP economic engine tests
├── test_voice_foundation.py           # Voice processing tests
├── test_websocket_streaming.py        # WebSocket streaming tests
├── test_end_to_end_workflows.py       # Complete workflow tests
├── test_economic_behaviors.py         # Economic agent behavior tests
├── test_prompt_cache.py               # Prompt caching tests
├── test_chaos.py                      # Chaos engineering tests
└── test_production_readiness.py       # 🎯 Load testing & production validation
```

## 🎤 Voice Foundation (SOTA Voice Integration)

```
voice_foundation/
├── README.md                          # Voice system documentation
├── requirements.txt                   # Voice-specific dependencies
├── create_test_audio.py               # Audio file generation
├── orchestrator_integration.py        # Voice-orchestrator integration
├── production_voice_engines.py        # Production voice pipelines
├── simple_voice_pipeline.py           # Basic voice pipeline
├── test_*.py                         # Voice testing scripts
├── *.wav                             # Test audio files
├── outputs/                          # Generated audio outputs
│   └── *.wav                         # Voice synthesis outputs
└── voice_foundation/                 # Nested voice utilities
    └── outputs/                      # Additional audio outputs
```

## 📡 WebSocket Handlers (Real-time Communication)

```
websockets/
├── __init__.py
├── handlers.py                        # Base WebSocket handlers
├── chat_handlers.py                   # Chat-specific WebSocket logic
└── voice_handlers.py                  # Voice-specific WebSocket logic
```

## 🖥️ Static Assets (Web UI)

```
static/
├── index.html                         # Main web interface
├── realtime-voice.html                # Voice interface
├── voice-test.html                    # Voice testing interface
├── css/
│   └── styles.css                     # UI styling
└── js/
    └── client.js                      # Frontend JavaScript
```

## 🐳 Containerization & Deployment

```
├── docker-compose.yaml                # Local development services
├── docker/                           # Custom Docker configurations
│   └── vllm/                         # vLLM container configs (legacy)
└── render.yaml                       # Cloud deployment config (future)
```

## 📚 Documentation Deep Dive

```
docs/
├── Hybrid AI Council_ Architectural Blueprint v3.8 (Final).md    # System architecture
├── Unified Implementation Plan v2.3 (Final).md                  # Development roadmap
├── dev-log-Hybrid-AI-Council.md                                 # Detailed development log
├── KIP_AUTONOMOUS_AGENTS_EXPLAINED.md                           # KIP layer explanation
├── AUTONOMOUS_TRADING_SYSTEM.md                                 # Trading agent business model
├── TigerGraph_Community_Edition_Setup.md                        # Database setup guide
├── CODE_PATTERNS.md                      # ✅ Standard patterns & conventions
├── INTEGRATION_MAP.md                    # ✅ Component interaction flows
├── DEBUGGING_GUIDE.md                    # ✅ Project-specific troubleshooting
├── FEATURE_FLAGS.md                      # ✅ Runtime configuration toggles
├── errors/                               # ✅ Error code documentation
│   ├── REDIS_001.md                      # Redis connection failures
│   ├── TG_002.md                         # TigerGraph schema issues
│   └── template.md                       # Error documentation template
└── templates/                            # ✅ Development templates
    ├── new_endpoint.py                   # API endpoint template
    ├── test_template.py                  # Test file template
    ├── kip_agent_template.py             # KIP agent template
    └── orchestrator_node_template.py     # Orchestrator node template
```

## 🔍 External Dependencies (Not in Repository)

```
kyutai-tts/                           # External TTS model (gitignored)
.cursor-logs/                         # Cursor chat history (gitignored)
.env                                  # Environment variables (gitignored)
```

---

## 📝 **Recently Modified** (Active Development Session)

> **Last Updated**: August 4, 2025  
> **Status**: Multi-model AI Council fully operational, 5/5 system verification PASS

| File | Action | Reason | Session |
|------|--------|---------|---------|
| `MULTI_MODEL_TEST_GUIDE.md` | ✅ Created | Complete guide for testing multi-model orchestration across cognitive layers | Current |
| `docs/MIDDLEWARE_FIX_DOCUMENTATION.md` | ✅ Created | Detailed fix for rate limiting middleware Redis timeout issues | Current |
| `middleware/rate_limiting.py` | 🔄 Updated | Added 50ms Redis timeout protection and graceful degradation | Current |
| `main.py` | 🔄 Updated | Re-enabled all security middleware with timeout fixes | Current |
| `endpoints/chat.py` | 🔄 Updated | Cleaned up debug logging, simplified orchestrator access | Current |
| `verify_system.py` | 🔄 Updated | Fixed LLM client calls, orchestrator state attributes, and API guidance | Previous |
| `All Verification Issues` | ✅ Fixed | Core system verification now working (5/5 components PASS) | Previous |
| `scripts/check_financial_status.py` | 🔄 Updated | Fixed EconomicAnalytics attribute names and added more metrics | Previous |
| `Makefile` | 🔄 Updated | Fixed Redis container name and simplified financial status script | Previous |
| `docs/CODE_PATTERNS.md` | ✅ Created | Standard patterns, conventions & best practices | Current |
| `docs/INTEGRATION_MAP.md` | ✅ Created | Component interaction flows & system architecture | Current |
| `docs/DEBUGGING_GUIDE.md` | ✅ Created | Project-specific troubleshooting & solutions | Current |
| `Makefile` | ✅ Created | One-command operations (dev-setup, test-all, verify) | Current |
| `decisions/003-why-smart-router-architecture.md` | ✅ Created | Smart router architecture decision record | Current |
| `decisions/002-why-tigergraph-over-postgres.md` | ✅ Created | TigerGraph database choice decision record | Current |
| `decisions/001-why-ollama-over-vllm.md` | ✅ Created | Ollama vs vLLM model serving decision record | Current |
| `decisions/template.md` | ✅ Created | Standard template for future architecture decisions | Current |
| `CURRENT_ISSUES.md` | ✅ Created | Active priorities & blockers tracking system | Current |
| `PROJECT_STRUCTURE.md` | 🔄 Updated | Added system improvement documentation structure | Current |
| `System Improvements Plan` | ✅ Created | ADRs, debugging guides, patterns, templates planned | Current |
| `TODO System` | ✅ Created | Financial safeguards and risk management task tracking | Current |
| `.cursorrules` | 🔄 Updated | Added mandatory PROJECT_STRUCTURE.md maintenance rule | Current |
| `PROJECT_STRUCTURE.md` | ✅ Created | Living documentation for file structure visibility | Current |
| `.vscode/settings.json` | ✅ Created | Force Git Bash as default terminal | Current |
| `CURSOR_BASH_SETUP.md` | 🔄 Updated | Enhanced troubleshooting for terminal issues | Current |
| `find_git_bash.ps1` | ✅ Created | PowerShell script to locate Git Bash path | Current |
| `quick_db_check.py` | ✅ Created | Database inspection utility | Previous |
| `SYSTEM_VERIFICATION_GUIDE.md` | 🔄 Updated | Converted PowerShell → Bash commands | Previous |
| `tests/test_production_readiness.py` | ✅ Created | 6th critical test suite (load testing) | Previous |

**Legend**: ✅ Created | 🔄 Updated | ❌ Removed | 🔧 Refactored

---

## 🎯 **Update Protocol**

**When adding files:**
1. Update this document FIRST
2. Add brief description of file purpose
3. Note any dependencies or relationships

**When removing files:**
1. Remove from this document
2. Note reason for removal in commit message

**File Size Monitoring:**
- Keep ALL files under 500 lines (enforced)
- Run `python scripts/check-file-sizes.py` regularly

---

## 🏆 **Current Status: Multi-Model AI Council Fully Operational**

✅ **5/5 System Verification** (All components PASS)  
✅ **Multi-Model Orchestration**: Qwen3 + DeepSeek + Mistral working together  
✅ **Production-ready architecture** with full security middleware  
✅ **Complete documentation** + fix documentation  
✅ **Enterprise-grade code quality** with timeout protection

**Evidence**: Live production logs show all 3 models processing complex questions concurrently  
**Performance**: Simple queries 1-2s (Mistral), Complex analysis 45-60s (All 3 models)  
**Security**: CORS, headers, validation, rate limiting all operational  

**Next Phase:** Cloud hybrid deployment for distributed cognitive processing