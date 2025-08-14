#!/usr/bin/env python3
"""
Detailed Quality Comparison: Baseline vs JSON Prompting
Analyzes every single response pair for quality differences
"""

import json
from typing import Dict, List, Tuple

def load_results(filename: str) -> List[Dict]:
    """Load test results from JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_response_quality(response: str, query: str) -> Dict[str, int]:
    """Analyze response quality on multiple dimensions (1-10 scale)"""
    
    # Structure Analysis
    has_numbered_points = any(str(i) + '.' in response for i in range(1, 11))
    has_sections = any(keyword in response.lower() for keyword in ['advantages:', 'disadvantages:', 'benefits:', 'risks:', 'pros:', 'cons:'])
    logical_flow = len(response.split('\n\n')) >= 3  # Multiple paragraphs
    
    structure_score = (
        (3 if has_numbered_points else 0) +
        (3 if has_sections else 0) + 
        (4 if logical_flow else 2)
    )
    
    # Completeness Analysis
    word_count = len(response.split())
    addresses_multiple_factors = response.lower().count('factor') + response.lower().count('consider') + response.lower().count('aspect')
    provides_examples = response.lower().count('example') + response.lower().count('instance') + response.lower().count('such as')
    
    completeness_score = min(10, (
        (4 if word_count > 200 else 2) +
        (3 if addresses_multiple_factors >= 2 else 1) +
        (3 if provides_examples >= 1 else 1)
    ))
    
    # Actionability Analysis  
    actionable_words = ['should', 'can', 'consider', 'try', 'implement', 'start', 'focus', 'avoid', 'ensure', 'recommend']
    actionable_count = sum(response.lower().count(word) for word in actionable_words)
    has_steps = any(keyword in response.lower() for keyword in ['step', 'approach', 'strategy', 'method'])
    
    actionability_score = min(10, (
        (5 if actionable_count >= 5 else 2) +
        (5 if has_steps else 3)
    ))
    
    # Depth Analysis
    analytical_words = ['because', 'therefore', 'however', 'furthermore', 'moreover', 'consequently', 'analysis', 'comparison']
    analytical_count = sum(response.lower().count(word) for word in analytical_words)
    addresses_tradeoffs = any(keyword in response.lower() for keyword in ['trade-off', 'balance', 'weigh', 'versus', 'vs'])
    
    depth_score = min(10, (
        (5 if analytical_count >= 3 else 2) +
        (5 if addresses_tradeoffs else 3)
    ))
    
    # Clarity Analysis
    sentence_count = response.count('.') + response.count('!') + response.count('?')
    avg_sentence_length = word_count / max(sentence_count, 1)
    clear_language = avg_sentence_length < 25  # Not overly complex sentences
    
    clarity_score = (
        (5 if clear_language else 3) +
        (5 if sentence_count >= 8 else 3)  # Adequate sentence variety
    )
    
    return {
        'structure': min(10, structure_score),
        'completeness': completeness_score,
        'actionability': actionability_score, 
        'depth': depth_score,
        'clarity': min(10, clarity_score),
        'overall': None  # Will calculate as average
    }

def compare_responses(baseline_response: str, json_response: str, query: str) -> Dict:
    """Compare two responses and determine which is better"""
    
    baseline_scores = analyze_response_quality(baseline_response, query)
    json_scores = analyze_response_quality(json_response, query)
    
    # Calculate overall scores
    baseline_overall = sum(score for key, score in baseline_scores.items() if key != 'overall') / 5
    json_overall = sum(score for key, score in json_scores.items() if key != 'overall') / 5
    
    baseline_scores['overall'] = baseline_overall
    json_scores['overall'] = json_overall
    
    # Determine winner for each dimension
    comparison = {}
    for dimension in ['structure', 'completeness', 'actionability', 'depth', 'clarity', 'overall']:
        baseline_score = baseline_scores[dimension]
        json_score = json_scores[dimension]
        
        if json_score > baseline_score + 0.5:
            comparison[dimension] = 'JSON_BETTER'
        elif baseline_score > json_score + 0.5:
            comparison[dimension] = 'BASELINE_BETTER'
        else:
            comparison[dimension] = 'TIE'
    
    return {
        'baseline_scores': baseline_scores,
        'json_scores': json_scores,
        'comparison': comparison,
        'winner': 'JSON' if json_overall > baseline_overall else 'BASELINE' if baseline_overall > json_overall else 'TIE',
        'score_difference': json_overall - baseline_overall
    }

def main():
    print("🔍 DETAILED QUALITY COMPARISON: Baseline vs JSON Prompting")
    print("=" * 80)
    
    # Load results
    baseline_results = load_results('baseline_results.json')
    json_results = load_results('json_prompting_results.json')
    
    if len(baseline_results) != len(json_results):
        print(f"⚠️ Warning: Different number of results ({len(baseline_results)} vs {len(json_results)})")
        return
    
    # Track overall statistics
    json_wins = 0
    baseline_wins = 0
    ties = 0
    dimension_wins = {
        'structure': {'JSON': 0, 'BASELINE': 0, 'TIE': 0},
        'completeness': {'JSON': 0, 'BASELINE': 0, 'TIE': 0},
        'actionability': {'JSON': 0, 'BASELINE': 0, 'TIE': 0},
        'depth': {'JSON': 0, 'BASELINE': 0, 'TIE': 0},
        'clarity': {'JSON': 0, 'BASELINE': 0, 'TIE': 0}
    }
    
    detailed_comparisons = []
    
    for i, (baseline, json_result) in enumerate(zip(baseline_results, json_results), 1):
        query = baseline['query']
        print(f"\n📋 QUERY {i}: {query[:80]}...")
        print("-" * 80)
        
        comparison = compare_responses(baseline['response'], json_result['response'], query)
        detailed_comparisons.append({
            'query_num': i,
            'query': query,
            'comparison': comparison
        })
        
        # Display scores
        baseline_scores = comparison['baseline_scores']
        json_scores = comparison['json_scores']
        
        print(f"📊 QUALITY SCORES (1-10 scale):")
        print(f"  Structure:     Baseline {baseline_scores['structure']:.1f} | JSON {json_scores['structure']:.1f} | Winner: {comparison['comparison']['structure']}")
        print(f"  Completeness:  Baseline {baseline_scores['completeness']:.1f} | JSON {json_scores['completeness']:.1f} | Winner: {comparison['comparison']['completeness']}")
        print(f"  Actionability: Baseline {baseline_scores['actionability']:.1f} | JSON {json_scores['actionability']:.1f} | Winner: {comparison['comparison']['actionability']}")
        print(f"  Depth:         Baseline {baseline_scores['depth']:.1f} | JSON {json_scores['depth']:.1f} | Winner: {comparison['comparison']['depth']}")
        print(f"  Clarity:       Baseline {baseline_scores['clarity']:.1f} | JSON {json_scores['clarity']:.1f} | Winner: {comparison['comparison']['clarity']}")
        print(f"  OVERALL:       Baseline {baseline_scores['overall']:.1f} | JSON {json_scores['overall']:.1f} | Winner: {comparison['winner']}")
        
        # Update statistics
        if comparison['winner'] == 'JSON':
            json_wins += 1
        elif comparison['winner'] == 'BASELINE':
            baseline_wins += 1
        else:
            ties += 1
            
        # Update dimension statistics
        for dim in dimension_wins:
            result = comparison['comparison'][dim]
            if result == 'JSON_BETTER':
                dimension_wins[dim]['JSON'] += 1
            elif result == 'BASELINE_BETTER':
                dimension_wins[dim]['BASELINE'] += 1
            else:
                dimension_wins[dim]['TIE'] += 1
    
    # Final Analysis
    print(f"\n" + "=" * 80)
    print(f"🏆 FINAL QUALITY ANALYSIS")
    print(f"=" * 80)
    
    total_questions = len(baseline_results)
    
    print(f"📊 OVERALL WINNERS:")
    print(f"  JSON Prompting:  {json_wins}/{total_questions} ({json_wins/total_questions*100:.1f}%)")
    print(f"  Baseline:        {baseline_wins}/{total_questions} ({baseline_wins/total_questions*100:.1f}%)")
    print(f"  Ties:            {ties}/{total_questions} ({ties/total_questions*100:.1f}%)")
    
    print(f"\n📊 DIMENSION-BY-DIMENSION ANALYSIS:")
    for dimension, wins in dimension_wins.items():
        json_pct = wins['JSON'] / total_questions * 100
        baseline_pct = wins['BASELINE'] / total_questions * 100
        tie_pct = wins['TIE'] / total_questions * 100
        
        print(f"  {dimension.capitalize():12} - JSON: {wins['JSON']:2d} ({json_pct:4.1f}%) | Baseline: {wins['BASELINE']:2d} ({baseline_pct:4.1f}%) | Tie: {wins['TIE']:2d} ({tie_pct:4.1f}%)")
    
    # Determine recommendation
    print(f"\n🎯 RECOMMENDATION FOR LIFE/BUSINESS AI SYSTEM:")
    if json_wins > baseline_wins * 1.5:
        print(f"✅ STRONG RECOMMENDATION: Use JSON Prompting")
        print(f"   - Significantly better quality ({json_wins} vs {baseline_wins} wins)")
        print(f"   - Worth the 2.4s additional processing time")
    elif json_wins > baseline_wins:
        print(f"✅ MILD RECOMMENDATION: Use JSON Prompting")
        print(f"   - Moderately better quality ({json_wins} vs {baseline_wins} wins)")
        print(f"   - Consider if 2.4s delay is acceptable for users")
    elif baseline_wins > json_wins:
        print(f"❌ RECOMMENDATION: Keep Baseline Approach")
        print(f"   - Better quality with faster responses")
        print(f"   - JSON prompting doesn't justify 2.4s overhead")
    else:
        print(f"⚖️ NEUTRAL: Quality is similar")
        print(f"   - Choose based on speed preference (baseline faster)")
    
    # Save detailed results
    with open('detailed_quality_comparison.json', 'w') as f:
        json.dump({
            'summary': {
                'json_wins': json_wins,
                'baseline_wins': baseline_wins,
                'ties': ties,
                'dimension_analysis': dimension_wins
            },
            'detailed_comparisons': detailed_comparisons
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to 'detailed_quality_comparison.json'")

if __name__ == "__main__":
    main()
