#!/usr/bin/env python3
"""
File Size Monitor - Enforces 500-line limit per .cursorrules

This script checks all Python files and reports any that exceed the 500-line limit.
Can be run locally or in CI/CD pipelines.

Usage:
    python scripts/check-file-sizes.py              # Check all files
    python scripts/check-file-sizes.py --fix        # Interactive splitting suggestions
    python scripts/check-file-sizes.py --strict     # Exit with error on violations
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

# File exclusions per .cursorrules
EXCLUDED_DIRS = {
    '.git', 'venv', '.venv', 'env', '.env', 
    '__pycache__', '.pytest_cache', 'node_modules'
}

MAX_LINES = 500
WARNING_THRESHOLD = 400


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())
    except (UnicodeDecodeError, IOError):
        return 0


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files, excluding specified directories."""
    python_files = []
    
    for file_path in root_dir.rglob("*.py"):
        # Skip if in excluded directory
        if any(excluded in file_path.parts for excluded in EXCLUDED_DIRS):
            continue
        python_files.append(file_path)
    
    return python_files


def analyze_file_sizes(root_dir: Path) -> Tuple[List[Tuple[Path, int]], List[Tuple[Path, int]], int]:
    """Analyze all Python files and categorize by size."""
    python_files = find_python_files(root_dir)
    
    oversized = []
    warnings = []
    total_files = len(python_files)
    
    for file_path in python_files:
        line_count = count_lines(file_path)
        
        if line_count > MAX_LINES:
            oversized.append((file_path, line_count))
        elif line_count > WARNING_THRESHOLD:
            warnings.append((file_path, line_count))
    
    return oversized, warnings, total_files


def suggest_split_points(file_path: Path) -> List[str]:
    """Suggest logical split points for oversized files."""
    suggestions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Look for class and function definitions
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('class ') and ':' in stripped:
                class_name = stripped.split()[1].split('(')[0].split(':')[0]
                suggestions.append(f"Line {i}: Extract class '{class_name}' to separate module")
            elif stripped.startswith('def ') and not stripped.startswith('def __'):
                func_name = stripped.split()[1].split('(')[0]
                suggestions.append(f"Line {i}: Extract function '{func_name}' to utilities module")
        
        # Generic suggestions based on file type
        filename = file_path.name
        if 'orchestrator' in filename:
            suggestions.append("Consider splitting into: state_machine.py, nodes.py, streaming.py")
        elif 'handler' in filename:
            suggestions.append("Consider splitting by feature: chat_handlers.py, voice_handlers.py")
        elif 'client' in filename:
            suggestions.append("Consider splitting: connection.py, operations.py, models.py")
    
    except (IOError, UnicodeDecodeError):
        pass
    
    return suggestions[:3]  # Limit to top 3 suggestions


def print_results(oversized: List[Tuple[Path, int]], warnings: List[Tuple[Path, int]], 
                 total_files: int, show_suggestions: bool = False):
    """Print analysis results with color coding."""
    print(f"\n📊 File Size Analysis ({total_files} Python files checked)")
    print("=" * 60)
    
    if oversized:
        print(f"\n❌ VIOLATIONS ({len(oversized)} files exceed {MAX_LINES} lines):")
        for file_path, line_count in sorted(oversized, key=lambda x: x[1], reverse=True):
            relative_path = file_path.relative_to(Path.cwd())
            print(f"   {relative_path}: {line_count} lines (+{line_count - MAX_LINES} over limit)")
            
            if show_suggestions:
                suggestions = suggest_split_points(file_path)
                if suggestions:
                    print("     💡 Split suggestions:")
                    for suggestion in suggestions:
                        print(f"        • {suggestion}")
                print()
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)} files approaching limit):")
        for file_path, line_count in sorted(warnings, key=lambda x: x[1], reverse=True):
            relative_path = file_path.relative_to(Path.cwd())
            print(f"   {relative_path}: {line_count} lines ({MAX_LINES - line_count} from limit)")
    
    if not oversized and not warnings:
        print("\n✅ All files are within size limits!")
        print(f"   • Maximum file size: {MAX_LINES} lines")
        print(f"   • Warning threshold: {WARNING_THRESHOLD} lines")
    
    # Summary statistics
    if oversized or warnings:
        print(f"\n📈 Summary:")
        print(f"   • Total files: {total_files}")
        print(f"   • Violations: {len(oversized)}")
        print(f"   • Warnings: {len(warnings)}")
        print(f"   • Compliant: {total_files - len(oversized) - len(warnings)}")


def main():
    parser = argparse.ArgumentParser(description="Monitor Python file sizes per .cursorrules")
    parser.add_argument('--fix', action='store_true', 
                       help='Show splitting suggestions for oversized files')
    parser.add_argument('--strict', action='store_true',
                       help='Exit with error code if violations found (for CI/CD)')
    parser.add_argument('--root', type=Path, default=Path.cwd(),
                       help='Root directory to scan (default: current directory)')
    
    args = parser.parse_args()
    
    if not args.root.exists():
        print(f"❌ Error: Directory {args.root} does not exist")
        sys.exit(1)
    
    print(f"🔍 Scanning Python files in: {args.root}")
    print(f"📏 Enforcing {MAX_LINES}-line limit per .cursorrules")
    
    oversized, warnings, total_files = analyze_file_sizes(args.root)
    
    print_results(oversized, warnings, total_files, show_suggestions=args.fix)
    
    if oversized:
        print(f"\n💡 To fix violations:")
        print(f"   python scripts/check-file-sizes.py --fix")
        print(f"   # Then split files using single-responsibility principle")
        
        if args.strict:
            sys.exit(1)
    
    print(f"\n🎯 Keep files focused and maintainable!")


if __name__ == "__main__":
    main()