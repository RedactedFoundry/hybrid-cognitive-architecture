# TigerGraph Community Edition Setup Guide

## Overview

The Hybrid AI Council project uses **TigerGraph Community Edition** for its knowledge graph and vector database needs. This guide provides step-by-step instructions for setting up TigerGraph Community Edition in your development environment.

## Why Community Edition?

- ✅ **License-free**: No enterprise licensing required
- ✅ **Full-featured**: All core TigerGraph functionality
- ✅ **Development-ready**: Perfect for local development and testing
- ✅ **Simple setup**: Automated installation scripts
- ✅ **200GB data limit**: More than sufficient for development use

## Prerequisites

1. **Docker Desktop** installed and running
2. **2.4GB free disk space** for the TigerGraph image
3. **8GB+ RAM recommended** (4GB minimum)
4. **Internet connection** for initial download

## Quick Start

### Option 1: Automated Setup (Recommended)

**Linux/Mac:**
```bash
./scripts/setup-tigergraph.sh
```

**Windows:**
```powershell
.\scripts\setup-tigergraph.ps1
```

### Option 2: Manual Setup

1. **Download Community Edition**
   - Visit: https://dl.tigergraph.com/
   - Download: `tigergraph-4.2.0-community-docker-image.tar.gz`
   - Place in project root directory

2. **Load and Run**
   ```bash
   # Load image
   docker load -i tigergraph-4.2.0-community-docker-image.tar.gz
   
   # Run container
   docker run -d --init --name tigergraph -p 14240:14240 tigergraph/community:4.2.0
   ```

3. **Initialize Database**
   ```bash
   python scripts/init_tigergraph.py
   ```

## Access Points

After successful setup:

- **GraphStudio UI**: http://localhost:14240
- **REST API**: http://localhost:14240/restpp
- **Default Credentials**: `tigergraph` / `tigergraph`

## Project Integration

### Client Configuration

The project automatically connects to TigerGraph Community Edition:

```python
from clients.tigervector_client import get_tigergraph_connection

# Connects to localhost:14240 with default credentials
conn = get_tigergraph_connection("HybridAICouncil")
```

### Environment Variables (Optional)

Override defaults if needed:

```bash
export TIGERGRAPH_HOST="http://localhost"
export TIGERGRAPH_PORT="14240"
export TIGERGRAPH_USERNAME="tigergraph"
export TIGERGRAPH_PASSWORD="tigergraph"
```

## Docker Compose Integration

**Important**: TigerGraph Community Edition is **not included** in `docker-compose.yaml` because:

1. The Community Edition image is not available on Docker Hub
2. It requires manual download and loading
3. The automated setup scripts handle this process

Other services (Redis) use docker-compose normally:

```bash
# Start other services
docker-compose up -d redis

# TigerGraph runs separately via setup scripts
./scripts/setup-tigergraph.sh
```

## Management Commands

### Container Management
```bash
# Check status
docker ps | grep tigergraph

# View logs
docker logs tigergraph

# Stop container
docker stop tigergraph

# Start container
docker start tigergraph

# Remove container
docker rm -f tigergraph
```

### TigerGraph Services

Access the container shell:
```bash
docker exec -it tigergraph bash
```

Inside the container:
```bash
# Check service status
gadmin status

# Start all services
gadmin start all

# Stop all services
gadmin stop all

# Access GSQL shell
gsql
```

## Database Schema Management

### Initial Schema Loading

The initialization script automatically loads `schemas/schema.gsql`:

```bash
python scripts/init_tigergraph.py
```

### Manual Schema Management

Via GraphStudio:
1. Open http://localhost:14240
2. Login with `tigergraph`/`tigergraph`
3. Navigate to "Design Schema"
4. Import or create your schema

Via GSQL command line:
```bash
docker exec -it tigergraph bash
gsql
GSQL> USE GRAPH HybridAICouncil
GSQL> @/home/tigergraph/schemas/schema.gsql
```

## Troubleshooting

### Container Won't Start

1. **Check Docker status**:
   ```bash
   docker info
   ```

2. **Check port conflicts**:
   ```bash
   lsof -i :14240  # Mac/Linux
   netstat -ano | findstr :14240  # Windows
   ```

3. **Check image exists**:
   ```bash
   docker images | grep community
   ```

### Connection Issues

1. **Verify container is running**:
   ```bash
   docker ps | grep tigergraph
   ```

2. **Check logs**:
   ```bash
   docker logs tigergraph
   ```

3. **Test client connection**:
   ```bash
   python -c "from clients.tigervector_client import test_connection; test_connection()"
   ```

### Performance Issues

1. **Increase Docker resources**:
   - Docker Desktop → Settings → Resources
   - Recommended: 8GB RAM, 4+ CPUs

2. **Check available space**:
   ```bash
   docker system df
   ```

3. **Clean up unused Docker data**:
   ```bash
   docker system prune -a
   ```

### Schema Loading Issues

1. **Check schema file exists**:
   ```bash
   ls -la schemas/schema.gsql
   ```

2. **Validate schema syntax**:
   ```bash
   # Access GSQL shell and test commands manually
   docker exec -it tigergraph gsql
   ```

3. **Reset database**:
   ```bash
   # Remove container and start fresh
   docker rm -f tigergraph
   ./scripts/setup-tigergraph.sh
   ```

## Development Workflow

### Typical Development Cycle

1. **Start TigerGraph** (once per development session):
   ```bash
   ./scripts/setup-tigergraph.sh
   ```

2. **Start other services**:
   ```bash
   docker-compose up -d redis
   ```

3. **Initialize database** (first time only):
   ```bash
   python scripts/init_tigergraph.py
   ```

4. **Develop and test** your application

5. **Stop services when done**:
   ```bash
   docker-compose down
   docker stop tigergraph
   ```

### Schema Development

1. **Edit schema**: Modify `schemas/schema.gsql`
2. **Reload schema**: Run `python scripts/init_tigergraph.py`
3. **Test changes**: Use GraphStudio or Python client

### Data Persistence

- **Container data**: Persists across container stops/starts
- **Complete reset**: Remove container with `docker rm -f tigergraph`
- **Backup**: Use TigerGraph's built-in backup features

## Integration with Other Services

### Redis (Session Storage)
- **Connection**: `redis://localhost:6379`
- **Purpose**: Pheromind ephemeral data (12s TTL)

### Ollama (Local AI Models)
- **Connection**: `http://localhost:11434`
- **Purpose**: Local AI model inference

### TigerGraph (Knowledge Persistence)
- **Connection**: `http://localhost:14240`
- **Purpose**: Long-term knowledge graph storage

## Production Considerations

For production deployment:

1. **Use Enterprise Edition** with proper licensing
2. **Configure persistent volumes** for data retention
3. **Set up backup/restore** procedures
4. **Implement monitoring** and alerting
5. **Secure credentials** and network access

## Support and Resources

- **TigerGraph Documentation**: https://docs.tigergraph.com/
- **Community Forum**: https://community.tigergraph.com/
- **Project Issues**: Check GitHub issues for known problems
- **GraphStudio Guide**: Built-in tutorials in GraphStudio UI

## Version Information

- **TigerGraph Version**: 4.2.0 Community Edition
- **pyTigerGraph**: 1.9.0+
- **Docker Image**: `tigergraph/community:4.2.0`
- **Download Size**: 2.4GB
- **Memory Usage**: ~2-4GB RAM when running 