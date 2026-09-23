"""Orchestrates contract analysis, vector selection, and artifact rendering."""

from __future__ import annotations

from typing import Any

from .contract_analyzer import ContractAnalyzer
from .errors import InputError
from .models import PlannerResult
from .plan_renderer import PlanRenderer
from .remediation_renderer import RemediationRenderer
from .suite_renderer import SuiteRenderer
from .vector_catalog import VectorCatalog


class Planner:
    """Coordinates generation of eval plan, JSONL suite, and remediations."""

    DEFAULT_OPTIONS = {
        "team": None,
        "agent_name": None,
        "tools": None,
        "declared_scope": None,
        "out_of_scope": None,
        "harness": "generic",
    }

    def __init__(
        self,
        input_path: str | None = None,
        raw: str | None = None,
        team: str | None = None,
        agent_name: str | None = None,
        tools: list[str] | str | None = None,
        declared_scope: str | None = None,
        out_of_scope: str | None = None,
        harness: str = "generic",
        **options: Any,
    ) -> None:
        self.input_path = input_path
        self.raw = raw
        merged = {**self.DEFAULT_OPTIONS, **options}
        self.options = {
            **merged,
            "team": team if team is not None else merged.get("team"),
            "agent_name": agent_name if agent_name is not None else merged.get("agent_name"),
            "tools": tools if tools is not None else merged.get("tools"),
            "declared_scope": declared_scope
            if declared_scope is not None
            else merged.get("declared_scope"),
            "out_of_scope": out_of_scope if out_of_scope is not None else merged.get("out_of_scope"),
            "harness": harness or merged.get("harness") or "generic",
        }

    def call(self) -> PlannerResult:
        """Runs the pipeline and returns plan, suite, remediations, and metadata."""
        analyzer = ContractAnalyzer(
            source_path=self.input_path,
            raw=self.raw,
            agent_name=self.options.get("agent_name"),
            tools=self.options.get("tools"),
            declared_scope=self.options.get("declared_scope"),
            out_of_scope=self.options.get("out_of_scope"),
            harness=self.options.get("harness") or "generic",
        )
        vectors = VectorCatalog.vectors_for(analyzer)
        if not vectors:
            raise InputError("Nenhum vetor aplicável encontrado.")

        team = self.options.get("team")
        return PlannerResult(
            plan=PlanRenderer(analyzer=analyzer, vectors=vectors, team=team).render(),
            suite=SuiteRenderer(analyzer=analyzer, vectors=vectors).render(),
            remediations=RemediationRenderer(
                analyzer=analyzer, vectors=vectors, team=team
            ).render(),
            analyzer=analyzer,
            vectors=vectors,
        )
