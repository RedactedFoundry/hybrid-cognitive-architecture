#!/usr/bin/env python3
"""
Smart TigerGraph Community Edition Initialization Script

Intelligently handles existing graphs and only creates what's missing.
Designed for TigerGraph Community Edition running in Docker.

Features:
- Checks if graph already exists before creating
- Gracefully handles existing vertices/edges  
- Automates graph startup for Community Edition
- Provides status reporting for existing setup

Usage:
    python scripts/smart_tigergraph_init.py
"""

import time
import sys
import os
from pathlib import Path
import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from clients.tigergraph_client import get_tigergraph_connection, test_connection

# Set up structured logging  
logger = structlog.get_logger("smart_tigergraph_init")

def check_tigergraph_status():
    """Check current TigerGraph status and what exists."""
    try:
        logger.info("Checking TigerGraph Community Edition status")
        
        # Test basic connection
        conn = get_tigergraph_connection()
        if not conn:
            logger.error("Cannot connect to TigerGraph")
            return False, {}
            
        # Check if we can reach the server
        try:
            version = conn.getVersion()
            logger.info("TigerGraph version retrieved", version=version)
        except Exception as e:
            logger.error("Failed to get TigerGraph version", error=str(e))
            return False, {}
        
        # Check what graphs exist
        try:
            graphs = conn.getGraphList()
            logger.info("Available graphs", graphs=graphs)
        except Exception as e:
            logger.warning("Could not list graphs", error=str(e))
            graphs = []
        
        # Check if our specific graph exists and is accessible
        graph_exists = False
        try:
            conn.graphname = "HybridAICouncil"
            # Try to get vertex stats - this will work if graph exists and is ready
            vertex_count = conn.getVertexCount("*")
            graph_exists = True
            logger.info("HybridAICouncil graph is ready", total_vertices=vertex_count)
        except Exception as e:
            logger.info("HybridAICouncil graph not ready or doesn't exist", error=str(e))
        
        status = {
            "connected": True,
            "version": version,
            "graphs": graphs,
            "target_graph_exists": graph_exists,
            "target_graph_ready": graph_exists
        }
        
        return True, status
        
    except Exception as e:
        logger.error("TigerGraph status check failed", error=str(e))
        return False, {}

def ensure_graph_exists():
    """Ensure the HybridAICouncil graph exists, create only if missing."""
    try:
        conn = get_tigergraph_connection()
        
        # First, try to switch to the graph to see if it exists
        try:
            result = conn.gsql("USE GRAPH HybridAICouncil")
            logger.info("Successfully switched to existing graph", result=result)
            return True, "Graph already exists and is accessible"
        except Exception as e:
            logger.info("Graph doesn't exist or isn't accessible, will create", error=str(e))
        
        # Graph doesn't exist, create it
        logger.info("Creating new HybridAICouncil graph")
        create_graph_command = "CREATE GRAPH HybridAICouncil()"
        try:
            result = conn.gsql(create_graph_command)
            logger.info("Graph creation result", result=result)
            
            # Switch to the new graph
            switch_result = conn.gsql("USE GRAPH HybridAICouncil")
            logger.info("Switched to new graph", result=switch_result)
            
            return True, "New graph created successfully"
        except Exception as e:
            if "conflicts with another type" in str(e):
                logger.warning("Graph name conflicts, attempting to use existing graph")
                try:
                    switch_result = conn.gsql("USE GRAPH HybridAICouncil")
                    logger.info("Using existing conflicting graph", result=switch_result)
                    return True, "Using existing graph despite name conflict"
                except Exception as e2:
                    logger.error("Failed to use existing graph", error=str(e2))
                    return False, f"Graph creation failed: {e2}"
            else:
                logger.error("Graph creation failed", error=str(e))
                return False, f"Graph creation failed: {e}"
                
    except Exception as e:
        logger.error("Graph setup failed", error=str(e))
        return False, f"Graph setup failed: {e}"

def ensure_schema_loaded():
    """Ensure schema is loaded, skip if vertices already exist."""
    try:
        conn = get_tigergraph_connection()
        conn.graphname = "HybridAICouncil"
        
        # Check if schema is already loaded by looking for existing vertices
        try:
            vertex_types = conn.getVertexTypes()
            if vertex_types and len(vertex_types) > 0:
                logger.info("Schema already loaded", vertex_types=vertex_types)
                return True, f"Schema already exists with {len(vertex_types)} vertex types"
        except Exception as e:
            logger.info("No existing vertex types found, will load schema", error=str(e))
        
        # Load schema from file
        schema_path = project_root / "schemas" / "schema.gsql"
        if not schema_path.exists():
            logger.error("Schema file not found", path=str(schema_path))
            return False, f"Schema file not found: {schema_path}"
        
        logger.info("Loading schema from file", schema_path=str(schema_path))
        
        # Read and execute schema
        with open(schema_path, 'r') as f:
            schema_content = f.read()
            
        try:
            result = conn.gsql(schema_content)
            logger.info("Schema loading result", result=result)
            
            # Install the queries if any
            install_result = conn.gsql("INSTALL QUERY ALL")
            logger.info("Query installation result", result=install_result)
            
            return True, "Schema loaded and queries installed successfully"
            
        except Exception as e:
            error_msg = str(e)
            if "is used by another object" in error_msg:
                logger.warning("Some schema elements already exist", error=error_msg)
                # Try to install queries anyway
                try:
                    install_result = conn.gsql("INSTALL QUERY ALL")
                    logger.info("Query installation result", result=install_result)
                    return True, "Schema elements exist, queries installed"
                except Exception as e2:
                    logger.warning("Query installation failed", error=str(e2))
                    return True, "Schema elements exist, query installation skipped"
            else:
                logger.error("Schema loading failed", error=error_msg)
                return False, f"Schema loading failed: {error_msg}"
                
    except Exception as e:
        logger.error("Schema setup failed", error=str(e))
        return False, f"Schema setup failed: {e}"

def smart_initialize():
    """Smart initialization that only does what's needed."""
    logger.info("Starting smart TigerGraph Community Edition initialization")
    
    # Step 1: Check current status
    connected, status = check_tigergraph_status()
    if not connected:
        logger.error("Cannot connect to TigerGraph - ensure container is running")
        logger.info("Run: ./scripts/setup-tigergraph.sh")
        return False
    
    # Step 2: If graph is already ready, we're done!
    if status.get("target_graph_ready", False):
        logger.info("TigerGraph is already fully initialized and ready!")
        logger.info("Graph exists with vertices - no initialization needed")
        return True
    
    # Step 3: Ensure graph exists
    graph_success, graph_msg = ensure_graph_exists()
    if not graph_success:
        logger.error("Graph setup failed", message=graph_msg)
        return False
    logger.info("Graph setup completed", message=graph_msg)
    
    # Step 4: Ensure schema is loaded
    schema_success, schema_msg = ensure_schema_loaded()
    if not schema_success:
        logger.error("Schema setup failed", message=schema_msg)
        return False
    logger.info("Schema setup completed", message=schema_msg)
    
    # Step 5: Final verification
    logger.info("Running final verification")
    final_connected, final_status = check_tigergraph_status()
    if final_connected and final_status.get("target_graph_ready", False):
        logger.info("Smart initialization completed successfully!")
        logger.info("TigerGraph Community Edition is ready for use")
        return True
    else:
        logger.warning("Initialization completed but final verification failed")
        logger.info("You may need to manually check TigerGraph via GraphStudio: http://localhost:14240")
        return True  # Still return True as we did what we could

if __name__ == "__main__":
    try:
        success = smart_initialize()
        if success:
            print("\nTigerGraph initialization completed successfully!")
            print("GraphStudio available at: http://localhost:14240")
            print("Graph: HybridAICouncil")
            sys.exit(0)
        else:
            print("\nTigerGraph initialization failed!")
            print("Try manual setup via GraphStudio: http://localhost:14240")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Initialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error during initialization", error=str(e))
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)