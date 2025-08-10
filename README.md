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
   # SGLang runs via Python scripts (not Docker)
   python scripts/start_sglang_multi.py
   ```

4. **Initialize database**:
   ```bash
   python scripts/init_tigergraph.py
   ```

5. **Access services**:
   - **TigerGraph GraphStudio**: http://localhost:14240 (tigergraph/tigergraph)
   - **SGLang Council**: http://localhost:5000-5002 (analytical/creative/coordinator)
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
- **Local AI Models**: SGLang with RTX 4090 support
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
./scripts/setup-tigergraph.sh && docker-compose up -d redis && python scripts/start_sglang_multi.py

# Option 2: Individual services  
docker-compose up -d redis                # Start Redis
./scripts/setup-tigergraph.sh             # Start TigerGraph separately
python scripts/start_sglang_multi.py      # Start SGLang council
```

### Common Tasks

```bash
# Test connections
python -c "from clients.tigervector_client import test_connection; test_connection()"
python -c "from clients.redis_client import get_redis_connection; print(get_redis_connection().ping())"

# View logs
docker logs tigergraph
docker-compose logs redis
# SGLang logs appear in the terminal where you ran start_sglang_multi.py

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
- **Production**: Enterprise Edition, cloud deployment

## 📚 Documentation

- **[TigerGraph Setup Guide](docs/TigerGraph_Community_Edition_Setup.md)**: Detailed TigerGraph Community Edition setup
- **[Architecture Blueprint](docs/Hybrid AI Council_ Architectural Blueprint v3.8 (Final).md)**: Complete system architecture
- **[Implementation Plan](docs/Unified Implementation Plan v2.3 (Final).md)**: Development roadmap

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
