# Python 3.11 Voice Service Tests

This directory contains tests for the Python 3.11 voice processing microservice.

## Test Files

### `test_voice_engines.py`
Tests the actual voice processing engines:
- **NeMo Parakeet STT** (NVIDIA Parakeet-TDT-0.6B-v2)
- **Coqui XTTS v2** TTS engine
- Complete voice pipeline integration

### `test_voice_service.py` 
Tests the FastAPI HTTP service endpoints:
- Health check endpoint
- STT endpoint (`/voice/stt`)
- TTS endpoint (`/voice/tts`) 
- Audio file download endpoint
- Error handling

### `test_production_voice_legacy.py`
Legacy production voice test (moved from main project).

## Running Tests

### Prerequisites
Make sure you're in the Python 3.11 environment:
```bash
cd python311-services
python -m pip install pytest pytest-asyncio httpx
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_voice_engines.py -v
pytest tests/test_voice_service.py -v
```

### Run Smoke Tests
```bash
python tests/test_voice_engines.py
python tests/test_voice_service.py
```

## Test Requirements

- **Real Models**: Some tests download and initialize actual models (NeMo Parakeet, Coqui XTTS v2)
- **First Run**: Model downloads may take time and require internet connection
- **Disk Space**: Models require several GB of disk space
- **Memory**: Voice models require sufficient RAM (4GB+ recommended)

## Integration with Main Project

The main Python 3.13 project has integration tests in:
- `tests/test_voice_microservice_integration.py` - Tests HTTP client integration
- `tests/test_voice_foundation.py` - Tests voice foundation with mocked microservice

These test that the main project can communicate with this voice service without importing voice libraries directly.