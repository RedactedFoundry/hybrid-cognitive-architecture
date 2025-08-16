# tests/test_kip_tools.py
"""
Comprehensive tests for KIP Tools and Live Data Integration.

This test suite covers:
- Web tools API integration (with mocking)
- Tool registry management
- Agent-tool authorization
- Cost tracking and usage limits
- Tool execution and error handling
- Economic impact of tool usage
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import aiohttp

# Import the modules we're testing
from tools.web_tools import (
    get_current_bitcoin_price,
    get_current_ethereum_price, 
    get_crypto_market_summary,
    WEB_TOOLS
)
from core.kip.tools import ToolRegistry
from core.kip.models import Tool, ActionResult, AgentStatus
from core.kip.agents import AgentManager
from config import Config


class TestWebToolsAPI:
    """Test the actual web tools that interact with external APIs."""
    
    @pytest.mark.asyncio
    async def test_bitcoin_price_fetch_success(self):
        """Test successful Bitcoin price fetching."""
        # Mock the aiohttp response
        mock_response_data = {
            "bitcoin": {"usd": 45123.45}
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Configure mock response
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_response_data)
            
            # Configure session context manager
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test the function
            result = await get_current_bitcoin_price()
            
            # Verify result format
            assert result == "$45,123.45"
            assert "$" in result
            assert "," in result  # Thousand separator
            
            # Verify API was called correctly
            mock_session.assert_called_once()
            mock_session.return_value.get.assert_called_once()
            call_args = mock_session.return_value.get.call_args[0]
            assert "api.coingecko.com" in call_args[0]
            assert "bitcoin" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_bitcoin_price_api_error(self):
        """Test Bitcoin price fetch with API error."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Configure mock to raise an error
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(
                side_effect=aiohttp.ClientError("API Error")
            )
            
            # Test that proper exception is raised
            with pytest.raises(aiohttp.ClientError) as exc_info:
                await get_current_bitcoin_price()
            
            assert "CoinGecko API request failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_bitcoin_price_invalid_response(self):
        """Test Bitcoin price fetch with invalid API response."""
        # Mock invalid response (missing expected data)
        mock_response_data = {"invalid": "data"}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_response_data)
            
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test that ValueError is raised for invalid response
            with pytest.raises(ValueError) as exc_info:
                await get_current_bitcoin_price()
            
            assert "Invalid API response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_bitcoin_price_timeout(self):
        """Test Bitcoin price fetch with timeout."""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(
                side_effect=asyncio.TimeoutError("Request timeout")
            )
            
            # Test that timeout is handled properly
            with pytest.raises(asyncio.TimeoutError) as exc_info:
                await get_current_bitcoin_price()
            
            assert "timed out after 10 seconds" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_ethereum_price_fetch_success(self):
        """Test successful Ethereum price fetching."""
        mock_response_data = {
            "ethereum": {"usd": 2456.78}
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_response_data)
            
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await get_current_ethereum_price()
            
            assert result == "$2,456.78"
            assert "$" in result
    
    @pytest.mark.asyncio
    async def test_crypto_market_summary_success(self):
        """Test successful crypto market summary fetching."""
        mock_response_data = {
            "bitcoin": {"usd": 45123.45, "usd_24h_change": 2.5},
            "ethereum": {"usd": 2456.78, "usd_24h_change": -1.2},
            "cardano": {"usd": 0.45, "usd_24h_change": 0.8},
            "polkadot": {"usd": 5.67, "usd_24h_change": -0.3}
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_response_data)
            
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await get_crypto_market_summary()
            
            # Verify structure and content
            assert isinstance(result, dict)
            assert "bitcoin" in result
            assert "ethereum" in result
            assert "cardano" in result
            assert "polkadot" in result
            
            # Verify Bitcoin data formatting
            bitcoin_data = result["bitcoin"]
            assert bitcoin_data["price"] == "$45,123.45"
            assert bitcoin_data["24h_change"] == "+2.50%"
            assert bitcoin_data["raw_price"] == 45123.45
            assert bitcoin_data["raw_change"] == 2.5
            
            # Verify negative change formatting
            ethereum_data = result["ethereum"]
            assert ethereum_data["24h_change"] == "-1.20%"
    
    def test_web_tools_registry(self):
        """Test that WEB_TOOLS registry is properly configured."""
        assert "get_bitcoin_price" in WEB_TOOLS
        assert "get_ethereum_price" in WEB_TOOLS
        assert "get_crypto_summary" in WEB_TOOLS
        
        # Verify all entries are callable
        for tool_name, tool_func in WEB_TOOLS.items():
            assert callable(tool_func)


class TestKIPToolRegistry:
    """Test the KIP Tool Registry system."""
    
    @pytest.fixture
    def config(self):
        """Provide a test configuration."""
        return Config()
    
    @pytest.fixture
    def tool_registry(self, config):
        """Provide a configured tool registry."""
        return ToolRegistry(config)
    
    def test_tool_registry_initialization(self, tool_registry):
        """Test that tool registry initializes with default tools."""
        # Verify default tools are registered
        assert "get_bitcoin_price" in tool_registry.tool_registry
        assert "get_ethereum_price" in tool_registry.tool_registry
        assert "get_crypto_summary" in tool_registry.tool_registry
        
        # Verify tool properties
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        assert bitcoin_tool.tool_name == "get_bitcoin_price"
        assert bitcoin_tool.tool_type == "web"
        assert bitcoin_tool.module_path == "tools.web_tools"
        assert bitcoin_tool.function_name == "get_current_bitcoin_price"
        assert bitcoin_tool.cost_per_use == 100  # $1.00
        assert bitcoin_tool.daily_limit == 100
        assert bitcoin_tool.required_authorization == "basic"
    
    def test_tool_cost_calculation(self, tool_registry):
        """Test tool cost calculation."""
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        assert bitcoin_tool.cost_usd == "$1.00"
        
        crypto_summary_tool = tool_registry.tool_registry["get_crypto_summary"]
        assert crypto_summary_tool.cost_usd == "$2.00"
    
    @pytest.mark.asyncio
    async def test_tool_execution_success(self, tool_registry):
        """Test successful tool execution."""
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        
        # Mock the web tool response
        with patch('tools.web_tools.get_current_bitcoin_price', new_callable=AsyncMock) as mock_func:
            mock_func.return_value = "$45,123.45"
            
            # Execute the tool
            result = await bitcoin_tool.execute()
            
            # Verify execution
            assert result == "$45,123.45"
            mock_func.assert_called_once()
            
            # Verify usage statistics updated
            assert bitcoin_tool.total_uses == 1
            assert bitcoin_tool.last_used is not None
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_params(self, tool_registry):
        """Test tool execution with parameters."""
        # Create a test tool that accepts parameters
        test_tool = Tool(
            tool_name="test_tool",
            description="Test tool with params",
            tool_type="test",
            version="1.0",
            module_path="tools.web_tools",
            function_name="get_current_bitcoin_price",  # Use existing function for test
            required_authorization="basic",
            cost_per_use=50,
            daily_limit=10
        )
        
        with patch('tools.web_tools.get_current_bitcoin_price', new_callable=AsyncMock) as mock_func:
            mock_func.return_value = "test_result"
            
            # Execute with empty params (should work)
            result = await test_tool.execute({})
            assert result == "test_result"
    
    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, tool_registry):
        """Test tool execution failure handling."""
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        
        # Mock the web tool to raise an error
        with patch('tools.web_tools.get_current_bitcoin_price', new_callable=AsyncMock) as mock_func:
            mock_func.side_effect = Exception("API Error")
            
            # Test that execution failure is handled
            with pytest.raises(Exception) as exc_info:
                await bitcoin_tool.execute()
            
            assert "Tool 'get_bitcoin_price' execution failed" in str(exc_info.value)
            assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_tool_execution_invalid_function(self):
        """Test tool execution with invalid function."""
        # Create tool with non-existent function
        invalid_tool = Tool(
            tool_name="invalid_tool",
            description="Invalid tool",
            tool_type="test",
            version="1.0",
            module_path="tools.web_tools",
            function_name="nonexistent_function",
            required_authorization="basic",
            cost_per_use=50,
            daily_limit=10
        )
        
        with pytest.raises(Exception) as exc_info:
            await invalid_tool.execute()
        
        assert "execution failed" in str(exc_info.value)


class TestKIPAgentToolIntegration:
    """Test integration between KIP agents and tools."""
    
    @pytest.fixture
    def config(self):
        return Config()
    
    @pytest.fixture
    def agent_manager(self, config):
        return AgentManager(config)
    
    @pytest.mark.asyncio
    async def test_analyst_agent_tool_access(self, agent_manager):
        """Test that analyst agents get full web tool access."""
        with patch('clients.tigergraph_client.get_tigergraph_connection') as mock_tg:
            mock_tg.return_value = MagicMock()
            
            # Load tools for an analyst agent
            tools = await agent_manager._load_agent_tools("test_analyst_001")
            
            # Verify analyst gets all web tools
            web_tool_names = [tool.tool_name for tool in tools if tool.tool_type == "web"]
            assert "get_bitcoin_price" in web_tool_names
            assert "get_ethereum_price" in web_tool_names
            assert "get_crypto_summary" in web_tool_names
            
            # Verify authorization levels
            web_tools = {tool.tool_name: tool for tool in tools if tool.tool_type == "web"}
            assert web_tools["get_bitcoin_price"].authorization_level == "full"
            assert web_tools["get_crypto_summary"].authorization_level == "full"
    
    @pytest.mark.asyncio
    async def test_creator_agent_limited_tool_access(self, agent_manager):
        """Test that creator agents get limited web tool access."""
        with patch('clients.tigergraph_client.get_tigergraph_connection') as mock_tg:
            mock_tg.return_value = MagicMock()
            
            # Load tools for a creator agent
            tools = await agent_manager._load_agent_tools("test_creator_001")
            
            # Verify creator gets limited web tools
            web_tool_names = [tool.tool_name for tool in tools if tool.tool_type == "web"]
            assert "get_bitcoin_price" in web_tool_names
            assert "get_ethereum_price" not in web_tool_names  # Limited access
            assert "get_crypto_summary" not in web_tool_names  # Limited access
            
            # Verify authorization level is basic
            web_tools = {tool.tool_name: tool for tool in tools if tool.tool_type == "web"}
            assert web_tools["get_bitcoin_price"].authorization_level == "basic"
    
    @pytest.mark.asyncio
    async def test_default_agent_no_web_tools(self, agent_manager):
        """Test that default agents don't get web tool access."""
        with patch('clients.tigergraph_client.get_tigergraph_connection') as mock_tg:
            mock_tg.return_value = MagicMock()
            
            # Load tools for a default agent
            tools = await agent_manager._load_agent_tools("test_agent_001")
            
            # Verify no web tools for default agents
            web_tool_names = [tool.tool_name for tool in tools if tool.tool_type == "web"]
            assert len(web_tool_names) == 0
    
    @pytest.mark.asyncio
    async def test_agent_tool_loading_error_handling(self, agent_manager):
        """Test error handling in agent tool loading."""
        # Mock datetime.now to throw an exception to trigger the error handling path
        with patch('core.kip.agents.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Internal error")
            
            # Should handle gracefully and return empty list
            tools = await agent_manager._load_agent_tools("test_agent_001")
            assert tools == []


class TestKIPToolEconomics:
    """Test the economic aspects of tool usage."""
    
    @pytest.fixture
    def tool_registry(self):
        return ToolRegistry()
    
    def test_tool_cost_structure(self, tool_registry):
        """Test that tools have proper cost structure."""
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        ethereum_tool = tool_registry.tool_registry["get_ethereum_price"]
        crypto_summary_tool = tool_registry.tool_registry["get_crypto_summary"]
        
        # Verify cost hierarchy (more comprehensive tools cost more)
        assert bitcoin_tool.cost_per_use == 100  # $1.00
        assert ethereum_tool.cost_per_use == 100  # $1.00
        assert crypto_summary_tool.cost_per_use == 200  # $2.00 (more comprehensive)
        
        # Verify daily limits (more expensive tools have lower limits)
        assert bitcoin_tool.daily_limit == 100
        assert ethereum_tool.daily_limit == 100
        assert crypto_summary_tool.daily_limit == 50  # Lower limit for expensive tool
    
    def test_tool_authorization_levels(self, tool_registry):
        """Test that tools have appropriate authorization requirements."""
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        crypto_summary_tool = tool_registry.tool_registry["get_crypto_summary"]
        
        # Basic tools require basic authorization
        assert bitcoin_tool.required_authorization == "basic"
        
        # Comprehensive tools require full authorization
        assert crypto_summary_tool.required_authorization == "full"
    
    @pytest.mark.asyncio
    async def test_tool_usage_tracking(self, tool_registry):
        """Test that tool usage is properly tracked."""
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        
        # Initial state
        initial_uses = bitcoin_tool.total_uses
        initial_last_used = bitcoin_tool.last_used
        
        with patch('tools.web_tools.get_current_bitcoin_price', new_callable=AsyncMock) as mock_func:
            mock_func.return_value = "$45,123.45"
            
            # Execute tool
            await bitcoin_tool.execute()
            
            # Verify usage tracking
            assert bitcoin_tool.total_uses == initial_uses + 1
            
            # Handle initial None case for last_used
            if initial_last_used is None:
                assert bitcoin_tool.last_used is not None
            else:
                assert bitcoin_tool.last_used > initial_last_used
            
            assert bitcoin_tool.last_used.tzinfo == timezone.utc


class TestKIPToolsIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_analyst_crypto_research_workflow(self):
        """Test a realistic analyst workflow using crypto tools."""
        config = Config()
        agent_manager = AgentManager(config)
        tool_registry = ToolRegistry(config)
        
        with patch('clients.tigergraph_client.get_tigergraph_connection') as mock_tg:
            mock_tg.return_value = MagicMock()
            
            # Load analyst tools
            tools = await agent_manager._load_agent_tools("crypto_analyst_001")
            
            # Simulate analyst workflow: get individual prices then summary
            with patch('tools.web_tools.get_current_bitcoin_price', new_callable=AsyncMock) as mock_btc, \
                 patch('tools.web_tools.get_current_ethereum_price', new_callable=AsyncMock) as mock_eth, \
                 patch('tools.web_tools.get_crypto_market_summary', new_callable=AsyncMock) as mock_summary:
                
                mock_btc.return_value = "$45,123.45"
                mock_eth.return_value = "$2,456.78"
                mock_summary.return_value = {
                    "bitcoin": {"price": "$45,123.45", "24h_change": "+2.50%"},
                    "ethereum": {"price": "$2,456.78", "24h_change": "-1.20%"}
                }
                
                # Execute tools as analyst would
                bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
                ethereum_tool = tool_registry.tool_registry["get_ethereum_price"]
                summary_tool = tool_registry.tool_registry["get_crypto_summary"]
                
                btc_price = await bitcoin_tool.execute()
                eth_price = await ethereum_tool.execute()
                market_summary = await summary_tool.execute()
                
                # Verify workflow results
                assert btc_price == "$45,123.45"
                assert eth_price == "$2,456.78"
                assert "bitcoin" in market_summary
                assert "ethereum" in market_summary
                
                # Verify cost tracking (total cost: $1 + $1 + $2 = $4.00)
                total_cost = (bitcoin_tool.cost_per_use + 
                             ethereum_tool.cost_per_use + 
                             summary_tool.cost_per_use)
                assert total_cost == 400  # $4.00 in cents
    
    @pytest.mark.asyncio
    async def test_tool_error_recovery_workflow(self):
        """Test workflow with tool failures and recovery."""
        tool_registry = ToolRegistry()
        bitcoin_tool = tool_registry.tool_registry["get_bitcoin_price"]
        ethereum_tool = tool_registry.tool_registry["get_ethereum_price"]
        
        with patch('tools.web_tools.get_current_bitcoin_price', new_callable=AsyncMock) as mock_btc, \
             patch('tools.web_tools.get_current_ethereum_price', new_callable=AsyncMock) as mock_eth:
            
            # Simulate Bitcoin API failure, Ethereum success
            mock_btc.side_effect = aiohttp.ClientError("Bitcoin API down")
            mock_eth.return_value = "$2,456.78"
            
            # Test graceful degradation
            bitcoin_result = None
            try:
                bitcoin_result = await bitcoin_tool.execute()
            except Exception:
                bitcoin_result = "Price unavailable"
            
            ethereum_result = await ethereum_tool.execute()
            
            # Verify partial success scenario
            assert bitcoin_result == "Price unavailable"
            assert ethereum_result == "$2,456.78"
            assert ethereum_tool.total_uses == 1
            assert bitcoin_tool.total_uses == 0  # Failed execution shouldn't count


# Integration with existing test infrastructure
if __name__ == "__main__":
    pytest.main([__file__, "-v"])