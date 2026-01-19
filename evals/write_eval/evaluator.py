"""
Write Evaluation Scoring and Analysis

Evaluates generated Worldview content against expected structural elements.
Uses a combination of:
1. Syntax validation (via validator binary or subprocess)
2. Structural analysis (Python-based parsing)
3. Content quality scoring
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .test_cases import WriteTestCase, ExpectedStructure, Complexity


@dataclass
class ParsedWorldview:
    """Parsed structure of a Worldview document."""

    concepts: list[str] = field(default_factory=list)
    facets: list[str] = field(default_factory=list)  # includes dot prefix
    claims: list[str] = field(default_factory=list)
    operators_found: list[str] = field(default_factory=list)
    raw_content: str = ""


@dataclass
class WriteScore:
    """Scoring result for a write evaluation."""

    # Syntax validation
    syntax_valid: bool = False
    syntax_errors: list[str] = field(default_factory=list)
    syntax_warnings: list[str] = field(default_factory=list)

    # Structural checks
    concepts_found: list[str] = field(default_factory=list)
    concepts_missing: list[str] = field(default_factory=list)
    facets_found: list[str] = field(default_factory=list)
    facets_missing: list[str] = field(default_factory=list)
    operators_found: list[str] = field(default_factory=list)
    operators_missing: list[str] = field(default_factory=list)
    terms_found: list[str] = field(default_factory=list)
    terms_missing: list[str] = field(default_factory=list)
    forbidden_terms_found: list[str] = field(default_factory=list)

    # Claim count
    claim_count: int = 0
    min_claims_required: int = 1

    # Computed scores (0.0 to 1.0)
    syntax_score: float = 0.0
    concept_score: float = 0.0
    facet_score: float = 0.0
    operator_score: float = 0.0
    term_score: float = 0.0
    claim_count_score: float = 0.0

    # Overall
    overall_score: float = 0.0
    notes: Optional[str] = None

    @property
    def passed(self) -> bool:
        """Whether this evaluation passed (syntax valid and overall score >= 0.5)."""
        return self.syntax_valid and self.overall_score >= 0.5


@dataclass
class AgentMetrics:
    """Metrics about the agent's performance."""

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0

    # Tool usage
    tool_calls: int = 0
    read_calls: int = 0
    edit_calls: int = 0
    failed_edits: int = 0

    # Timing
    total_time_ms: int = 0
    thinking_time_ms: int = 0

    # Agent interactions (captured from verbose output)
    thinking_content: list[str] = field(default_factory=list)
    tool_interactions: list[dict] = field(default_factory=list)


@dataclass
class WriteResult:
    """Complete result for a single write test case evaluation."""

    test_case: WriteTestCase
    model_name: str
    generated_content: str
    score: WriteScore
    metrics: AgentMetrics
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Whether this evaluation succeeded."""
        if self.error:
            return False
        return self.score.passed


# Known Worldview operators
WORLDVIEW_OPERATORS = ["=>", "<=", "<>", "><", "//", "vs", "~", "=", "|", "@", "&", "!", "?", "*", "^", "v", "[<="]


def parse_worldview_content(content: str) -> ParsedWorldview:
    """
    Parse Worldview content into structured data.

    Args:
        content: Raw Worldview document content

    Returns:
        ParsedWorldview with extracted structure
    """
    parsed = ParsedWorldview(raw_content=content)

    for line in content.split("\n"):
        stripped = line.rstrip()
        if not stripped:
            continue

        # Count leading spaces
        indent = len(line) - len(line.lstrip())

        if indent == 0 and stripped:
            # Concept (unindented)
            parsed.concepts.append(stripped)
        elif indent == 2 and stripped.startswith("."):
            # Facet (2-space indent, dot prefix)
            facet_name = stripped[1:].strip()
            parsed.facets.append(f".{facet_name}")
        elif indent == 4 and stripped.startswith("-"):
            # Claim (4-space indent, dash prefix)
            claim_text = stripped[1:].strip()
            parsed.claims.append(claim_text)

    # Extract operators from claims
    for claim in parsed.claims:
        for op in WORLDVIEW_OPERATORS:
            if op in claim:
                if op not in parsed.operators_found:
                    parsed.operators_found.append(op)

    return parsed


def validate_syntax_with_binary(
    content: str,
    validator_path: str = "worldview-validator",
) -> tuple[bool, list[str], list[str]]:
    """
    Validate Worldview syntax using the validator binary.

    Args:
        content: Worldview content to validate
        validator_path: Path to validator binary

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    import tempfile

    errors = []
    warnings = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".wvf", delete=False) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = subprocess.run(
            [validator_path, temp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Parse output for errors and warnings
        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "error" in line.lower():
                errors.append(line)
            elif "warning" in line.lower():
                warnings.append(line)

        is_valid = result.returncode == 0 and not errors
        return is_valid, errors, warnings

    except subprocess.TimeoutExpired:
        return False, ["Validator timeout"], []
    except FileNotFoundError:
        # Validator not found - fall back to basic validation
        return validate_syntax_basic(content)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def validate_syntax_basic(content: str) -> tuple[bool, list[str], list[str]]:
    """
    Basic syntax validation without the validator binary.

    Checks:
    - Proper indentation (0, 2, or 4 spaces)
    - Facets have dot prefix
    - Claims have dash prefix
    - Concepts have facets
    - Facets have claims

    Args:
        content: Worldview content to validate

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    lines = content.split("\n")
    current_concept = None
    current_facet = None
    concept_has_facet = False
    facet_has_claim = False

    for i, line in enumerate(lines):
        line_num = i + 1
        stripped = line.rstrip()

        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        # Check indentation
        if indent not in [0, 2, 4]:
            errors.append(f"Line {line_num}: Invalid indentation ({indent} spaces)")
            continue

        content_text = stripped.strip()

        if indent == 0:
            # Check previous concept had facets
            if current_concept and not concept_has_facet:
                errors.append(f"Concept '{current_concept}' has no facets")

            # Check previous facet had claims
            if current_facet and not facet_has_claim:
                errors.append(f"Facet '{current_facet}' has no claims")

            current_concept = content_text
            current_facet = None
            concept_has_facet = False
            facet_has_claim = False

        elif indent == 2:
            if not content_text.startswith("."):
                errors.append(f"Line {line_num}: Facet missing '.' prefix")
            else:
                # Check previous facet had claims
                if current_facet and not facet_has_claim:
                    errors.append(f"Facet '{current_facet}' has no claims")

                if not current_concept:
                    errors.append(f"Line {line_num}: Orphan facet (no concept)")

                current_facet = content_text
                concept_has_facet = True
                facet_has_claim = False

        elif indent == 4:
            if not content_text.startswith("-"):
                errors.append(f"Line {line_num}: Claim missing '-' prefix")
            else:
                if not current_facet:
                    errors.append(f"Line {line_num}: Orphan claim (no facet)")
                facet_has_claim = True

    # Check final concept/facet
    if current_concept and not concept_has_facet:
        errors.append(f"Concept '{current_concept}' has no facets")
    if current_facet and not facet_has_claim:
        errors.append(f"Facet '{current_facet}' has no claims")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.lower().strip()


def find_term(term: str, content: str) -> bool:
    """
    Check if a term appears in the content.

    Uses flexible matching:
    - Case-insensitive
    - Word boundary aware
    - Handles hyphenated terms
    """
    normalized_content = normalize_text(content)
    normalized_term = normalize_text(term)

    # Direct match
    if normalized_term in normalized_content:
        return True

    # Word boundary match
    pattern = r"\b" + re.escape(normalized_term) + r"\b"
    if re.search(pattern, normalized_content, re.IGNORECASE):
        return True

    # Hyphen-flexible match (e.g., "social capital" matches "social-capital")
    hyphen_term = normalized_term.replace(" ", "-")
    if hyphen_term in normalized_content:
        return True

    space_term = normalized_term.replace("-", " ")
    if space_term in normalized_content:
        return True

    return False


def find_concept(concept: str, parsed: ParsedWorldview) -> bool:
    """Check if a concept exists in the parsed content."""
    normalized = normalize_text(concept)
    for c in parsed.concepts:
        if normalize_text(c) == normalized or normalized in normalize_text(c):
            return True
    return False


def find_facet(facet: str, parsed: ParsedWorldview) -> bool:
    """Check if a facet exists in the parsed content."""
    # Ensure facet starts with dot for comparison
    if not facet.startswith("."):
        facet = f".{facet}"
    normalized = normalize_text(facet)

    for f in parsed.facets:
        normalized_f = normalize_text(f)
        # Allow partial matches (e.g., ".formation" matches ".trust-formation")
        if normalized in normalized_f or normalized_f.endswith(normalized):
            return True
        # Also check without the dot
        if normalized[1:] in normalized_f:
            return True
    return False


def find_operator(operator: str, parsed: ParsedWorldview) -> bool:
    """Check if an operator is used in the parsed content."""
    return operator in parsed.operators_found


def evaluate_write(
    generated_content: str,
    test_case: WriteTestCase,
    validator_path: Optional[str] = None,
) -> WriteScore:
    """
    Evaluate generated Worldview content against expected structure.

    Args:
        generated_content: The Worldview content generated by the agent
        test_case: The test case with expected structure
        validator_path: Optional path to validator binary

    Returns:
        WriteScore with detailed scoring breakdown
    """
    expected = test_case.expected
    score = WriteScore(min_claims_required=expected.min_claims)

    # Syntax validation
    if validator_path:
        syntax_valid, errors, warnings = validate_syntax_with_binary(
            generated_content, validator_path
        )
    else:
        syntax_valid, errors, warnings = validate_syntax_basic(generated_content)

    score.syntax_valid = syntax_valid
    score.syntax_errors = errors
    score.syntax_warnings = warnings
    score.syntax_score = 1.0 if syntax_valid else 0.0

    # Parse content
    parsed = parse_worldview_content(generated_content)
    score.claim_count = len(parsed.claims)

    # Check required concepts
    for concept in expected.required_concepts:
        if find_concept(concept, parsed):
            score.concepts_found.append(concept)
        else:
            score.concepts_missing.append(concept)

    if expected.required_concepts:
        score.concept_score = len(score.concepts_found) / len(expected.required_concepts)
    else:
        score.concept_score = 1.0

    # Check required facets
    for facet in expected.required_facets:
        if find_facet(facet, parsed):
            score.facets_found.append(facet)
        else:
            score.facets_missing.append(facet)

    if expected.required_facets:
        score.facet_score = len(score.facets_found) / len(expected.required_facets)
    else:
        score.facet_score = 1.0

    # Check required operators
    for op in expected.required_operators:
        if find_operator(op, parsed):
            score.operators_found.append(op)
        else:
            score.operators_missing.append(op)

    if expected.required_operators:
        score.operator_score = len(score.operators_found) / len(expected.required_operators)
    else:
        score.operator_score = 1.0

    # Check required terms (in full content)
    for term in expected.required_terms:
        if find_term(term, generated_content):
            score.terms_found.append(term)
        else:
            score.terms_missing.append(term)

    # Check forbidden terms
    for term in expected.forbidden_terms:
        if find_term(term, generated_content):
            score.forbidden_terms_found.append(term)

    if expected.required_terms:
        score.term_score = len(score.terms_found) / len(expected.required_terms)
    else:
        score.term_score = 1.0

    # Penalize for forbidden terms
    if expected.forbidden_terms and score.forbidden_terms_found:
        forbidden_penalty = len(score.forbidden_terms_found) / len(expected.forbidden_terms)
        score.term_score *= (1.0 - forbidden_penalty * 0.5)

    # Claim count score
    if score.claim_count >= expected.min_claims:
        score.claim_count_score = 1.0
    else:
        score.claim_count_score = score.claim_count / expected.min_claims if expected.min_claims > 0 else 0.0

    # Compute overall score with weights
    # Weights: syntax=20%, concepts=20%, facets=15%, operators=15%, terms=20%, claims=10%
    score.overall_score = (
        0.20 * score.syntax_score +
        0.20 * score.concept_score +
        0.15 * score.facet_score +
        0.15 * score.operator_score +
        0.20 * score.term_score +
        0.10 * score.claim_count_score
    )

    # Add notes for failures
    notes = []
    if not syntax_valid:
        notes.append(f"Syntax errors: {len(errors)}")
    if score.concepts_missing:
        notes.append(f"Missing concepts: {score.concepts_missing}")
    if score.facets_missing:
        notes.append(f"Missing facets: {score.facets_missing}")
    if score.forbidden_terms_found:
        notes.append(f"Forbidden terms used: {score.forbidden_terms_found}")

    if notes:
        score.notes = "; ".join(notes)

    return score


@dataclass
class WriteSummary:
    """Summary statistics for a batch of write evaluations."""

    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0

    # By complexity
    simple_success: int = 0
    simple_total: int = 0
    moderate_success: int = 0
    moderate_total: int = 0
    complex_success: int = 0
    complex_total: int = 0

    # Scores
    avg_syntax_score: float = 0.0
    avg_concept_score: float = 0.0
    avg_overall_score: float = 0.0

    # Efficiency metrics
    avg_tool_calls: float = 0.0
    avg_tokens: float = 0.0
    avg_time_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.successful_cases / self.total_cases

    @property
    def simple_rate(self) -> float:
        if self.simple_total == 0:
            return 0.0
        return self.simple_success / self.simple_total

    @property
    def moderate_rate(self) -> float:
        if self.moderate_total == 0:
            return 0.0
        return self.moderate_success / self.moderate_total

    @property
    def complex_rate(self) -> float:
        if self.complex_total == 0:
            return 0.0
        return self.complex_success / self.complex_total


def summarize_write_results(results: list[WriteResult]) -> WriteSummary:
    """
    Generate summary statistics from write evaluation results.

    Args:
        results: List of individual write evaluation results

    Returns:
        WriteSummary with aggregate statistics
    """
    summary = WriteSummary(total_cases=len(results))

    syntax_scores = []
    concept_scores = []
    overall_scores = []
    tool_calls = []
    tokens = []
    times = []

    for result in results:
        # Count by outcome
        if result.error:
            summary.error_cases += 1
        elif result.success:
            summary.successful_cases += 1
        else:
            summary.failed_cases += 1

        # Count by complexity
        complexity = result.test_case.complexity
        if complexity == Complexity.SIMPLE:
            summary.simple_total += 1
            if result.success:
                summary.simple_success += 1
        elif complexity == Complexity.MODERATE:
            summary.moderate_total += 1
            if result.success:
                summary.moderate_success += 1
        elif complexity == Complexity.COMPLEX:
            summary.complex_total += 1
            if result.success:
                summary.complex_success += 1

        # Collect scores (skip errors)
        if not result.error:
            syntax_scores.append(result.score.syntax_score)
            concept_scores.append(result.score.concept_score)
            overall_scores.append(result.score.overall_score)

        # Collect efficiency metrics
        tool_calls.append(result.metrics.tool_calls)
        total_tokens = result.metrics.input_tokens + result.metrics.output_tokens
        tokens.append(total_tokens)
        times.append(result.metrics.total_time_ms)

    # Compute averages
    if syntax_scores:
        summary.avg_syntax_score = sum(syntax_scores) / len(syntax_scores)
    if concept_scores:
        summary.avg_concept_score = sum(concept_scores) / len(concept_scores)
    if overall_scores:
        summary.avg_overall_score = sum(overall_scores) / len(overall_scores)
    if tool_calls:
        summary.avg_tool_calls = sum(tool_calls) / len(tool_calls)
    if tokens:
        summary.avg_tokens = sum(tokens) / len(tokens)
    if times:
        summary.avg_time_ms = sum(times) / len(times)

    return summary
