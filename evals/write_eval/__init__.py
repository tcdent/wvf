"""
Write Evaluation Module

Benchmarks embedding models on their ability to correctly generate
and update Worldview documents using the agent CLI.
"""

from .evaluator import (
    AgentMetrics,
    WriteScore,
    WriteResult,
    WriteSummary,
    evaluate_write,
    summarize_write_results,
)
from .runner import (
    WriteEvalRunner,
    WRITE_MODELS,
    DEFAULT_WRITE_MODELS,
    get_write_model,
    generate_write_report,
    generate_write_json,
)
from .test_cases import (
    Complexity,
    TaskType,
    ExpectedStructure,
    WriteTestCase,
    ALL_WRITE_CASES,
    REJECTION_CASES,
    get_cases_by_complexity,
    get_cases_by_task_type,
    get_case_by_id,
)

__all__ = [
    # Evaluator
    "AgentMetrics",
    "WriteScore",
    "WriteResult",
    "WriteSummary",
    "evaluate_write",
    "summarize_write_results",
    # Runner
    "WriteEvalRunner",
    "WRITE_MODELS",
    "DEFAULT_WRITE_MODELS",
    "get_write_model",
    "generate_write_report",
    "generate_write_json",
    # Test cases
    "Complexity",
    "TaskType",
    "ExpectedStructure",
    "WriteTestCase",
    "ALL_WRITE_CASES",
    "REJECTION_CASES",
    "get_cases_by_complexity",
    "get_cases_by_task_type",
    "get_case_by_id",
]
