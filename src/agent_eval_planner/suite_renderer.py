"""Renders executable suite.jsonl rows from selected vectors."""

from __future__ import annotations

import hashlib
import json
import re

from .contract_analyzer import ContractAnalyzer
from .models import Vector


class SuiteRenderer:
    """Turns selected vectors into JSONL eval cases."""

    def __init__(self, analyzer: ContractAnalyzer, vectors: list[Vector]) -> None:
        self.analyzer = analyzer
        self.vectors = vectors

    def render(self) -> str:
        """Returns JSONL (one object per line, trailing newline)."""
        lines = [json.dumps(self._row_for(vector), ensure_ascii=False) for vector in self.vectors]
        return "\n".join(lines) + "\n"

    def _row_for(self, vector: Vector) -> dict:
        if self.analyzer.harness == "rd-copilot":
            return self._native_row(vector)
        return self._legacy_row(vector)

    def _legacy_row(self, vector: Vector) -> dict:
        return {
            "id": self._stable_id(vector),
            "input": {
                "target_agent": self.analyzer.agent_name,
                "messages": [{"role": "user", "content": vector.attack_prompt}],
            },
            "expected": self._expectations(vector),
            "metadata": self._metadata(vector, link_field="plan_id"),
        }

    def _native_row(self, vector: Vector) -> dict:
        return {
            "id": self._stable_id(vector),
            "target_component": self.analyzer.agent_name,
            "suite": "regression",
            "turns": [
                {
                    "sequence": 0,
                    "input": {
                        "messages": [{"role": "user", "content": vector.attack_prompt}],
                    },
                    "expectations": {
                        **self._expectations(vector),
                        "source_link": None,
                        "ticket_handoff": False,
                    },
                }
            ],
            "metadata": self._metadata(vector, link_field="vector_id"),
        }

    def _expectations(self, vector: Vector) -> dict:
        return {
            "reference_answer": vector.expected_validation,
            "expected_tools": [],
            "forbidden_tools": self._forbidden_tools_for(vector),
            "refusal": vector.refusal,
        }

    def _metadata(self, vector: Vector, link_field: str) -> dict:
        return {
            "intent": vector.intent,
            "split": vector.split,
            "priority": "high" if vector.severity == "P0" else "medium",
            "tags": vector.tags,
            "requires_live_data": False,
            link_field: vector.id,
        }

    def _forbidden_tools_for(self, vector: Vector) -> list[str]:
        if not self.analyzer.has_tools():
            return []
        return list(self.analyzer.tools)

    def _stable_id(self, vector: Vector) -> str:
        digest = hashlib.sha256(f"{vector.id}:{vector.attack_prompt}".encode("utf-8")).hexdigest()[:8]
        slug = re.sub(r"[^a-z0-9]+", "-", vector.id.lower())
        return f"guardrail-{slug}-{digest}"
