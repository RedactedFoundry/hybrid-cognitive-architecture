#!/usr/bin/env python3
"""
Voice Foundation Test Pipeline

A simple STT+TTS pipeline to validate the voice stack before orchestrator integration.
This is a research/validation tool, not production code.

NVIDIA Parakeet TDT 0.6B V2 + Kokoro TTS 82M
"""

import argparse
import time
import torch
import soundfile as sf
from pathlib import Path

def setup_stt():
    """Initialize NVIDIA Parakeet STT model"""
    print("🎙️ Loading NVIDIA Parakeet TDT 0.6B V2...")
    
    try:
        import nemo.collections.asr as nemo_asr
        model = nemo_asr.models.ASRModel.from_pretrained(
            model_name="nvidia/parakeet-tdt-0.6b-v2"
        )
        print("✅ STT model loaded successfully")
        return model
    except ImportError:
        print("❌ NeMo not installed. Run: pip install -U nemo_toolkit[asr]")
        return None
    except Exception as e:
        print(f"❌ Failed to load STT model: {e}")
        return None

def setup_tts():
    """Initialize Kokoro TTS model"""
    print("🔊 Loading Kokoro TTS 82M...")
    
    try:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code='a')  # American English
        print("✅ TTS model loaded successfully")
        return pipeline
    except ImportError:
        print("❌ Kokoro not installed. Run: pip install kokoro>=0.9.4")
        return None
    except Exception as e:
        print(f"❌ Failed to load TTS model: {e}")
        return None

def transcribe_audio(stt_model, audio_path):
    """Convert audio to text using Parakeet"""
    print(f"🎯 Transcribing: {audio_path}")
    
    start_time = time.time()
    try:
        output = stt_model.transcribe([str(audio_path)])
        transcription = output[0].text
        latency = time.time() - start_time
        
        print(f"📝 Transcription: '{transcription}'")
        print(f"⚡ STT Latency: {latency:.2f}s")
        return transcription
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return None

def synthesize_speech(tts_pipeline, text, output_path, voice='af_heart'):
    """Convert text to speech using Kokoro"""
    print(f"🗣️ Synthesizing: '{text}'")
    
    start_time = time.time()
    try:
        generator = tts_pipeline(text, voice=voice)
        
        # Get the first (and likely only) audio chunk
        for i, (gs, ps, audio) in enumerate(generator):
            if i == 0:  # Use first chunk
                # Save to file
                sf.write(output_path, audio, 24000)
                latency = time.time() - start_time
                
                print(f"🎵 Audio saved: {output_path}")
                print(f"⚡ TTS Latency: {latency:.2f}s")
                return True
                
        print("❌ No audio generated")
        return False
        
    except Exception as e:
        print(f"❌ Speech synthesis failed: {e}")
        return False

def simple_text_transform(text):
    """Simple text processing (placeholder for future orchestrator integration)"""
    # For now, just echo the text with a prefix
    response = f"I heard you say: {text}"
    print(f"🧠 Processed: '{response}'")
    return response

def test_pipeline(input_path, output_path):
    """Run the complete STT+TTS pipeline"""
    print("🚀 Starting Voice Foundation Pipeline Test")
    print("=" * 50)
    
    # Validate input
    if not Path(input_path).exists():
        print(f"❌ Input file not found: {input_path}")
        return False
    
    # Initialize models
    stt_model = setup_stt()
    tts_pipeline = setup_tts()
    
    if not stt_model or not tts_pipeline:
        print("❌ Failed to initialize models")
        return False
    
    print("\n🎯 Running Pipeline...")
    print("-" * 30)
    
    # Step 1: Speech to Text
    transcription = transcribe_audio(stt_model, input_path)
    if not transcription:
        return False
    
    # Step 2: Process text (simple transform for now)
    response_text = simple_text_transform(transcription)
    
    # Step 3: Text to Speech
    success = synthesize_speech(tts_pipeline, response_text, output_path)
    
    if success:
        print("\n✅ Pipeline completed successfully!")
        print(f"🎯 Input: {input_path}")
        print(f"📝 Transcription: '{transcription}'")
        print(f"🧠 Response: '{response_text}'")
        print(f"🎵 Output: {output_path}")
        return True
    else:
        print("\n❌ Pipeline failed")
        return False

def main():
    parser = argparse.ArgumentParser(description="Voice Foundation Test Pipeline")
    parser.add_argument("--input", "-i", required=True, help="Input audio file (.wav)")
    parser.add_argument("--output", "-o", required=True, help="Output audio file (.wav)")
    parser.add_argument("--voice", "-v", default="af_heart", help="TTS voice (default: af_heart)")
    
    args = parser.parse_args()
    
    # Create output directory if needed
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Run pipeline
    success = test_pipeline(args.input, args.output)
    
    if success:
        print("\n🎉 Voice Foundation validation successful!")
        print("Ready for orchestrator integration in future sprints.")
    else:
        print("\n💥 Voice Foundation validation failed.")
        print("Check model installations and try again.")

if __name__ == "__main__":
    main()