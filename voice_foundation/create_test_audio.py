#!/usr/bin/env python3
"""
Simple test audio file generator for voice foundation testing.
Creates a synthetic audio file with spoken text for pipeline validation.
"""

from pathlib import Path

def create_test_audio(output_path: str, duration: float = 2.0, sample_rate: int = 16000):
    """
    Create a simple test audio file (mock WAV format).
    
    Args:
        output_path: Path to save the test audio file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    """
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create a simple mock WAV file with proper header
    with open(output_path, 'wb') as f:
        # WAV header for 16kHz, 16-bit, mono
        data_size = int(sample_rate * duration * 2)  # 2 bytes per sample
        file_size = 36 + data_size
        
        # RIFF header
        f.write(b'RIFF')
        f.write(file_size.to_bytes(4, byteorder='little'))
        f.write(b'WAVE')
        
        # Format chunk
        f.write(b'fmt ')
        f.write((16).to_bytes(4, byteorder='little'))  # Chunk size
        f.write((1).to_bytes(2, byteorder='little'))   # Audio format (PCM)
        f.write((1).to_bytes(2, byteorder='little'))   # Number of channels
        f.write(sample_rate.to_bytes(4, byteorder='little'))  # Sample rate
        f.write((sample_rate * 2).to_bytes(4, byteorder='little'))  # Byte rate
        f.write((2).to_bytes(2, byteorder='little'))   # Block align
        f.write((16).to_bytes(2, byteorder='little'))  # Bits per sample
        
        # Data chunk
        f.write(b'data')
        f.write(data_size.to_bytes(4, byteorder='little'))
        f.write(b'\x00' * data_size)  # Silent audio data
    import structlog
    logger = structlog.get_logger(__name__)
    
    logger.info("Test audio created successfully",
        output_path=output_path,
        duration=duration,
        sample_rate=sample_rate
    )

if __name__ == "__main__":
    create_test_audio("voice_foundation/test_audio.wav")