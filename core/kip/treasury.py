# core/kip/treasury.py
"""
KIP Treasury - Economic Engine and Financial Management

REFACTORED: This module has been split into focused components for better maintainability.

The original 850-line Treasury class has been refactored into:
- BudgetManager: Budget allocation and limits (budget_manager.py)
- TransactionProcessor: Transaction recording and history (transaction_processor.py) 
- EconomicAnalyzer: ROI calculations and analytics (economic_analyzer.py)
- TreasuryCore: Main coordination and emergency controls (treasury_core.py)

This file now provides backward compatibility imports.

BEFORE: 850 lines - monolithic class with multiple responsibilities
AFTER: 4 focused modules - each <300 lines with single responsibility
"""

# Backward compatibility imports
from .treasury_core import TreasuryCore as Treasury, create_treasury, treasury_session
from .budget_manager import BudgetManager
from .transaction_processor import TransactionProcessor
from .economic_analyzer import EconomicAnalyzer

# Export the main interface
__all__ = [
    'Treasury',
    'create_treasury', 
    'treasury_session',
    'BudgetManager',
    'TransactionProcessor',
    'EconomicAnalyzer'
]