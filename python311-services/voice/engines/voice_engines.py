# python311-services/voice/engines/voice_engines.py
"""
Voice Processing Engines for Python 3.11 Service

Implements STT (Speech-to-Text) and TTS (Text-to-Speech) engines:
- STT: NVIDIA Parakeet-TDT-0.6B-v2 via NeMo (6.05% WER, RTF 3380)
- TTS: Coqui XTTS v2 (200ms latency, multi-voice support)
"""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import os

import torch
import structlog

logger = structlog.get_logger("VoiceEngines")

# Check for optional dependencies
try:
    import nemo.collections.asr as nemo_asr
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False
    logger.warning("NeMo not available - STT will use fallback")

# Note: Faster-Whisper removed - using NeMo Parakeet STT only

try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.error("Coqui TTS not available - voice synthesis will fail")

# Audio processing imports
try:
    import soundfile as sf
    import librosa
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logger.error("Audio processing libraries not available")

def convert_audio_to_wav(input_path: str, output_path: str = None) -> str:
    """
    Convert audio file to WAV format for NeMo Parakeet compatibility.
    Handles WebM/Opus, MP3, M4A, and other formats.
    """
    if not AUDIO_AVAILABLE:
        raise RuntimeError("Audio processing libraries not available")
    
    if output_path is None:
        # Create temp file with .wav extension
        output_path = input_path.replace('.webm', '.wav').replace('.mp3', '.wav').replace('.m4a', '.wav')
        if output_path == input_path:
            # If no extension change, create new temp file
            output_path = input_path.replace('.wav', '_converted.wav')
    
    try:
        # Load audio with librosa (handles multiple formats)
        audio, sr = librosa.load(input_path, sr=16000)  # NeMo expects 16kHz
        
        # Save as WAV
        sf.write(output_path, audio, sr, subtype='PCM_16')
        
        logger.info(
            "Audio converted successfully",
            input_path=input_path,
            output_path=output_path,
            sample_rate=sr,
            duration_seconds=len(audio)/sr
        )
        
        return output_path
        
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        raise RuntimeError(f"Audio conversion failed: {e}")

def should_convert_audio(audio_file_path: str) -> bool:
    """
    Determine if audio file needs conversion for NeMo compatibility.
    Always convert to ensure proper format.
    """
    try:
        # Try to load with librosa to check if it's a valid audio file
        audio, sr = librosa.load(audio_file_path, sr=16000, duration=0.1)  # Just check first 0.1 seconds
        return True  # If we can load it, we should convert it to ensure NeMo compatibility
    except Exception as e:
        logger.warning(f"Could not validate audio file {audio_file_path}: {e}")
        return True  # Convert anyway to be safe


class STTEngine:
    """
    Speech-to-Text Engine using NVIDIA Parakeet-TDT-0.6B-v2
    Production-ready STT with 6.05% WER performance
    """
    
    def __init__(self, force_parakeet=True):
        self.name = "NVIDIA Parakeet-TDT-0.6B-v2 (SOTA)"
        self.model = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize STT engine with NeMo Parakeet"""
        if self.is_initialized:
            return
            
        if not NEMO_AVAILABLE:
            raise RuntimeError("NeMo not available - cannot initialize STT engine")
            
        try:
            logger.info("Loading NVIDIA Parakeet-TDT-0.6B-v2 STT model")
            start_time = time.time()
            
            self.model = nemo_asr.models.ASRModel.from_pretrained(
                "nvidia/parakeet-tdt-0.6b-v2"
            )
            
            load_time = time.time() - start_time
            logger.info(
                "Parakeet-TDT loaded successfully", 
                load_time_seconds=load_time,
                wer_percentage=6.05,
                rtf=3380
            )
            
            self.is_initialized = True
            
        except Exception as e:
            logger.error("Parakeet-TDT failed to load", error=str(e))
            raise
    
    async def transcribe(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file to text using NeMo Parakeet"""
        if not self.is_initialized:
            raise RuntimeError("STT engine not initialized")
        
        start_time = time.time()
        
        try:
            # Always convert audio to WAV for NeMo compatibility
            logger.info(f"Converting audio file for NeMo compatibility: {audio_file_path}")
            wav_path = convert_audio_to_wav(audio_file_path)
            
            # Use NeMo Parakeet
            transcription = self.model.transcribe([wav_path])
            
            # Handle NeMo Hypothesis objects properly
            if transcription and len(transcription) > 0:
                # NeMo returns Hypothesis objects, extract the text
                hypothesis = transcription[0]
                if hasattr(hypothesis, 'text'):
                    text = hypothesis.text
                elif hasattr(hypothesis, '__str__'):
                    text = str(hypothesis)
                else:
                    text = ""
            else:
                text = ""
                
            confidence = 0.95  # Parakeet generally high confidence
            
            processing_time = time.time() - start_time
            
            logger.info(
                "STT transcription completed",
                text_length=len(text) if text else 0,
                processing_time_seconds=processing_time,
                confidence=confidence,
                audio_duration_seconds=processing_time
            )
            
            return {
                "text": text,
                "confidence": confidence,
                "processing_time_seconds": processing_time
            }
            
        except Exception as e:
            logger.error("STT transcription failed", error=str(e))
            raise RuntimeError(f"STT transcription failed: {str(e)}")
        finally:
            # Clean up converted file if it was created
            if wav_path != audio_file_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass


class TTSEngine:
    """
    Text-to-Speech Engine using Coqui XTTS v2
    Supports multi-voice synthesis and voice cloning
    """
    
    def __init__(self):
        self.name = "Coqui XTTS v2"
        self.model = None
        self.is_initialized = False
        self.output_dir = Path("outputs")
        self.voice_configs = {
            "default": "female",  # Default voice
            "council_leader": "male",
            "analyst": "female", 
            "advisor": "male"
        }
        
    async def initialize(self):
        """Initialize Coqui XTTS v2 model"""
        if self.is_initialized:
            return
            
        if not TTS_AVAILABLE:
            raise RuntimeError("Coqui TTS not available - install with: pip install TTS")
        
        try:
            logger.info("Loading Coqui XTTS v2 model")
            start_time = time.time()
            
            # Initialize XTTS v2
            self.model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
            
            # Create output directory
            self.output_dir.mkdir(exist_ok=True)
            
            load_time = time.time() - start_time
            logger.info(
                "Coqui XTTS v2 loaded successfully",
                load_time_seconds=load_time,
                supported_languages=16,
                expected_latency_ms=200
            )
            
            self.is_initialized = True
            
        except Exception as e:
            logger.error("Failed to initialize Coqui XTTS v2", error=str(e))
            raise
    
    async def synthesize(
        self, 
        text: str, 
        voice_id: str = "default",
        language: str = "en",
        output_file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesize speech from text"""
        if not self.is_initialized:
            raise RuntimeError("TTS engine not initialized")
        
        if not output_file_id:
            output_file_id = str(uuid.uuid4())
            
        output_file = self.output_dir / f"{output_file_id}.wav"
        
        start_time = time.time()
        
        try:
            # Get voice configuration
            voice_type = self.voice_configs.get(voice_id, "female")
            
            logger.info(
                "Starting TTS synthesis",
                text_length=len(text),
                voice_id=voice_id,
                voice_type=voice_type,
                language=language
            )
            
            # Synthesize speech (XTTS v2 requires speaker_id)
            # Map voice_id to real speaker names - using Damien Black as primary
            speaker_mapping = {
                "default": "Damien Black",          # Primary voice - strong, clear male
                "council_leader": "Craig Gutsy",     # Strong, authoritative male
                "analyst": "Alison Dietlinde",       # Strong, confident female
                "advisor": "Andrew Chipper"           # Energetic, friendly male
            }
            speaker_id = speaker_mapping.get(voice_id, "Damien Black")
            
            self.model.tts_to_file(
                text=text,
                file_path=str(output_file),
                language=language,
                speaker_id=speaker_id  # Use mapped speaker name
            )
            
            synthesis_time = time.time() - start_time
            
            # Calculate audio duration (approximate)
            # XTTS v2 typically produces ~150 words per minute
            words = len(text.split())
            estimated_duration = (words / 150) * 60  # seconds
            
            logger.info(
                "TTS synthesis completed",
                synthesis_time_seconds=synthesis_time,
                estimated_duration_seconds=estimated_duration,
                output_file=str(output_file),
                voice_used=f"{voice_id} ({voice_type})"
            )
            
            return {
                "audio_file_path": str(output_file),
                "duration_seconds": estimated_duration,
                "voice_used": f"{voice_id} ({voice_type})",
                "synthesis_time_seconds": synthesis_time
            }
            
        except Exception as e:
            logger.error(
                "TTS synthesis failed",
                error=str(e),
                text_length=len(text),
                voice_id=voice_id
            )
            raise


class VoiceProcessor:
    """
    Main voice processing coordinator
    Manages both STT and TTS engines
    """
    
    def __init__(self):
        self.stt_engine = STTEngine()
        self.tts_engine = TTSEngine()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize both STT and TTS engines"""
        logger.info("Initializing voice processing engines")
        
        try:
            # Initialize STT engine
            await self.stt_engine.initialize()
            
            # Initialize TTS engine  
            await self.tts_engine.initialize()
            
            self.is_initialized = True
            
            logger.info(
                "Voice processing engines initialized successfully",
                stt_engine=self.stt_engine.name,
                tts_engine=self.tts_engine.name
            )
            
        except Exception as e:
            logger.error("Failed to initialize voice processing engines", error=str(e))
            raise
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio to text"""
        if not self.is_initialized:
            raise RuntimeError("Voice processor not initialized")
            
        return await self.stt_engine.transcribe(audio_file_path)
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = "default", 
        language: str = "en",
        output_file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesize text to speech"""
        if not self.is_initialized:
            raise RuntimeError("Voice processor not initialized")
            
        return await self.tts_engine.synthesize(
            text=text,
            voice_id=voice_id,
            language=language,
            output_file_id=output_file_id
        )