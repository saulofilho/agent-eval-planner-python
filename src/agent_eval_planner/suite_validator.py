"""Hard-fail validator for suite JSONL."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import InputError, ValidationError

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
GUARDRAIL_INTENTS = {
    "out_of_scope_refusal",
    "prompt_injection",
    "role_escape",
    "prompt_exfiltration",
    "pii_probe",
}
GUARDRAIL_TAGS = {"scope", "injection", "role", "exfil", "pii", "guardrail"}


class SuiteValidator:
    """Validates a generated (or hand-edited) suite.jsonl file."""

    def __init__(
        self,
        path: str,
        known_tools: list[str] | None = None,
        agent_has_no_tools: bool = False,
    ) -> None:
        self.path = path
        self.known_tools = [str(tool) for tool in (known_tools or []) if str(tool)]
        self.agent_has_no_tools = agent_has_no_tools

    def validate_raise(self) -> bool:
        """Raises ValidationError when the suite is invalid."""
        errors = self.validate()
        if errors:
            raise ValidationError("\n".join(errors))
        return True

    def validate(self) -> list[str]:
        """Returns a list of validation errors (empty if OK)."""
        source = Path(self.path)
        if not source.is_file():
            raise InputError(f"Arquivo não encontrado: {self.path}")

        raw = source.read_text(encoding="utf-8")
        errors = self._placeholder_errors(raw) + self._mode_errors()
        known = set(self.known_tools)
        seen_ids: dict[str, bool] = {}

        for line_no, line in enumerate(raw.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row, load_errors = self._load_row(stripped, line_no)
            if row is None:
                errors.extend(load_errors)
                continue
            row_id, id_errors = self._row_id_errors(row, line_no, seen_ids)
            errors.extend(id_errors)
            if row_id is None:
                continue
            errors.extend(self._errors_for_row(row, row_id, known=known))

        return errors

    def _placeholder_errors(self, raw: str) -> list[str]:
        matches = sorted(set(PLACEHOLDER_RE.findall(raw)))
        if not matches:
            return []
        return [f"placeholders remaining (must be replaced before delivery): {matches}"]

    def _mode_errors(self) -> list[str]:
        if self.agent_has_no_tools and self.known_tools:
            return ["pass either --agent-has-no-tools OR --known-tools, not both"]
        if not self.agent_has_no_tools and not self.known_tools:
            return [
                "agent tool inventory required: pass --known-tools a,b,c "
                "or --agent-has-no-tools if the agent truly has no tools"
            ]
        return []

    def _load_row(self, line: str, line_no: int) -> tuple[dict | None, list[str]]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            return None, [f"line {line_no}: invalid JSON ({exc.msg})"]
        if not isinstance(row, dict):
            return None, [f"line {line_no}: row must be a JSON object"]
        return row, []

    def _row_id_errors(
        self, row: dict, line_no: int, seen_ids: dict[str, bool]
    ) -> tuple[str | None, list[str]]:
        row_id = row.get("id")
        if row_id is None or str(row_id) == "":
            return None, [f"line {line_no}: missing id"]
        row_id_str = str(row_id)
        errors: list[str] = []
        if seen_ids.get(row_id_str):
            errors.append(f"line {line_no}: duplicate id {row_id!r}")
        seen_ids[row_id_str] = True
        return row_id_str, errors

    def _errors_for_row(self, row: dict, row_id: str, known: set[str]) -> list[str]:
        forbidden, errors = self._forbidden_tools(row, row_id)
        if forbidden is None:
            return errors
        if self.agent_has_no_tools:
            return errors + self._no_tools_mode_errors(row_id, forbidden)
        return (
            errors
            + self._empty_guardrail_forbidden_errors(row, row_id, forbidden)
            + self._unknown_tools_errors(row_id, forbidden, known)
            + self._placeholder_tools_errors(row_id, forbidden)
        )

    def _forbidden_tools(self, row: dict, row_id: str) -> tuple[list | None, list[str]]:
        expected = row.get("expected") or {}
        forbidden = expected.get("forbidden_tools")
        if forbidden is None:
            return None, [f"{row_id}: missing expected.forbidden_tools"]
        if not isinstance(forbidden, list):
            return None, [f"{row_id}: forbidden_tools must be a list"]
        return forbidden, []

    def _no_tools_mode_errors(self, row_id: str, forbidden: list) -> list[str]:
        if not forbidden:
            return []
        return [f"{row_id}: agent-has-no-tools but forbidden_tools={forbidden!r}"]

    def _unknown_tools_errors(self, row_id: str, forbidden: list, known: set[str]) -> list[str]:
        unknown = [tool for tool in forbidden if str(tool) not in known]
        if not unknown:
            return []
        return [f"{row_id}: forbidden_tools not in --known-tools: {unknown}"]

    def _placeholder_tools_errors(self, row_id: str, forbidden: list) -> list[str]:
        errors = []
        for tool in forbidden:
            if PLACEHOLDER_RE.search(str(tool)):
                errors.append(f"{row_id}: placeholder left in forbidden_tools: {tool!r}")
        return errors

    def _empty_guardrail_forbidden_errors(
        self, row: dict, row_id: str, forbidden: list
    ) -> list[str]:
        if not self._guardrail_row(row) or forbidden:
            return []
        return [
            f"{row_id}: HARD FAIL — guardrail/refusal row has "
            "forbidden_tools=[] while agent has tools; suite cannot "
            "detect tool abuse (false sense of safety)"
        ]

    def _guardrail_row(self, row: dict) -> bool:
        expected = row.get("expected") or {}
        metadata = row.get("metadata") or {}
        if expected.get("refusal") is True:
            return True
        if str(metadata.get("intent") or "") in GUARDRAIL_INTENTS:
            return True
        tags = [str(tag) for tag in (metadata.get("tags") or [])]
        return bool(set(tags) & GUARDRAIL_TAGS)
