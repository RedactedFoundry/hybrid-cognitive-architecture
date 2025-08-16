# Hybrid AI Council

An autonomous AI system with a three-layered cognitive architecture combining local and cloud intelligence.

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** installed and running
- **Python 3.11+** with pip
- **8GB+ RAM** recommended (4GB minimum)
- **25GB+ free disk space** (for models and databases)

### Setup

1. **Clone and setup Python environment**:
   ```bash
   git clone <repository-url>
   cd hybrid-cognitive-architecture
   pip install -e .
   ```

2. **Setup TigerGraph Community Edition**:
   ```bash
   # Linux/Mac
   ./scripts/setup-tigergraph.sh
   
   # Windows
   .\scripts\setup-tigergraph.ps1
   ```

3. **Start other services**:
   ```bash
   docker-compose up -d redis
   # Start llama.cpp servers (configure LLAMA_SERVER_BIN and PYTHONPATH for config)
   PYTHONPATH=.:./config LLAMA_SERVER_BIN="D:/llama.cpp/llama-server.exe" python scripts/start_llamacpp_servers.py
   ```

4. **Initialize database**:
   ```bash
   python scripts/init_tigergraph.py
   ```

5. **Access services**:
   - **TigerGraph GraphStudio**: http://localhost:14240 (tigergraph/tigergraph)
   - **llama.cpp servers**: http://localhost:8081 (HuiHui) and http://localhost:8082 (Mistral)
   - **Redis**: localhost:6379

## 🏗️ Architecture

### Three-Layer Cognitive System

1. **Pheromind Layer** - Ambient pattern recognition (Redis, 12s TTL)
2. **Council Layer** - Heavyweight reasoning (Local LLMs)  
3. **KIP Layer** - Knowledge persistence (TigerGraph)

### Technology Stack

- **Knowledge Graph**: TigerGraph Community Edition 4.2.0
- **Vector Database**: TigerGraph (hybrid graph+vector)
- **Session Storage**: Redis 8.0-alpine
- **Local AI Models**: llama.cpp (multi-instance) on RTX 4090
- **Backend**: FastAPI with WebSockets
- **Frontend**: Streamlit dashboard

## 📋 Services

| Service | Purpose | Port | Status |
|---------|---------|------|---------|
| TigerGraph | Knowledge persistence | 14240 | Community Edition |
| Redis | Ephemeral data (12s TTL) | 6379 | Docker Compose |
| SGLang Council | Local AI inference | 5000-5002 | Python Scripts |

## 🔧 Development

### Start Development Environment

```bash
# Option 1: All services
./scripts/setup-tigergraph.sh && docker-compose up -d redis && PYTHONPATH=.:./config LLAMA_SERVER_BIN="D:/llama.cpp/llama-server.exe" python scripts/start_llamacpp_servers.py

# Option 2: Individual services  
docker-compose up -d redis                # Start Redis
./scripts/setup-tigergraph.sh             # Start TigerGraph separately
PYTHONPATH=.:./config LLAMA_SERVER_BIN="D:/llama.cpp/llama-server.exe" python scripts/start_llamacpp_servers.py
```

### Common Tasks

```bash
# Test connections
python -c "from clients.tigergraph_client import test_connection; test_connection()"
python -c "from clients.redis_client import get_redis_connection; print(get_redis_connection().ping())"

# View logs
docker logs tigergraph
docker-compose logs redis
# llama.cpp logs appear in .logs/llamacpp_servers.log (see script output)

# Stop services
docker-compose down
docker stop tigergraph
```

## 📁 Project Structure

```
hybrid-cognitive-architecture/
├── clients/              # Database clients (TigerGraph, Redis)
├── core/                 # AI cognitive layers
├── schemas/              # TigerGraph schemas
├── scripts/              # Setup and utility scripts
├── docker/               # Custom Docker configurations
├── docs/                 # Project documentation
└── tests/                # Test suites
```

## 🔍 Important Notes

### TigerGraph Community Edition

- **Manual download required**: Not available on Docker Hub
- **License-free**: No enterprise licensing needed
- **200GB limit**: Sufficient for development
- **Setup scripts**: Automated installation provided

### Local AI Models

- **Model storage**: `./models/` directory (gitignored)
- **Runtime mounting**: Models mounted at container startup
- **GPU support**: Optimized for RTX 4090

### Development vs Production

- **Development**: Community Edition, local models
- **Production**: Hybrid cloud deployment on Fly.io with Tailscale

## 📚 Documentation

- **[TigerGraph Setup Guide](docs/TigerGraph_Community_Edition_Setup.md)**: Detailed TigerGraph Community Edition setup
- **[Architecture Blueprint](project-docs/Hybrid AI Council_ Architectural Blueprint v3.8 (Final).md)**: Complete system architecture (updated to Fly.io + llama.cpp)
- **[Implementation Plan v4.5](project-docs/Unified-Implementation-Plan-Final-v4.5.md)**: Current roadmap (supersedes v2.3)

## 🚨 Troubleshooting

### TigerGraph Issues
```bash
# Check container status
docker ps | grep tigergraph

# View logs
docker logs tigergraph

# Reset TigerGraph
docker rm -f tigergraph && ./scripts/setup-tigergraph.sh
```

### General Issues
```bash
# Check Docker resources
docker system df

# Clean up space
docker system prune -a

# Restart Docker Desktop
# (Use Docker Desktop UI)
```

## 🤝 Contributing

1. Follow the minimalist mentor approach
2. Prioritize simplicity and readability
3. Include tests for new functionality
4. Update documentation for changes

## 📄 License

See LICENSE file for details.
