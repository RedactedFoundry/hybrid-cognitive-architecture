#!/usr/bin/env python3
"""
Orchestrator Response Synthesis - Final Response Generation

This module handles the synthesis of final responses from all cognitive layers,
implementing true 3-layer cognitive integration with fallback mechanisms.

This is separated for modularity so synthesis logic can be easily modified
as different AI models and response strategies become available.
"""

from datetime import datetime, timezone
from typing import Dict, Any, TYPE_CHECKING

import structlog
from langchain_core.messages import AIMessage

from config.models import COORDINATOR_MODEL
from clients.model_router import get_model_router
from core.verifier import run_verifier, violates_safety_floor

from .models import OrchestratorState, ProcessingPhase

# Type-only imports to avoid circular dependencies
if TYPE_CHECKING:
    from .orchestrator import UserFacingOrchestrator


class ResponseSynthesizer:
    """
    Handles the synthesis of final responses from all cognitive layers.
    
    This class integrates insights from:
    1. Pheromind Layer: Ambient patterns and contextual signals
    2. Council Layer: Multi-agent analytical deliberation  
    3. KIP Layer: Agent execution results and live data
    """
    
    def __init__(self, orchestrator: 'UserFacingOrchestrator'):
        """
        Initialize the response synthesizer.
        
        Args:
            orchestrator: The parent orchestrator instance
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger("ResponseSynthesizer")
    
    async def synthesize_response(self, state: OrchestratorState) -> OrchestratorState:
        """
        Synthesize final response from all processing layers.
        
        This implements true 3-layer cognitive synthesis:
        - Pheromind: Ambient patterns and contextual signals
        - Council: Multi-agent deliberation outcomes  
        - KIP: Agent execution results and tool outputs
        """
        self.logger.info(
            "Starting response synthesis from all cognitive layers",
            request_id=state.request_id,
            pheromind_signals=len(state.pheromind_signals),
            council_decision=bool(state.council_decision),
            kip_tasks=len(state.kip_tasks)
        )
        state.update_phase(ProcessingPhase.RESPONSE_SYNTHESIS)
        
        try:
            # Use model router (llama.cpp) for synthesis
            router = await get_model_router()
            
            # Gather insights from all 3 layers
            synthesis_context = await self._gather_synthesis_context(state)
            
            # Use coordinator model to synthesize final response
            synthesis_prompt = self._build_synthesis_prompt(state.user_input, synthesis_context)
            
            # Generate synthesized response using coordinator agent
            synthesis_suffix = (
                "Write a direct, conversational response that feels natural to read aloud.\n"
                "Do NOT include any role statements, preambles, or headings.\n"
                "Start with the answer, then add only the most useful details.\n"
                "Use short paragraphs; bullet points only if they improve clarity.\n"
                "Avoid phrases like 'as an AI' or 'as the coordinator'.\n"
            )
            synthesis_result = await router.generate(
                model_alias=COORDINATOR_MODEL,
                prompt=synthesis_prompt + "\n\n" + synthesis_suffix,
                max_tokens=800,
                temperature=0.3
            )
            
            state.final_response = str(synthesis_result.get("content", "")).strip()

            # Optional verifier pass (JSON gate) – only run if response is non-empty
            if state.final_response:
                verifier_result = await run_verifier(router, state.final_response)
                state.metadata["verifier"] = verifier_result.to_dict()
                if violates_safety_floor(verifier_result):
                    state.metadata["blocked_by_verifier"] = True
                    # Keep the text but flag it; UI/API can decide follow-up per Constitution v5.4
            
            # Store conversation in TigerGraph for future context
            await self._store_conversation_history(state)
            
            self.logger.info(
                "Response synthesis completed successfully",
                request_id=state.request_id,
                response_length=len(state.final_response),
                tokens_used=synthesis_result.get("usage", {}).get("total_tokens", 0)
            )
            
        except Exception as e:
            # Fallback to enhanced manual synthesis if LLM synthesis fails
            self.logger.warning(
                "LLM synthesis failed, using manual synthesis fallback",
                request_id=state.request_id,
                error=str(e)
            )
            state.final_response = self._manual_synthesis_fallback(state)
            
        state.add_message(AIMessage(content=state.final_response))
        state.update_phase(ProcessingPhase.COMPLETED)
        
        return state
    
    async def _gather_synthesis_context(self, state: OrchestratorState) -> Dict[str, Any]:
        """Gather structured context from all cognitive layers for synthesis."""
        context = {
            "pheromind_insights": [],
            "council_outcome": None,
            "kip_results": [],
            "metadata": {
                "processing_time": (datetime.now(timezone.utc) - state.started_at).total_seconds(),
                "request_id": state.request_id
            }
        }
        
        # Extract Pheromind insights
        if state.pheromind_signals:
            for signal in state.pheromind_signals:
                context["pheromind_insights"].append({
                    "pattern": signal.pattern_id,
                    "strength": signal.strength,
                    "content": signal.content,
                    "source": signal.source_agent
                })
        
        # Extract Council outcome
        if state.council_decision:
            context["council_outcome"] = {
                "decision": state.council_decision.outcome,
                "confidence": state.council_decision.confidence,
                "reasoning": state.council_decision.reasoning,
                "participants": state.council_decision.voting_agents
            }
        
        # Extract KIP results
        if state.kip_tasks:
            for task in state.kip_tasks:
                context["kip_results"].append({
                    "agent_id": task.agent_id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "result": task.result,
                    "execution_time": getattr(task, 'execution_time', None)
                })
        
        return context
    
    def _build_synthesis_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Build the synthesis prompt for the coordinator model."""
        # Check if any cognitive layers have data
        has_pheromind_data = bool(context["pheromind_insights"])
        has_council_data = bool(context["council_outcome"])  
        has_kip_data = bool(context["kip_results"])
        has_any_layer_data = has_pheromind_data or has_council_data or has_kip_data
        
        prompt_parts = [f"USER QUESTION: {user_input}", ""]
        
        # If no layers have data, use simple synthesis without cognitive layer framing
        if not has_any_layer_data:
            prompt_parts.extend([
                "The system has generated a comprehensive response to this question.",
                "Please review and refine the response to ensure it:",
                "1. Directly addresses the user's question",
                "2. Provides actionable advice or information", 
                "3. Maintains a helpful and professional tone",
                "4. Is well-organized and clear",
                "",
                "Do not mention cognitive layers, analysis processes, or system architecture.",
                "Focus purely on providing a helpful answer to the user's question.",
                "",
                "Response:"
            ])
        else:
            # Use cognitive analysis framing when layers have data
            prompt_parts.append("=== 3-LAYER COGNITIVE ANALYSIS ===")
            
            # Add Pheromind insights (only if available)
            if has_pheromind_data:
                prompt_parts.append("\n🧠 PHEROMIND LAYER (Ambient Patterns):")
                for insight in context["pheromind_insights"]:
                    prompt_parts.append(f"- Pattern '{insight['pattern']}' (strength: {insight['strength']:.2f}): {insight['content']}")
            
            # Add Council outcome (only if available)
            if has_council_data:
                council = context["council_outcome"]
                prompt_parts.extend([
                    "\n🏛️ COUNCIL LAYER (Multi-Agent Deliberation):",
                    f"Decision: {council['decision']}",
                    f"Confidence: {council['confidence']:.1%}",
                    f"Reasoning: {council['reasoning']}",
                    f"Participants: {', '.join(council['participants'])}"
                ])
            
            # Add KIP results (only if available)
            if has_kip_data:
                prompt_parts.append("\n⚡ KIP LAYER (Agent Execution Results):")
                for result in context["kip_results"]:
                    status_emoji = "✅" if result['status'] == "completed" else "❌" if result['status'] == "failed" else "⏳"
                    prompt_parts.append(f"{status_emoji} Agent {result['agent_id']} ({result['task_type']}): {result['result']}")
            
            prompt_parts.extend([
                "",
                "=== SYNTHESIS TASK ===",
                "Based on the analysis above, provide a comprehensive response that:",
                "1. Directly answers the user's question",
                "2. Integrates the most relevant insights from each layer",
                "3. Highlights any concrete data or results from KIP agent execution",
                "4. Acknowledges uncertainty if layers provide conflicting information",
                "",
                "Response:"
            ])
        
        return "\n".join(prompt_parts)
    
    def _manual_synthesis_fallback(self, state: OrchestratorState) -> str:
        """Manual synthesis fallback when LLM synthesis fails."""
        response_parts = [f"Based on your request: '{state.user_input}'"]
        
        # Add Pheromind insights
        if state.pheromind_signals:
            strongest_signals = sorted(state.pheromind_signals, key=lambda s: s.strength, reverse=True)[:2]
            patterns_text = ", ".join([f"{s.pattern_id} ({s.strength:.1%})" for s in strongest_signals])
            response_parts.append(f"I detected relevant patterns: {patterns_text}.")
        
        # Add Council outcome
        if state.council_decision:
            response_parts.append(f"After multi-agent deliberation, the council concluded: {state.council_decision.outcome}")
        
        # Add KIP results
        completed_tasks = [task for task in state.kip_tasks if task.status == "completed"]
        if completed_tasks:
            if any("bitcoin" in task.result.lower() or "crypto" in task.result.lower() for task in completed_tasks):
                # Include crypto data if available
                crypto_results = [task.result for task in completed_tasks if "bitcoin" in task.result.lower() or "$" in task.result]
                if crypto_results:
                    response_parts.append(f"Live data: {crypto_results[0]}")
            else:
                response_parts.append(f"I executed {len(completed_tasks)} analysis tasks to provide accurate information.")
        
        response_parts.append("I've integrated insights from all cognitive layers to provide this comprehensive response.")
        
        return " ".join(response_parts)
    
    async def _store_conversation_history(self, state: OrchestratorState) -> None:
        """Store conversation context in TigerGraph for future reference."""
        try:
            # This would integrate with TigerGraph to store conversation context
            # For now, we log the conversation for audit purposes
            self.logger.info(
                "Conversation processed and logged",
                request_id=state.request_id,
                user_input=state.user_input,
                final_response_length=len(state.final_response) if state.final_response else 0,
                processing_phases=state.current_phase.value,
                total_processing_time=(datetime.now(timezone.utc) - state.started_at).total_seconds()
            )
            # NOTE: TigerGraph conversation storage will be implemented in Sprint 5
            # This provides audit trails and conversation context for future sessions
        except Exception as e:
            self.logger.warning(
                "Failed to store conversation history",
                request_id=state.request_id,
                error=str(e)
            )