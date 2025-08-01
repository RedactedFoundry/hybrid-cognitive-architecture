#!/usr/bin/env python3
"""
Tests for Modular Cognitive Processing Nodes

Tests the new modular cognitive architecture components:
- SmartRouterNode: Intent classification and routing
- PheromindNode: Ambient pattern detection  
- CouncilNode: Multi-agent deliberation
- KIPNode: Direct action execution
- SupportNode: Infrastructure and error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.orchestrator.models import OrchestratorState, ProcessingPhase, TaskIntent
from core.orchestrator.nodes import (
    SmartRouterNode,
    PheromindNode, 
    CouncilNode,
    KIPNode,
    SupportNode
)


class MockOrchestrator:
    """Mock orchestrator for testing nodes."""
    
    def __init__(self):
        self.test_mode = True


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    return MockOrchestrator()


@pytest.fixture  
def sample_state():
    """Create a sample orchestrator state for testing."""
    return OrchestratorState(
        user_input="What is artificial intelligence?",
        conversation_id="test_conv_123",
        request_id="test_req_456"
    )


class TestSmartRouterNode:
    """Test Smart Router cognitive layer."""
    
    def test_initialization(self, mock_orchestrator):
        """Test SmartRouterNode initialization."""
        node = SmartRouterNode(mock_orchestrator)
        assert node.orchestrator == mock_orchestrator
        assert hasattr(node, 'logger')
    
    @patch('core.orchestrator.nodes.smart_router_nodes.get_ollama_client')
    @patch('core.orchestrator.nodes.smart_router_nodes.get_global_cache_manager')
    async def test_simple_query_classification(self, mock_cache_manager, mock_ollama, mock_orchestrator, sample_state):
        """Test classification of simple queries."""
        # Mock cache manager
        mock_cache_manager.return_value = MagicMock()
        mock_cached_client = AsyncMock()
        mock_cache_manager.return_value.get_cached_ollama_client.return_value = mock_cached_client
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.text = "simple_query_task"
        mock_cached_client.generate_response.return_value = mock_response
        
        node = SmartRouterNode(mock_orchestrator)
        result = await node.smart_triage_node(sample_state)
        
        assert result.routing_intent == TaskIntent.SIMPLE_QUERY_TASK
        assert result.current_phase == ProcessingPhase.SMART_TRIAGE
    
    async def test_rule_based_overrides(self, mock_orchestrator, sample_state):
        """Test rule-based intent classification overrides."""
        node = SmartRouterNode(mock_orchestrator)
        
        # Test simple query patterns
        sample_state.user_input = "Who is the CEO of Google?"
        with patch.object(node, '_get_cached_ollama_client') as mock_client:
            result = await node.smart_triage_node(sample_state)
            assert result.routing_intent == TaskIntent.SIMPLE_QUERY_TASK
        
        # Test complex reasoning patterns  
        sample_state.user_input = "Compare Python vs JavaScript for web development"
        with patch.object(node, '_get_cached_ollama_client') as mock_client:
            result = await node.smart_triage_node(sample_state)
            assert result.routing_intent == TaskIntent.COMPLEX_REASONING_TASK


class TestPheromindNode:
    """Test Pheromind cognitive layer."""
    
    def test_initialization(self, mock_orchestrator):
        """Test PheromindNode initialization."""
        node = PheromindNode(mock_orchestrator)
        assert node.orchestrator == mock_orchestrator
        assert hasattr(node, 'logger')
    
    def test_extract_search_patterns(self, mock_orchestrator):
        """Test search pattern extraction."""
        node = PheromindNode(mock_orchestrator)
        
        patterns = node._extract_search_patterns("I need help with AI and machine learning")
        assert "*" in patterns  # Broad pattern
        assert "*ai*" in patterns  # AI-specific pattern
        assert "*help*" in patterns  # Help pattern
    
    @patch('core.orchestrator.nodes.pheromind_nodes.pheromind_session')
    async def test_pheromind_scan(self, mock_session, mock_orchestrator, sample_state):
        """Test pheromind ambient scan functionality."""
        # Mock pheromind session
        mock_pheromind = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_pheromind
        mock_pheromind.query_signals.return_value = []
        
        node = PheromindNode(mock_orchestrator)
        result = await node.pheromind_scan_node(sample_state)
        
        assert result.current_phase == ProcessingPhase.PHEROMIND_SCAN
        assert isinstance(result.pheromind_signals, list)


class TestCouncilNode:
    """Test Council cognitive layer."""
    
    def test_initialization(self, mock_orchestrator):
        """Test CouncilNode initialization."""
        node = CouncilNode(mock_orchestrator)
        assert node.orchestrator == mock_orchestrator
        assert hasattr(node, 'logger')
    
    @patch('core.orchestrator.nodes.council_nodes.get_global_cache_manager')
    async def test_council_deliberation_structure(self, mock_cache_manager, mock_orchestrator, sample_state):
        """Test council deliberation process structure."""
        # Mock cache manager and Ollama client
        mock_cache_manager.return_value = MagicMock()
        mock_cached_client = AsyncMock()
        mock_cache_manager.return_value.get_cached_ollama_client.return_value = mock_cached_client
        mock_cached_client.health_check.return_value = True
        
        # Mock LLM responses
        mock_response = MagicMock()
        mock_response.text = "Test agent response"
        mock_response.tokens_generated = 100
        mock_cached_client.generate_response.return_value = mock_response
        
        node = CouncilNode(mock_orchestrator)
        result = await node.council_deliberation_node(sample_state)
        
        assert result.current_phase == ProcessingPhase.COUNCIL_DELIBERATION
        if result.council_decision:
            assert hasattr(result.council_decision, 'question')
            assert hasattr(result.council_decision, 'outcome')


class TestKIPNode:
    """Test KIP cognitive layer."""
    
    def test_initialization(self, mock_orchestrator):
        """Test KIPNode initialization."""
        node = KIPNode(mock_orchestrator)
        assert node.orchestrator == mock_orchestrator
        assert hasattr(node, 'logger')
    
    @patch('core.orchestrator.nodes.kip_nodes.kip_session')
    @patch('core.orchestrator.nodes.kip_nodes.treasury_session')
    async def test_kip_execution_structure(self, mock_treasury, mock_kip, mock_orchestrator, sample_state):
        """Test KIP execution process structure."""
        # Mock KIP and Treasury sessions
        mock_kip_instance = AsyncMock()
        mock_treasury_instance = AsyncMock()
        
        mock_kip.return_value.__aenter__.return_value = mock_kip_instance
        mock_treasury.return_value.__aenter__.return_value = mock_treasury_instance
        
        mock_kip_instance.list_agents.return_value = []  # No agents available
        
        node = KIPNode(mock_orchestrator)
        result = await node.kip_execution_node(sample_state)
        
        assert result.current_phase == ProcessingPhase.KIP_EXECUTION
        assert len(result.kip_tasks) > 0  # Should create at least a fallback task


class TestSupportNode:
    """Test Support infrastructure layer."""
    
    def test_initialization(self, mock_orchestrator):
        """Test SupportNode initialization."""
        node = SupportNode(mock_orchestrator)
        assert node.orchestrator == mock_orchestrator
        assert hasattr(node, 'logger')
    
    async def test_initialize_node_validation(self, mock_orchestrator, sample_state):
        """Test initialization and input validation."""
        node = SupportNode(mock_orchestrator)
        result = await node.initialize_node(sample_state)
        
        assert result.current_phase == ProcessingPhase.INITIALIZATION
        assert "initialized_at" in result.metadata
        assert "input_length" in result.metadata
    
    async def test_initialize_node_empty_input(self, mock_orchestrator):
        """Test initialization with invalid input."""
        empty_state = OrchestratorState(
            user_input="",  # Empty input should trigger validation error
            conversation_id="test",
            request_id="test"
        )
        
        node = SupportNode(mock_orchestrator)
        result = await node.initialize_node(empty_state)
        
        assert result.error_message is not None
    
    @patch('core.orchestrator.nodes.support_nodes.get_global_cache_manager')
    async def test_fast_response_node(self, mock_cache_manager, mock_orchestrator, sample_state):
        """Test fast response functionality."""
        # Mock cache manager and Ollama client
        mock_cache_manager.return_value = MagicMock()
        mock_cached_client = AsyncMock()
        mock_cache_manager.return_value.get_cached_ollama_client.return_value = mock_cached_client
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.text = "Test fast response"
        mock_cached_client.generate_response.return_value = mock_response
        
        node = SupportNode(mock_orchestrator)
        result = await node.fast_response_node(sample_state)
        
        assert result.current_phase == ProcessingPhase.FAST_RESPONSE
        assert result.final_response is not None
        assert result.metadata.get("fast_path_used") is True


class TestProcessingNodesIntegration:
    """Test integration between processing nodes."""
    
    def test_all_nodes_inherit_from_base(self, mock_orchestrator):
        """Test that all nodes properly inherit base functionality."""
        nodes = [
            SmartRouterNode(mock_orchestrator),
            PheromindNode(mock_orchestrator),
            CouncilNode(mock_orchestrator),
            KIPNode(mock_orchestrator),
            SupportNode(mock_orchestrator)
        ]
        
        for node in nodes:
            assert hasattr(node, 'orchestrator')
            assert hasattr(node, 'logger')
            assert hasattr(node, '_get_cached_ollama_client')
    
    async def test_state_transitions(self, mock_orchestrator, sample_state):
        """Test that nodes properly update state phases."""
        nodes_and_phases = [
            (SupportNode(mock_orchestrator), ProcessingPhase.INITIALIZATION, 'initialize_node'),
            (SmartRouterNode(mock_orchestrator), ProcessingPhase.SMART_TRIAGE, 'smart_triage_node')
        ]
        
        for node, expected_phase, method_name in nodes_and_phases:
            # Mock dependencies as needed
            with patch.object(node, '_get_cached_ollama_client') as mock_client:
                if hasattr(node, method_name):
                    method = getattr(node, method_name)
                    result = await method(sample_state)
                    assert result.current_phase == expected_phase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])