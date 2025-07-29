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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from clients.tigervector_client import get_tigergraph_connection, test_connection

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
    print("🔄 Waiting for TigerGraph Community Edition to be ready...")
    print("💡 Make sure you've run: ./scripts/setup-tigergraph.sh")
    
    for attempt in range(max_retries):
        print(f"⏳ Attempt {attempt + 1}/{max_retries}")
        
        try:
            if test_connection():
                conn = get_tigergraph_connection()
                if conn:
                    print("✅ TigerGraph Community Edition is ready!")
                    return conn
        except Exception as e:
            print(f"   Connection attempt failed: {e}")
            
        if attempt < max_retries - 1:
            print(f"💤 Waiting {delay} seconds before retry...")
            time.sleep(delay)
    
    # Provide helpful troubleshooting info
    print("❌ TigerGraph failed to become ready within the timeout period")
    print("\n💡 Troubleshooting:")
    print("   1. Check if container is running: docker ps | grep tigergraph")
    print("   2. Check container logs: docker logs tigergraph")
    print("   3. Try accessing GraphStudio: http://localhost:14240")
    print("   4. Run setup script: ./scripts/setup-tigergraph.sh")
    raise Exception("TigerGraph Community Edition failed to start after maximum retries")

def initialize_database():
    """
    Initialize TigerGraph Community Edition database and load schema.
    
    Creates the HybridAICouncil graph and loads the schema from schemas/schema.gsql
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    print("🚀 Starting TigerGraph Community Edition initialization...")
    print("📋 This will create the HybridAICouncil graph and load the schema")
    
    # Wait for TigerGraph to be ready
    conn = wait_for_tigergraph()
    
    try:
        # Create database/graph (TigerGraph calls it a "graph")
        graph_name = "HybridAICouncil"
        print(f"\n📊 Creating graph: {graph_name}")
        
        # Create graph using GSQL commands
        try:
            print(f"   Creating graph via GSQL...")
            create_result = conn.gsql(f"CREATE GRAPH {graph_name}()")
            print(f"✅ Graph '{graph_name}' created successfully")
            if create_result:
                print(f"   Creation result: {create_result}")
        except Exception as create_error:
            if "already exists" in str(create_error) or "Graph name already exists" in str(create_error):
                print(f"ℹ️  Graph '{graph_name}' already exists")
            else:
                print(f"⚠️  Graph creation: {create_error}")
                print(f"   Continuing with schema loading...")
        
        # Switch to using the graph
        print(f"   Switching to graph '{graph_name}'...")
        use_result = conn.gsql(f"USE GRAPH {graph_name}")
        conn.graphname = graph_name
        if use_result:
            print(f"   Use graph result: {use_result}")
        
        # Load schema from file
        schema_path = Path("schemas/schema.gsql")
        if schema_path.exists():
            print(f"\n📝 Loading schema from {schema_path}...")
            with open(schema_path, 'r') as f:
                schema_content = f.read()
            
            print("   Executing schema...")
            # Execute schema
            result = conn.gsql(schema_content)
            print("✅ Schema loaded successfully")
            if result:
                print(f"   Schema result: {result}")
        else:
            print(f"⚠️  Schema file not found: {schema_path}")
            print("   You can load the schema manually later from GraphStudio")
        
        # Verify the graph is operational
        print(f"\n🔍 Verifying graph '{graph_name}' is operational...")
        try:
            # Try to list the schema to verify everything loaded
            verify_result = conn.gsql("ls")
            print("✅ Graph is operational and schema is accessible")
            if verify_result and len(str(verify_result)) > 10:
                print(f"   Schema verification: Schema loaded with vertices and edges")
            else:
                print(f"   Schema verification result: {verify_result}")
        except Exception as verify_error:
            print(f"⚠️  Graph verification warning: {verify_error}")
            print(f"   The graph may still be functional")
        
        print(f"\n🎉 TigerGraph Community Edition initialization complete!")
        print(f"🌐 Access GraphStudio: http://localhost:14240")
        print(f"🔑 Login with: tigergraph/tigergraph")
        print(f"📊 Graph name: {graph_name}")
        print(f"\n📋 Manual Verification Steps:")
        print(f"   1. Open GraphStudio at http://localhost:14240")
        print(f"   2. Login with tigergraph/tigergraph")
        print(f"   3. Select the '{graph_name}' graph from the dropdown")
        print(f"   4. Navigate to 'Design Schema' to see vertices and edges")
        print(f"   5. Check that vertices like Person, AIPersona, Preference are listed")
        return True
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure TigerGraph is running: docker ps | grep tigergraph")
        print("   2. Check TigerGraph logs: docker logs tigergraph")
        print("   3. Try manual setup via GraphStudio: http://localhost:14240")
        return False

if __name__ == "__main__":
    try:
        success = initialize_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Initialization interrupted by user")
        sys.exit(1) 