# 🚀 Python 3.11 Voice Service Setup Guide

Complete setup instructions for the voice processing microservice.

## Prerequisites

### 1. Install Python 3.11

**Windows:**
```bash
# Download from python.org or use winget
winget install Python.Python.3.11
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.11
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# CentOS/RHEL
sudo dnf install python3.11 python3.11-devel
```

### 2. Verify Python 3.11 Installation

```bash
python3.11 --version
# Should output: Python 3.11.x
```

## Setup Steps

### 1. Create Virtual Environment

```bash
# Navigate to the python311-services directory
cd python311-services

# Create virtual environment
python3.11 -m venv venv311

# Activate virtual environment
# Windows:
venv311\\Scripts\\activate
# macOS/Linux:
source venv311/bin/activate

# Verify you're using Python 3.11
python --version
```

### 2. Install Dependencies

**Option A: Automatic Setup (Recommended)**
```bash
python setup.py
```

**Option B: Manual Installation**
```bash
# Core web framework
pip install fastapi>=0.104.0 uvicorn[standard]>=0.24.0

# Voice processing (heavy dependencies)
pip install TTS>=0.22.0
pip install torch>=2.7.1 torchaudio>=2.7.1
pip install transformers>=4.54.1
pip install nemo-toolkit>=2.4.0

# Additional utilities
pip install structlog>=23.0.0 python-dotenv>=1.0.0
pip install faster-whisper>=1.0.0  # STT fallback
```

### 3. Test Installation

```bash
# Run import tests
python -c "from voice.engines.voice_engines import VoiceProcessor; print('✅ Voice engines ready')"

# Check service health
python -c "from voice.main import app; print('✅ FastAPI service ready')"
```

## Running the Service

### Development Mode
```bash
# With auto-reload (recommended for development)
python -m uvicorn voice.main:app --host 0.0.0.0 --port 8011 --reload
```

### Production Mode
```bash
# Production settings
python -m uvicorn voice.main:app --host 0.0.0.0 --port 8011 --workers 1
```

## Testing the API

### Health Check
```bash
curl http://localhost:8011/health
```

### Text-to-Speech
```bash
curl -X POST http://localhost:8011/voice/tts \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from the Hybrid AI Council", "voice_id": "default"}'
```

### Speech-to-Text
```bash
# Upload audio file for transcription
curl -X POST http://localhost:8011/voice/stt \\
  -F "audio_file=@path/to/audio.wav"
```

## Architecture Overview

```
python311-services/
├── voice/                      # Voice processing service
│   ├── main.py                # FastAPI application
│   ├── engines/               # Voice processing engines
│   │   └── voice_engines.py   # STT + TTS implementations
│   └── outputs/               # Generated audio files
├── shared/                    # Shared utilities (future)
├── pyproject.toml             # Dependencies
└── setup.py                   # Auto-setup script
```

## Engine Details

### STT Engine: NVIDIA Parakeet-TDT-0.6B-v2
- **Performance**: 6.05% WER, RTF 3380
- **Fallback**: Faster-Whisper Large-v3-Turbo
- **Dependencies**: NeMo toolkit, PyTorch

### TTS Engine: Coqui XTTS v2  
- **Latency**: ~200ms
- **Features**: Multi-voice, voice cloning, 16 languages
- **Dependencies**: Coqui TTS, PyTorch

## Communication with Main Project

The main Python 3.13 project communicates with this service via HTTP:

```python
# In main project
import httpx

async def get_voice_response(text: str) -> str:
    async with httpx.AsyncClient() as client:
        # Send text to voice service
        tts_response = await client.post(
            "http://localhost:8011/voice/tts",
            json={"text": text, "voice_id": "council_leader"}
        )
        return tts_response.json()["audio_file_id"]
```

## Troubleshooting

### Common Issues

**1. "TTS import failed"**
```bash
pip install TTS --upgrade
# or for development version:
pip install git+https://github.com/coqui-ai/TTS.git
```

**2. "NeMo not available"**
```bash
pip install nemo-toolkit[all]
# Requires PyTorch to be installed first
```

**3. "CUDA not available"**
- STT/TTS will work on CPU but slower
- For GPU acceleration, install CUDA-compatible PyTorch:
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**4. "Port 8011 already in use"**
```bash
# Change port in main.py or use:
python -m uvicorn voice.main:app --port 8012
```

### Performance Optimization

1. **GPU Usage**: Ensure CUDA is available for faster processing
2. **Memory**: Voice models require ~2-4GB RAM/VRAM
3. **Concurrency**: Service handles one request at a time (by design)

## Next Steps

1. ✅ **Service Running**: Voice service operational on port 8011
2. 🔄 **Main Project**: Update main project to call voice service
3. 🧪 **Integration**: Test end-to-end voice workflow
4. 🚀 **Production**: Deploy both services (3.11 + 3.13)