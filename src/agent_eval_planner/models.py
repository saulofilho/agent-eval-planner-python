"""Data models for agent_eval_planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Vector:
    """A guardrail evaluation vector (attack prompt + expected behavior)."""

    id: str
    name: str
    category: str
    category_title: str
    severity: str
    objective: str
    attack_prompt: str
    expected_validation: str
    failure_criteria: str
    intent: str
    tags: list[str] = field(default_factory=list)
    refusal: bool = True
    split: str = "smoke"
    notes: str = ""
    always: bool = False
    triggers: list[str] = field(default_factory=list)


@dataclass
class PlannerResult:
    """Artifacts produced by a planner run."""

    plan: str
    suite: str
    remediations: str
    analyzer: Any
    vectors: list[Vector]
