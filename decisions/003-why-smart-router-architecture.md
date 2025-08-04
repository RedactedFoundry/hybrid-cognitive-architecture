# ADR-003: Implement Smart Router Architecture for Cognitive Layer Orchestration

**Date**: 2024-12-10  
**Status**: Accepted  
**Deciders**: Project Lead

## Context

The Hybrid AI Council has three distinct cognitive layers (Pheromind, Council, KIP) that serve different purposes. Users need to interact with the system through natural language, but determining which layer should handle each request was becoming complex. The original approach used simple keyword matching and manual routing, which was inflexible and error-prone.

## Decision

**Implement a Smart Router architecture that uses intent classification to automatically route user requests to the appropriate cognitive layer.**

## Rationale

### Why Smart Router Architecture Won

1. **Intelligent Intent Classification**: Uses LLM to understand user intent and route appropriately
2. **Seamless User Experience**: Users don't need to know which layer handles what
3. **Scalable Architecture**: Easy to add new routing rules and cognitive layers
4. **Performance Optimization**: Fast response routing for simple queries
5. **Context Awareness**: Can consider conversation history and user patterns
6. **Graceful Degradation**: Falls back to appropriate default when intent is unclear

### Routing Strategy

**Fast Response Path**: Simple queries (weather, facts, calculations)  
**Pheromind Path**: Pattern discovery, ambient intelligence, background analysis  
**Council Path**: Complex decisions, multi-perspective analysis, deliberation  
**KIP Path**: Economic actions, agent management, financial operations

### Alternatives Considered

1. **Manual Layer Selection**: User explicitly chooses layer
   - **Rejected**: Poor user experience, requires deep system knowledge
   
2. **Round-Robin Routing**: Distribute requests evenly across layers
   - **Rejected**: Inefficient resource usage, inappropriate task assignment
   
3. **Keyword Matching**: Simple pattern matching for routing
   - **Rejected**: Brittle, difficult to maintain, poor accuracy
   
4. **Full Context Passing**: Send every request to all layers
   - **Rejected**: Expensive, slow, creates conflicting responses

## Consequences

### Positive
- ✅ **Intuitive User Experience**: Natural conversation without technical knowledge
- ✅ **Optimal Resource Usage**: Right layer handles appropriate tasks
- ✅ **Maintainable Routing Logic**: Centralized, configurable routing rules
- ✅ **Performance Benefits**: Fast path for simple queries
- ✅ **Extensible Design**: Easy to add new layers or routing criteria
- ✅ **Context-Aware Decisions**: Can consider conversation history

### Negative  
- ❌ **Additional Complexity**: New orchestration layer to maintain
- ❌ **LLM Dependency**: Routing depends on LLM performance and availability  
- ❌ **Potential Misrouting**: Intent classification may occasionally be wrong
- ❌ **Latency Overhead**: Classification step adds small delay
- ❌ **Debug Complexity**: Harder to trace which routing decision was made

### Neutral
- Same cognitive layers exist, just better organized
- Total system complexity similar to previous approach

## Implementation Notes

### Smart Router Components

**Intent Classifier**: Uses Qwen3-14B to analyze user intent and determine routing
**Node-Based Architecture**: Each cognitive layer implemented as processing nodes
**State Management**: Tracks conversation context and routing decisions
**Fallback Handling**: Default routing when intent classification fails

### Routing Node Types

1. **SmartRouterNode**: Main classification and routing logic
2. **FastResponseNode**: Quick answers for simple queries
3. **PheromindNode**: Ambient intelligence and pattern discovery
4. **CouncilNode**: Multi-agent deliberation and complex decisions
5. **KIPNode**: Economic actions and agent management

### Configuration

```python
# Route classification prompts in core/orchestrator/nodes/smart_router_nodes.py
ROUTING_PROMPT = """
Classify this user request into one of these categories:
- fast_response: Simple facts, calculations, weather
- pheromind: Pattern analysis, background research
- council: Complex decisions, pros/cons analysis  
- kip: Economic actions, agent management
"""
```

### Performance Metrics

- Intent classification accuracy: Target >95%
- Routing latency: <200ms for classification
- User satisfaction: Measured via conversation success rate

## References

- Implementation: `core/orchestrator/nodes/smart_router_nodes.py`
- State management: `core/orchestrator/state_machine.py`
- Documentation: `SMART_ROUTER_HANDOFF.md`
- Testing: `tests/test_smart_router.py`