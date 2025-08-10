#!/usr/bin/env python3
"""
Council Processing Node - Multi-Agent Deliberation

This module contains the Council logic for multi-agent deliberation and reasoning.
The Council implements sophisticated multi-agent reasoning with different AI perspectives.
"""

import asyncio

from config.models import ANALYTICAL_MODEL, CREATIVE_MODEL, COORDINATOR_MODEL
from .base import CognitiveProcessingNode
from ..models import OrchestratorState, ProcessingPhase, CouncilDecision
from clients.model_router import get_model_router


class CouncilNode(CognitiveProcessingNode):
    """
    Council - Multi-Agent Deliberation Layer.
    
    This layer implements sophisticated multi-agent reasoning:
    1. Multiple AI agents analyze the user input concurrently
    2. Each agent provides their perspective and reasoning
    3. Agents critique each other's responses
    4. A final vote determines the best approach
    """
    
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process Council multi-agent deliberation."""
        return await self.council_deliberation_node(state)
    
    async def council_deliberation_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute Council-layer multi-agent deliberation using LLM integration.
        
        This implements a sophisticated multi-agent reasoning process:
        1. Multiple AI agents analyze the user input concurrently
        2. Each agent provides their perspective and reasoning
        3. Agents critique each other's responses
        4. A final vote determines the best approach
        """
        self.logger.debug("Starting Council deliberation with multi-agent reasoning")
        state.update_phase(ProcessingPhase.COUNCIL_DELIBERATION)
        
        try:
            # Initialize model router for hybrid LLM inference (llama.cpp + Ollama)
            router = await get_model_router()
            
            # Check if both backends are available
            health_status = await router.health_check_all()
            unhealthy_models = [model for model, healthy in health_status.items() if not healthy]
            if unhealthy_models:
                raise Exception(f"Some models are unavailable: {unhealthy_models}")
            
            # Define council agents with different perspectives
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
            
            user_question = state.user_input
            self.logger.info("Starting multi-agent council deliberation", agents=list(council_agents.keys()))
            
            # Phase 1: Concurrent initial responses
            self.logger.debug("Phase 1: Gathering initial agent responses")
            initial_responses = {}
            
            # Create concurrent tasks for each agent
            agent_tasks = []
            for agent_name, agent_config in council_agents.items():
                task = asyncio.create_task(
                    router.generate(
                        model_alias=agent_config["model"],
                        prompt=f"System: {agent_config['system_prompt']}\n\nUser question: {user_question}\n\nProvide your analysis and recommended approach:",
                        max_tokens=800,
                        temperature=0.7
                    ),
                    name=agent_name
                )
                agent_tasks.append((agent_name, task))
            
            # Wait for all initial responses
            for agent_name, task in agent_tasks:
                try:
                    response = await task
                    initial_responses[agent_name] = response["content"]
                    self.logger.debug("Received initial response", agent=agent_name, provider=response.get("provider"), usage=response.get("usage", {}))
                except Exception as e:
                    self.logger.warning("Agent response failed", agent=agent_name, error=str(e))
                    initial_responses[agent_name] = f"[Agent {agent_name} failed to respond: {str(e)}]"
            
            # Phase 2: Critique round
            self.logger.debug("Phase 2: Cross-agent critique")
            critiques = {}
            
            critique_tasks = []
            for critic_agent, critic_config in council_agents.items():
                # Each agent critiques the other agents' responses
                other_responses = {name: resp for name, resp in initial_responses.items() if name != critic_agent}
                
                if other_responses:
                    critique_prompt = f"""Review these responses from other council members to the user question: "{user_question}"

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
                        router.generate(
                            model_alias=critic_config["model"],
                            prompt=f"System: {critic_config['system_prompt']}\n\n{critique_prompt}",
                            max_tokens=600,
                            temperature=0.6
                        ),
                        name=f"{critic_agent}_critique"
                    )
                    critique_tasks.append((critic_agent, task))
            
            # Wait for all critiques
            for agent_name, task in critique_tasks:
                try:
                    response = await task
                    critiques[agent_name] = response["content"]
                    self.logger.debug("Received critique", agent=agent_name, provider=response.get("provider"), usage=response.get("usage", {}))
                except Exception as e:
                    self.logger.warning("Agent critique failed", agent=agent_name, error=str(e))
                    critiques[agent_name] = f"[Critique from {agent_name} failed: {str(e)}]"
            
            # Phase 3: Final voting and decision
            self.logger.debug("Phase 3: Final voting and decision synthesis")
            
            # Create voting prompt with all information
            voting_prompt = f"""As the Council Coordinator, review the complete deliberation and make a final decision.

ORIGINAL QUESTION: {user_question}

INITIAL RESPONSES:
"""
            for agent, response in initial_responses.items():
                voting_prompt += f"\n{agent.upper()}:\n{response}\n"
            
            voting_prompt += "\nCRITIQUES:\n"
            for agent, critique in critiques.items():
                voting_prompt += f"\n{agent.upper()} CRITIQUE:\n{critique}\n"
            
            voting_prompt += """
Based on this deliberation, provide:
1. The best synthesized approach incorporating insights from all agents
2. Your confidence level (0-1) in this decision
3. Brief reasoning for your choice
4. Which agent's initial approach was strongest and why

Format your response as:
DECISION: [Your synthesized approach]
CONFIDENCE: [0.0-1.0]
REASONING: [Your reasoning]
STRONGEST_AGENT: [agent_name because reasoning]
"""
            
            # Generate final decision using coordinator model
            final_decision_response = await router.generate(
                model_alias=COORDINATOR_MODEL,
                prompt=f"System: You are the Council Coordinator responsible for synthesizing multi-agent deliberations into final decisions.\n\n{voting_prompt}",
                max_tokens=800,
                temperature=0.5
            )
            
            # Parse the final decision
            decision_text = final_decision_response["content"]
            
            # Extract structured information (basic parsing)
            decision_lines = decision_text.split('\n')
            final_outcome = ""
            confidence = 0.8  # default
            reasoning = ""
            winning_agent = "analytical_agent"  # default
            
            for line in decision_lines:
                if line.startswith("DECISION:"):
                    final_outcome = line.replace("DECISION:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.replace("CONFIDENCE:", "").strip())
                    except:
                        confidence = 0.8
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()
                elif line.startswith("STRONGEST_AGENT:"):
                    agent_line = line.replace("STRONGEST_AGENT:", "").strip()
                    if "analytical_agent" in agent_line.lower():
                        winning_agent = "analytical_agent"
                    elif "creative_agent" in agent_line.lower():
                        winning_agent = "creative_agent"
            
            # If no structured decision was found, use the full response
            if not final_outcome:
                final_outcome = decision_text
                reasoning = "Full council deliberation synthesis"
            
            # Create comprehensive council decision
            council_decision = CouncilDecision(
                question=user_question,
                outcome=final_outcome,
                reasoning=reasoning,
                confidence=confidence,
                voting_agents=list(council_agents.keys()) + ["coordinator"],
                initial_responses=initial_responses,
                critiques=critiques,
                final_vote_scores={agent: 1.0 for agent in council_agents.keys()},  # All participated
                winning_agent=winning_agent
            )
            
            state.council_decision = council_decision
            
            # Add token usage tracking
            total_tokens = sum([
                len(resp.split()) * 1.3 for resp in initial_responses.values()
            ]) + sum([
                len(crit.split()) * 1.3 for crit in critiques.values()
            ]) + len(decision_text.split()) * 1.3
            
            state.metadata["council_tokens_used"] = int(total_tokens)
            state.metadata["council_agents"] = list(council_agents.keys())
            
            self.logger.info(
                "Council deliberation completed",
                confidence=confidence,
                winning_agent=winning_agent,
                total_tokens=int(total_tokens),
                agents_participated=len(council_agents)
            )
            
        except Exception as e:
            # Mark error in state - conditional routing will handle this
            error_msg = f"Council deliberation failed: {str(e)}"
            state.mark_error(error_msg)
            self.logger.error("Council deliberation error", error=error_msg)
        
        return state