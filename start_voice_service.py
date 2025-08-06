#!/usr/bin/env python3
"""
🎤 Voice Service Starter

Simple script to start the voice service in the foreground.
This ensures it stays alive and doesn't terminate.
"""

import subprocess
import sys
from pathlib import Path

def start_voice_service():
    """Start the voice service in the foreground"""
    print("🎤 Starting Voice Service...")
    
    # Get the voice service directory
    voice_dir = Path(__file__).parent / "python311-services"
    
    # Create the bash script
    voice_script = f"""#!/bin/bash
cd "{voice_dir}"
source "C:/Users/Jake/AppData/Local/pypoetry/Cache/virtualenvs/python311-services-A1b0dxtl-py3.11/Scripts/activate"
python voice/main.py
"""
    
    # Write the script
    script_path = Path(__file__).parent / "start_voice.sh"
    with open(script_path, 'w') as f:
        f.write(voice_script)
    
    # Make it executable
    script_path.chmod(0o755)
    
    print(f"✅ Voice service script created: {script_path}")
    print("🔄 Starting voice service in foreground...")
    print("💡 Press Ctrl+C to stop the voice service")
    
    # Run the script in the foreground (this will block)
    try:
        subprocess.run(["bash", str(script_path)], check=True)
    except KeyboardInterrupt:
        print("\n⚠️ Voice service stopped by user")
    except Exception as e:
        print(f"❌ Voice service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_voice_service() 