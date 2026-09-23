"""Renders the Markdown evaluation action plan."""

from __future__ import annotations

from .contract_analyzer import ContractAnalyzer
from .models import Vector
from .vector_catalog import CATEGORY_TITLES

CATEGORY_ORDER = ["SCOPE", "INJECT", "ROLE", "PII", "TOOL", "HALLUC", "EXFIL"]


class PlanRenderer:
    """Renders a Markdown eval action plan from analyzer + selected vectors."""

    def __init__(
        self,
        analyzer: ContractAnalyzer,
        vectors: list[Vector],
        team: str | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.vectors = vectors
        self.team = team or "TIME"

    def render(self) -> str:
        """Returns the full Markdown plan."""
        sections = [
            self._header(),
            self._introduction(),
            self._eval_sections(),
            self._summary_table(),
            self._recommendations(),
            self._out_of_scope(),
        ]
        return "\n\n".join(section for section in sections if section) + "\n"

    def _header(self) -> str:
        return f"# {self.team} — Plano de Ação de Eval de Agente"

    def _introduction(self) -> str:
        tools = (
            "_(nenhuma)_"
            if not self.analyzer.tools
            else ", ".join(f"`{tool}`" for tool in self.analyzer.tools)
        )
        source = self.analyzer.source_path or "inline"
        return (
            "## Introdução\n\n"
            f"{self.analyzer.introduction()}\n\n"
            f"**Agente(s) em escopo:** {self.analyzer.agent_name}\n\n"
            f"**Contrato analisado:** `{source}`\n\n"
            f"**Harness alvo:** {self.analyzer.harness}\n\n"
            f"**Escopo declarado (resumo):** {self.analyzer.declared_scope}\n\n"
            f"**Fora de escopo declarado:** {self.analyzer.out_of_scope}\n\n"
            f"**Tools / capabilities:** {tools}"
        )

    def _eval_sections(self) -> str:
        grouped: dict[str, list[Vector]] = {}
        for vector in self.vectors:
            grouped.setdefault(vector.category, []).append(vector)

        blocks: list[str] = []
        for category in CATEGORY_ORDER:
            items = grouped.get(category)
            if not items:
                continue
            title = CATEGORY_TITLES.get(category, category)
            body = "\n\n".join(self._render_vector(vector) for vector in items)
            blocks.append(f"## EVAL — {title}\n\n{body}")
        return "\n\n---\n\n".join(blocks)

    def _render_vector(self, vector: Vector) -> str:
        notes = vector.notes if vector.notes else "—"
        return (
            f"#### {vector.id} — {vector.name}\n\n"
            f"- **Severidade:** {vector.severity}\n"
            f"- **Objetivo:** {vector.objective}\n"
            "- **Prompt de ataque:**\n"
            "  ```text\n"
            f"  {vector.attack_prompt}\n"
            "  ```\n"
            f"- **Validação esperada:** {vector.expected_validation}\n"
            f"- **Critério de falha:** {vector.failure_criteria}\n"
            f"- **Observação:** {notes}"
        )

    def _summary_table(self) -> str:
        rows = [
            f"| {v.id} | {v.category} | {v.severity} | {v.name} | {v.failure_criteria} |"
            for v in self.vectors
        ]
        return (
            "## Tabela de resumo\n\n"
            "| ID | Categoria | Severidade | Vetor | Falha se |\n"
            "|----|-----------|------------|-------|----------|\n"
            + "\n".join(rows)
            + "\n\n"
            "**Prioridade de execução:** SCOPE → INJECT → ROLE → PII → TOOL → HALLUC → EXFIL"
        )

    def _recommendations(self) -> str:
        tips = [
            "Rodar smoke pack (SCOPE-01, INJECT-01, ROLE-01) no harness antes de expandir a suite.",
            "Preencher `forbidden_tools` com as tools reais do agente — suite com lista vazia em refusal é falso verde.",
            "Preferir policy gate determinístico para off-topic previsível; o modelo sozinho não basta.",
        ]
        if self.analyzer.multi_specialist():
            tips.append(
                "Validar handoff entre specialists (SCOPE-04) — orchestrator detectado no contrato."
            )
        if self.analyzer.analytics_domain():
            tips.append(
                "Cobrir grounding de métricas (HALLUC-01) com tool obrigatória ou recusa explícita."
            )
        body = "\n".join(f"{index}. {tip}" for index, tip in enumerate(tips, start=1))
        return f"## Recomendações imediatas\n\n{body}"

    def _out_of_scope(self) -> str:
        return (
            "## Fora do escopo deste plano\n\n"
            "- Pentest de API/infra (usar `security_pentest_planner`)\n"
            "- Journeys de UI / synthetics de browser\n"
            "- Modelo de ameaça corporativo completo"
        )
