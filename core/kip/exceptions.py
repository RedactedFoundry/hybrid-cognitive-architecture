# core/kip/exceptions.py
"""
KIP Layer Custom Exceptions

This module defines custom exception classes for the KIP Layer,
providing better error handling and debugging capabilities.
"""


class KIPLayerError(Exception):
    """Base exception for all KIP Layer errors."""
    pass


class AgentNotFoundError(KIPLayerError):
    """Raised when a requested agent cannot be found."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        super().__init__(f"Agent '{agent_id}' not found")


class AgentAuthorizationError(KIPLayerError):
    """Raised when an agent is not authorized to perform an action."""
    
    def __init__(self, agent_id: str, action: str):
        self.agent_id = agent_id
        self.action = action
        super().__init__(f"Agent '{agent_id}' not authorized for action: {action}")


class ToolNotFoundError(KIPLayerError):
    """Raised when a requested tool cannot be found."""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' not found")


class ToolExecutionError(KIPLayerError):
    """Raised when tool execution fails."""
    
    def __init__(self, tool_name: str, original_error: str):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool '{tool_name}' execution failed: {original_error}")


class InsufficientFundsError(KIPLayerError):
    """Raised when an agent has insufficient funds for an action."""
    
    def __init__(self, agent_id: str, required: int, available: int):
        self.agent_id = agent_id
        self.required = required
        self.available = available
        super().__init__(
            f"Agent '{agent_id}' has insufficient funds: "
            f"required ${required/100:.2f}, available ${available/100:.2f}"
        )


class UsageLimitExceededError(KIPLayerError):
    """Raised when daily usage limits are exceeded."""
    
    def __init__(self, agent_id: str, tool_name: str, current_usage: int, limit: int):
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.current_usage = current_usage
        self.limit = limit
        super().__init__(
            f"Agent '{agent_id}' exceeded daily limit for tool '{tool_name}': "
            f"{current_usage}/{limit} uses"
        )


class TreasuryError(KIPLayerError):
    """Base exception for Treasury-related errors."""
    pass


class BudgetNotFoundError(TreasuryError):
    """Raised when an agent's budget cannot be found."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        super().__init__(f"Budget for agent '{agent_id}' not found")


class TransactionError(TreasuryError):
    """Raised when a transaction cannot be processed."""
    
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Transaction failed: {reason}")


class EmergencyFreezeError(TreasuryError):
    """Raised when operations are blocked due to emergency freeze."""
    
    def __init__(self, reason: str = "Emergency freeze active"):
        self.reason = reason
        super().__init__(f"Operation blocked: {reason}")


class ConfigurationError(KIPLayerError):
    """Raised when there are configuration issues."""
    
    def __init__(self, parameter: str, issue: str):
        self.parameter = parameter
        self.issue = issue
        super().__init__(f"Configuration error in '{parameter}': {issue}")


class ConnectionError(KIPLayerError):
    """Raised when database connections fail."""
    
    def __init__(self, service: str, details: str):
        self.service = service
        self.details = details
        super().__init__(f"Failed to connect to {service}: {details}")