"""Parses an agent contract (markdown/text/JSON/YAML) into a structured profile."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .errors import InputError

TOOL_LINE_RE = re.compile(
    r"^\s*[-*]\s*`?([a-z][a-z0-9_]*)`?\s*$|"
    r"^\s*[-*]\s*tool[s]?\s*:\s*`?([a-z][a-z0-9_]*)`?|"
    r"^\s*`([a-z][a-z0-9_]*)`\s*[—(]\s*tool",
    re.IGNORECASE | re.MULTILINE,
)
TOOLS_INLINE_RE = re.compile(r"tools?\s*[:=]\s*\[([^\]]+)\]", re.IGNORECASE)
NAME_RE = re.compile(
    r"(?:agent(?:[_\s]name)?|specialist|target[_ ]?agent)\s*[:=]\s*[\"']?([A-Za-z0-9_\-./]+)[\"']?",
    re.IGNORECASE,
)
SCOPE_RE = re.compile(r"escopo(?:\s+declarado)?\s*[:=]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
HEADING_RE = re.compile(r"^#+\s*(.+)$", re.MULTILINE)


class ContractAnalyzer:
    """Parses an agent contract file into a structured profile."""

    def __init__(
        self,
        source_path: str | None = None,
        raw: str | None = None,
        agent_name: str | None = None,
        tools: list[str] | str | None = None,
        declared_scope: str | None = None,
        out_of_scope: str | None = None,
        harness: str = "generic",
    ) -> None:
        self.source_path = source_path
        self.raw = raw if raw is not None else self._read_source(source_path)
        self.agent_name = agent_name or self._extract_agent_name() or "default"
        self.tools = self._normalize_tools(tools if tools is not None else self._extract_tools())
        self.declared_scope = (
            declared_scope or self._extract_scope_hint() or "Escopo declarado no contrato do agente"
        )
        self.out_of_scope = out_of_scope or (
            "Pedidos off-topic, assistente geral, conteúdo fora do domínio"
        )
        self.harness = harness or "generic"
        self.signals = self._detect_signals()

    def has_tools(self) -> bool:
        """Returns True when the contract declares at least one tool."""
        return bool(self.tools)

    def multi_specialist(self) -> bool:
        """Returns True when the contract looks like a multi-agent setup."""
        return bool(self.signals.get("multi_specialist"))

    def analytics_domain(self) -> bool:
        """Returns True when the contract mentions analytics/metrics."""
        return bool(self.signals.get("analytics"))

    def introduction(self) -> str:
        """Short introduction used in the generated plan."""
        parts = [f"Agente **{self.agent_name}**"]
        if self.has_tools():
            parts.append(f"com {len(self.tools)} tool(s) no contrato")
        else:
            parts.append("sem tools declaradas")
        parts.append(f"(harness: {self.harness})")
        return (
            f"{' '.join(parts)}. Pipeline de eval de guardrails — paralelo do plano de "
            "pentest de API, aplicado a comportamento de LLM."
        )

    def _read_source(self, path: str | None) -> str:
        if not path:
            raise InputError("input_path é obrigatório quando raw não é informado.")
        source = Path(path)
        if not source.is_file():
            raise InputError(f"Arquivo não encontrado: {path}")
        return source.read_text(encoding="utf-8")

    def _normalize_tools(self, lst: list[str] | str | None) -> list[str]:
        if lst is None:
            return []
        items = lst if isinstance(lst, list) else [lst]
        found: list[str] = []
        for item in items:
            found.extend(part.strip() for part in str(item).split(","))
        unique: list[str] = []
        seen: set[str] = set()
        for name in found:
            if name and name not in seen:
                seen.add(name)
                unique.append(name)
        return unique

    def _extract_tools(self) -> list[str]:
        from_structured = self._tools_from_structured()
        if from_structured:
            return from_structured

        found: list[str] = []
        for match in TOOLS_INLINE_RE.finditer(self.raw):
            found.extend(
                part.strip().strip("\"'`") for part in re.split(r"[,\s]+", match.group(1))
            )
        for match in TOOL_LINE_RE.finditer(self.raw):
            found.append(next(g for g in match.groups() if g))
        return found

    def _tools_from_structured(self) -> list[str]:
        data = self._parse_structured()
        if not isinstance(data, dict):
            return []
        agent = data.get("agent")
        candidates = (
            data.get("tools")
            or data.get("agent_tools")
            or (agent.get("tools") if isinstance(agent, dict) else None)
            or []
        )
        if not isinstance(candidates, list):
            candidates = [candidates]
        return [str(item) for item in candidates]

    def _parse_structured(self) -> dict[str, Any] | None:
        if not self.raw or not self.raw.strip():
            return None
        path = self.source_path or ""
        stripped = self.raw.strip()
        try:
            if path.endswith(".json") or stripped.startswith("{"):
                parsed = json.loads(self.raw)
                return parsed if isinstance(parsed, dict) else None
            if re.search(r"\.(ya?ml)$", path, re.IGNORECASE):
                parsed = yaml.safe_load(self.raw)
                return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
        return None

    def _extract_agent_name(self) -> str | None:
        data = self._parse_structured()
        if isinstance(data, dict):
            agent = data.get("agent")
            name = (
                data.get("agent_name")
                or data.get("target_agent")
                or data.get("name")
                or (agent.get("name") if isinstance(agent, dict) else None)
            )
            if name:
                return str(name)
        match = NAME_RE.search(self.raw)
        return match.group(1) if match else None

    def _extract_scope_hint(self) -> str | None:
        match = SCOPE_RE.search(self.raw)
        if match:
            return match.group(1).strip()
        heading = HEADING_RE.search(self.raw)
        if heading:
            return heading.group(1).strip()
        return None

    def _detect_signals(self) -> dict[str, bool]:
        down = self.raw.lower()
        return {
            "has_tools": self.has_tools(),
            "multi_specialist": bool(
                re.search(r"specialist|orchestrator|handoff|multi[- ]?agent", down)
            ),
            "analytics": bool(
                re.search(r"analytics|métrica|metrica|funnel|abertura|convers[aã]o|bigquery", down)
            ),
            "docs": bool(re.search(r"docs?|help.?center|conhecimento|rag|retrieval", down)),
            "mutable_tools": any(
                re.search(r"ticket|delete|create|update|write|send|open_", tool, re.IGNORECASE)
                for tool in self.tools
            ),
            "pii_surface": bool(re.search(r"pii|cpf|email|tenant|cliente|customer", down)),
        }
