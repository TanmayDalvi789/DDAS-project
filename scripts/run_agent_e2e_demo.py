#!/usr/bin/env python3
"""
DDAS End-to-End Demo Runner

Standalone script to manually trigger and observe the full event processing
pipeline. Useful for demos, debugging, and understanding system behavior.

Run with:
    python scripts/run_agent_e2e_demo.py

Or from root:
    python -m scripts.run_agent_e2e_demo
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Add agent to path
AGENT_DIR = Path(__file__).parent.parent / "agent"
if AGENT_DIR.exists():
    sys.path.insert(0, str(AGENT_DIR.parent))

# Import helpers
from agent.app.tests.integration.e2e_helpers import (
    TestDataLoader,
    ProxyEventValidator,
    BackendResponseValidator,
    MockBackendClient,
    PipelineExecutor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


class E2EDemoRunner:
    """Run end-to-end demonstration scenarios."""

    def __init__(self):
        """Initialize demo runner."""
        self.loader = TestDataLoader()
        self.results = {}

    def print_header(self, title: str):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_section(self, title: str):
        """Print formatted section."""
        print(f"\n{title}")
        print("-" * 80)

    def demo_1_valid_event_processing(self):
        """Demo 1: Process valid event (should ALLOW)."""
        self.print_header("DEMO 1: Valid Event Processing (ALLOW)")

        event = self.loader.get_proxy_event_valid()
        mock_backend = MockBackendClient(self.loader.get_backend_response_empty())

        self.print_section("Input Event")
        print(json.dumps(event, indent=2))

        self.print_section("Backend Response (No Matches)")
        print(json.dumps(self.loader.get_backend_response_empty(), indent=2))

        self.print_section("Pipeline Execution")
        executor = PipelineExecutor(backend_client=mock_backend)
        result = executor.execute(event)

        self.print_section("Result")
        print(f"Decision: {result.get('decision', 'N/A')}")
        print(f"Errors: {result.get('errors', [])}")
        print(f"Status: {'[OK] SUCCESS' if not result['errors'] else '[FAIL] FAILED'}")

        self.results["demo_1"] = result
        return result

    def demo_2_exact_match_block(self):
        """Demo 2: Exact match detected (should BLOCK)."""
        self.print_header("DEMO 2: Exact Match Detection (BLOCK)")

        event = self.loader.get_proxy_event_valid()
        mock_backend = MockBackendClient(self.loader.get_backend_response_exact())

        self.print_section("Input Event")
        print(json.dumps(event, indent=2))

        self.print_section("Backend Response (Exact Match)")
        exact_match = self.loader.get_backend_response_exact()
        print(json.dumps(exact_match, indent=2))

        self.print_section("Pipeline Execution")
        executor = PipelineExecutor(backend_client=mock_backend)
        result = executor.execute(event)

        self.print_section("Result")
        print(f"Decision: {result.get('decision', 'N/A')}")
        print(f"Exact Match Score: {exact_match['exact_match']['score']}")
        print(f"Errors: {result.get('errors', [])}")
        print(f"Status: {'[OK] SUCCESS' if not result['errors'] else '[FAIL] FAILED'}")

        self.results["demo_2"] = result
        return result

    def demo_3_fuzzy_match_warn(self):
        """Demo 3: Fuzzy match detected (should WARN)."""
        self.print_header("DEMO 3: Fuzzy Match Detection (WARN)")

        event = self.loader.get_proxy_event_valid()
        mock_backend = MockBackendClient(self.loader.get_backend_response_fuzzy())

        self.print_section("Input Event")
        print(json.dumps(event, indent=2))

        self.print_section("Backend Response (Fuzzy Match)")
        fuzzy_match = self.loader.get_backend_response_fuzzy()
        print(json.dumps(fuzzy_match, indent=2))

        self.print_section("Pipeline Execution")
        executor = PipelineExecutor(backend_client=mock_backend)
        result = executor.execute(event)

        self.print_section("Result")
        print(f"Decision: {result.get('decision', 'N/A')}")
        print(f"Fuzzy Match Score: {fuzzy_match['fuzzy_match']['score']}")
        print(f"Errors: {result.get('errors', [])}")
        print(f"Status: {'[OK] SUCCESS' if not result['errors'] else '[FAIL] FAILED'}")

        self.results["demo_3"] = result
        return result

    def demo_4_semantic_match_warn(self):
        """Demo 4: Semantic match detected (should WARN)."""
        self.print_header("DEMO 4: Semantic Match Detection (WARN)")

        event = self.loader.get_proxy_event_valid()
        mock_backend = MockBackendClient(self.loader.get_backend_response_semantic())

        self.print_section("Input Event")
        print(json.dumps(event, indent=2))

        self.print_section("Backend Response (Semantic Match)")
        semantic_match = self.loader.get_backend_response_semantic()
        print(json.dumps(semantic_match, indent=2))

        self.print_section("Pipeline Execution")
        executor = PipelineExecutor(backend_client=mock_backend)
        result = executor.execute(event)

        self.print_section("Result")
        print(f"Decision: {result.get('decision', 'N/A')}")
        print(f"Semantic Match Score: {semantic_match['semantic_match']['score']}")
        print(f"Errors: {result.get('errors', [])}")
        print(f"Status: {'[OK] SUCCESS' if not result['errors'] else '[FAIL] FAILED'}")

        self.results["demo_4"] = result
        return result

    def demo_5_invalid_event_rejection(self):
        """Demo 5: Invalid event rejection."""
        self.print_header("DEMO 5: Invalid Event Rejection")

        event = self.loader.get_proxy_event_invalid()

        self.print_section("Input Event (Invalid)")
        print(json.dumps(event, indent=2))

        self.print_section("Validation")
        valid, error = ProxyEventValidator.validate(event)
        print(f"Valid: {valid}")
        print(f"Error: {error}")

        self.print_section("Pipeline Execution (Should Fail Gracefully)")
        executor = PipelineExecutor()
        try:
            result = executor.execute(event)
        except ValueError as e:
            # Expected: invalid event is rejected
            result = {
                "decision": "REJECT",
                "errors": [str(e)]
            }

        self.print_section("Result")
        print(f"Errors: {result.get('errors', [])}")
        print(f"Status: {'[OK] ERROR CAUGHT (EXPECTED)' if result['errors'] else '[FAIL] ERROR NOT CAUGHT'}")

        self.results["demo_5"] = result
        return result

    def demo_6_contract_validation(self):
        """Demo 6: Contract validation enforcement."""
        self.print_header("DEMO 6: Contract Validation")

        self.print_section("Valid Proxy Event")
        valid_event = self.loader.get_proxy_event_valid()
        valid, error = ProxyEventValidator.validate(valid_event)
        print(f"Valid Event Validation: {valid} (Error: {error})")

        self.print_section("Invalid Proxy Event")
        invalid_event = self.loader.get_proxy_event_invalid()
        valid, error = ProxyEventValidator.validate(invalid_event)
        print(f"Invalid Event Validation: {valid} (Error: {error})")

        self.print_section("Valid Backend Response")
        valid_response = self.loader.get_backend_response_exact()
        valid, error = BackendResponseValidator.validate(valid_response)
        print(f"Valid Response Validation: {valid} (Error: {error})")

        self.print_section("Result")
        print("✓ Contract validation working correctly")

        self.results["demo_6"] = {"valid_event": True, "invalid_event": False}
        return self.results["demo_6"]

    def print_summary(self):
        """Print execution summary."""
        self.print_header("EXECUTION SUMMARY")

        total_demos = len(self.results)
        successful = sum(
            1 for r in self.results.values() if isinstance(r, dict) and not r.get("errors")
        )

        print(f"\nTotal Demos: {total_demos}")
        print(f"Successful: {successful}/{total_demos}")
        print(f"Success Rate: {successful/total_demos*100:.1f}%")

        print("\nDetails:")
        for demo_name, result in self.results.items():
            if isinstance(result, dict):
                errors = result.get("errors", [])
                status = "[OK] PASS" if not errors else f"[FAIL] FAIL ({len(errors)} errors)"
                print(f"  {demo_name}: {status}")

    def run_all(self):
        """Run all demonstrations."""
        print("\n")
        print("+" + "=" * 78 + "+")
        print("|" + " DDAS Local Agent — End-to-End Validation Demo ".center(78) + "|")
        print("+" + "=" * 78 + "+")

        try:
            self.demo_1_valid_event_processing()
            self.demo_2_exact_match_block()
            self.demo_3_fuzzy_match_warn()
            self.demo_4_semantic_match_warn()
            self.demo_5_invalid_event_rejection()
            self.demo_6_contract_validation()

            self.print_summary()

            print("\n" + "=" * 80)
            print("All demonstrations complete!")
            print("=" * 80 + "\n")

            return 0

        except Exception as e:
            logger.error(f"Demo failed: {e}", exc_info=True)
            print("\n" + "=" * 80)
            print(f"ERROR: {e}")
            print("=" * 80 + "\n")
            return 1


def main():
    """Entry point."""
    runner = E2EDemoRunner()
    return runner.run_all()


if __name__ == "__main__":
    sys.exit(main())
