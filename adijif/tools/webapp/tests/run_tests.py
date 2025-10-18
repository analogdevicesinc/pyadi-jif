#!/usr/bin/env python3
"""Test runner script for PyADI-JIF webapp tests."""

import argparse
import sys
import subprocess
from pathlib import Path


def run_tests(args):
    """Run pytest with specified options."""
    test_dir = Path(__file__).parent

    # Build pytest command
    cmd = ["pytest"]

    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Add test selection
    if args.quick:
        cmd.extend(["-m", "not slow"])
    elif args.slow:
        cmd.extend(["-m", "slow"])

    # Add specific test file or pattern
    if args.test:
        cmd.append(args.test)
    else:
        cmd.append(str(test_dir))

    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    # Add HTML report
    if args.html:
        report_path = test_dir / "test_report.html"
        cmd.extend(["--html", str(report_path), "--self-contained-html"])

    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=../backend", "--cov-report=html", "--cov-report=term"])

    # Add fail fast
    if args.failfast:
        cmd.append("-x")

    # Add markers filter
    if args.markers:
        cmd.extend(["-m", args.markers])

    # Add keyword filter
    if args.keyword:
        cmd.extend(["-k", args.keyword])

    # Run pytest
    print(f"\n{'='*70}")
    print("Running PyADI-JIF Webapp Tests")
    print(f"{'='*70}\n")
    print(f"Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=test_dir)

    if args.html:
        print(f"\n{'='*70}")
        print(f"HTML report generated: {report_path}")
        print(f"{'='*70}\n")

    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run PyADI-JIF webapp Selenium tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests.py

  # Run quick tests only (skip slow tests)
  python run_tests.py --quick

  # Run specific test file
  python run_tests.py --test test_comprehensive_jesd_selector.py

  # Run tests in parallel
  python run_tests.py --parallel 4

  # Generate HTML report
  python run_tests.py --html

  # Run tests matching a keyword
  python run_tests.py -k "dropdown"

  # Run tests with specific marker
  python run_tests.py -m "api"

  # Fail fast on first error
  python run_tests.py --failfast
        """,
    )

    parser.add_argument(
        "-t",
        "--test",
        help="Specific test file or pattern to run",
    )

    parser.add_argument(
        "-q",
        "--quick",
        action="store_true",
        help="Run only quick tests (skip slow tests)",
    )

    parser.add_argument(
        "-s",
        "--slow",
        action="store_true",
        help="Run only slow tests",
    )

    parser.add_argument(
        "-p",
        "--parallel",
        type=int,
        help="Run tests in parallel with N workers",
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML test report",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "-x",
        "--failfast",
        action="store_true",
        help="Stop on first failure",
    )

    parser.add_argument(
        "-m",
        "--markers",
        help="Run tests matching given mark expression (e.g., 'api and not slow')",
    )

    parser.add_argument(
        "-k",
        "--keyword",
        help="Run tests matching given keyword expression (e.g., 'dropdown or clock')",
    )

    args = parser.parse_args()

    # Check for conflicting options
    if args.quick and args.slow:
        parser.error("Cannot use --quick and --slow together")

    # Run tests
    exit_code = run_tests(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
