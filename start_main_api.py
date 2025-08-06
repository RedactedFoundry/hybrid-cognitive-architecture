#!/usr/bin/env python3
"""
🌐 Main API Server Starter

Simple script to start the main API server in the foreground.
This ensures it stays alive and doesn't terminate.
"""

import subprocess
import sys

def start_main_api():
    """Start the main API server in the foreground"""
    print("🌐 Starting Main API Server...")
    print("🔄 Starting main API in foreground...")
    print("💡 Press Ctrl+C to stop the main API")
    
    # Run the main API in the foreground (this will block)
    try:
        subprocess.run(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001", "--timeout-keep-alive", "5"], check=True)
    except KeyboardInterrupt:
        print("\n⚠️ Main API stopped by user")
    except Exception as e:
        print(f"❌ Main API error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_main_api() 