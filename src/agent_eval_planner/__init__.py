"""agent_eval_planner package.

Turns an agent contract into a guardrail evaluation plan, JSONL suite, and remediations.
"""

from __future__ import annotations

from .errors import Error, InputError, ValidationError
from .models import PlannerResult, Vector
from .planner import Planner
from .suite_validator import SuiteValidator
from .version import __version__


def generate(input_path: str | None = None, raw: str | None = None, **options) -> PlannerResult:
    """Generate plan, suite, and remediations from an agent contract."""
    return Planner(input_path=input_path, raw=raw, **options).call()


def generate_plan(input_path: str | None = None, raw: str | None = None, **options) -> str:
    """Generate only the Markdown evaluation plan."""
    return generate(input_path=input_path, raw=raw, **options).plan


def validate_suite(
    path: str,
    known_tools: list[str] | None = None,
    agent_has_no_tools: bool = False,
    bound_tools: list[str] | None = None,
    target_components: list[str] | None = None,
    suites: list[str] | None = None,
    schema: str = "auto",
) -> list[str]:
    """Validate a suite.jsonl file. Returns errors (empty if OK).

    Warnings are not returned. Construct ``SuiteValidator`` when the caller
    needs ``OK WITH WARNINGS`` (catalog tools the target cannot call).
    """
    return SuiteValidator(
        path=path,
        known_tools=known_tools or [],
        bound_tools=bound_tools,
        agent_has_no_tools=agent_has_no_tools,
        target_components=target_components,
        suites=suites,
        schema=schema,
    ).validate()


__all__ = [
    "__version__",
    "generate",
    "generate_plan",
    "validate_suite",
    "Planner",
    "PlannerResult",
    "Vector",
    "SuiteValidator",
    "Error",
    "InputError",
    "ValidationError",
]
