#!/usr/bin/env python3
"""Quick financial status check for Makefile."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def check_finances():
    """Check current financial status."""
    try:
        from core.kip import Treasury
        from config import Config
        
        config = Config()
        treasury = Treasury(config)
        
        async with treasury:
            analytics = await treasury.get_economic_analytics()
            print(f'💰 Total Balance: ${analytics.total_balance/100:.2f}')
            print(f'📈 Total Spent: ${analytics.total_spent/100:.2f}')
            print(f'🎯 Total Earned: ${analytics.total_earned/100:.2f}')
            print(f'🤖 Active Agents: {analytics.active_agents}/{analytics.total_agents}')
            print(f'📊 System ROI: {analytics.system_roi:.2%}')
            
    except ImportError as e:
        print(f'❌ KIP layer not available: {e}')
    except Exception as e:
        print(f'❌ Cannot check finances: {e}')

if __name__ == "__main__":
    asyncio.run(check_finances())