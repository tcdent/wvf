"""
Write Evaluation Test Cases

Test cases for evaluating how well models can generate and update
Worldview documents from plain-text fact statements.

Each test case defines:
- A fact statement to add
- Optional base content (existing file content)
- Expected structural elements in the output
- Complexity rating for benchmarking
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Complexity(Enum):
    """
    Complexity level of the write task.

    SIMPLE: Single concept, single facet
    MODERATE: Single concept with multiple facets or operators
    COMPLEX: Multiple concepts, cross-references, or nuanced notation
    """

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class TaskType(Enum):
    """Type of write operation being tested."""

    CREATE = "create"  # Add to empty file
    APPEND = "append"  # Add new content to existing file
    UPDATE = "update"  # Modify existing content


@dataclass
class ExpectedStructure:
    """Expected structural elements in the generated Worldview content."""

    # Required concepts (top-level entries)
    required_concepts: list[str] = field(default_factory=list)

    # Required facets (with dot prefix, can be partial match)
    required_facets: list[str] = field(default_factory=list)

    # Required operators or notation elements
    required_operators: list[str] = field(default_factory=list)

    # Terms that should appear somewhere in the content
    required_terms: list[str] = field(default_factory=list)

    # Terms that should NOT appear (incorrect formatting, etc.)
    forbidden_terms: list[str] = field(default_factory=list)

    # Minimum number of claims (lines with - prefix)
    min_claims: int = 1

    # Whether proper indentation is required (always yes, but tracked)
    requires_valid_syntax: bool = True


@dataclass
class WriteTestCase:
    """
    A single write evaluation test case.

    Attributes:
        id: Unique identifier
        name: Human-readable name
        complexity: How complex the write task is
        task_type: Type of write operation
        fact_statement: Plain-text fact to add via CLI
        base_content: Starting file content (empty for CREATE tasks)
        expected: Expected structural elements in output
        notes: Additional notes about the test case
    """

    id: str
    name: str
    complexity: Complexity
    task_type: TaskType
    fact_statement: str
    expected: ExpectedStructure
    base_content: str = ""
    notes: Optional[str] = None


# =============================================================================
# SIMPLE TEST CASES
# Single concept, straightforward formatting
# =============================================================================

SIMPLE_CASES = [
    WriteTestCase(
        id="simple-gravity",
        name="Basic physics fact",
        complexity=Complexity.SIMPLE,
        task_type=TaskType.CREATE,
        fact_statement="Gravity pulls objects toward Earth with a force proportional to their mass.",
        expected=ExpectedStructure(
            required_concepts=["Gravity"],
            required_facets=[".force", ".effect"],
            required_terms=["Earth", "mass", "pull"],
            min_claims=1,
        ),
        notes="Simple scientific fact with clear concept",
    ),
    WriteTestCase(
        id="simple-trust",
        name="Trust formation",
        complexity=Complexity.SIMPLE,
        task_type=TaskType.CREATE,
        fact_statement="Trust is built slowly through consistent actions over time.",
        expected=ExpectedStructure(
            required_concepts=["Trust"],
            required_facets=[".formation"],
            required_terms=["slow", "consistent", "time"],
            min_claims=1,
        ),
        notes="Simple philosophical concept",
    ),
    WriteTestCase(
        id="simple-water",
        name="Water boiling point",
        complexity=Complexity.SIMPLE,
        task_type=TaskType.CREATE,
        fact_statement="Water boils at 100 degrees Celsius at standard atmospheric pressure.",
        expected=ExpectedStructure(
            required_concepts=["Water"],
            required_terms=["100", "boil"],
            min_claims=1,
        ),
        notes="Simple factual statement",
    ),
    WriteTestCase(
        id="simple-append",
        name="Append to existing file",
        complexity=Complexity.SIMPLE,
        task_type=TaskType.APPEND,
        fact_statement="Patience leads to better decision-making.",
        base_content="""Trust
  .formation
    - slow
    - requires consistency
""",
        expected=ExpectedStructure(
            required_concepts=["Trust", "Patience"],
            required_terms=["decision", "better"],
            min_claims=2,  # Original + new
        ),
        notes="Add new concept to existing file",
    ),
]

# =============================================================================
# MODERATE TEST CASES
# Multiple facets, operators, conditions
# =============================================================================

MODERATE_CASES = [
    WriteTestCase(
        id="moderate-causation",
        name="Causal relationship with operator",
        complexity=Complexity.MODERATE,
        task_type=TaskType.CREATE,
        fact_statement=(
            "Sleep deprivation causes reduced cognitive function, which leads to "
            "poor decision-making and increased accident risk."
        ),
        expected=ExpectedStructure(
            required_concepts=["Sleep"],
            required_facets=[".deprivation"],
            required_operators=["=>"],  # Causation operator
            required_terms=["cognitive", "decision", "accident"],
            min_claims=2,
        ),
        notes="Tests proper use of causation operator",
    ),
    WriteTestCase(
        id="moderate-conditional",
        name="Conditional statement",
        complexity=Complexity.MODERATE,
        task_type=TaskType.CREATE,
        fact_statement=(
            "Exercise improves mood, but only when done consistently. "
            "Sporadic exercise provides minimal mental health benefits."
        ),
        expected=ExpectedStructure(
            required_concepts=["Exercise"],
            required_facets=[".mood", ".mental-health"],
            required_operators=["|"],  # Condition operator
            required_terms=["consistent", "sporadic", "benefit"],
            min_claims=2,
        ),
        notes="Tests conditional notation",
    ),
    WriteTestCase(
        id="moderate-tension",
        name="Conflicting ideas",
        complexity=Complexity.MODERATE,
        task_type=TaskType.CREATE,
        fact_statement=(
            "Individual freedom and collective security often conflict. "
            "Maximizing one typically requires limiting the other."
        ),
        expected=ExpectedStructure(
            required_concepts=["Freedom", "Society"],
            required_operators=["><"],  # Tension operator
            required_terms=["individual", "collective", "security", "limit"],
            min_claims=2,
        ),
        notes="Tests tension/conflict notation",
    ),
    WriteTestCase(
        id="moderate-update",
        name="Update existing content",
        complexity=Complexity.MODERATE,
        task_type=TaskType.UPDATE,
        fact_statement=(
            "Trust can be rebuilt after betrayal, but it requires significantly "
            "more effort than initial trust formation."
        ),
        base_content="""Trust
  .formation
    - slow
    - requires consistency | over time
  .erosion
    - fast !
    - single violation => collapse?
""",
        expected=ExpectedStructure(
            required_concepts=["Trust"],
            required_facets=[".formation", ".erosion", ".rebuilding"],
            required_terms=["rebuild", "betrayal", "effort"],
            min_claims=4,  # Original + new claims
        ),
        notes="Add new facet to existing concept",
    ),
    WriteTestCase(
        id="moderate-source",
        name="Statement with source attribution",
        complexity=Complexity.MODERATE,
        task_type=TaskType.CREATE,
        fact_statement=(
            "According to evolutionary psychology, humans have an innate fear of snakes "
            "and spiders because these posed significant survival threats to our ancestors."
        ),
        expected=ExpectedStructure(
            required_concepts=["Fear"],
            required_facets=[".innate", ".evolutionary"],
            required_operators=["@"],  # Source attribution
            required_terms=["snake", "spider", "survival", "ancestor"],
            min_claims=2,
        ),
        notes="Tests source attribution notation",
    ),
]

# =============================================================================
# COMPLEX TEST CASES
# Multiple concepts, cross-references, nuanced notation
# =============================================================================

COMPLEX_CASES = [
    WriteTestCase(
        id="complex-multi-concept",
        name="Multiple interrelated concepts",
        complexity=Complexity.COMPLEX,
        task_type=TaskType.CREATE,
        fact_statement=(
            "Education increases earning potential, but the relationship is mediated "
            "by social capital. People from wealthy backgrounds benefit more from "
            "education due to pre-existing networks. This creates a feedback loop "
            "where inequality perpetuates itself across generations."
        ),
        expected=ExpectedStructure(
            required_concepts=["Education", "Social-Capital"],
            required_facets=[".earning", ".inequality"],
            required_operators=["=>", "<>", "&"],  # Causation, mutual, reference
            required_terms=["wealth", "network", "generation", "feedback"],
            min_claims=4,
        ),
        notes="Complex multi-concept with cross-references",
    ),
    WriteTestCase(
        id="complex-supersession",
        name="Belief evolution with supersession",
        complexity=Complexity.COMPLEX,
        task_type=TaskType.UPDATE,
        fact_statement=(
            "I used to believe that willpower is unlimited, but research shows "
            "it depletes with use. Ego depletion is real, and managing energy "
            "is more important than pushing through fatigue."
        ),
        base_content="""Willpower
  .nature
    - unlimited resource
    - mind over matter
""",
        expected=ExpectedStructure(
            required_concepts=["Willpower"],
            required_facets=[".nature", ".depletion"],
            required_operators=["[<="],  # Supersession marker
            required_terms=["deplete", "energy", "fatigue", "ego"],
            min_claims=3,
        ),
        notes="Tests supersession notation for belief evolution",
    ),
    WriteTestCase(
        id="complex-uncertainty",
        name="Uncertain and emphatic claims",
        complexity=Complexity.COMPLEX,
        task_type=TaskType.CREATE,
        fact_statement=(
            "Consciousness is definitely more than just brain activity - this I'm "
            "certain of. But whether it's fundamental to reality or emergent from "
            "complex information processing, I'm genuinely uncertain. The hard problem "
            "of consciousness might be unsolvable."
        ),
        expected=ExpectedStructure(
            required_concepts=["Consciousness"],
            required_facets=[".nature", ".hard-problem"],
            required_operators=["!", "?"],  # Emphatic and uncertain
            required_terms=["brain", "fundamental", "emergent", "unsolvable"],
            forbidden_terms=["definitely fundamental", "definitely emergent"],
            min_claims=3,
        ),
        notes="Tests emphatic and uncertainty modifiers",
    ),
    WriteTestCase(
        id="complex-bidirectional",
        name="Bidirectional causation",
        complexity=Complexity.COMPLEX,
        task_type=TaskType.CREATE,
        fact_statement=(
            "Thoughts influence emotions and emotions influence thoughts in a "
            "continuous feedback loop. Cognitive behavioral therapy leverages this "
            "bidirectional relationship. Changing thought patterns can improve mood, "
            "and mood regulation can lead to clearer thinking."
        ),
        expected=ExpectedStructure(
            required_concepts=["Cognition", "Emotion"],
            required_facets=[".relationship", ".therapy"],
            required_operators=["<>"],  # Bidirectional
            required_terms=["feedback", "thought", "mood", "CBT"],
            min_claims=3,
        ),
        notes="Tests bidirectional relationship notation",
    ),
    WriteTestCase(
        id="complex-full-integration",
        name="Full notation integration",
        complexity=Complexity.COMPLEX,
        task_type=TaskType.APPEND,
        fact_statement=(
            "Power corrupts, but absolute power corrupts absolutely. However, I think "
            "this effect is stronger in individualistic cultures than collectivist ones. "
            "The corruption is caused by reduced accountability and the isolation that "
            "comes with authority. Historical examples like ancient Rome and modern "
            "corporations demonstrate this pattern repeatedly."
        ),
        base_content="""Leadership
  .effectiveness
    - requires trust
    - communication => team-performance
""",
        expected=ExpectedStructure(
            required_concepts=["Leadership", "Power"],
            required_facets=[".corruption", ".accountability"],
            required_operators=["=>", "|", "@", "!"],
            required_terms=["corrupt", "absolute", "accountability", "isolation"],
            min_claims=5,
        ),
        notes="Tests comprehensive notation usage",
    ),
]

# =============================================================================
# ALL TEST CASES
# =============================================================================

ALL_WRITE_CASES = SIMPLE_CASES + MODERATE_CASES + COMPLEX_CASES


def get_cases_by_complexity(complexity: Complexity) -> list[WriteTestCase]:
    """Get all test cases of a specific complexity."""
    return [tc for tc in ALL_WRITE_CASES if tc.complexity == complexity]


def get_cases_by_task_type(task_type: TaskType) -> list[WriteTestCase]:
    """Get all test cases of a specific task type."""
    return [tc for tc in ALL_WRITE_CASES if tc.task_type == task_type]


def get_case_by_id(case_id: str) -> Optional[WriteTestCase]:
    """Get a specific test case by ID."""
    for tc in ALL_WRITE_CASES:
        if tc.id == case_id:
            return tc
    return None
