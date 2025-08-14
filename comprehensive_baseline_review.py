#!/usr/bin/env python3
"""
COMPREHENSIVE Question-by-Question Baseline Review
Analyzes every single response for quality and routing correctness
"""

import json
from typing import List, Dict, Any

def load_results(filename: str) -> List[Dict[str, Any]]:
    """Load test results from JSON file"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_individual_response(query_num: int, result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single response comprehensively"""
    
    query = result['query']
    response = result['response']
    duration = result['duration']
    response_length = result['response_length']
    
    # Determine ACTUAL path taken
    if duration < 5.0 and response_length < 500:
        actual_path = "FAST_RESPONSE"
    else:
        actual_path = "CONSTITUTION_V5.4"
    
    # Determine what path SHOULD have been taken
    # Complex tasks that need thorough analysis, pros/cons, multiple factors
    complex_indicators = [
        "pros and cons", "compare", "analyze", "trade-offs", "benefits and risks",
        "approaches", "advantages and disadvantages", "factors to consider",
        "how should", "what should", "balance", "multiple", "different approaches"
    ]
    
    simple_indicators = [
        "what is", "who is", "when is", "where is", "define", "explain briefly"
    ]
    
    # Check query complexity
    query_lower = query.lower()
    has_complex_indicators = any(indicator in query_lower for indicator in complex_indicators)
    has_simple_indicators = any(indicator in query_lower for indicator in simple_indicators)
    
    # Determine SHOULD path based on question complexity
    if has_simple_indicators and not has_complex_indicators:
        should_path = "FAST_RESPONSE"
        complexity_reasoning = "Simple factual question"
    elif has_complex_indicators or "decision" in query_lower or len(query.split()) > 15:
        should_path = "CONSTITUTION_V5.4"
        complexity_reasoning = "Complex analysis requiring multiple factors/perspectives"
    else:
        # Middle ground - depends on depth needed
        if any(word in query_lower for word in ["should i", "how do i", "what factors", "how can"]):
            should_path = "CONSTITUTION_V5.4"
            complexity_reasoning = "Personal decision requiring comprehensive advice"
        else:
            should_path = "FAST_RESPONSE"
            complexity_reasoning = "Straightforward question"
    
    # Check for template language issues
    template_phrases = [
        "Unfortunately, at this time, our multi-agent analytical deliberation",
        "no concrete data or results from KIP agent execution",
        "our Pheromind Layer did not detect any significant ambient patterns",
        "Council Layer, which represents multi-agent analytical deliberation",
        "KIP Layer, although no specific data is available",
        "Pheromind Layer",
        "Council Layer",
        "KIP Layer",
        "agent execution results",
        "cognitive layers"
    ]
    
    template_issues = []
    for phrase in template_phrases:
        if phrase in response:
            template_issues.append(phrase)
    
    # Grade response quality (1-10 scale)
    quality_score = 10
    quality_issues = []
    
    # Deduct for template language
    if template_issues:
        quality_score -= 3
        quality_issues.append(f"Template language pollution ({len(template_issues)} phrases)")
    
    # Deduct for length appropriateness
    if should_path == "CONSTITUTION_V5.4" and response_length < 300:
        quality_score -= 4
        quality_issues.append("Too brief for complex question")
    elif should_path == "FAST_RESPONSE" and response_length > 1000:
        quality_score -= 2
        quality_issues.append("Unnecessarily verbose for simple question")
    
    # Deduct for routing mismatch
    if actual_path != should_path:
        if should_path == "CONSTITUTION_V5.4" and actual_path == "FAST_RESPONSE":
            quality_score -= 5
            quality_issues.append("CRITICAL: Complex question routed to fast path - missing depth")
        else:
            quality_score -= 2
            quality_issues.append("Simple question unnecessarily sent to complex path")
    
    # Check for specific content quality
    if actual_path == "FAST_RESPONSE" and response_length < 150:
        quality_score -= 2
        quality_issues.append("Fast response too brief even for simple path")
    
    # Check for helpfulness
    if "I apologize" in response or "I don't have" in response:
        quality_score -= 1
        quality_issues.append("Apologetic/unhelpful tone")
    
    # Ensure minimum score
    quality_score = max(1, quality_score)
    
    return {
        "query_num": query_num,
        "query": query,
        "actual_path": actual_path,
        "should_path": should_path,
        "routing_correct": actual_path == should_path,
        "complexity_reasoning": complexity_reasoning,
        "duration": duration,
        "response_length": response_length,
        "template_issues": template_issues,
        "quality_score": quality_score,
        "quality_issues": quality_issues,
        "response_preview": response[:200] + "..." if len(response) > 200 else response
    }

def main():
    print("🔍 COMPREHENSIVE QUESTION-BY-QUESTION BASELINE REVIEW")
    print("=" * 80)
    
    results = load_results('baseline_results.json')
    
    analyses = []
    routing_errors = []
    template_pollution_count = 0
    total_quality_score = 0
    
    for i, result in enumerate(results, 1):
        analysis = analyze_individual_response(i, result)
        analyses.append(analysis)
        
        if not analysis["routing_correct"]:
            routing_errors.append(analysis)
        
        if analysis["template_issues"]:
            template_pollution_count += 1
        
        total_quality_score += analysis["quality_score"]
        
        # Print detailed analysis for each question
        print(f"\n📋 QUERY {i:2d}: {analysis['quality_score']}/10")
        print(f"Question: {analysis['query']}")
        print(f"Actual Path:  {analysis['actual_path']}")
        print(f"Should Path:  {analysis['should_path']} ({analysis['complexity_reasoning']})")
        print(f"Routing: {'✅ CORRECT' if analysis['routing_correct'] else '❌ WRONG'}")
        print(f"Duration: {analysis['duration']:.1f}s | Length: {analysis['response_length']} chars")
        
        if analysis['template_issues']:
            print(f"Template Issues: {len(analysis['template_issues'])} phrases")
            for issue in analysis['template_issues'][:2]:  # Show first 2
                print(f"  • '{issue[:50]}...'")
        
        if analysis['quality_issues']:
            print(f"Quality Issues:")
            for issue in analysis['quality_issues']:
                print(f"  • {issue}")
        
        print(f"Response Preview: {analysis['response_preview']}")
        print("-" * 60)
    
    # Summary analysis
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE SUMMARY")
    print(f"{'='*80}")
    
    average_quality = total_quality_score / len(analyses)
    correct_routing = len([a for a in analyses if a["routing_correct"]])
    
    print(f"Overall Quality Score: {average_quality:.1f}/10")
    print(f"Routing Accuracy: {correct_routing}/{len(analyses)} ({correct_routing/len(analyses)*100:.1f}%)")
    print(f"Template Pollution: {template_pollution_count}/{len(analyses)} responses ({template_pollution_count/len(analyses)*100:.1f}%)")
    
    if routing_errors:
        print(f"\n❌ ROUTING ERRORS ({len(routing_errors)}):")
        for error in routing_errors:
            print(f"  Query {error['query_num']}: {error['query'][:60]}...")
            print(f"    Went to {error['actual_path']}, should have gone to {error['should_path']}")
            print(f"    Reason: {error['complexity_reasoning']}")
    
    # Specific recommendations
    print(f"\n🎯 SPECIFIC RECOMMENDATIONS:")
    
    fast_to_complex = [a for a in analyses if a['should_path'] == 'CONSTITUTION_V5.4' and a['actual_path'] == 'FAST_RESPONSE']
    if fast_to_complex:
        print(f"\n🚨 CRITICAL: {len(fast_to_complex)} complex questions incorrectly sent to fast path:")
        for item in fast_to_complex:
            print(f"  • Query {item['query_num']}: {item['query'][:60]}...")
    
    template_responses = [a for a in analyses if a['template_issues']]
    if template_responses:
        print(f"\n🔧 Template language needs fixing in {len(template_responses)} responses")
    
    brief_responses = [a for a in analyses if a['response_length'] < 200 and a['should_path'] == 'CONSTITUTION_V5.4']
    if brief_responses:
        print(f"\n📏 {len(brief_responses)} complex questions got inadequately brief responses")

if __name__ == "__main__":
    main()
