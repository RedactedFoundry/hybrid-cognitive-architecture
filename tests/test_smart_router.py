#!/usr/bin/env python3
"""
Test Smart Router Classification and Response Quality
"""

import asyncio
import requests
import time
import json
import os
import structlog

# Configure logging for smart router testing
logger = structlog.get_logger("smart_router_test")

async def test_smart_router():
    """Test the Smart Router with different types of queries"""
    
    # Wait for server to start
    logger.info("Waiting for server to start", component="smart_router")
    time.sleep(3)
    
    test_cases = [
        {
            "query": "Who is the CEO of Google?",
            "expected_intent": "simple_query_task",
            "expected_response_type": "short factual answer"
        },
        {
            "query": "What color is the sky typically?", 
            "expected_intent": "simple_query_task",
            "expected_response_type": "short factual answer"
        },
        {
            "query": "What are the pros and cons of AI in education?",
            "expected_intent": "complex_reasoning_task", 
            "expected_response_type": "detailed analysis"
        },
        {
            "query": "Find connections between my research notes",
            "expected_intent": "exploratory_task",
            "expected_response_type": "pattern discovery"
        },
        {
            "query": "Execute the Q2 sales report",
            "expected_intent": "action_task",
            "expected_response_type": "action execution"
        }
    ]
    
    logger.info("Starting Smart Router classification tests", 
                component="smart_router", 
                test_count=len(test_cases))
    
    for i, case in enumerate(test_cases, 1):
        logger.info("Running test case", 
                   test_number=i,
                   query=case['query'],
                   expected_intent=case['expected_intent'])
        
        try:
            # Make request to the API - configurable via environment
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            response = requests.post(
                f"{api_base_url}/api/chat",
                json={
                    "message": case["query"],
                    "conversation_id": f"test_{i}"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "No response")
                response_length = len(response_text)
                
                logger.info("Response received successfully", 
                           test_number=i,
                           response_length=response_length,
                           response_preview=response_text[:200])
                
                # Check if it's appropriately brief for simple queries
                if case["expected_intent"] == "simple_query_task":
                    if response_length > 300:
                        logger.warning("Response too long for simple query", 
                                     test_number=i,
                                     response_length=response_length,
                                     expected_intent=case["expected_intent"])
                    else:
                        logger.info("Response length appropriate for query type", 
                                   test_number=i,
                                   response_length=response_length)
                        
            else:
                logger.error("Request failed", 
                            test_number=i,
                            status_code=response.status_code)
                
        except Exception as e:
            logger.error("Test case failed", 
                        test_number=i,
                        error=str(e))
        
        logger.debug("Test case completed", test_number=i)
        time.sleep(2)  # Brief pause between requests

if __name__ == "__main__":
    asyncio.run(test_smart_router())