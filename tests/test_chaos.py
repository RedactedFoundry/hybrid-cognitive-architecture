#!/usr/bin/env python3
"""
Chaos Engineering Tests for Hybrid AI Council

This module tests system resilience under failure conditions,
ensuring graceful degradation rather than catastrophic failures.

The chaos engineering philosophy: "What doesn't kill the system makes it stronger."
"""

import sys
import os
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import docker
from docker.errors import NotFound, APIError

from core.orchestrator import UserFacingOrchestrator, OrchestratorState, ProcessingPhase
from core.kip import kip_session, treasury_session
from core.pheromind import pheromind_session

# Clean config import
from config import Config


class ChaosTestManager:
    """
    Manages chaos engineering test infrastructure.
    
    Handles Docker container manipulation and ensures proper cleanup
    even when tests fail catastrophically.
    """
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.redis_container_name = "hybrid-cognitive-architecture-redis-1"
        self.redis_was_running = False
        
    def get_redis_container(self):
        """Get the Redis container, handling cases where it might not exist."""
        try:
            return self.docker_client.containers.get(self.redis_container_name)
        except NotFound:
            pytest.skip(f"Redis container '{self.redis_container_name}' not found. Run 'docker-compose up -d redis' first.")
            
    def stop_redis(self):
        """Stop Redis container and record its initial state."""
        container = self.get_redis_container()
        self.redis_was_running = container.status == 'running'
        
        if self.redis_was_running:
            print(f"🔥 CHAOS: Stopping Redis container '{self.redis_container_name}'...")
            container.stop()
            
            # Wait for container to actually stop
            timeout = 10
            start_time = time.time()
            while container.status == 'running' and (time.time() - start_time) < timeout:
                time.sleep(0.5)
                container.reload()
                
            if container.status == 'running':
                pytest.fail(f"Failed to stop Redis container within {timeout} seconds")
                
            print(f"✅ Redis container stopped (status: {container.status})")
        else:
            print(f"⚠️  Redis container was already stopped (status: {container.status})")
            
    def start_redis(self):
        """Restart Redis container if it was running before the test."""
        container = self.get_redis_container()
        
        if self.redis_was_running and container.status != 'running':
            print(f"🔄 RECOVERY: Starting Redis container '{self.redis_container_name}'...")
            container.start()
            
            # Wait for container to actually start
            timeout = 15
            start_time = time.time()
            while container.status != 'running' and (time.time() - start_time) < timeout:
                time.sleep(0.5)
                container.reload()
                
            if container.status != 'running':
                pytest.fail(f"Failed to restart Redis container within {timeout} seconds")
                
            # Give Redis a moment to fully initialize
            time.sleep(2)
            print(f"✅ Redis container restarted (status: {container.status})")
        else:
            print(f"ℹ️  Redis restart not needed (was_running: {self.redis_was_running}, status: {container.status})")


@pytest.fixture
def chaos_manager():
    """Provide a chaos test manager with automatic cleanup."""
    manager = ChaosTestManager()
    try:
        yield manager
    finally:
        # Ensure Redis is restarted even if test fails
        try:
            manager.start_redis()
        except Exception as e:
            print(f"⚠️  Warning: Failed to restart Redis during cleanup: {e}")


@pytest.mark.asyncio
async def test_orchestrator_handles_redis_failure(chaos_manager):
    """
    Test that the orchestrator gracefully handles Redis infrastructure failure.
    
    This is a critical resilience test - the system should degrade gracefully
    rather than crash when Redis (pheromone layer + treasury cache) goes down.
    """
    print("🧪 CHAOS TEST: Orchestrator Redis Failure Resilience")
    print("=" * 55)
    
    # Initialize orchestrator (gets config from environment)
    config = Config()
    orchestrator = UserFacingOrchestrator()
    
    # Test 1: Normal operation (baseline)
    print("📊 Phase 1: Baseline test with Redis running...")
    
    try:
        # This should work normally
        final_state = await orchestrator.process_request(
            user_input="Tell me about AI safety",
            conversation_id="chaos-baseline-001"
        )
        # Check that processing completed successfully (could be COMPLETED or a valid final phase like FAST_RESPONSE)
        assert final_state.current_phase in [ProcessingPhase.COMPLETED, ProcessingPhase.FAST_RESPONSE, ProcessingPhase.RESPONSE_SYNTHESIS]
        assert final_state.final_response is not None
        assert len(final_state.final_response) > 0
        print("✅ Baseline test passed - system working normally")
    except Exception as e:
        pytest.fail(f"Baseline test failed - system not working properly: {e}")
    
    print()
    
    # Test 2: Redis failure scenario
    print("🔥 Phase 2: Chaos test with Redis stopped...")
    
    # Stop Redis to simulate infrastructure failure
    chaos_manager.stop_redis()
    
    # The orchestrator should handle this gracefully
    try:
        final_state = await orchestrator.process_request(
            user_input="What is the current state of cryptocurrency markets?",
            conversation_id="chaos-redis-failure-001"
        )
        
        # Assert graceful degradation
        assert final_state is not None, "Orchestrator should return a state, not crash"
        assert final_state.conversation_id == "chaos-redis-failure-001", "Conversation ID should be preserved"
        
        # Check that the system handled the infrastructure failure gracefully
        # Success can be: 1) Normal completion, 2) Graceful degradation, 3) Graceful error
        if final_state.current_phase in [ProcessingPhase.COMPLETED, ProcessingPhase.FAST_RESPONSE, ProcessingPhase.RESPONSE_SYNTHESIS]:
            # System completed successfully - this is excellent resilience!
            assert final_state.final_response is not None
            assert len(final_state.final_response) > 0
            
            # Check if response mentions degradation (optional - system may be robust enough to work normally)
            response_lower = final_state.final_response.lower()
            degradation_indicators = ["unavailable", "temporary", "limited", "degraded", "offline"]
            has_degradation_notice = any(indicator in response_lower for indicator in degradation_indicators)
            
            if has_degradation_notice:
                print(f"✅ System completed with graceful degradation notice")
            else:
                print(f"✅ System demonstrated excellent resilience - worked normally despite Redis failure")
            print(f"   Final phase: {final_state.current_phase}")
            print(f"   Response preview: {final_state.final_response[:100]}...")
            
        elif hasattr(final_state, 'error_message') and final_state.error_message:
            # If it errored, it should be a graceful error message
            assert "crash" not in final_state.error_message.lower(), "Error should not mention crashing"
            print(f"✅ System failed gracefully with error: {final_state.error_message}")
            
        else:
            pytest.fail("System should either complete successfully or provide graceful error message")
            
    except Exception as e:
        # If an exception was raised, it should be a graceful, expected exception
        # not a catastrophic failure
        error_message = str(e).lower()
        
        # These are acceptable "graceful" failures
        acceptable_errors = [
            "redis", "connection", "timeout", "unavailable", 
            "service", "infrastructure", "temporary"
        ]
        
        # These indicate catastrophic failures
        catastrophic_errors = ["segmentation", "core dump", "null pointer", "memory"]
        
        is_graceful = any(acceptable in error_message for acceptable in acceptable_errors)
        is_catastrophic = any(catastrophic in error_message for catastrophic in catastrophic_errors)
        
        if is_catastrophic:
            pytest.fail(f"CATASTROPHIC FAILURE detected: {e}")
        elif is_graceful:
            print(f"✅ System failed gracefully with expected infrastructure error: {e}")
        else:
            pytest.fail(f"Unexpected error type (not graceful degradation): {e}")
    
    print()
    print("🔄 Phase 3: Recovery test...")
    
    # Restart Redis
    chaos_manager.start_redis()
    
    # Test that system recovers after infrastructure is restored
    try:
        final_state = await orchestrator.process_request(
            user_input="Test recovery after infrastructure restoration",
            conversation_id="chaos-recovery-001"
        )
        # Check that processing completed successfully (could be COMPLETED or a valid final phase like FAST_RESPONSE)
        assert final_state.current_phase in [ProcessingPhase.COMPLETED, ProcessingPhase.FAST_RESPONSE, ProcessingPhase.RESPONSE_SYNTHESIS]
        assert final_state.final_response is not None
        print("✅ Recovery test passed - system restored to normal operation")
    except Exception as e:
        pytest.fail(f"Recovery test failed - system did not recover properly: {e}")
    
    print()
    print("🎉 CHAOS TEST COMPLETED: System demonstrates excellent resilience!")


@pytest.mark.asyncio
async def test_pheromind_layer_redis_failure():
    """
    Test that the Pheromind layer gracefully handles Redis failures.
    
    When Redis is down, pheromone operations should fail gracefully
    without crashing the entire system.
    """
    print("🧪 CHAOS TEST: Pheromind Redis Failure Resilience")
    print("=" * 50)
    
    # Test with Redis running (baseline)
    try:
        async with pheromind_session() as pheromind:
            signals = await pheromind.query_signals("test_pattern")
            print("✅ Baseline: Pheromind layer working normally")
    except Exception as e:
        pytest.skip(f"Cannot test Pheromind resilience - baseline failed: {e}")
    
    # Temporarily stop Redis using Docker
    docker_client = docker.from_env()
    try:
        redis_container = docker_client.containers.get("hybrid-cognitive-architecture-redis-1")
        was_running = redis_container.status == 'running'
        
        if was_running:
            redis_container.stop()
            time.sleep(2)  # Wait for stop
            
            # Test Pheromind behavior with Redis down
            try:
                async with pheromind_session() as pheromind:
                    # This should fail gracefully, not crash
                    with pytest.raises((ConnectionError, TimeoutError, Exception)):
                        await pheromind.query_signals("test_pattern")
                        
                print("✅ Pheromind layer fails gracefully when Redis is down")
                
            except Exception as e:
                pytest.fail(f"Pheromind layer crashed ungracefully: {e}")
                
            finally:
                # Always restart Redis
                if was_running:
                    redis_container.start()
                    time.sleep(3)  # Wait for startup
                    
    except NotFound:
        pytest.skip("Redis container not found - cannot test Redis failure scenarios")


@pytest.mark.asyncio
async def test_treasury_redis_failure():
    """
    Test that the Treasury system gracefully handles Redis failures.
    
    Economic operations should fail gracefully when Redis cache is unavailable,
    potentially falling back to TigerGraph for critical operations.
    """
    print("🧪 CHAOS TEST: Treasury Redis Failure Resilience") 
    print("=" * 48)
    
    # Test with Redis running (baseline)
    try:
        async with treasury_session() as treasury:
            analytics = await treasury.get_economic_analytics()
            print("✅ Baseline: Treasury working normally")
    except Exception as e:
        pytest.skip(f"Cannot test Treasury resilience - baseline failed: {e}")
    
    # Note: For now, we'll just verify the Treasury handles Redis connection errors gracefully
    # Full chaos testing would require stopping Redis, but that's covered in the main test
    
    # Test invalid Redis configuration (simulates connection failure)
    with patch('core.kip.treasury_core.redis.Redis') as mock_redis:
        mock_redis.side_effect = ConnectionError("Simulated Redis failure")
        
        try:
            async with treasury_session() as treasury:
                # This should handle the Redis failure gracefully
                # Either by falling back to TigerGraph or failing with a clear error
                with pytest.raises((ConnectionError, Exception)):
                    await treasury.get_budget("test_agent")
                    
            print("✅ Treasury handles Redis failures gracefully")
            
        except Exception as e:
            # Check if this is a graceful failure or catastrophic crash
            if "redis" in str(e).lower() or "connection" in str(e).lower():
                print("✅ Treasury fails gracefully when Redis is unavailable")
            else:
                pytest.fail(f"Treasury crashed ungracefully: {e}")


@pytest.mark.asyncio  
async def test_kip_layer_partial_failure():
    """
    Test that the KIP layer handles partial system failures gracefully.
    
    When some components are unavailable, the system should continue
    operating with degraded functionality rather than complete failure.
    """
    print("🧪 CHAOS TEST: KIP Layer Partial Failure Resilience")
    print("=" * 52)
    
    # Test with full system (baseline)
    try:
        async with kip_session() as kip:
            agents = await kip.list_agents()
            print(f"✅ Baseline: KIP layer working normally ({len(agents)} agents)")
    except Exception as e:
        pytest.skip(f"Cannot test KIP resilience - baseline failed: {e}")
    
    # Simulate TigerGraph connection issues
    with patch('clients.tigervector_client.get_tigergraph_connection') as mock_tg:
        mock_tg.side_effect = ConnectionError("Simulated TigerGraph failure")
        
        try:
            async with kip_session() as kip:
                # This should handle TigerGraph failure gracefully (not crash)
                result = await kip.load_agent("test_agent_001")
                
                # System should gracefully return None for missing agent, not crash
                assert result is None, "Expected None for missing agent in degraded mode"
                    
            print("✅ KIP layer handles TigerGraph failures gracefully")
            
        except Exception as e:
            if "tigergraph" in str(e).lower() or "connection" in str(e).lower():
                print("✅ KIP fails gracefully when TigerGraph is unavailable")
            else:
                pytest.fail(f"KIP layer crashed ungracefully: {e}")


if __name__ == "__main__":
    print("🔥 CHAOS ENGINEERING TEST SUITE")
    print("=" * 35)
    print("Testing system resilience under failure conditions...")
    print()
    
    # Run with pytest: poetry run pytest tests/test_chaos.py -v -s
    pytest.main([__file__, "-v", "-s"])