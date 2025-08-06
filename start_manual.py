#!/usr/bin/env python3
"""
🚀 MANUAL START - DIRECT STARTUP 🚀

Manual startup that starts services directly without complex orchestration.

Usage:
    python start_manual.py
"""

import sys
import subprocess
import time
from pathlib import Path

def start_voice_service():
    """Start voice service directly"""
    print("🎤 Starting Voice Service...")
    voice_dir = Path(__file__).parent / "python311-services"
    
    # Start voice service in background
    subprocess.Popen([
        "cmd", "/c", 
        f"cd {voice_dir} && "
        "source C:/Users/Jake/AppData/Local/pypoetry/Cache/virtualenvs/python311-services-A1b0dxtl-py3.11/Scripts/activate && "
        "python voice/main.py"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("✅ Voice service started in background")

def start_main_api():
    """Start main API directly"""
    print("🌐 Starting Main API...")
    
    # Start main API in background
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "main:app", 
        "--host", "127.0.0.1", "--port", "8001", "--timeout-keep-alive", "5"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("✅ Main API started in background")

if __name__ == "__main__":
    print("🚀 Manual Starting Hybrid AI Council...")
    print("=" * 50)
    
    # Start services directly
    start_voice_service()
    time.sleep(2)  # Brief pause
    start_main_api()
    
    print("\n⏳ Waiting for services to be ready...")
    time.sleep(10)  # Wait for services to start
    
    print("\n🎉 MANUAL START COMPLETE!")
    print("\n🌐 Access your system at:")
    print("   • Main Dashboard: http://localhost:8001/")
    print("   • Voice Chat: http://localhost:8001/realtime-voice.html")
    print("   • Voice Health: http://localhost:8011/health")
    print("\n🎤 Voice chat should be ready!")
    print("\n💡 If services aren't ready, wait a few more seconds and refresh.") 