#!/usr/bin/env python3
"""
Tests for Configuration Management

Tests the enhanced configuration system with security settings.
"""

import pytest
import os
from unittest.mock import patch

from config import Config
from config.models import ANALYTICAL_MODEL, CREATIVE_MODEL, COORDINATOR_MODEL


class TestConfiguration:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test basic configuration initialization."""
        config = Config()
        
        # Test basic settings
        assert hasattr(config, 'environment')
        assert hasattr(config, 'api_host')
        assert hasattr(config, 'api_port')
        assert hasattr(config, 'log_level')
    
    def test_security_configuration(self):
        """Test security-related configuration."""
        config = Config()
        
        # Test security flags
        assert hasattr(config, 'security_enabled')
        assert hasattr(config, 'rate_limiting_enabled')
        assert hasattr(config, 'security_headers_enabled')
        assert hasattr(config, 'request_validation_enabled')
        
        # Test rate limiting config
        assert hasattr(config, 'rate_limit_requests_per_minute')
        assert hasattr(config, 'rate_limit_requests_per_hour')
        assert hasattr(config, 'rate_limit_chat_per_minute')
        assert hasattr(config, 'rate_limit_voice_per_minute')
        assert hasattr(config, 'rate_limit_websocket_connections')
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        config = Config()
        
        assert hasattr(config, 'cors_allowed_origins')
        assert hasattr(config, 'cors_allow_credentials')
        assert hasattr(config, 'cors_allowed_methods')
        assert hasattr(config, 'cors_allowed_headers')
    
    def test_cache_configuration(self):
        """Test cache configuration."""
        config = Config()
        
        assert hasattr(config, 'cache_enabled')
        assert hasattr(config, 'cache_ttl_hours')
        assert hasattr(config, 'cache_max_prompt_length')
        assert hasattr(config, 'cache_similarity_threshold')
    
    def test_url_properties(self):
        """Test URL generation properties."""
        config = Config()
        
        redis_url = config.redis_url
        assert "redis://" in redis_url
        assert str(config.redis_port) in redis_url
        
        tigergraph_url = config.tigergraph_url
        assert str(config.tigergraph_port) in tigergraph_url
        
        ollama_url = config.ollama_url
        assert "http://" in ollama_url
        assert str(config.ollama_port) in ollama_url
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'SECURITY_ENABLED': 'true',
        'RATE_LIMITING_ENABLED': 'false',
        'CORS_ALLOWED_ORIGINS': 'https://example.com,https://api.example.com',
        'TIGERGRAPH_PASSWORD': 'secure_test_password_123'  # Required for production
    })
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        config = Config()
        
        assert config.environment == 'production'
        assert config.security_enabled is True
        assert config.rate_limiting_enabled is False
        assert 'https://example.com' in config.cors_allowed_origins
    
    def test_default_values(self):
        """Test configuration default values."""
        config = Config()
        
        # Test security defaults
        assert config.security_enabled is True  # Default should be enabled
        assert config.rate_limiting_enabled is True
        assert config.rate_limit_requests_per_minute == 100
        assert config.rate_limit_websocket_connections == 5
        
        # Test cache defaults
        assert config.cache_enabled is True
        assert config.cache_ttl_hours == 24
    
    def test_validation_configuration(self):
        """Test request validation configuration."""
        config = Config()
        
        assert hasattr(config, 'max_request_size_mb')
        assert hasattr(config, 'max_json_size_mb')
        assert hasattr(config, 'max_query_params')
        
        assert config.max_request_size_mb == 10
        assert config.max_json_size_mb == 1
        assert config.max_query_params == 50


class TestModelConfiguration:
    """Test model configuration."""
    
    def test_model_constants(self):
        """Test model configuration constants."""
        assert ANALYTICAL_MODEL is not None
        assert CREATIVE_MODEL is not None
        assert COORDINATOR_MODEL is not None
        
        # Test that models are different
        assert ANALYTICAL_MODEL != CREATIVE_MODEL
        assert ANALYTICAL_MODEL != COORDINATOR_MODEL
        assert CREATIVE_MODEL != COORDINATOR_MODEL
    
    def test_model_import_from_config(self):
        """Test importing model configurations."""
        from config.models import ALL_MODELS, MODEL_MAPPING
        
        assert isinstance(ALL_MODELS, list)
        assert len(ALL_MODELS) >= 3  # At least the three main models
        
        assert isinstance(MODEL_MAPPING, dict)
        assert len(MODEL_MAPPING) >= 3


class TestConfigurationSecurity:
    """Test security aspects of configuration."""
    
    def test_password_handling(self):
        """Test secure password handling."""
        config = Config()
        
        # Test that password is handled securely
        assert hasattr(config, 'tigergraph_password')
        # Password should not be empty in most cases
        if config.tigergraph_password:
            assert isinstance(config.tigergraph_password, str)
    
    @patch.dict(os.environ, {
        'CSP_POLICY': "default-src 'self'; script-src 'none'",
        'HSTS_MAX_AGE': '63072000'
    })
    def test_security_headers_config(self):
        """Test security headers configuration."""
        config = Config()
        
        assert "default-src 'self'" in config.csp_policy
        assert config.hsts_max_age == 63072000
    
    def test_production_security_defaults(self):
        """Test that production has secure defaults."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'TIGERGRAPH_PASSWORD': 'secure_test_password_123'  # Required for production
        }):
            config = Config()
            
            # Production should have security enabled
            assert config.security_enabled is True
            assert config.rate_limiting_enabled is True
            assert config.security_headers_enabled is True
            assert config.request_validation_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])