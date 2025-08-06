#!/usr/bin/env python3
"""
Quick integration test for voice foundation
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

async def test_voice_foundation():
    """Test voice foundation integration"""
    try:
        from voice_foundation import create_voice_foundation
        
        print("🧪 Testing voice foundation integration...")
        
        # Create voice foundation
        foundation = await create_voice_foundation()
        print("✅ Voice foundation created successfully")
        
        # Check STT
        print(f"✅ STT Engine: {foundation.stt.name}")
        
        # Check TTS  
        print(f"✅ TTS Engine: {foundation.tts.name}")
        
        # Test health check
        health = await foundation.health_check()
        print(f"✅ Health check: {health['status']}")
        
        print("🎯 Voice foundation integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Voice foundation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_voice_foundation())
    sys.exit(0 if success else 1) 