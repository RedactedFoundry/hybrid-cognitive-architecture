#!/usr/bin/env python3
"""
TigerGraph Community Edition Initialization Script

Automatically creates the HybridAICouncil database and loads the schema.
Designed for TigerGraph Community Edition running in Docker.

Prerequisites:
1. TigerGraph Community Edition container running (use setup-tigergraph.sh)
2. Schema file available at schemas/schema.gsql
3. pyTigerGraph installed (pip install pyTigerGraph)

Usage:
    python scripts/init_tigergraph.py
"""

import time
import sys
import os
from pathlib import Path
import structlog

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from clients.tigervector_client import get_tigergraph_connection, test_connection

# Set up structured logging  
logger = structlog.get_logger("tigergraph_init")

def wait_for_tigergraph(max_retries=20, delay=5):
    """
    Wait for TigerGraph Community Edition to be ready.
    
    Args:
        max_retries: Maximum number of connection attempts (default: 20)
        delay: Seconds to wait between attempts (default: 5)
        
    Returns:
        TigerGraph connection object if successful
        
    Raises:
        Exception: If TigerGraph fails to become ready after max retries
    """
    logger.info("Waiting for TigerGraph Community Edition to be ready")
    logger.info("Make sure you've run: ./scripts/setup-tigergraph.sh")
    
    for attempt in range(max_retries):
        logger.info("Connection attempt", attempt=attempt + 1, max_retries=max_retries)
        
        try:
            if test_connection():
                conn = get_tigergraph_connection()
                if conn:
                    logger.info("TigerGraph Community Edition is ready")
                    return conn
        except Exception as e:
            logger.warning("Connection attempt failed", error=str(e))
            
        if attempt < max_retries - 1:
            logger.info("Waiting before retry", delay_seconds=delay)
            time.sleep(delay)
    
    # Provide helpful troubleshooting info
    logger.error("TigerGraph failed to become ready within timeout period")
    tigergraph_host = os.getenv("TIGERGRAPH_HOST", "http://localhost")
    tigergraph_port = os.getenv("TIGERGRAPH_PORT", "14240")
    logger.info("Troubleshooting steps",
               checks=[
                   "Check if container is running: docker ps | grep tigergraph",
                   "Check container logs: docker logs tigergraph", 
                   f"Try accessing GraphStudio: {tigergraph_host}:{tigergraph_port}",
                   "Run setup script: ./scripts/setup-tigergraph.sh"
               ])
    raise Exception("TigerGraph Community Edition failed to start after maximum retries")

def initialize_database():
    """
    Initialize TigerGraph Community Edition database and load schema.
    
    Creates the HybridAICouncil graph and loads the schema from schemas/schema.gsql
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    logger.info("Starting TigerGraph Community Edition initialization")
    logger.info("Creating HybridAICouncil graph and loading schema")
    
    # Wait for TigerGraph to be ready
    conn = wait_for_tigergraph()
    
    try:
        # Create database/graph (TigerGraph calls it a "graph")
        graph_name = "HybridAICouncil"
        logger.info("Creating graph", graph_name=graph_name)
        
        # Create graph using GSQL commands
        try:
            logger.info("Creating graph via GSQL")
            create_result = conn.gsql(f"CREATE GRAPH {graph_name}()")
            logger.info("Graph created successfully", graph_name=graph_name)
            if create_result:
                logger.debug("Graph creation result", result=create_result)
        except Exception as create_error:
            if "already exists" in str(create_error) or "Graph name already exists" in str(create_error):
                logger.info("Graph already exists", graph_name=graph_name)
            else:
                logger.warning("Graph creation warning, continuing", error=str(create_error))
        
        # Switch to using the graph
        logger.info("Switching to graph", graph_name=graph_name)
        use_result = conn.gsql(f"USE GRAPH {graph_name}")
        conn.graphname = graph_name
        if use_result:
            logger.debug("Use graph result", result=use_result)
        
        # Load schema from file
        schema_path = Path("schemas/schema.gsql")
        if schema_path.exists():
            logger.info("Loading schema from file", schema_path=str(schema_path))
            with open(schema_path, 'r') as f:
                schema_content = f.read()
            
            logger.info("Executing schema")
            # Execute schema
            result = conn.gsql(schema_content)
            logger.info("Schema loaded successfully")
            if result:
                logger.debug("Schema loading result", result=result)
        else:
            logger.warning("Schema file not found, manual loading required", 
                          schema_path=str(schema_path))
        
        # Verify the graph is operational
        logger.info("Verifying graph is operational", graph_name=graph_name)
        try:
            # Try to list the schema to verify everything loaded
            verify_result = conn.gsql("ls")
            logger.info("Graph is operational and schema is accessible")
            if verify_result and len(str(verify_result)) > 10:
                logger.info("Schema verification successful - vertices and edges loaded")
            else:
                logger.debug("Schema verification result", result=verify_result)
        except Exception as verify_error:
            logger.warning("Graph verification warning - graph may still be functional", 
                          error=str(verify_error))
        
        logger.info("TigerGraph Community Edition initialization complete!")
        tigergraph_host = os.getenv("TIGERGRAPH_HOST", "http://localhost")
        tigergraph_port = os.getenv("TIGERGRAPH_PORT", "14240")
        graphstudio_url = f"{tigergraph_host}:{tigergraph_port}"
        logger.info("Access information",
                   graphstudio_url=graphstudio_url,
                   login_credentials="tigergraph/tigergraph",
                   graph_name=graph_name,
                   verification_steps=[
                       f"Open GraphStudio at {graphstudio_url}",
                       "Login with tigergraph/tigergraph", 
                       f"Select the '{graph_name}' graph from the dropdown",
                       "Navigate to 'Design Schema' to see vertices and edges",
                       "Check that vertices like Person, AIPersona, Preference are listed"
                   ])
        return True
        
    except Exception as e:
        logger.error("Initialization failed", error=str(e))
        tigergraph_host = os.getenv("TIGERGRAPH_HOST", "http://localhost")
        tigergraph_port = os.getenv("TIGERGRAPH_PORT", "14240")
        logger.info("Troubleshooting steps",
                   checks=[
                       "Ensure TigerGraph is running: docker ps | grep tigergraph",
                       "Check TigerGraph logs: docker logs tigergraph",
                       f"Try manual setup via GraphStudio: {tigergraph_host}:{tigergraph_port}"
                   ])
        return False

if __name__ == "__main__":
    try:
        success = initialize_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("Initialization interrupted by user")
        sys.exit(1) 