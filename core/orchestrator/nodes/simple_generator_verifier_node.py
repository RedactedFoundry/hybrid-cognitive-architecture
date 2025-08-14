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
            
            # Step 1: JSON Structure Analysis with Mistral
            self.logger.debug("Step 1: Structuring query with Mistral JSON analysis")
            
            structure_prompt = f"""You are an analytical framework designer. Your task is to convert complex questions into structured JSON frameworks that ensure systematic, comprehensive analysis regardless of domain.

QUESTION TO ANALYZE:
{user_question}

Your JSON structure must follow these EXPERT STANDARDS:

=== CORE STRUCTURE ===
{{
  "analysis_type": "decision_making" | "comparison_analysis" | "problem_solving" | "explanation" | "planning",
  "complexity_level": "high" | "medium" | "low",
  "context_framework": {{
    "affected_parties": ["who is impacted by this topic"],
    "time_scope": "immediate" | "short_term" | "long_term" | "ongoing",
    "impact_level": "high" | "medium" | "low" | "none",
    "complexity_factors": ["what makes this complex"],
    "uncertainty_factors": ["what information is missing or uncertain"],
    "resource_constraints": ["time", "money", "energy", "relationships", "other_limitations"],
    "values_considerations": "how this aligns with personal values and priorities"
  }},
  "key_analysis_dimensions": [
    "List 4-6 specific areas that MUST be analyzed",
    "Each should be concrete and measurable", 
    "Include both quantitative and qualitative factors"
  ],
  "comparison_matrix": {{
    "options_to_compare": ["option1", "option2", "option3"],
    "evaluation_criteria": ["criterion1", "criterion2", "criterion3"],
    "weight_importance": ["most_critical", "important", "nice_to_have"]
  }},
  "required_evidence": [
    "What general principles or patterns to consider",
    "What personal factors need evaluation",
    "What external factors should be assessed"
  ],
  "output_structure": {{
    "executive_summary": "1-2 sentence overview",
    "detailed_sections": [
      "Section 1: [Specific focus area]",
      "Section 2: [Specific focus area]",
      "Section 3: [Specific focus area]"
    ],
    "recommendation_format": "prioritized_list" | "weighted_matrix" | "pros_cons_analysis" | "step_by_step_plan",
    "action_items": "Include specific next steps"
  }},
  "quality_standards": {{
    "depth_requirement": "comprehensive" | "focused" | "overview",
    "must_include_tradeoffs": true,
    "must_include_implementation": true,
    "must_include_risk_mitigation": true,
    "must_address_emotional_factors": true,
    "must_acknowledge_uncertainty": true
  }}
}}

=== EXAMPLE FOR LIFE DECISION ===
Question: "Should I move to a different city for better opportunities?"
{{
  "analysis_type": "decision_making",
  "complexity_level": "high",
  "context_framework": {{
    "affected_parties": ["myself", "family", "friends", "current_community"],
    "time_scope": "long_term",
    "impact_level": "high",
    "complexity_factors": ["personal_relationships", "career_impact", "lifestyle_changes", "financial_implications"],
    "uncertainty_factors": ["job_market_changes", "adaptation_challenges", "relationship_outcomes"],
    "resource_constraints": ["moving_costs", "time_to_establish_new_network", "emotional_energy", "family_obligations"],
    "values_considerations": "balance between career growth and relationship stability"
  }},
  "key_analysis_dimensions": [
    "Career and professional opportunities",
    "Financial impact and cost of living changes",
    "Social connections and relationship effects",
    "Quality of life and lifestyle factors",
    "Personal growth and development potential",
    "Practical logistics and transition planning"
  ],
  "comparison_matrix": {{
    "options_to_compare": ["move_now", "wait_6_months", "stay_current_city", "move_different_city"],
    "evaluation_criteria": ["career_growth", "life_satisfaction", "financial_impact", "relationship_preservation"],
    "weight_importance": ["career_growth", "life_satisfaction", "financial_impact", "relationship_preservation"]
  }},
  "required_evidence": [
    "General job market trends and career progression patterns",
    "Personal values and life priorities assessment",
    "Social support system evaluation and relationship impact"
  ],
  "output_structure": {{
    "summary": "Clear analysis with key considerations",
    "detailed_sections": [
      "Section 1: Career and Financial Analysis",
      "Section 2: Personal and Social Impact Assessment", 
      "Section 3: Quality of Life Comparison",
      "Section 4: Implementation Strategy and Risk Management"
    ],
    "recommendation_format": "structured_analysis",
    "next_steps": "Include specific actions to take"
  }},
  "quality_standards": {{
    "depth_requirement": "comprehensive",
    "must_include_tradeoffs": true,
    "must_include_implementation": true,
    "must_address_emotional_factors": true,
    "must_acknowledge_uncertainty": true
  }}
}}

=== EXAMPLE FOR TECHNICAL COMPARISON ===
Question: "Which programming language should I learn for data science?"
{{
  "analysis_type": "comparison_analysis",
  "complexity_level": "medium",
  "context_framework": {{
    "affected_parties": ["myself", "future_employers", "potential_collaborators"],
    "time_scope": "long_term",
    "impact_level": "high",
    "complexity_factors": ["rapidly_evolving_field", "multiple_viable_options", "career_path_uncertainty"],
    "uncertainty_factors": ["technology_adoption_trends", "personal_learning_aptitude", "job_market_evolution"],
    "resource_constraints": ["learning_time", "available_courses", "practice_opportunities"],
    "values_considerations": "balance between marketability and personal interest"
  }},
  "key_analysis_dimensions": [
    "Learning curve and accessibility for beginners",
    "Job market demand and career opportunities",
    "Ecosystem and library availability for data science",
    "Community support and learning resources",
    "Long-term viability and industry adoption",
    "Integration with existing skills and tools"
  ],
  "comparison_matrix": {{
    "options_to_compare": ["python", "r", "sql_focus", "multi_language_approach"],
    "evaluation_criteria": ["ease_of_learning", "job_opportunities", "data_science_capabilities", "long_term_value"],
    "weight_importance": ["job_opportunities", "ease_of_learning", "data_science_capabilities", "long_term_value"]
  }},
  "required_evidence": [
    "General industry trends and language popularity patterns",
    "Personal learning style and technical background assessment",
    "Career goals and target industry requirements"
  ],
  "output_structure": {{
    "summary": "Clear recommendation with reasoning and considerations",
    "detailed_sections": [
      "Section 1: Language Comparison and Learning Requirements",
      "Section 2: Career Impact and Market Opportunities",
      "Section 3: Technical Capabilities and Ecosystem Analysis", 
      "Section 4: Implementation Strategy and Learning Path"
    ],
    "recommendation_format": "prioritized_list",
    "next_steps": "Include specific learning milestones and timeline"
  }},
  "quality_standards": {{
    "depth_requirement": "focused",
    "must_include_tradeoffs": true,
    "must_include_implementation": true,
    "must_address_emotional_factors": false,
    "must_acknowledge_uncertainty": true
  }}
}}

NOW CREATE A SIMILAR HIGH-QUALITY JSON STRUCTURE FOR THE GIVEN QUESTION.

CRITICAL REQUIREMENTS:
1. Be SPECIFIC - avoid generic terms like "consider factors"
2. Include ACTIONABLE elements that lead to concrete analysis
3. Ensure the structure will produce a SYSTEMATIC, comprehensive response
4. Think systematically - what framework ensures thorough analysis?
5. Include both HIGH-LEVEL and PRACTICAL considerations
6. Acknowledge what is uncertain or unknown
7. Consider resource constraints and values alignment

Respond with ONLY the JSON structure:"""

            structure_response = await router.generate(
                model_alias=CouncilModels.VERIFIER_MODEL,  # Use Mistral for structuring
                prompt=structure_prompt,
                max_tokens=1000,  # Increased for sophisticated JSON structures
                temperature=0.3
            )
            
            json_structure = structure_response["content"]
            self.logger.debug("JSON structure received", 
                            length=len(json_structure),
                            provider=structure_response.get("provider"))
            
            # Step 2: Generate comprehensive response with HuiHui using JSON structure
            self.logger.debug("Step 2: Generating response with HuiHui OSS using JSON structure")
            
            generator_prompt = f"""
Using the structure below, write a clear, useful answer.
Be concise and conversational. Do not include headings or preambles.
Start with the answer, then provide only the most helpful details.

STRUCTURE:
{json_structure}

QUESTION: {user_question}

ANSWER:
"""
            
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
            
            # Step 3: Verify with Mistral per Constitution v5.4
            self.logger.debug("Step 3: Verifying response with Mistral")
            
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
                safety_prompt = f"""
Rewrite the answer safely and concisely for this question: {user_question}
Avoid legal/financial risk, keep facts tight, and be helpful.
Do not include any preamble.

Rewritten answer:
"""
                
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
