#!/usr/bin/env python3
"""
Test audio conversion functionality
"""

import requests
import base64
import tempfile
import os

def test_audio_conversion():
    """Test that the voice service can handle audio conversion"""
    
    # Create a simple test audio file (simulate WebM content)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        # Create a minimal WAV file header (this is just for testing)
        # In real usage, this would be WebM/Opus content from browser
        wav_header = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        temp_file.write(wav_header)
        temp_file_path = temp_file.name
    
    try:
        # Test the voice service STT endpoint
        with open(temp_file_path, 'rb') as f:
            files = {'audio_file': ('test.wav', f, 'audio/wav')}
            response = requests.post('http://localhost:8011/voice/stt', files=files)
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Audio conversion test passed!")
            return True
        else:
            print("❌ Audio conversion test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

if __name__ == "__main__":
    test_audio_conversion() 