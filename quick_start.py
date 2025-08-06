#!/usr/bin/env python3
"""
🚀 QUICK START - FAST STARTUP 🚀

Quick startup that skips verification for faster startup.

Usage:
    python quick_start.py
"""

import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    print("🚀 Quick Starting Hybrid AI Council...")
    print("=" * 50)
    
    # Run the master startup script with skip-verify
    try:
        result = subprocess.run([
            sys.executable, "scripts/start_everything.py", "--with-api", "--skip-verify"
        ], cwd=Path(__file__).parent, check=True)
        
        print("\n🎉 QUICK START COMPLETE!")
        print("\n🌐 Access your system at:")
        print("   • Main Dashboard: http://localhost:8001/")
        print("   • Voice Chat: http://localhost:8001/realtime-voice.html")
        print("   • Voice Health: http://localhost:8011/health")
        print("\n🎤 Voice chat is ready to use!")
        sys.exit(0)
        
    except subprocess.CalledProcessError:
        print("\n💥 Quick start failed - check errors above")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Quick start interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 