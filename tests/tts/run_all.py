#!/usr/bin/env python3
"""
Test runner for TTS Platform Core.
Ensures site-packages and project root are in sys.path, then executes all test suites.
"""

import sys
from pathlib import Path

# Add project root and global venv site-packages
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SITE_PACKAGES = Path(r"C:\Users\Suraj\.venv\Lib\site-packages")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if SITE_PACKAGES.exists() and str(SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(SITE_PACKAGES))

import unittest

# Import test functions and modules
from tests.tts import test_tts_contracts, test_numeral_expander, test_universal_input_guard


def run_tests():
    print("=" * 60)
    print("TTS PLATFORM CORE - PHASE 1 TEST SUITE")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    modules = [
        ("Contracts & Immutability", test_tts_contracts),
        ("Numeral & Token Expander", test_numeral_expander),
        ("Universal Input Guard", test_universal_input_guard),
    ]

    for name, mod in modules:
        print(f"\n[*] Running Suite: {name}")
        for attr in dir(mod):
            if attr.startswith("test_"):
                func = getattr(mod, attr)
                if callable(func):
                    try:
                        func()
                        print(f"  [PASS] {attr}")
                        total_passed += 1
                    except Exception as e:
                        print(f"  [FAIL] {attr}: {e}")
                        total_failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {total_passed} Passed, {total_failed} Failed")
    print("=" * 60)
    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
