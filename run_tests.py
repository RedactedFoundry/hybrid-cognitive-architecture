#!/usr/bin/env python3
"""
Test Runner for Hybrid AI Council
=================================

Runs the comprehensive test suite for the modular architecture and security features.
"""

import subprocess
import sys
import time
from pathlib import Path

import structlog

# Set up logging for test runner
logger = structlog.get_logger("test_runner")


def run_test_suite():
    """Run the complete test suite."""
    logger.info("Starting Hybrid AI Council test suite")
    
    start_time = time.time()
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    # Test modules to run
    test_modules = [
        "tests/test_configuration.py",
        "tests/test_cognitive_nodes.py", 
        "tests/test_security_middleware.py",
        "tests/test_api_endpoints.py",
        "tests/test_prompt_cache.py"  # Existing test
    ]
    
    for test_module in test_modules:
        if not Path(test_module).exists():
            logger.warning(f"Test module not found: {test_module}")
            continue
            
        logger.info(f"Running tests: {test_module}")
        
        try:
            # Run pytest on the specific module
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_module, 
                "-v",
                "--tb=short"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"✅ {test_module}: PASSED")
                passed_tests += 1
            else:
                logger.error(f"❌ {test_module}: FAILED")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                failed_tests += 1
                
            total_tests += 1
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {test_module}: TIMEOUT")
            failed_tests += 1
            total_tests += 1
        except Exception as e:
            logger.error(f"💥 {test_module}: ERROR - {e}")
            failed_tests += 1
            total_tests += 1
    
    # Summary
    elapsed_time = time.time() - start_time
    
    logger.info("Test Suite Summary",
                total_tests=total_tests,
                passed=passed_tests,
                failed=failed_tests,
                elapsed_time=f"{elapsed_time:.2f}s")
    
    if failed_tests == 0:
        logger.info("🎉 All tests PASSED!")
        return True
    else:
        logger.error(f"💥 {failed_tests} test modules FAILED!")
        return False


def run_quick_tests():
    """Run a quick subset of tests for rapid feedback."""
    logger.info("Running quick test subset")
    
    quick_tests = [
        "tests/test_configuration.py::TestConfiguration::test_config_initialization",
        "tests/test_cognitive_nodes.py::TestSmartRouterNode::test_initialization",
        "tests/test_security_middleware.py::TestRateLimitingMiddleware::test_initialization"
    ]
    
    for test in quick_tests:
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test, 
                "-v"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"✅ {test}: PASSED")
            else:
                logger.error(f"❌ {test}: FAILED")
                return False
                
        except Exception as e:
            logger.error(f"💥 {test}: ERROR - {e}")
            return False
    
    logger.info("🚀 Quick tests PASSED!")
    return True


def check_dependencies():
    """Check if required testing dependencies are installed."""
    required_packages = ["pytest", "pytest-asyncio"]
    missing_packages = []
    
    for package in required_packages:
        try:
            subprocess.run([sys.executable, "-c", f"import {package}"], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error("Missing test dependencies", missing=missing_packages)
        logger.info("Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Hybrid AI Council tests")
    parser.add_argument("--quick", action="store_true", help="Run quick test subset")
    parser.add_argument("--check-deps", action="store_true", help="Check test dependencies")
    
    args = parser.parse_args()
    
    if args.check_deps:
        if check_dependencies():
            logger.info("✅ All test dependencies are installed")
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Check dependencies before running tests
    if not check_dependencies():
        logger.error("❌ Missing test dependencies. Run with --check-deps for details.")
        sys.exit(1)
    
    if args.quick:
        success = run_quick_tests()
    else:
        success = run_test_suite()
    
    sys.exit(0 if success else 1)