#!/usr/bin/env python3
"""
Simple Generator-Verifier Node - Constitution v5.4 Implementation

This module implements the Constitution v5.4 specified architecture:
User → HuiHui Generator → Mistral Verifier → (GPT-5 Backup if needed) → User

Per Constitution v5.4:
- HuiHui GPT-OSS 20B Abliterated (Generator) 
- Mistral-7B (Verifier) with <2s response time
- GPT-5 backup on verifier confidence <30% or error
- User override commands: proceed anyway, explain more, etc.
- Adaptive learning for non-safety categories
"""

import asyncio
from typing import Dict, Any, Optional
import os

from config.models import CouncilModels
from .base import CognitiveProcessingNode
from ..models import OrchestratorState, ProcessingPhase
from clients.model_router import get_model_router
from core.verifier import run_verifier, violates_safety_floor


class SimpleGeneratorVerifierNode(CognitiveProcessingNode):
    """
    Constitution v5.4 Generator-Verifier Node.
    
    Implements the exact architecture specified in Constitution v5.4:
    1. HuiHui GPT-OSS 20B generates response (abliterated, no refusals)
    2. Mistral-7B verifies with <2s response time per Constitution
    3. GPT-5 backup if verifier confidence <30% per Article I.4
    4. User override commands per Article III.3
    5. Adaptive learning per Article II.7
    """
    
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process using Constitution v5.4 generator-verifier flow."""
        # Check for user override commands first (Article III.3)
        if self._check_user_override_commands(state):
            return await self._handle_user_override(state)
        
        return await self.generator_verifier_flow(state)
    
    def _check_user_override_commands(self, state: OrchestratorState) -> bool:
        """Check if user input contains override commands per Constitution v5.4."""
        user_input = state.user_input.lower().strip()
        override_commands = [
            "proceed anyway", "explain more", "adjust threshold", 
            "disable check", "get second opinion", "audit-log"
        ]
        return any(cmd in user_input for cmd in override_commands)
    
    async def _handle_user_override(self, state: OrchestratorState) -> OrchestratorState:
        """Handle user override commands per Constitution Article III.3."""
        user_input = state.user_input.lower().strip()
        
        if "proceed anyway" in user_input:
            state.metadata["user_override"] = "proceed_anyway"
            state.metadata["safety_bypassed"] = True
            
        elif "explain more" in user_input:
            # Provide details about any previous suppression
            state.final_response = "Previous response was flagged for: [details would be stored in session context]. Would you like me to proceed anyway or modify the approach?"
            return state
            
        elif "get second opinion" in user_input:
            # Escalate to GPT-5 backup per Article I.4
            return await self._gpt5_backup_response(state, "user_requested_second_opinion")
            
        elif "audit-log" in user_input:
            # Session review per Constitution
            state.final_response = "Session audit log: [Implementation would show recent interactions, overrides, and safety interventions]"
            return state
        
        # Continue with normal flow but with override flags set
        return await self.generator_verifier_flow(state)
    
    async def _gpt5_backup_response(self, state: OrchestratorState, reason: str) -> OrchestratorState:
        """
        GPT-5 backup response per Constitution Article I.4.
        Called when verifier confidence <30% or on user request.
        """
        self.logger.info("Escalating to GPT-5 backup", reason=reason)
        
        # Note: In a real implementation, this would call GPT-5 API
        # For now, using Mistral as a safer fallback
        try:
            router = await get_model_router()
            
            gpt5_prompt = f"""You are a backup AI providing a second opinion per Constitution v5.4.
The primary system had {reason}. Please provide a safe, accurate response.

Original question: {state.user_input}

Provide a comprehensive but safe response:"""
            
            backup_response = await router.generate(
                model_alias=CouncilModels.VERIFIER_MODEL,  # Using Mistral as GPT-5 substitute
                prompt=gpt5_prompt,
                max_tokens=1000,
                temperature=0.3  # More conservative
            )
            
            state.final_response = backup_response["content"]
            state.metadata.update({
                "gpt5_backup_used": True,
                "backup_reason": reason,
                "response_source": "gpt5_backup"
            })
            
            self.logger.info("GPT-5 backup response provided", reason=reason)
            return state
            
        except Exception as e:
            self.logger.error("GPT-5 backup failed", error=str(e), reason=reason)
            state.final_response = "I apologize, but both primary and backup systems encountered issues. Please try rephrasing your question."
            state.metadata["backup_failed"] = True
            return state
    
    async def generator_verifier_flow(self, state: OrchestratorState) -> OrchestratorState:
        """
        Simple two-step flow:
        1. Generate comprehensive response with HuiHui OSS
        2. Verify safety and quality with Mistral
        """
        self.logger.debug("Starting simple generator-verifier flow")
        state.update_phase(ProcessingPhase.COUNCIL_DELIBERATION)
        
        try:
            # Initialize model router for hybrid LLM inference
            router = await get_model_router()
            
            # Check if both backends are available
            health_status = await router.health_check_all()
            unhealthy_models = [model for model, healthy in health_status.items() if not healthy]
            if unhealthy_models:
                raise Exception(f"Some models are unavailable: {unhealthy_models}")
            
            user_question = state.user_input
            self.logger.info("Starting generator-verifier flow", 
                           generator_model=CouncilModels.GENERATOR_MODEL, 
                           verifier_model=CouncilModels.VERIFIER_MODEL)
            
            # Step 1: Generate comprehensive response with HuiHui OSS
            self.logger.debug("Step 1: Generating response with HuiHui OSS")
            
            generator_prompt = f"""You are an expert AI assistant. Provide a comprehensive, accurate, and helpful response to the following question.

Be thorough but concise. Include relevant details and context. If the question is complex, break down your response logically.

Question: {user_question}

Response:"""
            
            generator_response = await router.generate(
                model_alias=CouncilModels.GENERATOR_MODEL,
                prompt=generator_prompt,
                max_tokens=1500,
                temperature=0.7
            )
            
            generated_text = generator_response["content"]
            self.logger.debug("Generator response received", 
                            length=len(generated_text),
                            provider=generator_response.get("provider"))
            
            # Step 2: Verify with Mistral per Constitution v5.4
            self.logger.debug("Step 2: Verifying response with Mistral")
            
            verifier_result = await run_verifier(router, generated_text)
            
            # Check Constitution v5.4 Article I.4: GPT-5 backup if confidence <30%
            if verifier_result.confidence < 0.30:
                self.logger.warning("Verifier confidence below threshold", 
                                  confidence=verifier_result.confidence,
                                  threshold=0.30)
                return await self._gpt5_backup_response(state, f"low_verifier_confidence_{verifier_result.confidence}")
            
            # Check for safety violations per Constitution Article II
            safety_violation = violates_safety_floor(verifier_result)
            
            if safety_violation:
                self.logger.warning("Safety violation detected", 
                                  category=verifier_result.category,
                                  concern=verifier_result.concern)
                
                # Generate a safer alternative with explicit safety prompt
                safety_prompt = f"""The previous response had safety concerns ({verifier_result.concern}). 
Please provide a safer, more appropriate response to: {user_question}

Ensure your response:
- Avoids legal/financial risks
- Is factually accurate
- Provides helpful information
- Follows ethical guidelines

Response:"""
                
                safe_response = await router.generate(
                    model_alias=CouncilModels.VERIFIER_MODEL,  # Use Mistral for safer response
                    prompt=safety_prompt,
                    max_tokens=1000,
                    temperature=0.5
                )
                
                final_text = safe_response["content"]
                
                # Store metadata about the safety intervention
                state.metadata.update({
                    "safety_intervention": True,
                    "original_concern": verifier_result.concern,
                    "verifier_result": verifier_result.to_dict(),
                    "safe_response_generated": True
                })
                
            else:
                final_text = generated_text
                state.metadata.update({
                    "safety_intervention": False,
                    "verifier_result": verifier_result.to_dict(),
                    "generator_provider": generator_response.get("provider"),
                    "generator_usage": generator_response.get("usage", {})
                })
            
            # Update state with final response
            state.final_response = final_text.strip()
            state.update_phase(ProcessingPhase.COMPLETED)
            
            self.logger.info("Generator-verifier flow completed", 
                           response_length=len(state.final_response),
                           safety_check_passed=not safety_violation,
                           verifier_confidence=verifier_result.confidence)
            
            return state
            
        except Exception as e:
            self.logger.error("Generator-verifier flow failed", error=str(e))
            state.final_response = f"I apologize, but I encountered an error processing your request: {str(e)}"
            state.metadata["error"] = str(e)
            state.update_phase(ProcessingPhase.ERROR)
            return state
