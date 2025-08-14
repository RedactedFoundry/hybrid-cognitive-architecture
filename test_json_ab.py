#!/usr/bin/env python3
"""
A/B Testing Script for JSON Prompting
Tests complex queries before and after JSON structuring implementation
"""

import asyncio
import time
import json
from datetime import datetime
from typing import List, Dict, Any
import websocket
import threading

# Test queries - diverse complex reasoning across multiple domains
TEST_QUERIES = [
    # Business Strategy (different industries)
    "What are the pros and cons of starting an AI business in 2025 and how can we maximize success?",
    "Should I open a restaurant franchise or start an independent restaurant? Analyze the key factors and trade-offs.",
    "Compare the advantages and disadvantages of remote work vs hybrid work for a growing tech company.",
    
    # Life Decisions & Personal Development  
    "I'm 25 and deciding between pursuing an MBA or gaining 2 years of work experience. What factors should I consider?",
    "What are the benefits and risks of buying a house vs renting in today's market, and how should I decide?",
    "How should I balance career advancement with work-life balance when considering a demanding new job offer?",
    
    # Scientific & Technical Analysis
    "Explain the trade-offs between renewable energy sources and fossil fuels from economic, environmental, and practical perspectives.",
    "What are the pros and cons of different approaches to treating depression: therapy, medication, lifestyle changes, and combinations?",
    "Compare and contrast the benefits and limitations of electric vehicles versus traditional gasoline cars in 2025.",
    
    # Creative Problem Solving & Innovation
    "How can cities reduce traffic congestion? Analyze multiple approaches and their effectiveness.",
    "What are innovative ways to make education more engaging and effective for modern students?",
    "How can we address the problem of social media addiction while preserving the benefits of connectivity?",
    
    # Ethical & Social Dilemmas
    "What are the ethical implications of AI in hiring decisions, and how should companies balance efficiency with fairness?",
    "Should governments regulate social media platforms more strictly? Analyze the arguments for and against.",
    "How should society balance individual privacy rights with collective security needs in the digital age?",
    
    # Historical & Comparative Analysis
    "What lessons can modern entrepreneurs learn from the dot-com bubble of the late 1990s?",
    "Compare the industrial revolution's impact on society with the current AI revolution's potential effects.",
    "How do different countries' approaches to healthcare (US, UK, Canada, Japan) compare in terms of outcomes and costs?"
]

WS_URL = "ws://localhost:8001/ws/chat"

class TestResult:
    def __init__(self, query: str, response: str, duration: float, timestamp: str):
        self.query = query
        self.response = response
        self.duration = duration
        self.timestamp = timestamp
        self.response_length = len(response)
        self.words_per_second = len(response.split()) / duration if duration > 0 else 0
        self.success = len(response) > 0  # Consider successful if we got a response

def test_query(query: str, test_type: str) -> TestResult:
    """Test a single query and return results using WebSocket"""
    print(f"\n{'='*60}")
    print(f"Testing ({test_type}): {query[:80]}...")
    print(f"{'='*60}")
    
    start_time = time.time()
    timestamp = datetime.now().isoformat()
    
    # Shared state for WebSocket communication
    result_data = {
        'response': '',
        'complete': False,
        'error': None
    }
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get('type') == 'final':
                result_data['response'] = data.get('content', '')
                result_data['complete'] = True
            elif data.get('type') == 'error':
                result_data['error'] = data.get('content', 'Unknown error')
                result_data['complete'] = True
        except json.JSONDecodeError:
            result_data['error'] = f"Invalid JSON response: {message}"
            result_data['complete'] = True
    
    def on_error(ws, error):
        result_data['error'] = str(error)
        result_data['complete'] = True
    
    def on_open(ws):
        # Send the query
        message = {
            "message": query,
            "conversation_id": f"test_ab_{int(time.time())}"
        }
        ws.send(json.dumps(message))
    
    try:
        # Create WebSocket connection
        ws = websocket.WebSocketApp(
            WS_URL,
            on_message=on_message,
            on_error=on_error,
            on_open=on_open
        )
        
        # Run in thread with timeout
        def run_ws():
            ws.run_forever()
        
        ws_thread = threading.Thread(target=run_ws)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for completion with timeout
        max_wait = 120  # 2 minutes
        waited = 0
        while not result_data['complete'] and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
        
        # Close WebSocket
        ws.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result_data['error']:
            print(f"❌ Error: {result_data['error']}")
            return TestResult(query, f"ERROR: {result_data['error']}", duration, timestamp)
        elif result_data['response']:
            response_text = result_data['response']
            print(f"✅ Success! Duration: {duration:.2f}s")
            print(f"Response length: {len(response_text)} chars")
            print(f"Response preview: {response_text[:200]}...")
            return TestResult(query, response_text, duration, timestamp)
        else:
            print(f"❌ Timeout: No response after {duration:.2f}s")
            return TestResult(query, "TIMEOUT: No response received", duration, timestamp)
            
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Exception: {str(e)}")
        return TestResult(query, f"EXCEPTION: {str(e)}", duration, timestamp)

def save_results(results: List[TestResult], filename: str):
    """Save test results to JSON file"""
    data = []
    for result in results:
        data.append({
            "query": result.query,
            "response": result.response,
            "duration": result.duration,
            "timestamp": result.timestamp,
            "response_length": result.response_length,
            "words_per_second": result.words_per_second
        })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Results saved to {filename}")

def print_summary(results: List[TestResult], test_type: str):
    """Print summary statistics"""
    if not results:
        print(f"No results for {test_type}")
        return
    
    durations = [r.duration for r in results if "ERROR" not in r.response and "EXCEPTION" not in r.response]
    response_lengths = [r.response_length for r in results if "ERROR" not in r.response and "EXCEPTION" not in r.response]
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        avg_length = sum(response_lengths) / len(response_lengths)
        
        print(f"\n📈 {test_type} Summary:")
        print(f"  Average Duration: {avg_duration:.2f}s")
        print(f"  Average Response Length: {avg_length:.0f} chars")
        print(f"  Success Rate: {len(durations)}/{len(results)} ({len(durations)/len(results)*100:.1f}%)")
        print(f"  Fastest: {min(durations):.2f}s")
        print(f"  Slowest: {max(durations):.2f}s")

def run_baseline_tests():
    """Run baseline tests before JSON implementation"""
    print("🚀 Starting BASELINE tests (before JSON structuring)...")
    
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Testing baseline query...")
        result = test_query(query, "BASELINE")
        results.append(result)
        
        # Brief pause between queries
        time.sleep(2)
    
    save_results(results, "baseline_results.json")
    print_summary(results, "BASELINE")
    
    return results

def run_json_prompting_tests():
    """Run JSON prompting tests with updated Constitution v5.4 flow"""
    print("🚀 Starting JSON PROMPTING tests (with JSON structuring)...")
    
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Testing JSON prompting query...")
        result = test_query(query, "JSON_PROMPTING")
        results.append(result)
        
        # Brief pause between queries
        time.sleep(2)
    
    save_results(results, "json_prompting_results.json")
    print_summary(results, "JSON PROMPTING")
    
    return results

def compare_results(baseline_results, json_results):
    """Compare baseline vs JSON prompting results"""
    print("\n🔍 COMPARATIVE ANALYSIS")
    print("="*60)
    
    def calc_stats(results):
        durations = [r.duration for r in results if r.success]
        lengths = [len(r.response) for r in results if r.success]
        return {
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'avg_length': sum(lengths) / len(lengths) if lengths else 0,
            'success_rate': len(durations) / len(results) * 100,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0
        }
    
    baseline_stats = calc_stats(baseline_results)
    json_stats = calc_stats(json_results)
    
    print(f"📊 PERFORMANCE COMPARISON:")
    print(f"  Average Duration:     {baseline_stats['avg_duration']:.2f}s → {json_stats['avg_duration']:.2f}s ({json_stats['avg_duration']-baseline_stats['avg_duration']:+.2f}s)")
    print(f"  Average Length:       {baseline_stats['avg_length']:.0f} → {json_stats['avg_length']:.0f} chars ({json_stats['avg_length']-baseline_stats['avg_length']:+.0f})")
    print(f"  Success Rate:         {baseline_stats['success_rate']:.1f}% → {json_stats['success_rate']:.1f}%")
    print(f"  Speed Range:          {baseline_stats['min_duration']:.1f}-{baseline_stats['max_duration']:.1f}s → {json_stats['min_duration']:.1f}-{json_stats['max_duration']:.1f}s")
    
    # Speed improvement analysis
    duration_change = json_stats['avg_duration'] - baseline_stats['avg_duration']
    if duration_change < -1:
        print(f"🚀 JSON prompting is {abs(duration_change):.1f}s FASTER on average!")
    elif duration_change > 1:
        print(f"🐌 JSON prompting is {duration_change:.1f}s SLOWER on average")
    else:
        print(f"⚖️ Performance is similar (±1s difference)")
    
    # Length change analysis  
    length_change = json_stats['avg_length'] - baseline_stats['avg_length']
    length_pct = (length_change / baseline_stats['avg_length']) * 100 if baseline_stats['avg_length'] > 0 else 0
    print(f"📝 Response length change: {length_change:+.0f} chars ({length_pct:+.1f}%)")

if __name__ == "__main__":
    print("🧪 JSON Prompting A/B Test Suite")
    print("=" * 50)
    
    # Step 1: Load or run baseline tests
    try:
        with open("baseline_results.json", "r") as f:
            baseline_data = json.load(f)
            # Only pass the parameters that TestResult expects
            baseline_results = [TestResult(
                query=item["query"],
                response=item["response"], 
                duration=item["duration"],
                timestamp=item["timestamp"]
            ) for item in baseline_data]
        print("📂 Loaded existing baseline results")
        print_summary(baseline_results, "BASELINE (loaded)")
    except FileNotFoundError:
        print("🚀 No existing baseline found, running baseline tests...")
        baseline_results = run_baseline_tests()
    
    print("\n" + "="*60)
    print("⏱️ Waiting 10 seconds before JSON prompting tests...")
    print("="*60)
    time.sleep(10)
    
    # Step 2: Run JSON prompting tests  
    json_results = run_json_prompting_tests()
    
    # Step 3: Compare results
    compare_results(baseline_results, json_results)
    
    print("\n" + "="*60)
    print("✅ A/B TESTING COMPLETE!")
    print("Check baseline_results.json and json_prompting_results.json for detailed results")
    print("="*60)
