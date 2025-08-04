#!/usr/bin/env python3
"""
Quick Database Check Script
==========================

This script quickly checks both Redis and TigerGraph to see what data 
is currently stored and verify database connectivity.
"""

import os
import sys
from datetime import datetime

def check_redis():
    """Check Redis connectivity and show stored data."""
    print("🔍 Redis Database Check:")
    print("-" * 30)
    
    try:
        from clients.redis_client import get_redis_connection
        redis_conn = get_redis_connection()
        
        # Test connection
        redis_conn.ping()
        print("   ✅ Redis Connection: SUCCESS")
        
        # Count keys
        total_keys = redis_conn.dbsize()
        print(f"   📊 Total Keys: {total_keys}")
        
        if total_keys == 0:
            print("   ℹ️  No data yet - use the system to generate data")
            return
        
        # Show key patterns
        all_keys = redis_conn.keys("*")
        key_patterns = {}
        
        for key in all_keys:
            pattern = key.decode() if isinstance(key, bytes) else key
            prefix = pattern.split(":")[0] if ":" in pattern else "other"
            key_patterns[prefix] = key_patterns.get(prefix, 0) + 1
        
        print("   📋 Key Patterns:")
        for pattern, count in sorted(key_patterns.items()):
            print(f"      {pattern}:* → {count} keys")
            
        # Show some actual data
        print("   🔍 Sample Data:")
        sample_keys = list(all_keys)[:5]
        for key in sample_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            try:
                value = redis_conn.get(key)
                value_str = value.decode() if isinstance(value, bytes) else str(value)
                # Truncate long values
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                print(f"      {key_str} = {value_str}")
            except Exception as e:
                print(f"      {key_str} = <error reading: {e}>")
                
    except Exception as e:
        print(f"   ❌ Redis Error: {e}")

def check_tigergraph():
    """Check TigerGraph connectivity and show stored data."""
    print("\n🔍 TigerGraph Database Check:")
    print("-" * 30)
    
    try:
        from clients.tigervector_client import get_tigergraph_connection
        conn = get_tigergraph_connection()
        
        if not conn:
            print("   ❌ TigerGraph Connection: FAILED")
            print("   💡 Try running: python scripts/init_tigergraph.py")
            return
            
        print("   ✅ TigerGraph Connection: SUCCESS")
        
        # Check schema
        try:
            schema = conn.getSchema()
            vertex_types = schema.vertexTypes if hasattr(schema, 'vertexTypes') else []
            edge_types = schema.edgeTypes if hasattr(schema, 'edgeTypes') else []
            
            print(f"   📊 Schema: {len(vertex_types)} vertex types, {len(edge_types)} edge types")
            
            # Show vertex counts
            print("   📋 Vertex Counts:")
            total_vertices = 0
            
            for vertex_type in vertex_types:
                try:
                    count = conn.getVertexCount(vertex_type)
                    total_vertices += count
                    print(f"      {vertex_type}: {count} vertices")
                except Exception as e:
                    print(f"      {vertex_type}: error counting ({e})")
            
            print(f"   📊 Total Vertices: {total_vertices}")
            
            if total_vertices == 0:
                print("   ℹ️  No data yet - use the system to generate conversation data")
            else:
                # Show some actual data
                print("   🔍 Sample Data:")
                try:
                    # Try to get some conversations
                    conversations = conn.getVertices('Conversation', limit=3)
                    if conversations:
                        print("      Recent Conversations:")
                        for i, conv in enumerate(conversations[:3]):
                            conv_id = conv[0] if isinstance(conv, tuple) else conv
                            print(f"         {i+1}. ID: {conv_id}")
                    
                    # Try to get some knowledge nodes
                    knowledge = conn.getVertices('KnowledgeNode', limit=3)
                    if knowledge:
                        print("      Recent Knowledge Nodes:")
                        for i, node in enumerate(knowledge[:3]):
                            if isinstance(node, tuple) and len(node) > 1:
                                node_data = node[1]
                                content = node_data.get('content', 'N/A') if isinstance(node_data, dict) else 'N/A'
                                if len(str(content)) > 50:
                                    content = str(content)[:47] + "..."
                                print(f"         {i+1}. Content: {content}")
                            else:
                                print(f"         {i+1}. ID: {node}")
                        
                except Exception as e:
                    print(f"      Error reading sample data: {e}")
            
        except Exception as e:
            print(f"   ⚠️  Schema Error: {e}")
            print("   💡 Try running: python scripts/init_tigergraph.py")
            
    except Exception as e:
        print(f"   ❌ TigerGraph Error: {e}")

def check_environment():
    """Check environment variables and configuration."""
    print("\n🔍 Environment Configuration Check:")
    print("-" * 30)
    
    # Check .env file
    env_file_exists = os.path.exists('.env')
    print(f"   📄 .env file: {'EXISTS' if env_file_exists else 'NOT FOUND'}")
    
    if env_file_exists:
        try:
            with open('.env', 'r') as f:
                lines = [line.strip() for line in f.readlines() 
                        if line.strip() and not line.startswith('#')]
            print(f"   📋 Environment Variables: {len(lines)} defined")
            if lines:
                print("   🔍 Sample Variables:")
                for line in lines[:5]:  # Show first 5
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Hide sensitive values
                        if any(secret in key.lower() for secret in ['password', 'key', 'secret', 'token']):
                            value = '***HIDDEN***'
                        print(f"      {key} = {value}")
        except Exception as e:
            print(f"   ⚠️  Error reading .env: {e}")
    else:
        print("   ℹ️  Using default configuration from config.py")
    
    # Check key environment variables
    important_vars = [
        'ENVIRONMENT', 'REDIS_HOST', 'TIGERGRAPH_HOST', 
        'TIGERGRAPH_USERNAME', 'OLLAMA_HOST'
    ]
    
    print("   🔑 Key Variables:")
    for var in important_vars:
        value = os.getenv(var, 'NOT SET (using default)')
        print(f"      {var} = {value}")

def main():
    """Run all database checks."""
    print("🔍 Hybrid AI Council - Quick Database Check")
    print("=" * 50)
    print(f"⏰ Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_environment()
    check_redis()
    check_tigergraph()
    
    print("\n" + "=" * 50)
    print("🎯 Quick Check Complete!")
    print("\nNext steps:")
    print("   1. If databases are empty, use the system to generate data")
    print("   2. Start the API: uvicorn main:app --host 0.0.0.0 --port 8000")
    print("   3. Make some requests to see data being written")
    print("   4. For comprehensive verification: python verify_system.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Check failed with error: {e}")
        sys.exit(1)