#!/usr/bin/env python3
"""
Test REAL Kyutai TTS-1.6B synthesis only
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from voice_foundation.production_voice_engines import ProductionTTSEngine

async def test_kyutai_tts():
    """Test REAL Kyutai TTS synthesis only"""
    print("🧪 Testing REAL Kyutai TTS-1.6B Synthesis")
    print("=" * 50)
    
    try:
        # Initialize TTS engine
        tts = ProductionTTSEngine()
        await tts.initialize()
        
        # Test synthesis
        test_text = "Hello! This is a test of the real Kyutai TTS-1.6B model."
        output_path = "outputs/kyutai_test.wav"
        
        # Ensure output directory exists
        os.makedirs("outputs", exist_ok=True)
        
        print(f"📝 Text: '{test_text}'")
        print(f"💾 Output: {output_path}")
        
        success = await tts.synthesize(test_text, output_path)
        
        if success:
            print("✅ SUCCESS! Kyutai TTS synthesis completed!")
            
            # Check file size
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"📊 Generated audio: {file_size:,} bytes")
            else:
                print("❌ Audio file not found")
                
        else:
            print("❌ TTS synthesis failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_kyutai_tts())