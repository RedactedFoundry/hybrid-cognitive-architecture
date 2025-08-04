# Git Changes Breakdown - What to Keep vs Revert

## ✅ CHANGES TO KEEP (Commit These)

### File Organization & Cleanup
```bash
# New directories created
archive/                          # Contains old handoff files
docs/ENVIRONMENT_VARIABLES.md    # Moved from root
docs/SECURITY.md                 # Moved from root  
docs/SYSTEM_PERFECTION_ROADMAP.md # Moved from root
docs/SYSTEM_VERIFICATION_GUIDE.md # Moved from root
tests/run_tests.py               # Moved from root
tests/test_setup.py              # Moved from scripts/
tests/voice_foundation/          # Voice tests organized
websockets/                      # Renamed from websocket_handlers/

# Files deleted (moved to archive/ or organized)
CHAT_SESSION_HANDOFF.md          # → archive/
CODE_CLEANUP_AUDIT.md            # → archive/
REFACTORING_HANDOFF_V2.md        # → archive/
SMART_ROUTER_HANDOFF.md          # → archive/
code_audit_progress.md           # → archive/
websocket_handlers/              # → websockets/
```

### New Scripts & Automation
```bash
scripts/smart_tigergraph_init.py     # Idempotent TigerGraph setup
scripts/start_tigergraph_safe.py     # Safe TigerGraph container startup
scripts/start_everything.py         # Master system startup script
scripts/README.md                   # Updated documentation
```

### Updated Files (Keep These Changes)
```bash
Makefile                        # New startup targets
PROJECT_STRUCTURE.md            # Updated file organization
endpoints/chat.py               # Import path fix (websocket_handlers → websockets)
endpoints/voice.py              # Import path fix (websocket_handlers → websockets)  
websockets/handlers.py          # Import path fix (websocket_handlers → websockets)
tests/test_websocket_streaming.py # Import path fix (websocket_handlers → websockets)
```

### Documentation Files
```bash
STARTUP_COMMAND_GUIDE.md        # New startup documentation
TIGERGRAPH_SOLUTION_SUMMARY.md  # TigerGraph initialization guide
```

## ❌ CHANGES TO REVERT (Don't Commit These)

### Poetry/Package Changes (REVERT)
```bash
poetry.lock     # Reverted websockets 10.4 → 11.0.2, uvicorn 0.24.0.post1 → 0.24.0
pyproject.toml  # Reverted dependency version constraints
```

### Problematic Script Changes (REVERT)
```bash
# In scripts/start_everything.py - REVERT this specific change:
# Line ~355-365: Remove "--ws none" flag addition
# Keep: WebSocket support enabled (don't disable it)
```

## 🔧 MANUAL GIT COMMANDS TO EXECUTE

1. **Stage only the good changes:**
```bash
# Add all new files and directories
git add archive/ docs/ tests/run_tests.py tests/test_setup.py tests/voice_foundation/ websockets/
git add scripts/smart_tigergraph_init.py scripts/start_tigergraph_safe.py scripts/start_everything.py
git add STARTUP_COMMAND_GUIDE.md TIGERGRAPH_SOLUTION_SUMMARY.md

# Add updated files (but not poetry files)
git add Makefile PROJECT_STRUCTURE.md scripts/README.md
git add endpoints/chat.py endpoints/voice.py websockets/handlers.py tests/test_websocket_streaming.py

# Add deletions/moves
git add -u  # This stages deletions
```

2. **Explicitly exclude problematic files:**
```bash
git reset HEAD poetry.lock pyproject.toml
```

3. **Commit the good stuff:**
```bash
git commit -m "feat: Complete codebase organization and startup automation

- Organized files into archive/ and docs/ directories  
- Created smart TigerGraph initialization (idempotent)
- Added master startup script (start_everything.py)
- Updated Makefile with new startup commands
- Renamed websocket_handlers/ to websockets/ for consistency
- Updated all import paths for directory rename
- Moved test files to proper tests/ structure
- Added comprehensive documentation

All core functionality preserved, WebSocket support intact"
```

4. **Revert the problematic poetry changes:**
```bash
git checkout HEAD -- poetry.lock pyproject.toml
```

## 🚨 ISSUE TO FIX AFTER COMMIT

The WebSocket issue is likely due to Python 3.13 compatibility with uvicorn's websockets.legacy import. 
Need to investigate this separately WITHOUT changing package versions randomly.

Original error: `ModuleNotFoundError: No module named 'websockets.legacy'`
Location: `uvicorn.protocols.websockets.websockets_impl.py`

## ✅ VERIFICATION STEPS

After git operations:
1. Verify `python scripts/start_everything.py` works for Docker/TigerGraph/Redis/Ollama
2. Investigate WebSocket issue systematically  
3. Test UI connectivity at `http://localhost:8000/static/index.html`