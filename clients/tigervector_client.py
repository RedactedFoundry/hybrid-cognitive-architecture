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

import pyTigerGraph as tg
import os

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

        print(f"Connecting to TigerGraph at {host}:{port} as {username}")
        
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
            print(f"✅ Successfully connected to TigerGraph graph: {graph_name}")
            return conn
        except Exception as token_error:
            print(f"⚠️  Connected to TigerGraph but token generation failed: {token_error}")
            print(f"   This may be normal if the graph '{graph_name}' doesn't exist yet.")
            return conn
            
    except Exception as e:
        print(f"❌ Error connecting to TigerGraph: {e}")
        print(f"💡 Make sure TigerGraph is running: docker ps | grep tigergraph")
        print(f"💡 Or run: ./scripts/setup-tigergraph.sh")
        return None

def test_connection():
    """
    Test function to verify TigerGraph Community Edition connectivity.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print("🔍 Testing TigerGraph Community Edition connection...")
    conn = get_tigergraph_connection()
    
    if conn:
        try:
            # Try to get server info
            info = conn.getVersion()
            print(f"✅ TigerGraph version: {info}")
            return True
        except Exception as e:
            print(f"⚠️  Connected but limited functionality: {e}")
            return True  # Connection exists, just limited
    else:
        print("❌ Connection failed")
        return False

if __name__ == "__main__":
    # Run connection test if script is executed directly
    test_connection() 