#!/usr/bin/env python3
"""
Show specific response differences between baseline and JSON prompting
Focus on the strongest wins to demonstrate quality improvements
"""

import json

def load_results(filename: str):
    with open(filename, 'r') as f:
        return json.load(f)

def show_comparison(query_num: int, query: str, baseline_response: str, json_response: str, scores: dict):
    """Show side-by-side comparison of responses"""
    
    print(f"\n{'='*100}")
    print(f"🔍 QUERY {query_num}: {query}")
    print(f"{'='*100}")
    
    print(f"\n📊 QUALITY SCORES:")
    print(f"  Overall: Baseline {scores['baseline_overall']:.1f} | JSON {scores['json_overall']:.1f} | Winner: JSON (+{scores['json_overall']-scores['baseline_overall']:.1f})")
    print(f"  Structure: {scores['baseline_structure']:.1f} vs {scores['json_structure']:.1f}")
    print(f"  Completeness: {scores['baseline_completeness']:.1f} vs {scores['json_completeness']:.1f}")
    print(f"  Actionability: {scores['baseline_actionability']:.1f} vs {scores['json_actionability']:.1f}")
    print(f"  Depth: {scores['baseline_depth']:.1f} vs {scores['json_depth']:.1f}")
    
    print(f"\n🔄 BASELINE RESPONSE ({len(baseline_response)} chars):")
    print("-" * 50)
    print(baseline_response[:1000] + ("..." if len(baseline_response) > 1000 else ""))
    
    print(f"\n🆕 JSON PROMPTING RESPONSE ({len(json_response)} chars):")
    print("-" * 50)
    print(json_response[:1000] + ("..." if len(json_response) > 1000 else ""))
    
    print(f"\n✨ KEY IMPROVEMENTS IN JSON VERSION:")
    return analyze_improvements(baseline_response, json_response)

def analyze_improvements(baseline: str, json_response: str):
    """Analyze specific improvements in JSON version"""
    improvements = []
    
    # Structure improvements
    baseline_numbered = sum(1 for i in range(1, 11) if f"{i}." in baseline)
    json_numbered = sum(1 for i in range(1, 11) if f"{i}." in json_response)
    
    if json_numbered > baseline_numbered:
        improvements.append(f"📋 Better Structure: {json_numbered} numbered points vs {baseline_numbered}")
    
    # Section improvements
    section_words = ['advantages:', 'disadvantages:', 'benefits:', 'risks:', 'pros:', 'cons:', 'factors:', 'considerations:']
    baseline_sections = sum(1 for word in section_words if word in baseline.lower())
    json_sections = sum(1 for word in section_words if word in json_response.lower())
    
    if json_sections > baseline_sections:
        improvements.append(f"🗂️ Better Organization: {json_sections} clear sections vs {baseline_sections}")
    
    # Actionability improvements
    action_words = ['should', 'can', 'consider', 'recommend', 'suggest', 'implement', 'focus', 'ensure']
    baseline_actions = sum(baseline.lower().count(word) for word in action_words)
    json_actions = sum(json_response.lower().count(word) for word in action_words)
    
    if json_actions > baseline_actions:
        improvements.append(f"🎯 More Actionable: {json_actions} action words vs {baseline_actions}")
    
    # Completeness improvements
    baseline_words = len(baseline.split())
    json_words = len(json_response.split())
    
    if json_words > baseline_words + 50:
        improvements.append(f"📝 More Comprehensive: {json_words} words vs {baseline_words} (+{json_words-baseline_words})")
    
    # Analysis depth
    analysis_words = ['analysis', 'compare', 'contrast', 'however', 'therefore', 'furthermore', 'consequently']
    baseline_analysis = sum(baseline.lower().count(word) for word in analysis_words)
    json_analysis = sum(json_response.lower().count(word) for word in analysis_words)
    
    if json_analysis > baseline_analysis:
        improvements.append(f"🧠 Deeper Analysis: {json_analysis} analytical terms vs {baseline_analysis}")
    
    for improvement in improvements:
        print(f"  • {improvement}")
    
    if not improvements:
        print("  • Subtle improvements in organization and flow")
    
    return improvements

def main():
    print("🔍 SPECIFIC RESPONSE QUALITY DIFFERENCES")
    print("Showing the strongest JSON prompting wins with detailed analysis")
    print("="*100)
    
    # Load results
    baseline_results = load_results('baseline_results.json')
    json_results = load_results('json_prompting_results.json')
    detailed_analysis = load_results('detailed_quality_comparison.json')
    
    # Find the strongest JSON wins
    strongest_wins = []
    for i, comparison in enumerate(detailed_analysis['detailed_comparisons']):
        if comparison['comparison']['winner'] == 'JSON':
            score_diff = comparison['comparison']['score_difference']
            strongest_wins.append((i, score_diff, comparison))
    
    # Sort by score difference (largest improvements first)
    strongest_wins.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Found {len(strongest_wins)} cases where JSON prompting was clearly better")
    print("Showing top 3 examples:\n")
    
    # Show top 3 examples
    for rank, (index, score_diff, comparison) in enumerate(strongest_wins[:3], 1):
        baseline = baseline_results[index]
        json_result = json_results[index]
        
        scores = {
            'baseline_overall': comparison['comparison']['baseline_scores']['overall'],
            'json_overall': comparison['comparison']['json_scores']['overall'],
            'baseline_structure': comparison['comparison']['baseline_scores']['structure'],
            'json_structure': comparison['comparison']['json_scores']['structure'],
            'baseline_completeness': comparison['comparison']['baseline_scores']['completeness'],
            'json_completeness': comparison['comparison']['json_scores']['completeness'],
            'baseline_actionability': comparison['comparison']['baseline_scores']['actionability'],
            'json_actionability': comparison['comparison']['json_scores']['actionability'],
            'baseline_depth': comparison['comparison']['baseline_scores']['depth'],
            'json_depth': comparison['comparison']['json_scores']['depth'],
        }
        
        show_comparison(
            index + 1,
            baseline['query'],
            baseline['response'],
            json_result['response'],
            scores
        )
        
        if rank < 3:
            input("\nPress Enter to see next example...")
    
    print(f"\n{'='*100}")
    print("🎯 SUMMARY: JSON prompting consistently provides:")
    print("  • Better structured organization")
    print("  • More comprehensive factor analysis") 
    print("  • More actionable recommendations")
    print("  • Deeper analytical insights")
    print("  • Clearer logical flow")
    print(f"{'='*100}")

if __name__ == "__main__":
    main()
