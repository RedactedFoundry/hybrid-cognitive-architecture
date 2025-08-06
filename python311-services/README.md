# Python 3.11 Services

Legacy compatibility services for the Hybrid AI Council project.

## Purpose

This microservice handles Python 3.11-only dependencies that are incompatible with the main project's Python 3.13 environment. Currently includes:

- **Voice Processing**: Speech-to-Text (STT) and Text-to-Speech (TTS)
- **Heavy ML Dependencies**: PyTorch, transformers, NeMo toolkit

## Architecture

- **Main Project** (Python 3.13): Core AI logic, web services, orchestration
- **This Service** (Python 3.11): Voice processing, legacy ML libraries
- **Communication**: HTTP API between services

## Current Services

### Voice Service (`/voice/`)
- **STT**: NVIDIA Parakeet-TDT-0.6B-v2 (6.05% WER, RTF 3380)
- **TTS**: Coqui XTTS v2 (200ms latency, multi-voice support)
- **API**: FastAPI endpoints for voice processing

## Setup

```bash
# Install dependencies
poetry install

# Run the service
poetry run uvicorn voice.main:app --host 0.0.0.0 --port 8011
```

## API Endpoints

- `POST /voice/stt` - Speech to Text conversion
- `POST /voice/tts` - Text to Speech synthesis  
- `GET /voice/health` - Service health check

## Future Expansion

This service can accommodate other Python 3.11-only dependencies:
- Legacy ML frameworks
- Older scientific computing libraries
- Specialized audio/video processing tools