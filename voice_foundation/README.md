# Epic 12.5: Voice Foundation

## Overview

This is a **research and validation** pipeline for testing voice capabilities before integration into the main Hybrid AI Council. 

**IMPORTANT**: This is NOT integrated with the orchestrator yet. It's a standalone test to validate the voice stack.

## Technology Stack

### STT: NVIDIA Parakeet TDT 0.6B V2
- **Performance**: 3380x Real-Time Factor
- **Accuracy**: 6.05% average WER
- **Parameters**: 600M
- **License**: CC-BY-4.0

### TTS: Kokoro TTS 82M
- **Performance**: 3.2x faster than XTTSv2
- **Quality**: Beats models 10x larger
- **Parameters**: 82M
- **License**: Apache 2.0

## Pipeline Architecture

```
Audio Input (.wav) 
    ↓
NVIDIA Parakeet TDT 0.6B V2 (STT)
    ↓
Text Processing (simple echo/transform)
    ↓  
Kokoro TTS 82M (TTS)
    ↓
Audio Output (.wav)
```

## Installation

```bash
# STT Requirements
pip install -U nemo_toolkit[asr]

# TTS Requirements  
pip install kokoro>=0.9.4 soundfile
# Windows: Download espeak-ng installer from GitHub releases
# Linux: apt-get install espeak-ng
```

## Usage

```python
# Simple test pipeline
python voice_foundation/test_pipeline.py --input audio.wav --output response.wav
```

## Validation Goals

1. **Latency Testing**: Measure total STT+TTS pipeline latency
2. **Quality Testing**: Verify transcription accuracy and voice quality
3. **Resource Usage**: Monitor VRAM/CPU usage
4. **Integration Readiness**: Confirm API compatibility for orchestrator integration

## Next Steps (Post-Sprint 3)

- Integration with main orchestrator
- Voice activity detection
- Streaming audio support
- Conversation flow management