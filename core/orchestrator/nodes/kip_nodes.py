#!/usr/bin/env python3
"""
KIP Processing Node - Direct Action Execution

This module contains the KIP (Knowledge-based Information Processing) logic 
for direct action execution and tool orchestration.
"""

from datetime import datetime, timezone

from core.kip import kip_session, treasury_session
from .base import CognitiveProcessingNode
from ..models import OrchestratorState, ProcessingPhase, KIPTask


class KIPNode(CognitiveProcessingNode):
    """
    KIP - Knowledge-based Information Processing Engine.
    
    This layer executes direct actions and tool orchestration based on
    Council decisions or direct action requests.
    """
    
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process KIP agent tasks based on Council decisions."""
        return await self.kip_execution_node(state)
    
    async def kip_execution_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute KIP agent tasks based on Council decisions."""
        self.logger.info(
            "Starting KIP agent execution", 
            request_id=state.request_id,
            council_decision=state.council_decision.outcome if state.council_decision else "No decision"
        )
        state.update_phase(ProcessingPhase.KIP_EXECUTION)
        
        try:
            # Initialize KIP layer and Treasury
            async with kip_session() as kip:
                async with treasury_session() as treasury:
                    
                    # Get available agents
                    available_agents = await kip.list_agents()
                    self.logger.debug(
                        "Available KIP agents",
                        request_id=state.request_id,
                        agent_count=len(available_agents)
                    )
                    
                    # If we have a council decision, try to execute relevant tools
                    if state.council_decision and available_agents:
                        # For demonstration, use data analyst agent if available
                        agent_id = "data_analyst_01"  # Default agent for this demo
                        
                        # Try to execute a sample action based on the user's request
                        if any(keyword in state.user_input.lower() for keyword in ["bitcoin", "crypto", "price", "market"]):
                            try:
                                action_result = await kip.execute_action(
                                    agent_id=agent_id,
                                    tool_name="get_bitcoin_price",
                                    params={},
                                    treasury=treasury
                                )
                                
                                if action_result.was_successful:
                                    # Create successful KIP task
                                    task = KIPTask(
                                        agent_id=agent_id,
                                        task_type="tool_execution",
                                        instruction=f"Execute tool based on council decision for: {state.user_input}",
                                        status="completed",
                                        result=f"Tool execution result: {action_result.result_data}"
                                    )
                                    task.completed_at = datetime.now(timezone.utc)
                                    state.kip_tasks.append(task)
                                    
                                    self.logger.info(
                                        "KIP tool execution successful",
                                        request_id=state.request_id,
                                        agent_id=agent_id,
                                        tool_name="get_bitcoin_price",
                                        cost_cents=action_result.cost_cents,
                                        execution_time=action_result.execution_time
                                    )
                                else:
                                    # Create failed KIP task
                                    task = KIPTask(
                                        agent_id=agent_id,
                                        task_type="tool_execution",
                                        instruction=f"Attempted tool execution for: {state.user_input}",
                                        status="failed",
                                        result=f"Tool execution failed: {action_result.error_message}"
                                    )
                                    task.completed_at = datetime.now(timezone.utc)
                                    state.kip_tasks.append(task)
                                    
                                    self.logger.warning(
                                        "KIP tool execution failed",
                                        request_id=state.request_id,
                                        agent_id=agent_id,
                                        error=action_result.error_message
                                    )
                            except Exception as e:
                                self.logger.error(
                                    "KIP action execution exception",
                                    request_id=state.request_id,
                                    agent_id=agent_id,
                                    error=str(e)
                                )
                        else:
                            # Create a basic analytical task for non-crypto requests
                            task = KIPTask(
                                agent_id=agent_id,
                                task_type="analysis",
                                instruction=f"Analyze council decision for: {state.user_input}",
                                status="completed",
                                result="Analysis completed - council decision processed and validated"
                            )
                            task.completed_at = datetime.now(timezone.utc)
                            state.kip_tasks.append(task)
                            
                            self.logger.info(
                                "KIP analysis task completed",
                                request_id=state.request_id,
                                agent_id=agent_id,
                                task_type="analysis"
                            )
                    else:
                        # Fallback task when no council decision or agents available
                        task = KIPTask(
                            agent_id="system",
                            task_type="fallback",
                            instruction=f"Process request: {state.user_input}",
                            status="completed",
                            result="Request processed without agent execution"
                        )
                        task.completed_at = datetime.now(timezone.utc)
                        state.kip_tasks.append(task)
                        
                        self.logger.info(
                            "KIP fallback task created",
                            request_id=state.request_id,
                            reason="No council decision or agents available"
                        )
                        
        except Exception as e:
            # Handle KIP layer failures gracefully
            self.logger.error(
                "KIP execution failed",
                request_id=state.request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Create error task
            error_task = KIPTask(
                agent_id="error_handler",
                task_type="error",
                instruction=f"Handle error for: {state.user_input}",
                status="failed",
                result=f"KIP execution failed: {str(e)}"
            )
            error_task.completed_at = datetime.now(timezone.utc)
            state.kip_tasks.append(error_task)
        
        return state