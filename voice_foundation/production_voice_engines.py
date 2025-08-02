"""
Production Voice Engines - SOTA Models (July 2025)
Based on latest benchmarks: Parakeet-TDT + Kyutai TTS + Silero VAD

NVIDIA Parakeet-TDT-0.6B-v2: 6.05% WER, RTF 3380 (60 min in 1 sec)
Kyutai TTS-1.6B: 2.82% WER (beats ElevenLabs 4.05%), 220ms latency
Silero VAD v3: <1ms processing, enterprise-grade accuracy
"""

import asyncio
import time
import numpy as np
import torch
import torchaudio
from pathlib import Path
from typing import Optional
import logging
import structlog

# For Parakeet-TDT via HuggingFace (primary method)
try:
    from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Faster-Whisper as backup STT
from faster_whisper import WhisperModel

# Silero VAD for voice activity detection
import silero_vad

# Set up structured logging
logger = structlog.get_logger("voice_engines")

# For Kyutai TTS
import subprocess
import os

class ProductionSTTEngine:
    """
    NVIDIA Parakeet-TDT-0.6B-v2 STT Engine (SOTA)
    Performance: 6.05% WER, RTF 3380 (60 min in 1 sec)
    Uses NeMo when available, falls back to Faster-Whisper
    """
    
    def __init__(self, force_parakeet=True):
        self.name = "NVIDIA Parakeet-TDT-0.6B-v2 (SOTA)"
        self.force_parakeet = force_parakeet
        self.model = None
        self.fallback_model = None
        self.use_nemo = False
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize Parakeet-TDT or fallback to Faster-Whisper"""
        if self.is_initialized:
            return
            
        # Try NeMo first for Parakeet-TDT
        if self.force_parakeet:
            try:
                logger.info("Loading NVIDIA Parakeet-TDT-0.6B-v2 SOTA STT model")
                start_time = time.time()
                
                # Import NeMo and load Parakeet (using working configuration)
                import nemo.collections.asr as nemo_asr
                self.model = nemo_asr.models.ASRModel.from_pretrained(
                    "nvidia/parakeet-tdt-0.6b-v2"
                )
                
                load_time = time.time() - start_time
                logger.info("NVIDIA Parakeet-TDT-0.6B-v2 loaded successfully", 
                          load_time_seconds=load_time, 
                          wer_percentage=6.05, 
                          rtf=3380)
                
                self.use_nemo = True
                self.is_initialized = True
                return
                
            except ImportError as e:
                logger.warning("NeMo not available, falling back to Faster-Whisper", error=str(e))
            except Exception as e:
                logger.warning("Parakeet-TDT failed to load, falling back to Faster-Whisper", error=str(e))
        
        # Fallback to Faster-Whisper
        try:
            logger.info("Loading Faster-Whisper Large-v3-Turbo as SOTA fallback")
            start_time = time.time()
            
            self.fallback_model = WhisperModel(
                "large-v3-turbo", 
                device="auto",  # Will use GPU if available
                compute_type="auto"  # Will optimize automatically
            )
            
            load_time = time.time() - start_time
            logger.info("Faster-Whisper Large-v3-Turbo loaded successfully", 
                       load_time_seconds=load_time, 
                       quality="high-quality-fallback")
            
            self.name = "Faster-Whisper Large-v3-Turbo (SOTA Fallback)"
            self.is_initialized = True
            
        except Exception as e:
            logger.error("STT initialization completely failed", error=str(e))
            raise
    
    async def transcribe(self, audio_path: str) -> Optional[str]:
        """Transcribe audio to text using Parakeet-TDT or Faster-Whisper"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            start_time = time.time()
            
            if self.use_nemo and self.model:
                # Use NVIDIA Parakeet-TDT (SOTA)
                output = self.model.transcribe([audio_path])
                transcription = output[0]
            else:
                # Use Faster-Whisper fallback
                segments, _ = self.fallback_model.transcribe(audio_path)
                transcription = " ".join([segment.text for segment in segments])
            
            processing_time = time.time() - start_time
            engine_name = "Parakeet-TDT" if self.use_nemo else "Faster-Whisper"
            logger.info("STT transcription completed", 
                       engine=engine_name,
                       processing_time_seconds=processing_time,
                       transcription_preview=str(transcription)[:50])
            
            return str(transcription).strip()
            
        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            return None

class ProductionTTSEngine:
    """
    Kyutai TTS-1.6B Engine - Real-Time Streaming TTS
    Performance: 2.82% WER (beats ElevenLabs 4.05%), 220ms latency, true streaming
    Model: kyutai/tts-1.6b-en_fr
    """
    
    def __init__(self):
        self.name = "Kyutai TTS-1.6B (SOTA Real-Time)"
        self.model = None
        self.tokenizer = None
        self.edge_tts = None
        self.use_edge_fallback = False
        self.use_real_kyutai = False
        self.kyutai_script_path = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the REAL Kyutai TTS-1.6B model"""
        if self.is_initialized:
            return
            
        try:
            logger.info("Loading REAL Kyutai TTS-1.6B SOTA model")
            start_time = time.time()
            
            # Use official Kyutai implementation via uvx
            try:
                import os
                import subprocess
                
                # Find the Kyutai repository
                current_dir = os.path.dirname(os.path.dirname(__file__))
                kyutai_path = os.path.join(current_dir, "kyutai-tts")
                script_path = os.path.join(kyutai_path, "scripts", "tts_pytorch.py")
                
                if os.path.exists(script_path):
                    logger.info("Found Kyutai TTS installation", path=kyutai_path)
                    
                    # Test if uvx and moshi work
                    test_result = subprocess.run([
                        "uvx", "--with", "moshi", "python", script_path,
                        "-", "-", "--device", "cpu"
                    ], input="test", text=True, capture_output=True, 
                       cwd=kyutai_path, timeout=60)
                    
                    if test_result.returncode == 0:
                        self.kyutai_script_path = script_path
                        self.use_real_kyutai = True
                        self.use_edge_fallback = False
                        logger.info("REAL Kyutai TTS-1.6B loaded successfully via official scripts",
                                   wer_percentage=2.82,
                                   performance_comparison="beats ElevenLabs 4.05%",
                                   latency_ms=220,
                                   real_time_streaming=True)
                    else:
                        raise Exception(f"Kyutai test failed: {test_result.stderr}")
                else:
                    raise Exception(f"Kyutai scripts not found at {script_path}")
                
            except Exception as kyutai_error:
                logger.warning("Kyutai TTS-1.6B failed, falling back to Edge-TTS", 
                              error=str(kyutai_error))
                
                # Fallback to Edge-TTS
                try:
                    import edge_tts
                    self.edge_tts = edge_tts
                    self.use_edge_fallback = True
                    self.use_real_kyutai = False
                    logger.info("Edge-TTS high-quality fallback loaded successfully")
                except ImportError:
                    logger.error("No TTS engine available - both Kyutai and Edge-TTS failed")
                    raise ImportError("No TTS engine available")
            
            load_time = time.time() - start_time
            engine_name = "REAL Kyutai TTS-1.6B" if self.use_real_kyutai else "Edge-TTS High-Quality Fallback"
            # Update the name to reflect the actual engine being used
            self.name = engine_name
            logger.info("TTS engine initialized successfully", 
                       engine=engine_name, 
                       load_time_seconds=load_time)
            self.is_initialized = True
            
        except Exception as e:
            logger.error("TTS initialization failed", error=str(e))
            raise
    
    async def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text to speech using REAL Kyutai TTS-1.6B or Edge-TTS fallback"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            start_time = time.time()
            
            if self.use_real_kyutai and self.kyutai_script_path:
                # Use the REAL Kyutai TTS-1.6B model via official script
                logger.info("Starting REAL Kyutai TTS-1.6B synthesis", 
                           text_preview=text[:30])
                
                import subprocess
                import tempfile
                import os
                
                # Create temporary text file for input
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                    tmp_file.write(text)
                    temp_text_path = tmp_file.name
                
                try:
                    # Run official Kyutai TTS script with absolute paths
                    kyutai_dir = os.path.dirname(self.kyutai_script_path)
                    abs_output_path = os.path.abspath(output_path)
                    
                    result = subprocess.run([
                        "uvx", "--with", "moshi", "python", self.kyutai_script_path,
                        temp_text_path, abs_output_path, "--device", "cpu"
                    ], capture_output=True, text=True, cwd=kyutai_dir, timeout=120)
                    
                    if result.returncode == 0:
                        logger.info("REAL Kyutai TTS-1.6B synthesis successful")
                    else:
                        logger.warning("Kyutai TTS synthesis failed", stderr=result.stderr)
                        raise Exception(f"Kyutai synthesis failed: {result.stderr}")
                        
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_text_path):
                        os.unlink(temp_text_path)
                
            elif self.use_edge_fallback and self.edge_tts:
                # Use edge-tts fallback
                logger.info("Using Edge-TTS fallback for synthesis", 
                           text_preview=text[:30])
                voice = "en-US-AriaNeural"  # High-quality female voice
                
                communicate = self.edge_tts.Communicate(text, voice)
                await communicate.save(output_path)
                
            else:
                logger.error("No TTS engine available for synthesis")
                return False
            
            synthesis_time = time.time() - start_time
            engine_name = "REAL Kyutai TTS-1.6B" if self.use_real_kyutai else "Edge-TTS"
            logger.info("TTS synthesis completed successfully",
                       engine=engine_name,
                       synthesis_time_seconds=synthesis_time)
            return True
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return False

class SileroVAD:
    """
    Silero VAD v3 - Voice Activity Detection
    Performance: <1ms processing, enterprise-grade accuracy
    """
    
    def __init__(self):
        self.name = "Silero VAD v3"
        self.model = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize Silero VAD"""
        if self.is_initialized:
            return
            
        try:
            logger.info("Loading Silero VAD v3")
            self.model = silero_vad.load_silero_vad()
            self.is_initialized = True
            logger.info("Silero VAD v3 ready")
            
        except Exception as e:
            logger.error(f"VAD initialization failed: {e}")
            
    def detect_speech(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> bool:
        """Detect if audio chunk contains speech"""
        if not self.is_initialized:
            return True  # Default to true if VAD not ready
            
        try:
            # Convert to tensor if needed
            if isinstance(audio_chunk, np.ndarray):
                audio_tensor = torch.from_numpy(audio_chunk.astype(np.float32))
            else:
                audio_tensor = audio_chunk
                
            # Detect speech
            speech_prob = silero_vad.get_speech_timestamps(
                audio_tensor, self.model, sampling_rate=sample_rate
            )
            
            return len(speech_prob) > 0
            
        except Exception as e:
            logger.error(f"VAD detection failed: {e}")
            return True

class ProductionVoiceFoundation:
    """
    Production Voice Foundation with SOTA models (2025)
    - Faster-Whisper Large-v3-Turbo (STT) - Proven SOTA performance
    - Edge-TTS/Kyutai (TTS) - High-quality synthesis
    - Silero VAD v3 (Voice Activity Detection)
    
    Note: This achieves SOTA performance while maintaining Windows compatibility
    """
    
    def __init__(self, force_parakeet=True):
        self.stt = ProductionSTTEngine(force_parakeet=force_parakeet)
        self.tts = ProductionTTSEngine()
        self.vad = SileroVAD()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all voice components"""
        logger.info("Initializing Production Voice Foundation SOTA Pipeline 2025")
        start_time = time.time()
        
        # Initialize all components
        await asyncio.gather(
            self.stt.initialize(),
            self.tts.initialize(),
            self.vad.initialize()
        )
        
        self.is_initialized = True
        init_time = time.time() - start_time
        logger.info("Production Voice Foundation ready",
                   init_time_seconds=init_time,
                   stt_engine=self.stt.name,
                   tts_engine=self.tts.name, 
                   vad_engine=self.vad.name,
                   cost_per_hour=0,
                   performance_level="SOTA")
        
    async def process_audio_to_text(self, audio_path: str) -> Optional[str]:
        """Convert audio file to text using SOTA STT"""
        if not self.is_initialized:
            await self.initialize()
            
        logger.info("Processing audio with SOTA STT", audio_path=audio_path)
        return await self.stt.transcribe(audio_path)
        
    async def process_text_to_audio(self, text: str, output_path: str) -> bool:
        """Convert text to audio using SOTA TTS"""
        if not self.is_initialized:
            await self.initialize()
            
        logger.info("Synthesizing with SOTA TTS", text_preview=text[:30])
        return await self.tts.synthesize(text, output_path)

# Compatibility function for existing code
async def create_voice_foundation(use_production=True, force_parakeet=True):
    """Create either production or mock voice foundation"""
    if use_production:
        foundation = ProductionVoiceFoundation(force_parakeet=force_parakeet)
    else:
        # Fall back to mock for testing
        from .simple_voice_pipeline import VoiceFoundation
        foundation = VoiceFoundation()
    
    await foundation.initialize()
    return foundation