#!/usr/bin/env python3
"""
Worldview Evaluation CLI

Run LLM evaluations against Worldview-encoded beliefs.

Usage:
    python -m evals.cli --help
    python -m evals.cli run --models claude-sonnet gpt-4o
    python -m evals.cli run --difficulty extreme
    python -m evals.cli list-models
    python -m evals.cli list-cases
"""

import argparse
import sys
from pathlib import Path


def cmd_run(args):
    """Run evaluations."""
    print("Starting evaluation run...", flush=True)
    from .config import ALL_MODELS, DEFAULT_MODELS, get_model, MODEL_REGISTRY
    from .runner import EvalRunner, generate_report, generate_json_results
    from .test_cases import ALL_TEST_CASES, Difficulty, get_cases_by_difficulty

    # Determine models to use
    if args.models:
        models = []
        for name in args.models:
            model = get_model(name)
            if model:
                models.append(model)
            else:
                print(f"Warning: Unknown model '{name}', skipping", flush=True)
        if not models:
            print("Error: No valid models specified", flush=True)
            sys.exit(1)
    elif args.all_models:
        models = ALL_MODELS
    else:
        models = DEFAULT_MODELS

    # Determine test cases
    if args.difficulty:
        try:
            difficulty = Difficulty(args.difficulty)
            test_cases = get_cases_by_difficulty(difficulty)
        except ValueError:
            print(f"Error: Unknown difficulty '{args.difficulty}'", flush=True)
            print(f"Valid options: {[d.value for d in Difficulty]}", flush=True)
            sys.exit(1)
    elif args.cases:
        from .test_cases import get_case_by_id
        test_cases = []
        for case_id in args.cases:
            tc = get_case_by_id(case_id)
            if tc:
                test_cases.append(tc)
            else:
                print(f"Warning: Unknown test case '{case_id}', skipping", flush=True)
        if not test_cases:
            print("Error: No valid test cases specified", flush=True)
            sys.exit(1)
    else:
        test_cases = ALL_TEST_CASES

    print(f"Running {len(test_cases)} test cases against {len(models)} models", flush=True)
    print(f"Models: {[m.display_name for m in models]}", flush=True)
    print(f"Worldview CLI: {args.worldview_cli}", flush=True)
    print(flush=True)

    # Create runner (always uses CLI)
    runner = EvalRunner(
        models=models,
        worldview_cli_path=args.worldview_cli,
        verbose=args.verbose,
    )

    # Run evaluations
    results = runner.run_all(test_cases=test_cases)

    # Generate outputs
    if args.output:
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate report
        report_path = output_path / "report.md"
        report = generate_report(results, str(report_path))
        print(f"\nReport written to: {report_path}")

        # Generate JSON
        json_path = output_path / "results.json"
        generate_json_results(results, str(json_path))
        print(f"JSON results written to: {json_path}")
    else:
        # Print report to stdout
        print("\n" + "=" * 60)
        report = generate_report(results)
        print(report)


def cmd_list_models(args):
    """List available models."""
    from .config import ALL_MODELS, DEFAULT_MODELS

    default_ids = {m.model_id for m in DEFAULT_MODELS}

    print("Available models:\n")
    print(f"{'Name':<20} {'Provider':<12} {'Model ID':<35} {'Default'}")
    print("-" * 80)

    for model in ALL_MODELS:
        default = "Yes" if model.model_id in default_ids else ""
        print(f"{model.display_name:<20} {model.provider.value:<12} {model.model_id:<35} {default}")


def cmd_list_cases(args):
    """List available test cases."""
    from .test_cases import ALL_TEST_CASES, Difficulty

    print("Available test cases:\n")

    for difficulty in Difficulty:
        cases = [tc for tc in ALL_TEST_CASES if tc.difficulty == difficulty]
        print(f"\n{difficulty.value.upper()} ({len(cases)} cases):")
        print("-" * 40)
        for tc in cases:
            print(f"  {tc.id:<30} {tc.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Worldview LLM Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run evaluations")
    run_parser.add_argument(
        "--models",
        nargs="+",
        help="Models to evaluate (e.g., claude-sonnet gpt-4o)",
    )
    run_parser.add_argument(
        "--all-models",
        action="store_true",
        help="Run against all available models",
    )
    run_parser.add_argument(
        "--difficulty",
        choices=["baseline", "moderate", "extreme"],
        help="Run only cases of specific difficulty",
    )
    run_parser.add_argument(
        "--cases",
        nargs="+",
        help="Specific test case IDs to run",
    )
    run_parser.add_argument(
        "--output", "-o",
        help="Output directory for report and results",
    )
    run_parser.add_argument(
        "--worldview-cli",
        default="worldview",
        help="Path to Worldview CLI tool (default: 'worldview' in PATH)",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    run_parser.set_defaults(func=cmd_run)

    # List models command
    models_parser = subparsers.add_parser("list-models", help="List available models")
    models_parser.set_defaults(func=cmd_list_models)

    # List cases command
    cases_parser = subparsers.add_parser("list-cases", help="List available test cases")
    cases_parser.set_defaults(func=cmd_list_cases)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
