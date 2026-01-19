#!/usr/bin/env python3
"""
Worldview Evaluation CLI

Run LLM evaluations against Worldview-encoded beliefs.

Usage:
    python -m evals.cli --help
    python -m evals.cli run --models claude-sonnet gpt-4o
    python -m evals.cli run --difficulty extreme
    python -m evals.cli write-eval --models claude-sonnet claude-haiku
    python -m evals.cli write-eval --complexity simple
    python -m evals.cli list-models
    python -m evals.cli list-cases
"""

import argparse
import sys
from pathlib import Path


def cmd_run(args):
    """Run evaluations."""
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
                print(f"Warning: Unknown model '{name}', skipping")
        if not models:
            print("Error: No valid models specified")
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
            print(f"Error: Unknown difficulty '{args.difficulty}'")
            print(f"Valid options: {[d.value for d in Difficulty]}")
            sys.exit(1)
    elif args.cases:
        from .test_cases import get_case_by_id
        test_cases = []
        for case_id in args.cases:
            tc = get_case_by_id(case_id)
            if tc:
                test_cases.append(tc)
            else:
                print(f"Warning: Unknown test case '{case_id}', skipping")
        if not test_cases:
            print("Error: No valid test cases specified")
            sys.exit(1)
    else:
        test_cases = ALL_TEST_CASES

    print(f"Running {len(test_cases)} test cases against {len(models)} models")
    print(f"Models: {[m.display_name for m in models]}")
    print()

    # Create runner
    runner = EvalRunner(
        models=models,
        use_cli_tool=args.use_cli,
        worldview_cli_path=args.worldview_cli,
        verbose=args.verbose,
    )

    # Run evaluations
    results = runner.run_all(test_cases=test_cases)

    # Generate outputs
    if args.output:
        output_path = Path(args.output)

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


def cmd_write_eval(args):
    """Run write evaluations (embedding model benchmark)."""
    from .write_eval.runner import (
        WriteEvalRunner,
        WRITE_MODELS,
        DEFAULT_WRITE_MODELS,
        get_write_model,
        generate_write_report,
        generate_write_json,
    )
    from .write_eval.test_cases import (
        ALL_WRITE_CASES,
        Complexity,
        get_cases_by_complexity,
        get_case_by_id,
    )

    # Determine models to use
    if args.models:
        model_names = args.models
    elif args.all_models:
        model_names = [m["name"] for m in WRITE_MODELS]
    else:
        model_names = DEFAULT_WRITE_MODELS

    # Validate models
    valid_models = []
    for name in model_names:
        if get_write_model(name):
            valid_models.append(name)
        else:
            print(f"Warning: Unknown model '{name}', skipping")

    if not valid_models:
        print("Error: No valid models specified")
        print(f"Available models: {[m['name'] for m in WRITE_MODELS]}")
        sys.exit(1)

    # Determine test cases
    if args.complexity:
        try:
            complexity = Complexity(args.complexity)
            test_cases = get_cases_by_complexity(complexity)
        except ValueError:
            print(f"Error: Unknown complexity '{args.complexity}'")
            print(f"Valid options: {[c.value for c in Complexity]}")
            sys.exit(1)
    elif args.cases:
        test_cases = []
        for case_id in args.cases:
            tc = get_case_by_id(case_id)
            if tc:
                test_cases.append(tc)
            else:
                print(f"Warning: Unknown test case '{case_id}', skipping")
        if not test_cases:
            print("Error: No valid test cases specified")
            sys.exit(1)
    else:
        test_cases = ALL_WRITE_CASES

    print(f"Running {len(test_cases)} write test cases against {len(valid_models)} models")
    print(f"Models: {valid_models}")
    print()

    # Create runner
    runner = WriteEvalRunner(
        models=valid_models,
        agent_cli_path=args.agent_cli,
        validator_path=args.validator,
        verbose=args.verbose,
    )

    # Run evaluations
    results = runner.run_all(test_cases=test_cases)

    # Generate outputs
    if args.output:
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate report
        report_path = output_path / "write_report.md"
        report = generate_write_report(results, str(report_path))
        print(f"\nReport written to: {report_path}")

        # Generate JSON
        json_path = output_path / "write_results.json"
        generate_write_json(results, str(json_path))
        print(f"JSON results written to: {json_path}")
    else:
        # Print report to stdout
        print("\n" + "=" * 60)
        report = generate_write_report(results)
        print(report)


def cmd_list_models(args):
    """List available models."""
    from .config import ALL_MODELS, DEFAULT_MODELS
    from .write_eval.runner import WRITE_MODELS, DEFAULT_WRITE_MODELS

    default_ids = {m.model_id for m in DEFAULT_MODELS}

    print("Read Evaluation Models (for testing LLM response to Worldview context):\n")
    print(f"{'Name':<20} {'Provider':<12} {'Model ID':<35} {'Default'}")
    print("-" * 80)

    for model in ALL_MODELS:
        default = "Yes" if model.model_id in default_ids else ""
        print(f"{model.display_name:<20} {model.provider.value:<12} {model.model_id:<35} {default}")

    print("\n")
    print("Write Evaluation Models (for testing Worldview document generation):\n")
    print(f"{'Name':<20} {'Model ID':<40} {'Default'}")
    print("-" * 70)

    for model in WRITE_MODELS:
        default = "Yes" if model["name"] in DEFAULT_WRITE_MODELS else ""
        print(f"{model['display_name']:<20} {model['model_id']:<40} {default}")


def cmd_list_cases(args):
    """List available test cases."""
    from .test_cases import ALL_TEST_CASES, Difficulty
    from .write_eval.test_cases import ALL_WRITE_CASES, Complexity

    print("Read Evaluation Test Cases (testing LLM response to Worldview context):\n")

    for difficulty in Difficulty:
        cases = [tc for tc in ALL_TEST_CASES if tc.difficulty == difficulty]
        print(f"\n{difficulty.value.upper()} ({len(cases)} cases):")
        print("-" * 40)
        for tc in cases:
            print(f"  {tc.id:<30} {tc.name}")

    print("\n")
    print("=" * 60)
    print("\nWrite Evaluation Test Cases (testing document generation):\n")

    for complexity in Complexity:
        cases = [tc for tc in ALL_WRITE_CASES if tc.complexity == complexity]
        print(f"\n{complexity.value.upper()} ({len(cases)} cases):")
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
        "--use-cli",
        action="store_true",
        help="Use Worldview CLI tool to generate content (slower, full integration)",
    )
    run_parser.add_argument(
        "--worldview-cli",
        default="worldview",
        help="Path to Worldview CLI tool",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output",
    )
    run_parser.set_defaults(func=cmd_run)

    # Write evaluation command
    write_parser = subparsers.add_parser(
        "write-eval",
        help="Run write evaluations (benchmark embedding models on document generation)"
    )
    write_parser.add_argument(
        "--models",
        nargs="+",
        help="Models to evaluate (e.g., claude-sonnet claude-haiku)",
    )
    write_parser.add_argument(
        "--all-models",
        action="store_true",
        help="Run against all available write models",
    )
    write_parser.add_argument(
        "--complexity",
        choices=["simple", "moderate", "complex"],
        help="Run only cases of specific complexity",
    )
    write_parser.add_argument(
        "--cases",
        nargs="+",
        help="Specific test case IDs to run",
    )
    write_parser.add_argument(
        "--output", "-o",
        help="Output directory for report and results",
    )
    write_parser.add_argument(
        "--agent-cli",
        default="worldview",
        help="Path to Worldview agent CLI tool",
    )
    write_parser.add_argument(
        "--validator",
        help="Path to Worldview validator binary (optional)",
    )
    write_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output including agent interactions",
    )
    write_parser.set_defaults(func=cmd_write_eval)

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
