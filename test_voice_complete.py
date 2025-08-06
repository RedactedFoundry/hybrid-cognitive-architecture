#!/usr/bin/env python3
"""
Test complete voice pipeline
"""

import requests
import time
import json

def test_voice_pipeline():
    """Test the complete voice pipeline"""
    print("🧪 Testing Complete Voice Pipeline...")
    
    # Test 1: Voice service health
    print("\n1. Testing Voice Service Health...")
    try:
        response = requests.get("http://localhost:8011/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Voice service healthy: {data['status']}")
            print(f"   STT: {data['services']['stt']['engine']}")
            print(f"   TTS: {data['services']['tts']['engine']}")
        else:
            print(f"❌ Voice service unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Voice service not reachable: {e}")
        return False
    
    # Test 2: TTS synthesis
    print("\n2. Testing TTS Synthesis...")
    try:
        tts_data = {
            "text": "Hello! This is a test of the voice system. The TTS is working correctly.",
            "voice_id": "default",
            "language": "en"
        }
        response = requests.post("http://localhost:8011/voice/tts", 
                               json=tts_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ TTS synthesis successful!")
            print(f"   Audio file ID: {result['audio_file_id']}")
            print(f"   Duration: {result['duration_seconds']:.1f}s")
            print(f"   Voice used: {result['voice_used']}")
            
            # Test 3: Audio file retrieval
            print("\n3. Testing Audio File Retrieval...")
            audio_response = requests.get(f"http://localhost:8011/voice/audio/{result['audio_file_id']}", 
                                       timeout=10)
            if audio_response.status_code == 200:
                print(f"✅ Audio file retrieved successfully!")
                print(f"   Content length: {len(audio_response.content)} bytes")
                print(f"   Content type: {audio_response.headers.get('content-type', 'unknown')}")
            else:
                print(f"❌ Audio file retrieval failed: {audio_response.status_code}")
                return False
                
        else:
            print(f"❌ TTS synthesis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False
    
    # Test 4: Main API health
    print("\n4. Testing Main API Health...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Main API healthy: {data['status']}")
        else:
            print(f"❌ Main API unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Main API not reachable: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("\n🌐 Voice chat is ready at: http://localhost:8001/realtime-voice.html")
    print("🎤 You can now use voice chat with working audio output!")
    
    return True

if __name__ == "__main__":
    success = test_voice_pipeline()
    if not success:
        print("\n💥 Voice pipeline test failed!")
        exit(1) 