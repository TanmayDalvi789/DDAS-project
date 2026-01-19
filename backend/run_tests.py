"""
DDAS Backend Demo Test Runner

Run automated tests to verify backend is demo-ready.

Usage:
    pytest app/tests/test_demo.py -v                    # Run all tests
    pytest app/tests/test_demo.py -v -k health          # Run health tests only
    pytest app/tests/test_demo.py -v -m auth            # Run auth tests only
    pytest app/tests/test_demo.py -v --tb=short         # Run with short traceback
    pytest app/tests/test_demo.py --cov=app --cov-report=html  # With coverage

Test Categories:
    -m health       Health check tests
    -m auth         Authentication tests
    -m fingerprint  Fingerprint ingestion tests
    -m detection    Detection engine tests
    -m audit        Audit logging tests
    -m integration  Integration tests

Output:
    Test results with pass/fail status
    Coverage report (if --cov option used)
"""

import subprocess
import sys
from pathlib import Path


def run_tests(args=None):
    """Run pytest with provided arguments."""
    
    # Default to verbose output
    cmd = ["pytest", "app/tests/test_demo.py", "-v"]
    
    if args:
        cmd.extend(args)
    
    print(f"\n{'='*70}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(cmd)
    
    print(f"\n{'='*70}")
    if result.returncode == 0:
        print("✓ ALL TESTS PASSED - Backend is DEMO-READY")
    else:
        print("✗ Some tests failed - See output above")
    print(f"{'='*70}\n")
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests(sys.argv[1:])
    sys.exit(exit_code)
