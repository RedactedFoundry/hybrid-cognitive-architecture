#!/usr/bin/env python3
"""
Test Smart Router Classification and Response Quality
"""

import asyncio
import requests
import time
import json
import os

async def test_smart_router():
    """Test the Smart Router with different types of queries"""
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
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
    
    print("🧠 Testing Smart Router Classification...\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}: {case['query']}")
        print(f"Expected Intent: {case['expected_intent']}")
        
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
                
                print(f"✅ Response received ({response_length} chars)")
                print(f"Response: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
                
                # Check if it's appropriately brief for simple queries
                if case["expected_intent"] == "simple_query_task":
                    if response_length > 300:
                        print(f"⚠️  WARNING: Response too long for simple query ({response_length} chars)")
                    else:
                        print(f"✅ Good: Appropriate length for simple query")
                        
            else:
                print(f"❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 60)
        time.sleep(2)  # Brief pause between requests

if __name__ == "__main__":
    asyncio.run(test_smart_router())