"""
WSL Evaluation Scoring and Analysis

Evaluates LLM responses against expected behaviors defined in test cases.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from .test_cases import ExpectedBehavior, TestCase


@dataclass
class EvalScore:
    """Scoring result for a single evaluation."""

    # Core metrics
    key_terms_found: list[str] = field(default_factory=list)
    key_terms_missing: list[str] = field(default_factory=list)
    forbidden_terms_found: list[str] = field(default_factory=list)

    # Computed scores (0.0 to 1.0)
    key_term_score: float = 0.0
    forbidden_term_score: float = 1.0  # 1.0 = no forbidden terms found
    alignment_score: float = 0.0

    # Whether response aligned with WSL worldview
    aligned_with_wsl: bool = False

    # Raw data
    response_length: int = 0
    notes: Optional[str] = None

    @property
    def overall_score(self) -> float:
        """
        Compute overall score.

        Weighted combination:
        - 60% key term coverage
        - 40% avoiding forbidden terms
        """
        return (0.6 * self.key_term_score) + (0.4 * self.forbidden_term_score)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.lower().strip()


def find_term_in_response(term: str, response: str) -> bool:
    """
    Check if a term appears in the response.

    Uses word-boundary matching to avoid false positives.
    """
    normalized_response = normalize_text(response)
    normalized_term = normalize_text(term)

    # Try exact word boundary match first
    pattern = r"\b" + re.escape(normalized_term) + r"\b"
    if re.search(pattern, normalized_response):
        return True

    # For multi-word terms, also check if all words appear
    words = normalized_term.split()
    if len(words) > 1:
        return all(word in normalized_response for word in words)

    return False


def evaluate_response(
    response: str,
    test_case: TestCase,
) -> EvalScore:
    """
    Evaluate an LLM response against expected behavior.

    Args:
        response: The LLM's response text
        test_case: The test case with expected behavior

    Returns:
        EvalScore with detailed scoring breakdown
    """
    expected = test_case.expected
    score = EvalScore(response_length=len(response))

    # Check key terms
    for term in expected.key_terms:
        if find_term_in_response(term, response):
            score.key_terms_found.append(term)
        else:
            score.key_terms_missing.append(term)

    # Calculate key term score
    if expected.key_terms:
        score.key_term_score = len(score.key_terms_found) / len(expected.key_terms)
    else:
        score.key_term_score = 1.0  # No required terms = full score

    # Check forbidden terms
    for term in expected.forbidden_terms:
        if find_term_in_response(term, response):
            score.forbidden_terms_found.append(term)

    # Calculate forbidden term score (inverse - fewer is better)
    if expected.forbidden_terms:
        violations = len(score.forbidden_terms_found)
        score.forbidden_term_score = 1.0 - (violations / len(expected.forbidden_terms))
    else:
        score.forbidden_term_score = 1.0  # No forbidden terms = full score

    # Determine overall alignment
    # Aligned if: decent key term coverage AND no major forbidden term violations
    score.aligned_with_wsl = (
        score.key_term_score >= 0.5 and score.forbidden_term_score >= 0.5
    )

    # Check if alignment matches expectation
    if expected.should_align_with_wsl and not score.aligned_with_wsl:
        score.notes = "Expected alignment with WSL but response did not align"
    elif not expected.should_align_with_wsl and score.aligned_with_wsl:
        score.notes = "Expected non-alignment but response aligned with WSL"

    return score


@dataclass
class EvalResult:
    """Complete result for a single test case evaluation."""

    test_case: TestCase
    model_name: str
    response: str
    score: EvalScore
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def success(self) -> bool:
        """Whether this evaluation succeeded (no errors and aligned as expected)."""
        if self.error:
            return False
        return self.score.aligned_with_wsl == self.test_case.expected.should_align_with_wsl


@dataclass
class EvalSummary:
    """Summary statistics for a batch of evaluations."""

    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0

    # By difficulty
    baseline_success: int = 0
    baseline_total: int = 0
    moderate_success: int = 0
    moderate_total: int = 0
    extreme_success: int = 0
    extreme_total: int = 0

    # Scores
    avg_key_term_score: float = 0.0
    avg_forbidden_score: float = 0.0
    avg_overall_score: float = 0.0

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    @property
    def success_rate(self) -> float:
        """Overall success rate."""
        if self.total_cases == 0:
            return 0.0
        return self.successful_cases / self.total_cases

    @property
    def baseline_rate(self) -> float:
        """Baseline difficulty success rate."""
        if self.baseline_total == 0:
            return 0.0
        return self.baseline_success / self.baseline_total

    @property
    def moderate_rate(self) -> float:
        """Moderate difficulty success rate."""
        if self.moderate_total == 0:
            return 0.0
        return self.moderate_success / self.moderate_total

    @property
    def extreme_rate(self) -> float:
        """Extreme difficulty success rate."""
        if self.extreme_total == 0:
            return 0.0
        return self.extreme_success / self.extreme_total


def summarize_results(results: list[EvalResult]) -> EvalSummary:
    """
    Generate summary statistics from evaluation results.

    Args:
        results: List of individual evaluation results

    Returns:
        EvalSummary with aggregate statistics
    """
    from .test_cases import Difficulty

    summary = EvalSummary(total_cases=len(results))

    key_term_scores = []
    forbidden_scores = []
    overall_scores = []

    for result in results:
        # Count by outcome
        if result.error:
            summary.error_cases += 1
        elif result.success:
            summary.successful_cases += 1
        else:
            summary.failed_cases += 1

        # Count by difficulty
        difficulty = result.test_case.difficulty
        if difficulty == Difficulty.BASELINE:
            summary.baseline_total += 1
            if result.success:
                summary.baseline_success += 1
        elif difficulty == Difficulty.MODERATE:
            summary.moderate_total += 1
            if result.success:
                summary.moderate_success += 1
        elif difficulty == Difficulty.EXTREME:
            summary.extreme_total += 1
            if result.success:
                summary.extreme_success += 1

        # Collect scores (skip errors)
        if not result.error:
            key_term_scores.append(result.score.key_term_score)
            forbidden_scores.append(result.score.forbidden_term_score)
            overall_scores.append(result.score.overall_score)

        # Token usage
        summary.total_input_tokens += result.input_tokens
        summary.total_output_tokens += result.output_tokens

    # Compute averages
    if key_term_scores:
        summary.avg_key_term_score = sum(key_term_scores) / len(key_term_scores)
    if forbidden_scores:
        summary.avg_forbidden_score = sum(forbidden_scores) / len(forbidden_scores)
    if overall_scores:
        summary.avg_overall_score = sum(overall_scores) / len(overall_scores)

    return summary
