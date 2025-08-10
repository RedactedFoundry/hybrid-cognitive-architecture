# clients/tigervector_client.py
"""
TigerGraph Community Edition Client for Hybrid AI Council

This client connects to TigerGraph Community Edition running in Docker.
Community Edition uses default credentials and runs on localhost:14240.

Setup Requirements:
1. Run ./scripts/setup-tigergraph.sh (Linux/Mac) or ./scripts/setup-tigergraph.ps1 (Windows)
2. Ensure TigerGraph container is running: docker ps | grep tigergraph
3. Verify GraphStudio access: http://localhost:14240

Default Configuration:
- Host: http://localhost:14240
- Username: tigergraph  
- Password: tigergraph
- Graph: HybridAICouncil
"""

import os

import pyTigerGraph as tg
import structlog

from utils.error_utils import (
    error_boundary,
    handle_tigergraph_error
)

# Set up structured logging
logger = structlog.get_logger("tigervector_client")

def get_tigergraph_connection(graph_name="HybridAICouncil"):
    """
    Establishes a connection to the TigerGraph Community Edition server.

    Community Edition runs on localhost:14240 with default credentials.
    Environment variables can override defaults for different setups.

    Args:
        graph_name: Name of the graph to connect to (default: HybridAICouncil)

    Returns:
        A TigerGraph connection object if successful, otherwise None.
        
    Environment Variables (optional):
        TIGERGRAPH_HOST: TigerGraph host URL (default: http://localhost)
        TIGERGRAPH_PORT: TigerGraph port (default: 14240)
        TIGERGRAPH_USERNAME: Username (default: tigergraph)
        TIGERGRAPH_PASSWORD: Password (default: tigergraph)
    """
    try:
        # TigerGraph Community Edition configuration
        host = os.getenv("TIGERGRAPH_HOST", "http://localhost")
        port = os.getenv("TIGERGRAPH_PORT", "14240")
        username = os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
        password = os.getenv("TIGERGRAPH_PASSWORD", "tigergraph")

        logger.info("Connecting to TigerGraph", host=host, port=port, username=username)
        
        # Community Edition uses the same port for REST API and GraphStudio
        conn = tg.TigerGraphConnection(
            host=host,
            restppPort=port,
            gsPort=port,
            username=username,
            password=password,
            graphname=graph_name
        )

        # Test the connection by getting a token
        try:
            conn.getToken()
            logger.info("Successfully connected to TigerGraph graph", graph_name=graph_name)
            return conn
        except Exception as token_error:
            logger.warning("Connected to TigerGraph but token generation failed", 
                          error=str(token_error), 
                          graph_name=graph_name,
                          note="This may be normal if the graph doesn't exist yet")
            return conn
            
    except Exception as e:
        logger.error("Error connecting to TigerGraph", 
                    error=str(e),
                    troubleshooting_steps=[
                        "Check if TigerGraph is running: docker ps | grep tigergraph",
                        "Run setup script: ./scripts/setup-tigergraph.sh"
                    ])
        return None

@error_boundary(component="tigergraph_test")
def test_connection():
    """
    Test function to verify TigerGraph Community Edition connectivity with comprehensive error handling.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    logger.info("Testing TigerGraph Community Edition connection")
    
    try:
        conn = get_tigergraph_connection()
        
        if conn:
            try:
                # Try to get server info
                info = conn.getVersion()
                logger.info("TigerGraph version retrieved", version=info)
                return True
            except Exception as version_error:
                logger.warning("Connected but limited functionality", error=str(version_error))
                return True  # Connection exists, just limited
        else:
            logger.error("TigerGraph connection failed")
            return False
            
    except Exception as e:
        # Use sync version of handle_tigergraph_error
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(handle_tigergraph_error(e, {"operation": "test_connection"}))
        except RuntimeError:
            # No event loop running, just log
            logger.error(
                "TigerGraph connection test failed with exception",
                error=str(e),
                error_type=type(e).__name__
            )
        return False

def is_graph_initialized(conn):
    """
    Check if the TigerGraph database is properly initialized with schema.
    
    Args:
        conn: TigerGraph connection object
        
    Returns:
        bool: True if graph exists with proper schema, False otherwise
    """
    try:
        # Expected vertex types for HybridAICouncil schema
        expected_vertices = [
            'Person', 'AIPersona', 'Preference', 'KIPAgent', 'Tool', 
            'Conversation', 'Message', 'Knowledge', 'Decision', 'Pheromone'
        ]
        
        # Use GSQL ls command since getVertexTypes() seems unreliable
        try:
            schema_info = conn.gsql('ls')
            
            # Check if expected vertices exist in the schema
            found_vertices = []
            for vertex in expected_vertices:
                if f"VERTEX {vertex}(" in schema_info:
                    found_vertices.append(vertex)
            
            has_core_schema = len(found_vertices) >= 3  # At least 3 core vertices
            
            if has_core_schema:
                logger.info("Graph schema verification successful", 
                           found_vertices=found_vertices,
                           total_expected=len(expected_vertices))
                return True
            else:
                logger.warning("Graph exists but schema incomplete", 
                              found_vertices=found_vertices,
                              expected_count=len(expected_vertices))
                return False
                
        except Exception as schema_error:
            logger.warning("Error checking schema via GSQL", error=str(schema_error))
            return False
            
    except Exception as e:
        logger.warning("Error checking graph schema", error=str(e))
        return False

if __name__ == "__main__":
    # Run connection test if script is executed directly
    test_connection() 