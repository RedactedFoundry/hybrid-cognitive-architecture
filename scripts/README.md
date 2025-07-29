# Scripts Directory

This directory contains utility scripts for the Hybrid AI Council project.

## TigerGraph Initialization

### `init_tigergraph.py`

Automatically initializes TigerGraph with the proper database and schema.

**What it does:**
1. Waits for TigerGraph to be ready (up to 5 minutes)
2. Creates the `HybridAICouncil` graph database
3. Loads the schema from `schemas/schema.gsql`
4. Starts the graph for use

**Usage:**
```bash
# Start TigerGraph first
docker-compose up -d tigervector

# Wait for it to be healthy, then run initialization
python scripts/init_tigergraph.py
```

**Troubleshooting:**
- If the script fails, check `docker-compose logs tigervector`
- Ensure TigerGraph container is healthy: `docker-compose ps`
- The script is idempotent - safe to run multiple times 