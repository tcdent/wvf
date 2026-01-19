"""
Write Evaluation Runner

Orchestrates running write test cases against the Worldview agent CLI
with different models, capturing metrics and verbose output.
"""

import json
import re
import subprocess
import tempfile
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .test_cases import (
    ALL_WRITE_CASES,
    Complexity,
    WriteTestCase,
    get_cases_by_complexity,
    get_case_by_id,
)
from .evaluator import (
    AgentMetrics,
    WriteResult,
    WriteScore,
    WriteSummary,
    evaluate_write,
    summarize_write_results,
)


# Models available for write evaluation (must support Anthropic API with extended thinking)
WRITE_MODELS = [
    {
        "name": "claude-sonnet",
        "model_id": "claude-sonnet-4-20250514",
        "display_name": "Claude Sonnet 4",
    },
    {
        "name": "claude-opus",
        "model_id": "claude-opus-4-5-20251101",
        "display_name": "Claude Opus 4.5",
    },
    {
        "name": "claude-haiku",
        "model_id": "claude-haiku-4-5-20251001",
        "display_name": "Claude Haiku 4.5",
    },
]

DEFAULT_WRITE_MODELS = ["claude-sonnet", "claude-haiku"]


def get_write_model(name: str) -> Optional[dict]:
    """Get model config by name."""
    for model in WRITE_MODELS:
        if model["name"] == name:
            return model
    return None


class WriteEvalRunner:
    """
    Runs write evaluations against the Worldview agent CLI.

    Tests the agent's ability to correctly generate and update
    Worldview documents from plain-text fact statements.
    """

    def __init__(
        self,
        models: Optional[list[str]] = None,
        agent_cli_path: str = "worldview",
        validator_path: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize the write evaluation runner.

        Args:
            models: List of model names to evaluate (default: DEFAULT_WRITE_MODELS)
            agent_cli_path: Path to Worldview agent CLI
            validator_path: Path to validator binary (optional)
            verbose: Print detailed output during evaluation
        """
        self.model_names = models or DEFAULT_WRITE_MODELS
        self.models = []
        for name in self.model_names:
            model = get_write_model(name)
            if model:
                self.models.append(model)
            elif verbose:
                print(f"Warning: Unknown model '{name}', skipping")

        self.agent_cli_path = agent_cli_path
        self.validator_path = validator_path
        self.verbose = verbose

    def _run_agent(
        self,
        fact_statement: str,
        base_content: str,
        model_id: str,
    ) -> tuple[str, AgentMetrics, Optional[str]]:
        """
        Run the Worldview agent CLI with verbose output capture.

        Args:
            fact_statement: The fact to add
            base_content: Starting file content
            model_id: Model ID to use

        Returns:
            Tuple of (generated_content, metrics, error_message)
        """
        metrics = AgentMetrics()

        # Create temporary file with base content
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".wvf", delete=False
        ) as f:
            f.write(base_content)
            temp_path = f.name

        try:
            # Build command with verbose flag
            cmd = [
                self.agent_cli_path,
                fact_statement,
                "--file", temp_path,
                "--model", model_id,
                "-v",  # Verbose mode
            ]

            if self.verbose:
                print(f"    Running: {' '.join(cmd[:3])}...")

            # Run with timing
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )
            end_time = time.time()

            metrics.total_time_ms = int((end_time - start_time) * 1000)

            # Parse verbose output from stderr
            self._parse_verbose_output(result.stderr, metrics)

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Agent CLI failed"
                return "", metrics, error_msg

            # Read generated content
            with open(temp_path) as f:
                generated_content = f.read()

            return generated_content, metrics, None

        except subprocess.TimeoutExpired:
            return "", metrics, "Agent timeout (120s)"
        except FileNotFoundError:
            return "", metrics, f"Agent CLI not found: {self.agent_cli_path}"
        except Exception as e:
            return "", metrics, str(e)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _parse_verbose_output(self, stderr: str, metrics: AgentMetrics):
        """
        Parse verbose output from agent CLI to extract metrics.

        Expected format (updated):
        [config] ...
        [start] ...
        [thinking] ...
        [tool:N] tool_name
        [params] {...}
        [result:Xms] ...
        [done] Input: X, Output: Y, Thinking: Z
        [timing] Total: Xms, Tool calls: N

        Args:
            stderr: The stderr output from the agent
            metrics: AgentMetrics to populate
        """
        current_thinking = []
        current_tool_name = None

        for line in stderr.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Thinking blocks (may be multi-line continuation)
            if line.startswith("[thinking]"):
                thinking_content = line[len("[thinking]"):].strip()
                current_thinking.append(thinking_content)
            elif current_thinking and not line.startswith("["):
                # Continuation of thinking block
                current_thinking.append(line)

            # Tool calls with numbering: [tool:N] tool_name
            elif line.startswith("[tool:"):
                metrics.tool_calls += 1
                # Extract tool name after the bracket
                tool_content = line.split("]", 1)[-1].strip()
                current_tool_name = tool_content

                # Parse tool name
                if "read_worldview" in tool_content:
                    metrics.read_calls += 1
                elif "edit_worldview" in tool_content:
                    metrics.edit_calls += 1

                # Store thinking before this tool call
                if current_thinking:
                    metrics.thinking_content.extend(current_thinking)
                    current_thinking = []

                # Store tool interaction
                metrics.tool_interactions.append({
                    "type": "tool_call",
                    "name": tool_content,
                })

            # Tool parameters
            elif line.startswith("[params]"):
                params_content = line[len("[params]"):].strip()
                if metrics.tool_interactions:
                    metrics.tool_interactions[-1]["params"] = params_content

            # Tool results with timing: [result:Xms] ...
            elif line.startswith("[result"):
                result_content = line.split("]", 1)[-1].strip()

                # Check for failed edits
                if "failed" in result_content.lower() or "error" in result_content.lower():
                    metrics.failed_edits += 1

                metrics.tool_interactions.append({
                    "type": "tool_result",
                    "content": result_content,
                })

            # Completion with token usage
            elif line.startswith("[done]"):
                done_content = line[len("[done]"):].strip()

                # Parse token counts: "Input: X, Output: Y, Thinking: Z"
                input_match = re.search(r"Input:\s*(\d+)", done_content)
                output_match = re.search(r"Output:\s*(\d+)", done_content)
                thinking_match = re.search(r"Thinking:\s*(\d+)", done_content)

                if input_match:
                    metrics.input_tokens = int(input_match.group(1))
                if output_match:
                    metrics.output_tokens = int(output_match.group(1))
                if thinking_match:
                    metrics.thinking_tokens = int(thinking_match.group(1))

            # Timing information
            elif line.startswith("[timing]"):
                timing_content = line[len("[timing]"):].strip()
                # Parse total time: "Total: Xms, Tool calls: N"
                total_match = re.search(r"Total:\s*(\d+)ms", timing_content)
                if total_match:
                    # Override if we got timing from the agent itself
                    metrics.total_time_ms = int(total_match.group(1))

            # Retry attempts
            elif line.startswith("[retry]"):
                metrics.tool_interactions.append({
                    "type": "retry",
                    "content": line[len("[retry]"):].strip(),
                })

            # Error with timing
            elif line.startswith("[error"):
                error_content = line.split("]", 1)[-1].strip()
                metrics.tool_interactions.append({
                    "type": "error",
                    "content": error_content,
                })

        # Store any remaining thinking content
        if current_thinking:
            metrics.thinking_content.extend(current_thinking)

    def _run_single_eval(
        self,
        test_case: WriteTestCase,
        model: dict,
    ) -> WriteResult:
        """
        Run a single write evaluation.

        Args:
            test_case: The test case to run
            model: The model configuration

        Returns:
            WriteResult with generated content and scoring
        """
        if self.verbose:
            print(f"  Running: {test_case.id} with {model['display_name']}")

        # Run the agent
        generated_content, metrics, error = self._run_agent(
            test_case.fact_statement,
            test_case.base_content,
            model["model_id"],
        )

        if error:
            return WriteResult(
                test_case=test_case,
                model_name=model["display_name"],
                generated_content="",
                score=WriteScore(),
                metrics=metrics,
                error=error,
            )

        # Evaluate the generated content
        score = evaluate_write(
            generated_content,
            test_case,
            validator_path=self.validator_path,
        )

        return WriteResult(
            test_case=test_case,
            model_name=model["display_name"],
            generated_content=generated_content,
            score=score,
            metrics=metrics,
        )

    def run_case(
        self,
        test_case: WriteTestCase,
        models: Optional[list[dict]] = None,
    ) -> list[WriteResult]:
        """
        Run a single test case against specified models.

        Args:
            test_case: The test case to run
            models: Models to test (default: self.models)

        Returns:
            List of WriteResults, one per model
        """
        models = models or self.models
        results = []

        for model in models:
            result = self._run_single_eval(test_case, model)
            results.append(result)

            if self.verbose:
                status = "PASS" if result.success else ("ERROR" if result.error else "FAIL")
                print(f"    [{status}] Score: {result.score.overall_score:.2f}, "
                      f"Time: {result.metrics.total_time_ms}ms, "
                      f"Tools: {result.metrics.tool_calls}")

        return results

    def run_all(
        self,
        test_cases: Optional[list[WriteTestCase]] = None,
        models: Optional[list[dict]] = None,
    ) -> dict[str, list[WriteResult]]:
        """
        Run all test cases against all models.

        Args:
            test_cases: Cases to run (default: ALL_WRITE_CASES)
            models: Models to test (default: self.models)

        Returns:
            Dict mapping model name to list of results
        """
        test_cases = test_cases or ALL_WRITE_CASES
        models = models or self.models

        results_by_model: dict[str, list[WriteResult]] = {
            m["display_name"]: [] for m in models
        }

        total = len(test_cases) * len(models)
        current = 0

        for test_case in test_cases:
            if self.verbose:
                print(f"\nTest: {test_case.name} [{test_case.complexity.value}]")

            for model in models:
                current += 1
                if self.verbose:
                    print(f"  [{current}/{total}] {model['display_name']}...")

                result = self._run_single_eval(test_case, model)
                results_by_model[model["display_name"]].append(result)

                if self.verbose:
                    status = "PASS" if result.success else ("ERROR" if result.error else "FAIL")
                    print(f"    [{status}] Score: {result.score.overall_score:.2f}")

        return results_by_model

    def run_complexity(
        self,
        complexity: Complexity,
        models: Optional[list[dict]] = None,
    ) -> dict[str, list[WriteResult]]:
        """
        Run all test cases of a specific complexity.

        Args:
            complexity: The complexity level to run
            models: Models to test

        Returns:
            Dict mapping model name to list of results
        """
        cases = get_cases_by_complexity(complexity)
        return self.run_all(test_cases=cases, models=models)


def generate_write_report(
    results_by_model: dict[str, list[WriteResult]],
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a markdown report from write evaluation results.

    Args:
        results_by_model: Results organized by model name
        output_path: Optional path to write report

    Returns:
        Markdown report string
    """
    lines = [
        "# Write Evaluation Report",
        "",
        "Benchmarks embedding models on Worldview document generation and updates.",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary by Model",
        "",
        "| Model | Success | Simple | Moderate | Complex | Avg Score | Avg Time | Avg Tools |",
        "|-------|---------|--------|----------|---------|-----------|----------|-----------|",
    ]

    model_summaries: dict[str, WriteSummary] = {}

    for model_name, results in results_by_model.items():
        summary = summarize_write_results(results)
        model_summaries[model_name] = summary

        lines.append(
            f"| {model_name} | "
            f"{summary.success_rate:.1%} | "
            f"{summary.simple_rate:.1%} | "
            f"{summary.moderate_rate:.1%} | "
            f"{summary.complex_rate:.1%} | "
            f"{summary.avg_overall_score:.2f} | "
            f"{summary.avg_time_ms:.0f}ms | "
            f"{summary.avg_tool_calls:.1f} |"
        )

    lines.extend([
        "",
        "## Efficiency Comparison",
        "",
        "| Model | Avg Input Tokens | Avg Output Tokens | Avg Total Tokens |",
        "|-------|------------------|-------------------|------------------|",
    ])

    for model_name, results in results_by_model.items():
        if results:
            avg_input = sum(r.metrics.input_tokens for r in results) / len(results)
            avg_output = sum(r.metrics.output_tokens for r in results) / len(results)
            avg_total = avg_input + avg_output
            lines.append(f"| {model_name} | {avg_input:.0f} | {avg_output:.0f} | {avg_total:.0f} |")

    lines.extend([
        "",
        "---",
        "",
        "## Detailed Results",
        "",
    ])

    # Group by test case
    all_cases: dict[str, dict[str, WriteResult]] = {}
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
            f"**Complexity:** `{tc.complexity.value}` | **Type:** `{tc.task_type.value}`",
            "",
            "#### Fact Statement",
            "",
            f"> {tc.fact_statement}",
            "",
        ])

        if tc.base_content:
            lines.extend([
                "#### Base Content",
                "",
                "```wvf",
                tc.base_content.strip(),
                "```",
                "",
            ])

        lines.extend([
            "#### Results by Model",
            "",
            "| Model | Pass | Syntax | Concepts | Terms | Score | Time | Tools |",
            "|-------|------|--------|----------|-------|-------|------|-------|",
        ])

        for model_name, result in model_results.items():
            if result.error:
                lines.append(f"| {model_name} | ERROR | - | - | - | - | - | - |")
            else:
                passed = "Yes" if result.success else "No"
                syntax = "OK" if result.score.syntax_valid else "FAIL"
                concepts = f"{len(result.score.concepts_found)}/{len(tc.expected.required_concepts)}"
                terms = f"{len(result.score.terms_found)}/{len(tc.expected.required_terms)}"
                lines.append(
                    f"| {model_name} | {passed} | {syntax} | {concepts} | {terms} | "
                    f"{result.score.overall_score:.2f} | "
                    f"{result.metrics.total_time_ms}ms | "
                    f"{result.metrics.tool_calls} |"
                )

        # Add generated content samples
        lines.extend([
            "",
            "<details>",
            "<summary>Generated Content (click to expand)</summary>",
            "",
        ])

        for model_name, result in model_results.items():
            lines.append(f"**{model_name}:**")
            if result.error:
                lines.append(f"```\nERROR: {result.error}\n```")
            elif result.generated_content:
                content_preview = result.generated_content[:800]
                if len(result.generated_content) > 800:
                    content_preview += "\n..."
                lines.append(f"```wvf\n{content_preview}\n```")
            else:
                lines.append("```\n(no content generated)\n```")

            # Add agent thinking if available
            if result.metrics.thinking_content:
                thinking_preview = " ".join(result.metrics.thinking_content)[:300]
                lines.append(f"\n*Agent thinking:* {thinking_preview}...")

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


def generate_write_json(
    results_by_model: dict[str, list[WriteResult]],
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
        "eval_type": "write",
        "models": {},
    }

    for model_name, results in results_by_model.items():
        summary = summarize_write_results(results)
        data["models"][model_name] = {
            "summary": {
                "total": summary.total_cases,
                "success": summary.successful_cases,
                "failed": summary.failed_cases,
                "errors": summary.error_cases,
                "success_rate": summary.success_rate,
                "simple_rate": summary.simple_rate,
                "moderate_rate": summary.moderate_rate,
                "complex_rate": summary.complex_rate,
                "avg_score": summary.avg_overall_score,
                "avg_tool_calls": summary.avg_tool_calls,
                "avg_time_ms": summary.avg_time_ms,
            },
            "results": [
                {
                    "test_id": r.test_case.id,
                    "test_name": r.test_case.name,
                    "complexity": r.test_case.complexity.value,
                    "task_type": r.test_case.task_type.value,
                    "success": r.success,
                    "error": r.error,
                    "score": {
                        "overall": r.score.overall_score,
                        "syntax": r.score.syntax_score,
                        "concepts": r.score.concept_score,
                        "facets": r.score.facet_score,
                        "operators": r.score.operator_score,
                        "terms": r.score.term_score,
                    },
                    "metrics": {
                        "time_ms": r.metrics.total_time_ms,
                        "tool_calls": r.metrics.tool_calls,
                        "input_tokens": r.metrics.input_tokens,
                        "output_tokens": r.metrics.output_tokens,
                        "thinking_tokens": r.metrics.thinking_tokens,
                    },
                    "content_preview": r.generated_content[:200] if r.generated_content else None,
                }
                for r in results
            ],
        }

    if output_path:
        Path(output_path).write_text(json.dumps(data, indent=2))

    return data
