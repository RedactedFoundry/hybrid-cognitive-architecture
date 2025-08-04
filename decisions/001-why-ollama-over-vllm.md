# ADR-001: Use Ollama Over vLLM for Local Model Serving

**Date**: 2024-12-15  
**Status**: Accepted  
**Deciders**: Project Lead

## Context

The Hybrid AI Council requires local LLM serving for autonomous agent operations. Two main options were considered for multi-model serving: vLLM and Ollama. The system needs to run multiple specialized models (Qwen3-14B for reasoning, DeepSeek-Coder-6.7B for coding, Mistral-7B for general tasks) efficiently on local hardware.

## Decision

**Use Ollama for local model serving instead of vLLM.**

## Rationale

### Why Ollama Won

1. **Simpler Multi-Model Management**: Ollama provides built-in model switching and management
2. **Better Resource Efficiency**: Lower memory overhead for model switching
3. **Easier Development**: Simple API and Docker integration
4. **Proven Stability**: More reliable for production autonomous operations
5. **Active Community**: Better documentation and community support

### Alternatives Considered

1. **vLLM**: High-performance serving but complex multi-model setup
   - **Rejected**: Required custom model switching logic and higher memory usage
   
2. **Hugging Face Transformers**: Direct model loading
   - **Rejected**: No serving infrastructure, would need custom API layer
   
3. **OpenAI API**: Cloud-based serving
   - **Rejected**: Latency issues and cost concerns for autonomous agents

## Consequences

### Positive
- ✅ **Simplified Architecture**: No custom model switching logic needed
- ✅ **Lower Operational Overhead**: Built-in model management
- ✅ **Better Development Experience**: Easier testing and debugging
- ✅ **Reduced Memory Usage**: Efficient model swapping
- ✅ **Production Stability**: Proven reliability for autonomous operations

### Negative  
- ❌ **Potentially Lower Throughput**: vLLM might be faster for high-volume serving
- ❌ **Less Fine-Grained Control**: More abstracted than direct vLLM usage
- ❌ **Vendor Lock-in**: Tied to Ollama's API and model format

### Neutral
- Model loading times similar between options
- Both support the required model types (Qwen, DeepSeek, Mistral)

## Implementation Notes

- Docker Compose configuration using `ollama/ollama` image
- Models pulled on first startup: `qwen2.5:14b`, `deepseek-coder:6.7b`, `mistral:7b`
- API endpoint: `http://localhost:11434/api/chat`
- Health check endpoint: `http://localhost:11434/api/tags`
- Model switching via `model` parameter in API calls

## References

- [Ollama Documentation](https://ollama.ai/docs)
- [vLLM vs Ollama Comparison](https://docs.vllm.ai/en/latest/)
- Project dev-log entries documenting the transition