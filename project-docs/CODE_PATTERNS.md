# 📋 Code Patterns - Hybrid AI Council

> **Standard patterns, conventions, and best practices for consistent development**

## 🎯 **Core Principles**

1. **Minimalist & Robust**: Simple, readable code over clever abstractions
2. **Single Responsibility**: Each module/function has one clear purpose
3. **Fail Fast**: Explicit error handling with structured logging
4. **Type Safety**: Full type hints for all function signatures
5. **500-Line Limit**: Split files before they exceed 500 lines

---

## 🗄️ **Database Connection Patterns**

### **Redis Client Pattern**

```python
# ✅ Standard Redis Connection
from clients.redis_client import get_redis_connection
from utils.error_utils import redis_circuit_breaker

@redis_circuit_breaker.call
async def redis_operation():
    async with get_redis_connection() as redis:
        result = await redis.get("key")
        return result

# ✅ Error Handling with Circuit Breaker
try:
    data = await redis_operation()
except Exception as e:
    logger.error("Redis operation failed", operation="get_key", error=str(e))
    # Graceful degradation
    return default_value
```

### **TigerGraph Connection Pattern**

```python
# ✅ Standard TigerGraph Connection
from clients.tigervector_client import get_tigergraph_connection

async def tigergraph_query(query: str, params: dict = None):
    try:
        async with get_tigergraph_connection() as conn:
            result = conn.runInstalledQuery(query, params or {})
            return result
    except Exception as e:
        logger.error("TigerGraph query failed", query=query, error=str(e))
        raise
```

---

## 🤖 **LLM Integration Patterns**

### **Standard LLM Call Pattern**

```python
# ✅ Standard Ollama Integration
from clients.ollama_client import get_ollama_client
import structlog

logger = structlog.get_logger(__name__)

async def generate_response(
    prompt: str, 
    model: str = "qwen2.5:14b",
    max_tokens: int = 1000
) -> str:
    """Generate LLM response with error handling and logging."""
    
    try:
        async with get_ollama_client() as client:
            response = await client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": max_tokens}
            )
            
            logger.info(
                "LLM response generated",
                model=model,
                prompt_length=len(prompt),
                response_length=len(response.message.content)
            )
            
            return response.message.content
            
    except Exception as e:
        logger.error(
            "LLM generation failed",
            model=model,
            prompt_length=len(prompt),
            error=str(e)
        )
        raise
```

### **Structured Prompt Pattern**

```python
# ✅ Consistent Prompt Structure
def build_prompt(context: str, task: str, constraints: list = None) -> str:
    """Build structured prompt with consistent format."""
    
    prompt_parts = [
        f"Context: {context}",
        f"Task: {task}"
    ]
    
    if constraints:
        prompt_parts.append("Constraints:")
        for constraint in constraints:
            prompt_parts.append(f"- {constraint}")
    
    prompt_parts.append("Response:")
    
    return "\n\n".join(prompt_parts)
```

---

## 💰 **KIP Agent Patterns**

### **Agent Action Pattern**

```python
# ✅ Standard Agent Action Execution
from core.kip import create_treasury
from core.kip.models import ActionResult

async def execute_agent_action(
    agent_id: str,
    tool_name: str,
    params: dict,
    max_cost_cents: int = 1000
) -> ActionResult:
    """Execute agent action with budget validation."""
    
    async with create_treasury() as treasury:
        # Pre-validate budget
        budget = await treasury.get_budget(agent_id)
        if budget.available_daily_budget < max_cost_cents:
            raise InsufficientFundsError(
                f"Insufficient daily budget: {budget.available_daily_budget} < {max_cost_cents}"
            )
        
        # Execute with transaction tracking
        result = await treasury.execute_action(
            agent_id=agent_id,
            tool_name=tool_name,
            params=params
        )
        
        logger.info(
            "Agent action executed",
            agent_id=agent_id,
            tool_name=tool_name,
            cost_cents=result.cost_cents,
            success=result.success
        )
        
        return result
```

### **Budget Validation Pattern**

```python
# ✅ Consistent Budget Validation
async def validate_spending(
    agent_id: str, 
    amount_cents: int,
    action_description: str
) -> bool:
    """Validate agent spending with comprehensive checks."""
    
    # Check emergency freeze
    if await treasury.is_emergency_freeze_active():
        raise EmergencyFreezeError("All spending frozen")
    
    # Check budget limits
    budget = await treasury.get_budget(agent_id)
    
    if amount_cents > budget.per_action_limit:
        raise UsageLimitExceededError(
            f"Action cost {amount_cents} exceeds per-action limit {budget.per_action_limit}"
        )
    
    if amount_cents > budget.available_daily_budget:
        raise UsageLimitExceededError(
            f"Action cost {amount_cents} exceeds daily budget {budget.available_daily_budget}"
        )
    
    return True
```

---

## 🌐 **API Endpoint Patterns**

### **FastAPI Endpoint Pattern**

```python
# ✅ Standard FastAPI Endpoint
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog

router = APIRouter()
logger = structlog.get_logger(__name__)

class RequestModel(BaseModel):
    """Request validation model."""
    field: str
    optional_field: Optional[int] = None

class ResponseModel(BaseModel):
    """Response model."""
    result: str
    success: bool

@router.post("/endpoint", response_model=ResponseModel)
async def endpoint_handler(request: RequestModel) -> ResponseModel:
    """
    Endpoint description.
    
    Args:
        request: Validated request data
        
    Returns:
        ResponseModel: Operation result
        
    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        logger.info("Endpoint called", endpoint="/endpoint", data=request.dict())
        
        # Business logic here
        result = await process_request(request)
        
        logger.info("Endpoint success", endpoint="/endpoint", result=result)
        return ResponseModel(result=result, success=True)
        
    except ValueError as e:
        logger.warning("Validation error", endpoint="/endpoint", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error("Endpoint error", endpoint="/endpoint", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
```

### **WebSocket Handler Pattern**

```python
# ✅ Standard WebSocket Handler
from fastapi import WebSocket, WebSocketDisconnect
import json

async def websocket_handler(websocket: WebSocket):
    """Standard WebSocket connection handler."""
    
    await websocket.accept()
    session_id = str(uuid.uuid4())
    
    logger.info("WebSocket connected", session_id=session_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(
                "WebSocket message received",
                session_id=session_id,
                message_type=message.get("type")
            )
            
            # Process message
            response = await process_websocket_message(message)
            
            # Send response
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        await websocket.close(code=1011, reason="Internal error")
```

---

## 🧪 **Testing Patterns**

### **Standard Test Structure**

```python
# ✅ Consistent Test Organization
import pytest
from unittest.mock import AsyncMock, patch
import structlog

# Module under test
from core.kip.budget_manager import BudgetManager

class TestBudgetManager:
    """Test suite for BudgetManager."""
    
    @pytest.fixture
    async def budget_manager(self, redis_client):
        """Provide test budget manager instance."""
        return BudgetManager(redis_client)
    
    @pytest.fixture
    def sample_budget_data(self):
        """Provide consistent test data."""
        return {
            "agent_id": "test_agent",
            "current_balance": 5000,
            "daily_limit": 10000,
            "per_action_limit": 1000
        }
    
    async def test_initialize_budget_success(
        self, 
        budget_manager, 
        sample_budget_data
    ):
        """Test successful budget initialization."""
        # Arrange
        agent_id = sample_budget_data["agent_id"]
        
        # Act
        budget = await budget_manager.initialize_agent_budget(agent_id)
        
        # Assert
        assert budget.agent_id == agent_id
        assert budget.current_balance == 5000
        assert budget.daily_limit == 10000
```

### **Mock Pattern for External Dependencies**

```python
# ✅ Consistent Mocking Pattern
@patch('clients.ollama_client.get_ollama_client')
async def test_llm_integration(mock_ollama):
    """Test LLM integration with mocked client."""
    
    # Setup mock
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.message.content = "Test response"
    mock_client.chat.return_value = mock_response
    mock_ollama.return_value.__aenter__.return_value = mock_client
    
    # Test
    result = await generate_response("Test prompt")
    
    # Verify
    assert result == "Test response"
    mock_client.chat.assert_called_once()
```

---

## 📝 **Logging Patterns**

### **Structured Logging Pattern**

```python
# ✅ Consistent Structured Logging
import structlog

logger = structlog.get_logger(__name__)

def process_transaction(agent_id: str, amount: int):
    """Process transaction with comprehensive logging."""
    
    # Start operation log
    logger.info(
        "Transaction processing started",
        agent_id=agent_id,
        amount_cents=amount,
        operation="process_transaction"
    )
    
    try:
        # Business logic
        result = perform_transaction(agent_id, amount)
        
        # Success log
        logger.info(
            "Transaction completed successfully",
            agent_id=agent_id,
            amount_cents=amount,
            transaction_id=result.transaction_id,
            new_balance=result.new_balance
        )
        
        return result
        
    except Exception as e:
        # Error log with context
        logger.error(
            "Transaction processing failed",
            agent_id=agent_id,
            amount_cents=amount,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

### **Performance Logging Pattern**

```python
# ✅ Performance Monitoring
import time
from functools import wraps

def log_performance(operation_name: str):
    """Decorator for performance logging."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    "Operation completed",
                    operation=operation_name,
                    duration_seconds=round(duration, 3),
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    "Operation failed",
                    operation=operation_name,
                    duration_seconds=round(duration, 3),
                    error=str(e),
                    success=False
                )
                raise
        return wrapper
    return decorator

# Usage
@log_performance("agent_action_execution")
async def execute_agent_action(...):
    # Implementation
    pass
```

---

## 🔧 **Configuration Patterns**

### **Environment Configuration Pattern**

```python
# ✅ Consistent Environment Handling
import os
from typing import Optional

def get_env_var(name: str, default: Optional[str] = None, required: bool = False) -> str:
    """Get environment variable with validation."""
    
    value = os.getenv(name, default)
    
    if required and value is None:
        raise ConfigurationError(f"Required environment variable {name} not set")
    
    logger.info("Environment variable loaded", name=name, has_value=value is not None)
    
    return value

# Usage
REDIS_HOST = get_env_var("REDIS_HOST", "localhost")
OLLAMA_URL = get_env_var("OLLAMA_URL", required=True)
```

### **Feature Flag Pattern**

```python
# ✅ Feature Flag Implementation
class FeatureFlags:
    """Centralized feature flag management."""
    
    def __init__(self):
        self.flags = {
            "experimental_agents": get_env_var("ENABLE_EXPERIMENTAL_AGENTS", "false").lower() == "true",
            "advanced_analytics": get_env_var("ENABLE_ADVANCED_ANALYTICS", "true").lower() == "true",
            "voice_processing": get_env_var("ENABLE_VOICE", "true").lower() == "true"
        }
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if feature flag is enabled."""
        return self.flags.get(flag_name, False)

# Global instance
feature_flags = FeatureFlags()

# Usage
if feature_flags.is_enabled("experimental_agents"):
    # Experimental feature code
    pass
```

---

## 🚨 **Error Handling Patterns**

### **Custom Exception Hierarchy**

```python
# ✅ Structured Exception Handling
class HybridAICouncilError(Exception):
    """Base exception for all application errors."""
    pass

class KIPLayerError(HybridAICouncilError):
    """Base exception for KIP layer errors."""
    pass

class InsufficientFundsError(KIPLayerError):
    """Raised when agent has insufficient funds."""
    
    def __init__(self, message: str, agent_id: str, required_amount: int, available_amount: int):
        super().__init__(message)
        self.agent_id = agent_id
        self.required_amount = required_amount
        self.available_amount = available_amount
```

### **Error Boundary Pattern**

```python
# ✅ Graceful Error Handling
async def with_error_boundary(
    operation: callable,
    operation_name: str,
    fallback_value: any = None
):
    """Execute operation with error boundary."""
    
    try:
        result = await operation()
        logger.info("Operation succeeded", operation=operation_name)
        return result
        
    except Exception as e:
        logger.error(
            "Operation failed, using fallback",
            operation=operation_name,
            error=str(e),
            fallback_value=fallback_value
        )
        return fallback_value

# Usage
result = await with_error_boundary(
    lambda: risky_operation(),
    "risky_operation",
    fallback_value="default"
)
```

---

## 📋 **File Organization Patterns**

### **Module Structure Pattern**

```python
# ✅ Standard module organization
"""
module_name.py - Brief description of module purpose

This module handles [specific responsibility].
Key components: [list main classes/functions]
"""

# Standard library imports
import asyncio
from typing import List, Optional

# Third-party imports
import structlog
from pydantic import BaseModel

# Local imports
from config import Config
from .models import DataModel
from .exceptions import ModuleError

# Module constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Module logger
logger = structlog.get_logger(__name__)

# Main classes/functions
class MainClass:
    """Class docstring with purpose and usage."""
    pass
```

### **Import Organization**

```python
# ✅ Consistent import order
# 1. Standard library
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict

# 2. Third-party packages
import structlog
import redis.asyncio as redis
from pydantic import BaseModel, Field

# 3. Local application imports
from config import Config
from clients.redis_client import get_redis_connection
from .models import AgentBudget
from .exceptions import BudgetNotFoundError
```

---

## 🎯 **Documentation Patterns**

### **Function Documentation Pattern**

```python
# ✅ Comprehensive function documentation
async def validate_agent_spending(
    agent_id: str,
    amount_cents: int,
    action_description: str,
    emergency_freeze_active: bool = False
) -> bool:
    """
    Validate if agent can spend the specified amount.
    
    Performs comprehensive validation including:
    - Emergency freeze status
    - Daily spending limits
    - Per-action spending limits
    - Current budget availability
    
    Args:
        agent_id: Unique identifier for the agent
        amount_cents: Amount to spend in USD cents
        action_description: Description of the action requiring spending
        emergency_freeze_active: Whether system emergency freeze is active
        
    Returns:
        bool: True if spending is allowed
        
    Raises:
        EmergencyFreezeError: If emergency freeze is active
        InsufficientFundsError: If agent lacks sufficient funds
        UsageLimitExceededError: If spending exceeds configured limits
        
    Example:
        >>> await validate_agent_spending("agent_001", 500, "API call")
        True
    """
```

---

## 🏆 **Best Practices Checklist**

### **Before Committing Code**

- [ ] All functions have type hints
- [ ] Error handling with specific exceptions
- [ ] Structured logging with context
- [ ] Tests cover main functionality
- [ ] File under 500 lines
- [ ] No hardcoded credentials
- [ ] Documentation for non-obvious logic

### **Code Review Checklist**

- [ ] Follows established patterns
- [ ] Consistent naming conventions
- [ ] Proper error boundaries
- [ ] Performance considerations addressed
- [ ] Security implications reviewed
- [ ] Tests are meaningful and maintainable