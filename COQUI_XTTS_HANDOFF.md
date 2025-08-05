# 🎤 Coqui XTTS v2 Implementation Handoff

> **Date**: August 5, 2025 @ 9:30pm  
> **Status**: Ready to implement - decision locked, voice foundation currently broken  
> **Priority**: HIGH - Fix broken voice chat functionality

## 🔒 **LOCKED DECISION**

**Coqui XTTS v2** is the chosen TTS solution for Hybrid AI Council (no backup APIs for MVP).

**Documentation**: `decisions/004-coqui-xtts-v2-for-council-voices.md`

## ❌ **Current Issue**

Voice foundation returns `None` - voice chat completely broken:
```
AttributeError: 'NoneType' object has no attribute 'process_audio_to_text'
```

**Root Cause**: Kyutai TTS disabled for performance (30-50s synthesis), Edge-TTS fallback failed to initialize.

## ✅ **What We Have**

- ✅ **Parakeet STT**: Working (NVIDIA NeMo, extracts clean text)
- ✅ **Smart Router**: Working (200ms text generation)  
- ✅ **Multi-model Council**: All 3 LLMs operational
- ✅ **Microphone Selection**: Fixed device selection UI
- ❌ **TTS**: Completely broken (returns None)

## 🎯 **Next Steps**

### **1. Install Coqui TTS**
```bash
poetry add TTS
```

### **2. Replace Broken TTS in Voice Foundation**
File: `voice_foundation/production_voice_engines.py`
- Remove Kyutai TTS forced exception
- Remove Edge-TTS fallback  
- Implement XTTS v2 as primary engine

### **3. Expected Performance**
- **Target**: 200ms synthesis (vs current broken state)
- **Quality**: 24kHz professional audio
- **Multi-voice**: Different voices for council members

## 📁 **Key Files to Modify**

1. `voice_foundation/production_voice_engines.py` - Replace TTS engine
2. `endpoints/voice.py` - Voice orchestrator initialization 
3. `websocket_handlers/voice_handlers.py` - Voice processing pipeline

## 🧠 **Why XTTS v2**

- **Multi-voice critical** for council architecture (different members = different voices)
- **200ms latency** perfectly acceptable for business conversations  
- **Local + unlimited** usage fits heavy-usage business model
- **Voice cloning** for distinct council personalities

## 📊 **Current Server**

Running on port 8007 - server stopped due to broken voice foundation.

## 🚀 **Goal**

Get voice chat working with Coqui XTTS v2 - clean implementation, no backup systems for MVP focus.