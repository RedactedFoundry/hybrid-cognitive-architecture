# Decision: Coqui XTTS v2 for Hybrid AI Council Voice Synthesis

## Status: ACCEPTED ✅

Date: 2025-08-05
Deciders: Redacted Foundry (Solo Builder)
Tags: tts, voice-synthesis, real-time, multi-voice, council

## Context

The Hybrid AI Council requires a robust Text-to-Speech (TTS) solution that can:

1. Generate natural-sounding speech for multiple council members
2. Provide real-time synthesis for voice chat interactions  
3. Support voice cloning for distinct council member personalities
4. Run locally for privacy and cost control
5. Handle high-volume usage without per-character API costs

### Previous Issues

- Kyutai TTS: 30-50+ second synthesis times (unacceptable for real-time)
- Edge-TTS fallback: Failed to initialize properly
- API solutions: Expensive for projected 3M+ characters/month usage

## Decision

**We will implement Coqui XTTS v2 as our primary and ONLY TTS solution for MVP.**

## Rationale

### ✅ Perfect Fit for Council Architecture

- **Multi-voice support**: Each council member can have a distinct voice
- **Voice cloning**: Create unique personalities with just 3 seconds of audio
- **16 languages**: Supports global council operations
- **Cross-language voice cloning**: Same voice across different languages

### ✅ Performance Specifications

- **~200ms latency**: Excellent for real-time conversation (below human perception threshold)
- **24kHz high-quality audio**: Professional-grade output
- **Streaming inference**: Audio plays as it generates
- **Local deployment**: No network latency, unlimited usage

### ✅ Technical Advantages

- **Open-source**: Full control, no vendor lock-in
- **Hardware compatibility**: Runs efficiently on RTX 4090
- **Integration flexibility**: Python API for seamless voice pipeline integration
- **Cost-effective**: No per-character fees, unlimited local generation

### ✅ Business Benefits

- **Privacy**: All voice processing stays local
- **Scalability**: No usage limits or API rate limiting
- **Reliability**: No external dependencies or service outages
- **Cost predictable**: Fixed infrastructure costs only

## Implementation Plan

1. **Remove current TTS engines**: Clean out Kyutai and Edge-TTS implementations
2. **Install Coqui TTS**: Set up XTTS v2 with proper dependencies
3. **Voice foundation integration**: Replace broken voice pipeline with XTTS
4. **Multi-voice setup**: Configure distinct voices for different council members
5. **Performance optimization**: Tune for real-time streaming synthesis

## Consequences

### Positive

- ✅ Consistent 200ms response times
- ✅ Unlimited voice generation at fixed cost  
- ✅ Multiple distinct council member voices
- ✅ Full privacy and data control
- ✅ No external API dependencies

### Negative

- ⚠️ Local setup complexity (manageable with proper documentation)
- ⚠️ Requires local GPU resources (already available with RTX 4090)
- ⚠️ No cloud fallback (acceptable for MVP focus)

## Monitoring

- Response time metrics (target: <250ms end-to-end)
- Voice quality consistency across council members
- Resource usage optimization
- Integration stability with voice chat pipeline

## Notes

This decision prioritizes the core council architecture requirements over theoretical speed optimizations. The 160ms difference between XTTS (200ms) and fastest APIs (40ms) is imperceptible to humans, while the multi-voice capability is essential for the council concept.

**No backup TTS planned for MVP** - focus on making XTTS v2 work excellently rather than managing multiple systems.