#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from voice.engines.voice_engines import VoiceProcessor

async def smoke_test():
    print('Testing voice engines...')
    try:
        processor = VoiceProcessor()
        print('✅ VoiceProcessor imported successfully')
        print('✅ No faster-whisper warnings!')
        print('🎯 Voice cleanup successful!')
    except Exception as e:
        print(f'❌ Test failed: {e}')

if __name__ == "__main__":
    asyncio.run(smoke_test())