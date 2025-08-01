# tools/web_tools.py
"""
Web-based tools for KIP agents.

This module provides tools that interact with external web APIs and services,
enabling agents to gather real-time data from the internet.
"""

import asyncio
from typing import Dict, Any, Optional
import aiohttp
import structlog

logger = structlog.get_logger("WebTools")


async def get_current_bitcoin_price() -> str:
    """
    Get the current Bitcoin price in USD from CoinGecko API.
    
    This tool demonstrates real-time data access for KIP agents.
    Agents can use this to make informed decisions based on current market data.
    
    Returns:
        str: Current Bitcoin price in USD format (e.g., "$45,123.45")
        
    Raises:
        aiohttp.ClientError: If the API request fails
        ValueError: If the API response is invalid
        asyncio.TimeoutError: If the request times out
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    logger.info("Fetching current Bitcoin price from CoinGecko API")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                # Check if request was successful
                response.raise_for_status()
                
                # Parse JSON response
                price_data = await response.json()
                
                # Extract Bitcoin price
                if "bitcoin" not in price_data or "usd" not in price_data["bitcoin"]:
                    raise ValueError("Invalid API response format")
                    
                bitcoin_price = price_data["bitcoin"]["usd"]
                
                # Format as currency string
                price_formatted = f"${bitcoin_price:,.2f}"
                
                logger.info(
                    "Bitcoin price retrieved successfully",
                    price=price_formatted,
                    raw_price=bitcoin_price
                )
                
                return price_formatted
                
    except aiohttp.ClientError as e:
        logger.error(
            "Failed to fetch Bitcoin price - API request error",
            error=str(e),
            url=url
        )
        raise aiohttp.ClientError(f"CoinGecko API request failed: {e}")
        
    except asyncio.TimeoutError as e:
        logger.error(
            "Failed to fetch Bitcoin price - request timeout",
            timeout_seconds=10,
            url=url
        )
        raise asyncio.TimeoutError("CoinGecko API request timed out after 10 seconds")
        
    except ValueError as e:
        logger.error(
            "Failed to fetch Bitcoin price - invalid response",
            error=str(e),
            url=url
        )
        raise ValueError(f"Invalid API response: {e}")
        
    except Exception as e:
        logger.error(
            "Failed to fetch Bitcoin price - unexpected error",
            error=str(e),
            error_type=type(e).__name__,
            url=url
        )
        raise Exception(f"Unexpected error fetching Bitcoin price: {e}")


async def get_current_ethereum_price() -> str:
    """
    Get the current Ethereum price in USD from CoinGecko API.
    
    Returns:
        str: Current Ethereum price in USD format (e.g., "$2,456.78")
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
    
    logger.info("Fetching current Ethereum price from CoinGecko API")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                price_data = await response.json()
                
                if "ethereum" not in price_data or "usd" not in price_data["ethereum"]:
                    raise ValueError("Invalid API response format")
                    
                ethereum_price = price_data["ethereum"]["usd"]
                price_formatted = f"${ethereum_price:,.2f}"
                
                logger.info(
                    "Ethereum price retrieved successfully",
                    price=price_formatted,
                    raw_price=ethereum_price
                )
                
                return price_formatted
                
    except Exception as e:
        logger.error(
            "Failed to fetch Ethereum price",
            error=str(e),
            error_type=type(e).__name__
        )
        raise


async def get_crypto_market_summary() -> Dict[str, Any]:
    """
    Get a summary of major cryptocurrency prices.
    
    Returns:
        Dict[str, Any]: Market summary with multiple cryptocurrency prices
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,cardano,polkadot&vs_currencies=usd&include_24hr_change=true"
    
    logger.info("Fetching crypto market summary from CoinGecko API")
    
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                market_data = await response.json()
                
                # Format the data into a readable summary
                market_summary = {}
                
                for crypto_id, price_data in market_data.items():
                    if "usd" in price_data:
                        price = price_data["usd"]
                        change_24h = price_data.get("usd_24h_change", 0)
                        
                        market_summary[crypto_id] = {
                            "price": f"${price:,.2f}",
                            "24h_change": f"{change_24h:+.2f}%",
                            "raw_price": price,
                            "raw_change": change_24h
                        }
                
                logger.info(
                    "Crypto market summary retrieved successfully",
                    cryptocurrencies=list(market_summary.keys())
                )
                
                return market_summary
                
    except Exception as e:
        logger.error(
            "Failed to fetch crypto market summary",
            error=str(e),
            error_type=type(e).__name__
        )
        raise


# Tool registry for easy access
WEB_TOOLS = {
    "get_bitcoin_price": get_current_bitcoin_price,
    "get_ethereum_price": get_current_ethereum_price,
    "get_crypto_summary": get_crypto_market_summary,
}