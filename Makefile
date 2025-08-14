# Hybrid AI Council - Development Makefile
# One-command operations for streamlined development

.PHONY: help dev-setup test-all verify reset-db clean status health backup

# Default target
help:
	@echo "🎯 Hybrid AI Council - Development Commands"
	@echo ""
	@echo "📋 Development Setup:"
	@echo "  make dev-setup    - Complete development environment setup"
	@echo "  make deps         - Install Python dependencies"
	@echo "  make services     - Start all required services"
	@echo ""
	@echo "🧪 Testing & Verification:"
	@echo "  make test-all     - Run complete test suite with coverage"
	@echo "  make test-quick   - Run fast tests only"
	@echo "  make verify       - Full system verification"
	@echo "  make lint         - Code quality checks"
	@echo ""
	@echo "🗄️  Database Operations:"
	@echo "  make reset-db     - Clean database restart"
	@echo "  make init-db      - Initialize TigerGraph schema"
	@echo "  make backup       - Backup agent genomes and data"
	@echo ""
	@echo "🔍 Monitoring & Health:"
	@echo "  make health       - Check all service health"
	@echo "  make status       - Show system status"
	@echo "  make logs         - Tail service logs"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean        - Remove temporary files"
	@echo "  make clean-all    - Reset everything (nuclear option)"

# Development Setup
dev-setup: deps services init-db
	@echo "✅ Development environment ready!"
	@echo "🚀 Run 'make verify' to test everything works"

# 🚀 MASTER STARTUP - ONE COMMAND FOR EVERYTHING  
start-all:
	@echo "🚀 Starting complete Hybrid AI Council system..."
	@echo "   (comprehensive startup with auto-dependencies)"
	python start_all.py

quick-start:
	@echo "⚡ Quick start..."
	@echo "   (same as start-all - comprehensive startup)"
	python start_all.py

deps:
	@echo "📦 Installing Python dependencies..."
	poetry install

services:
	@echo "🐳 Starting services..."
	./scripts/setup-tigergraph.sh
	docker-compose up -d redis

init-db:
	@echo "🗄️ Initializing TigerGraph database..."
	sleep 10  # Wait for TigerGraph to be ready
	python scripts/smart_tigergraph_init.py

# Testing & Verification
test-all:
	@echo "🧪 Running complete test suite..."
	pytest -v --cov=. --cov-report=term-missing --cov-report=html
	@echo "📊 Coverage report generated in htmlcov/"

test-quick:
	@echo "⚡ Running fast tests..."
	pytest -v -m "not slow"

verify:
	@echo "🔍 Running full system verification..."
	python verify_system.py
	@echo "📋 Check SYSTEM_VERIFICATION_GUIDE.md for manual verification steps"

lint:
	@echo "✨ Running code quality checks..."
	ruff check .
	black --check .
	mypy . --ignore-missing-imports

# Database Operations  
reset-db:
	@echo "🔄 Resetting databases..."
	docker stop tigergraph || true
	docker rm -f tigergraph || true
	docker-compose down -v
	@echo "🚀 Starting fresh..."
	$(MAKE) services
	$(MAKE) init-db

backup:
	@echo "💾 Creating backup..."
	mkdir -p backups
	python quick_db_check.py > backups/backup_$(shell date +%Y%m%d_%H%M%S).txt
	@echo "✅ Backup created in backups/"

# Monitoring & Health
health:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "🔴 Redis:"
	@docker exec hybrid-cognitive-architecture-redis-1 redis-cli ping || echo "❌ Redis not responding"
	@echo ""
	@echo "🟢 TigerGraph:"
	@curl -s http://localhost:14240/api/ping || echo "❌ TigerGraph not responding"
	@echo ""
	@echo "🟣 llama.cpp HuiHui:"
	@curl -s http://127.0.0.1:8081/health || echo "❌ llama.cpp HuiHui not responding"
	@echo "🟣 llama.cpp Mistral:"
	@curl -s http://127.0.0.1:8082/health || echo "❌ llama.cpp Mistral not responding"

status:
	@echo "📊 System Status:"
	@echo ""
	@echo "🐳 Docker Containers:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "💰 Financial Status:"
	@python scripts/check_financial_status.py

logs:
	@echo "📜 Service Logs (Press Ctrl+C to exit):"
	docker-compose logs -f

# Cleanup
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

clean-all: clean
	@echo "💥 Nuclear cleanup - resetting everything..."
	docker-compose down -v
	docker stop tigergraph || true
	docker rm -f tigergraph || true
	docker system prune -f
	@echo "⚠️  Everything has been reset!"

# Development Helpers
format:
	@echo "✨ Formatting code..."
	black .
	ruff --fix .

install-hooks:
	@echo "🪝 Installing pre-commit hooks..."
	pre-commit install

models:
	@echo "🤖 Preparing required models (llama.cpp)"
	@echo "   - Set LLAMACPP_MODEL_DIR to your GGUF directory"
	@echo "   - LLAMACPP_PORT_HUIHUI / LLAMACPP_PORT_MISTRAL to set ports"
	@echo "   - Start servers: python scripts/start_llamacpp_servers.py"

# Quick Development Workflow
dev: clean services test-quick
	@echo "🚀 Quick development cycle complete!"

# Production Preparation
prod-ready: clean deps test-all lint verify
	@echo "✅ Production readiness checks complete!"
	@echo "📋 Manual checklist:"
	@echo "   - Review .env file security"
	@echo "   - Verify backup system"
	@echo "   - Check financial safeguards"
	@echo "   - Test emergency freeze"