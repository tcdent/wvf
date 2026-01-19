"""
Worldview Evaluation Runner

Orchestrates running test cases against multiple LLMs and collecting results.
Always uses the Worldview CLI tool to generate content from fact statements.
"""

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import ModelConfig, ALL_MODELS, DEFAULT_MODELS, get_model
from .evaluator import EvalResult, EvalScore, EvalSummary, evaluate_response, summarize_results
from .llm_clients import LLMClient, LLMResponse, create_client
from .test_cases import (
    ALL_TEST_CASES,
    Difficulty,
    TestCase,
    get_cases_by_difficulty,
    get_case_by_id,
)
from .worldview_prompt import build_eval_prompt


class EvalRunner:
    """
    Runs Worldview evaluations against LLMs.

    Uses the Worldview CLI tool to generate content from fact statements,
    then evaluates LLM responses against the generated worldview.
    """

    def __init__(
        self,
        models: Optional[list[ModelConfig]] = None,
        worldview_cli_path: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize the evaluation runner.

        Args:
            models: List of models to evaluate (default: DEFAULT_MODELS)
            worldview_cli_path: Path to Worldview CLI tool (default: search in PATH)
            verbose: Print detailed output
        """
        self.models = models or DEFAULT_MODELS
        self.worldview_cli_path = worldview_cli_path or "worldview"
        self.verbose = verbose
        self._clients: dict[str, LLMClient] = {}

    def _get_client(self, model: ModelConfig) -> LLMClient:
        """Get or create client for model."""
        if model.model_id not in self._clients:
            self._clients[model.model_id] = create_client(model)
        return self._clients[model.model_id]

    def _generate_worldview_with_cli(
        self,
        fact_statement: str,
    ) -> tuple[str, Optional[str]]:
        """
        Use the Worldview CLI tool to generate content.

        Args:
            fact_statement: The fact to process

        Returns:
            Tuple of (worldview_content, error_message)
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".wvf", delete=False
        ) as f:
            f.write("")  # Start with empty file
            worldview_path = f.name

        try:
            cmd = [
                self.worldview_cli_path,
                fact_statement,
                "--file",
                worldview_path,
            ]

            if self.verbose:
                print(f"    Running CLI: {' '.join(cmd)}", flush=True)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout for CLI
            )

            if result.returncode != 0:
                return "", f"CLI error: {result.stderr}"

            # Read the generated Worldview file
            with open(worldview_path) as f:
                worldview_content = f.read()

            return worldview_content, None

        except subprocess.TimeoutExpired:
            return "", "CLI timeout (120s)"
        except FileNotFoundError:
            return "", f"CLI tool not found: {self.worldview_cli_path}"
        except Exception as e:
            return "", str(e)
        finally:
            Path(worldview_path).unlink(missing_ok=True)

    def _run_single_eval(
        self,
        test_case: TestCase,
        model: ModelConfig,
        worldview_content: str,
    ) -> EvalResult:
        """
        Run a single evaluation with pre-generated worldview content.

        Args:
            test_case: The test case to run
            model: The model to evaluate
            worldview_content: Pre-generated worldview content

        Returns:
            EvalResult with response and scoring
        """
        # Build prompt and query
        system_prompt = build_eval_prompt(worldview_content)
        question = test_case.question

        # Get client and run completion
        try:
            client = self._get_client(model)
            response = client.complete(system_prompt, question)
        except Exception as e:
            return EvalResult(
                test_case=test_case,
                model_name=model.display_name,
                response="",
                score=EvalScore(),
                error=str(e),
            )

        if response.error:
            return EvalResult(
                test_case=test_case,
                model_name=model.display_name,
                response="",
                score=EvalScore(),
                error=response.error,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

        # Evaluate response
        score = evaluate_response(response.content, test_case)

        return EvalResult(
            test_case=test_case,
            model_name=model.display_name,
            response=response.content,
            score=score,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    def run_all(
        self,
        test_cases: Optional[list[TestCase]] = None,
        models: Optional[list[ModelConfig]] = None,
    ) -> dict[str, list[EvalResult]]:
        """
        Run all test cases against all models.

        Generates worldview content once per test case, then runs all models
        against that same content.

        Args:
            test_cases: Cases to run (default: ALL_TEST_CASES)
            models: Models to test (default: self.models)

        Returns:
            Dict mapping model name to list of results
        """
        test_cases = test_cases or ALL_TEST_CASES
        models = models or self.models

        results_by_model: dict[str, list[EvalResult]] = {
            m.display_name: [] for m in models
        }

        total_evals = len(test_cases) * len(models)
        current = 0

        for test_case in test_cases:
            if self.verbose:
                print(f"\nTest: {test_case.name} [{test_case.difficulty.value}]", flush=True)
                print(f"  Generating worldview for: {test_case.fact_statement[:50]}...", flush=True)

            # Generate worldview content ONCE for this test case
            worldview_content, cli_error = self._generate_worldview_with_cli(
                test_case.fact_statement
            )

            if cli_error:
                # If CLI fails, create error results for all models
                if self.verbose:
                    print(f"  [CLI ERROR] {cli_error}", flush=True)
                for model in models:
                    current += 1
                    result = EvalResult(
                        test_case=test_case,
                        model_name=model.display_name,
                        response="",
                        score=EvalScore(),
                        error=f"Worldview generation failed: {cli_error}",
                    )
                    results_by_model[model.display_name].append(result)
                continue

            if self.verbose:
                print(f"  Worldview generated ({len(worldview_content)} chars)", flush=True)

            # Run all models against the same worldview content
            for model in models:
                current += 1
                if self.verbose:
                    print(f"  [{current}/{total_evals}] {model.display_name}...", flush=True)

                result = self._run_single_eval(test_case, model, worldview_content)
                results_by_model[model.display_name].append(result)

                if self.verbose:
                    status = "PASS" if result.success else ("ERROR" if result.error else "FAIL")
                    print(f"    [{status}] Score: {result.score.overall_score:.2f}", flush=True)

        return results_by_model

    def run_difficulty(
        self,
        difficulty: Difficulty,
        models: Optional[list[ModelConfig]] = None,
    ) -> dict[str, list[EvalResult]]:
        """
        Run all test cases of a specific difficulty.

        Args:
            difficulty: The difficulty level to run
            models: Models to test

        Returns:
            Dict mapping model name to list of results
        """
        cases = get_cases_by_difficulty(difficulty)
        return self.run_all(test_cases=cases, models=models)


def generate_report(
    results_by_model: dict[str, list[EvalResult]],
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a markdown report from evaluation results.

    Args:
        results_by_model: Results organized by model name
        output_path: Optional path to write report

    Returns:
        Markdown report string
    """
    lines = [
        "# Worldview Evaluation Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary by Model",
        "",
        "| Model | Success Rate | Baseline | Moderate | Extreme | Avg Score |",
        "|-------|-------------|----------|----------|---------|-----------|",
    ]

    model_summaries: dict[str, EvalSummary] = {}

    for model_name, results in results_by_model.items():
        summary = summarize_results(results)
        model_summaries[model_name] = summary

        lines.append(
            f"| {model_name} | "
            f"{summary.success_rate:.1%} | "
            f"{summary.baseline_rate:.1%} | "
            f"{summary.moderate_rate:.1%} | "
            f"{summary.extreme_rate:.1%} | "
            f"{summary.avg_overall_score:.2f} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Detailed Results",
        "",
    ])

    # Group by test case
    all_cases: dict[str, dict[str, EvalResult]] = {}
    for model_name, results in results_by_model.items():
        for result in results:
            case_id = result.test_case.id
            if case_id not in all_cases:
                all_cases[case_id] = {}
            all_cases[case_id][model_name] = result

    for case_id, model_results in all_cases.items():
        first_result = list(model_results.values())[0]
        tc = first_result.test_case

        lines.extend([
            f"### {tc.name}",
            "",
            f"**Difficulty:** `{tc.difficulty.value}` | **Category:** `{tc.category.value}`",
            "",
            "#### 1. Fact Statement (input to Worldview CLI)",
            "",
            f"> {tc.fact_statement}",
            "",
            "#### 2. Worldview Content",
            "",
            "```wvf",
            tc.wsl_content.strip(),
            "```",
            "",
            "#### 3. Question Asked",
            "",
            f"> **{tc.question}**",
            "",
            "#### 4. Results by Model",
            "",
            "| Model | Aligned | Key Terms | Forbidden | Score |",
            "|-------|---------|-----------|-----------|-------|",
        ])

        for model_name, result in model_results.items():
            if result.error:
                lines.append(f"| {model_name} | ERROR | - | - | - |")
            else:
                aligned = "Yes" if result.score.aligned_with_worldview else "No"
                key = f"{len(result.score.key_terms_found)}/{len(tc.expected.key_terms)}"
                forbidden = len(result.score.forbidden_terms_found)
                lines.append(
                    f"| {model_name} | {aligned} | {key} | {forbidden} | "
                    f"{result.score.overall_score:.2f} |"
                )

        # Add response previews for each model
        lines.extend([
            "",
            "<details>",
            "<summary>Model Responses (click to expand)</summary>",
            "",
        ])

        for model_name, result in model_results.items():
            lines.append(f"**{model_name}:**")
            if result.error:
                lines.append(f"```\nERROR: {result.error}\n```")
            elif result.response:
                # Truncate long responses
                response_preview = result.response[:500]
                if len(result.response) > 500:
                    response_preview += "..."
                lines.append(f"```\n{response_preview}\n```")
            else:
                lines.append("```\n(no response)\n```")
            lines.append("")

        lines.extend([
            "</details>",
            "",
            "---",
            "",
        ])

    report = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(report)

    return report


def generate_json_results(
    results_by_model: dict[str, list[EvalResult]],
    output_path: Optional[str] = None,
) -> dict:
    """
    Generate JSON results for programmatic analysis.

    Args:
        results_by_model: Results organized by model name
        output_path: Optional path to write JSON

    Returns:
        Dict with complete results data
    """
    data = {
        "timestamp": datetime.now().isoformat(),
        "models": {},
    }

    for model_name, results in results_by_model.items():
        summary = summarize_results(results)
        data["models"][model_name] = {
            "summary": {
                "total": summary.total_cases,
                "success": summary.successful_cases,
                "failed": summary.failed_cases,
                "errors": summary.error_cases,
                "success_rate": summary.success_rate,
                "baseline_rate": summary.baseline_rate,
                "moderate_rate": summary.moderate_rate,
                "extreme_rate": summary.extreme_rate,
                "avg_score": summary.avg_overall_score,
                "tokens": {
                    "input": summary.total_input_tokens,
                    "output": summary.total_output_tokens,
                },
            },
            "results": [
                {
                    "test_id": r.test_case.id,
                    "test_name": r.test_case.name,
                    "difficulty": r.test_case.difficulty.value,
                    "success": r.success,
                    "error": r.error,
                    "score": {
                        "overall": r.score.overall_score,
                        "key_term": r.score.key_term_score,
                        "forbidden": r.score.forbidden_term_score,
                        "aligned": r.score.aligned_with_worldview,
                    },
                    "response_preview": r.response[:200] if r.response else None,
                }
                for r in results
            ],
        }

    if output_path:
        Path(output_path).write_text(json.dumps(data, indent=2))

    return data
