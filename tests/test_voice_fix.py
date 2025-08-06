#!/usr/bin/env python3
"""
Test voice foundation fix
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

async def test_voice_foundation():
    """Test voice foundation creation"""
    try:
        from voice_foundation import create_voice_foundation
        
        print("🧪 Testing voice foundation with fixed voice service...")
        
        # Create voice foundation
        foundation = await create_voice_foundation()
        print(f"✅ Voice foundation created: {foundation is not None}")
        
        if foundation:
            # Test health check
            health = await foundation.health_check()
            print(f"✅ Health check: {health.get('status', 'unknown')}")
            
            print("🎯 Voice foundation test passed!")
            return True
        else:
            print("❌ Voice foundation is None!")
            return False
            
    except Exception as e:
        print(f"❌ Voice foundation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_voice_foundation())
    sys.exit(0 if success else 1) 