#!/usr/bin/env python3
"""
Orchestrator Streaming - Real-time Event Processing

This module handles real-time streaming of the orchestrator processing stages,
essential for voice interactions and responsive UI experiences.

The streaming system provides token-by-token generation and phase updates
that enable natural conversational interfaces.
"""

import asyncio
import uuid
from typing import AsyncGenerator, Optional, TYPE_CHECKING

import structlog

from config.models import ANALYTICAL_MODEL, CREATIVE_MODEL, COORDINATOR_MODEL
from clients.ollama_client import get_ollama_client

from .models import (
    StreamEvent, StreamEventType, ProcessingPhase
)

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .orchestrator import UserFacingOrchestrator


class StreamingProcessor:
    """
    Handles real-time streaming of orchestrator processing.
    
    This class provides token-by-token streaming and phase updates
    for voice interactions and responsive user interfaces.
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize the streaming processor.
        
        Args:
            orchestrator: The parent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger("StreamingProcessor")
    
    async def process_request_stream(
        self, 
        user_input: str, 
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream processing events for user requests in real-time.
        
        This method provides token-by-token streaming essential for voice interactions
        and real-time UI updates. It yields events for phase transitions, individual
        tokens, and completion status.
        
        Args:
            user_input: The user's input message or question
            conversation_id: Optional conversation ID for context
            
        Yields:
            StreamEvent objects containing phase updates, tokens, and metadata
            
        Raises:
            RuntimeError: If the orchestrator is not properly initialized
        """
        if not self.orchestrator._initialized or not self.orchestrator.graph:
            raise RuntimeError("Orchestrator not properly initialized")
        
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        conversation_id = conversation_id or str(uuid.uuid4())
        
        self.logger = self.logger.bind(request_id=request_id, conversation_id=conversation_id)
        self.logger.info("Starting streaming request processing", user_input_preview=user_input[:100])
        
        try:
            # Yield initialization event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🔍 Initializing request processing...",
                phase=ProcessingPhase.INITIALIZATION,
                request_id=request_id,
                metadata={"input_length": len(user_input)}
            )
            
            # Yield pheromind scanning event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🧠 Pheromind scanning for ambient patterns...",
                phase=ProcessingPhase.PHEROMIND_SCAN,
                request_id=request_id
            )
            
            # Yield council deliberation start event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="⚖️ AI Council beginning multi-agent deliberation...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id
            )
            
            # Process through council deliberation with streaming
            async for event in self._stream_council_deliberation(user_input, request_id):
                yield event
            
            # Yield completion event
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="✅ Processing completed",
                phase=ProcessingPhase.COMPLETED,
                request_id=request_id
            )
            
        except Exception as e:
            self.logger.error("Streaming request processing failed", error=str(e), exc_info=True)
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                content=f"Processing failed: {str(e)}",
                phase=ProcessingPhase.ERROR,
                request_id=request_id,
                metadata={"error": str(e)}
            )
    
    async def _stream_council_deliberation(
        self, 
        user_input: str, 
        request_id: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream the council deliberation process with real-time token generation.
        
        This method handles the multi-agent reasoning process while streaming
        the final response token-by-token for immediate voice/UI consumption.
        
        Args:
            user_input: The user's input to process
            request_id: Request ID for tracking
            
        Yields:
            StreamEvent objects for agent updates and tokens
        """
        try:
            # Initialize Ollama client
            ollama_client = get_ollama_client()
            
            if not await ollama_client.health_check():
                raise Exception("Ollama service is not available")
            
            # Define council agents
            council_agents = {
                "analytical_agent": {
                    "model": ANALYTICAL_MODEL,
                    "system_prompt": """You are the Analytical Agent in an AI Council. Your role is to provide logical, data-driven analysis.
Focus on:
- Breaking down complex problems into components
- Identifying key facts and assumptions
- Logical reasoning and cause-effect relationships
- Practical implementation considerations
Be precise, methodical, and evidence-based in your analysis.""",
                    "description": "Analytical reasoning specialist"
                },
                "creative_agent": {
                    "model": CREATIVE_MODEL, 
                    "system_prompt": """You are the Creative Agent in an AI Council. Your role is to provide innovative, outside-the-box thinking.
Focus on:
- Alternative approaches and novel solutions
- Creative connections between concepts
- User experience and emotional considerations
- Exploring possibilities others might miss
Be imaginative, user-focused, and think beyond conventional solutions.""",
                    "description": "Creative problem-solving specialist"
                }
            }
            
            # Phase 1: Concurrent initial responses (FAST multi-agent processing)
            self.logger.debug("Phase 1: Gathering concurrent agent responses")
            initial_responses = {}
            
            # Send start notifications for all agents
            for agent_name in council_agents.keys():
                yield StreamEvent(
                    event_type=StreamEventType.AGENT_START,
                    content=f"🤖 {agent_name} analyzing concurrently...",
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    agent=agent_name,
                    request_id=request_id
                )
            
            # Create concurrent tasks for ALL agents (this is the key optimization!)
            agent_tasks = []
            for agent_name, agent_config in council_agents.items():
                task = asyncio.create_task(
                    ollama_client.generate_response(
                        prompt=f"User question: {user_input}\n\nProvide your analysis and recommended approach:",
                        model_alias=agent_config["model"],
                        system_prompt=agent_config["system_prompt"],
                        max_tokens=600,
                        temperature=0.7,
                        timeout=30.0
                    ),
                    name=agent_name
                )
                agent_tasks.append((agent_name, task))
            
            # Wait for all concurrent responses and stream completion events
            for agent_name, task in agent_tasks:
                try:
                    response = await task
                    if response.success:
                        initial_responses[agent_name] = response.text
                        yield StreamEvent(
                            event_type=StreamEventType.AGENT_COMPLETE,
                            content=f"✅ {agent_name} analysis complete ({response.tokens_generated} tokens)",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"tokens": response.tokens_generated, "generation_time": response.generation_time}
                        )
                    else:
                        initial_responses[agent_name] = f"[{agent_name} failed to respond]"
                        yield StreamEvent(
                            event_type=StreamEventType.ERROR,
                            content=f"❌ {agent_name} failed to respond",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"error": response.error}
                        )
                except Exception as e:
                    initial_responses[agent_name] = f"[{agent_name} failed to respond: {str(e)}]"
                    yield StreamEvent(
                        event_type=StreamEventType.ERROR,
                        content=f"❌ {agent_name} exception: {str(e)}",
                        phase=ProcessingPhase.COUNCIL_DELIBERATION,
                        agent=agent_name,
                        request_id=request_id,
                        metadata={"error": str(e)}
                    )
            
            # Phase 2: Cross-Agent Critique Round
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🤝 Phase 2: Cross-agent critique round beginning...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id
            )
            
            critiques = {}
            
            # Send critique start notifications for all agents
            for agent_name in council_agents.keys():
                yield StreamEvent(
                    event_type=StreamEventType.AGENT_START,
                    content=f"🔍 {agent_name} critiquing other agents' responses...",
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    agent=agent_name,
                    request_id=request_id
                )
            
            # Create concurrent critique tasks for ALL agents
            critique_tasks = []
            for critic_agent, critic_config in council_agents.items():
                # Each agent critiques the other agents' responses
                other_responses = {name: resp for name, resp in initial_responses.items() if name != critic_agent}
                
                if other_responses:
                    critique_prompt = f"""Review these responses from other council members to the user question: "{user_input}"

Other responses:
"""
                    for other_agent, other_response in other_responses.items():
                        critique_prompt += f"\n{other_agent.upper()}:\n{other_response}\n"
                    
                    critique_prompt += f"""
As the {critic_config['description']}, provide constructive criticism:
1. What are the strengths of these approaches?
2. What potential issues or blind spots do you see?
3. How could these responses be improved?
4. What important aspects might be missing?

Be specific and constructive in your feedback."""

                    task = asyncio.create_task(
                        ollama_client.generate_response(
                            prompt=critique_prompt,
                            model_alias=critic_config["model"],
                            system_prompt=critic_config["system_prompt"],
                            max_tokens=600,
                            temperature=0.6,
                            timeout=45.0
                        ),
                        name=f"{critic_agent}_critique"
                    )
                    critique_tasks.append((critic_agent, task))
            
            # Wait for all concurrent critiques and stream completion events
            for agent_name, task in critique_tasks:
                try:
                    response = await task
                    if response.success:
                        critiques[agent_name] = response.text
                        yield StreamEvent(
                            event_type=StreamEventType.AGENT_COMPLETE,
                            content=f"✅ {agent_name} critique complete ({response.tokens_generated} tokens)",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"tokens": response.tokens_generated, "generation_time": response.generation_time}
                        )
                    else:
                        critiques[agent_name] = f"[Critique from {agent_name} failed]"
                        yield StreamEvent(
                            event_type=StreamEventType.ERROR,
                            content=f"❌ {agent_name} critique failed",
                            phase=ProcessingPhase.COUNCIL_DELIBERATION,
                            agent=agent_name,
                            request_id=request_id,
                            metadata={"error": response.error}
                        )
                except Exception as e:
                    critiques[agent_name] = f"[Critique from {agent_name} failed: {str(e)}]"
                    yield StreamEvent(
                        event_type=StreamEventType.ERROR,
                        content=f"❌ {agent_name} critique exception: {str(e)}",
                        phase=ProcessingPhase.COUNCIL_DELIBERATION,
                        agent=agent_name,
                        request_id=request_id,
                        metadata={"error": str(e)}
                    )
            
            # Phase 3: Enhanced Final Synthesis with Critiques
            yield StreamEvent(
                event_type=StreamEventType.PHASE_UPDATE,
                content="🧠 Phase 3: Council Coordinator synthesizing with critiques...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id
            )
            
            yield StreamEvent(
                event_type=StreamEventType.AGENT_START,
                content="🧠 Council Coordinator synthesizing final response with all perspectives...",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                agent="coordinator",
                request_id=request_id
            )
            
            # Create enhanced synthesis prompt with critiques
            synthesis_prompt = f"""As the Council Coordinator, review the complete deliberation and provide the best possible final response.

ORIGINAL QUESTION: {user_input}

INITIAL AGENT RESPONSES:
"""
            for agent, response in initial_responses.items():
                synthesis_prompt += f"\n{agent.upper()}:\n{response}\n"
            
            synthesis_prompt += "\nAGENT CRITIQUES:\n"
            for agent, critique in critiques.items():
                synthesis_prompt += f"\n{agent.upper()} CRITIQUE:\n{critique}\n"
            
            synthesis_prompt += """
Based on this complete deliberation (initial responses AND critiques), synthesize the most accurate, nuanced, and helpful final response. Incorporate the best insights from all perspectives while addressing any valid concerns raised in the critiques. Be comprehensive, accurate, and engaging."""
            
            # Stream the final response token by token
            full_response = ""
            async for token in ollama_client.generate_response_stream(
                prompt=synthesis_prompt,
                model_alias=COORDINATOR_MODEL,
                system_prompt="You are the Council Coordinator responsible for synthesizing multi-agent deliberations into final, helpful responses.",
                max_tokens=800,
                temperature=0.6,
                timeout=60.0
            ):
                full_response += token
                yield StreamEvent(
                    event_type=StreamEventType.TOKEN,
                    content=token,
                    phase=ProcessingPhase.COUNCIL_DELIBERATION,
                    agent="coordinator",
                    request_id=request_id
                )
            
            # Final response complete
            yield StreamEvent(
                event_type=StreamEventType.FINAL_RESPONSE,
                content=full_response,
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                agent="coordinator",
                request_id=request_id,
                metadata={
                    "agents_participated": list(council_agents.keys()),
                    "response_length": len(full_response),
                    "total_tokens": len(full_response.split()) * 1.3  # Rough estimate
                }
            )
            
        except Exception as e:
            self.logger.error("Council deliberation streaming failed", error=str(e))
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                content=f"Council deliberation failed: {str(e)}",
                phase=ProcessingPhase.COUNCIL_DELIBERATION,
                request_id=request_id,
                metadata={"error": str(e)}
            )