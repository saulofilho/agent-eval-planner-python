"""Hard-fail validator for suite JSONL.

Accepts the legacy row (`input` / `expected`) and the
native row (`target_component` / `turns` / `suite`).

Hard-fail rules:
- Remaining {{PLACEHOLDER}} tokens anywhere in the file
- Duplicate ids, or ids the stable-id regex would reject
- A refusal turn, or a turn tagged as a guardrail, whose forbidden_tools
  name none of the tools that target can call
- Native guardrail metadata on the row when no turn forbids such a tool
- forbidden_tools or expected_tools outside the allowlist
- expected_tools outside the tools bound to the target agent
- refusal true combined with a non-empty expected_tools on the same turn
- Native rows with a bad suite, target component, or turn sequence
- Mixed legacy and native rows in one file

Warnings (still fix or justify before delivery):
- forbidden_tools names a catalog tool the target agent cannot call.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import InputError, ValidationError

PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

GUARDRAIL_INTENTS = frozenset(
    {
        "out_of_scope_refusal",
        "prompt_injection",
        "role_escape",
        "prompt_exfiltration",
        "pii_probe",
    }
)
GUARDRAIL_TAGS = frozenset(
    {"scope", "injection", "role", "exfil", "pii", "guardrail"}
)
DEFAULT_SUITES = frozenset(
    {
        "golden",
        "regression",
        "routing",
        "calibration",
        "production-sample",
    }
)
SCHEMAS = frozenset({"auto", "legacy", "native"})

_Row = dict[str, Any]
_Block = tuple[str, _Row, bool]
_Blocks = list[_Block]


def _clean_names(names: list[str] | None) -> list[str]:
    if not names:
        return []
    return [str(name) for name in names if str(name)]


def _is_guardrail_metadata(metadata: dict[str, Any]) -> bool:
    intent = metadata.get("intent") or ""
    if intent in GUARDRAIL_INTENTS:
        return True
    tags = set(metadata.get("tags") or [])
    return bool(tags & GUARDRAIL_TAGS)


def _placeholder_errors(raw: str) -> list[str]:
    matches = PLACEHOLDER_RE.findall(raw)
    if not matches:
        return []
    found = sorted(set(matches))
    return [f"placeholders remaining (must be replaced before delivery): {found}"]


def _cli_mode_errors(
    known: list[str],
    bound: list[str],
    empty: bool,
) -> list[str]:
    if empty and (known or bound):
        return ["pass either --agent-has-no-tools OR tool flags, not both"]
    if not empty and not known and not bound:
        return [
            "agent tool inventory required: pass --bound-tools a,b "
            "(and --known-tools when the product catalog is wider) "
            "or --agent-has-no-tools if the agent truly has no tools"
        ]
    if bound and known and not set(bound) <= set(known):
        extra = sorted(set(bound) - set(known))
        return [f"--bound-tools must be a subset of --known-tools; extra: {extra}"]
    return []


def _load_row(line: str, line_no: int) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as exc:
        return None, [f"line {line_no}: invalid JSON ({exc.msg})"]
    if not isinstance(row, dict):
        return None, [f"line {line_no}: row must be a JSON object"]
    return row, []


def _row_schema(row: dict[str, Any]) -> str:
    native = "turns" in row or "target_component" in row or "suite" in row
    legacy = "input" in row or "expected" in row
    if native and legacy:
        return "mixed"
    if native:
        return "native"
    return "legacy"


def _row_id_errors(
    row: dict[str, Any], line_no: int, seen_ids: set[str]
) -> tuple[str | None, list[str]]:
    row_id = row.get("id")
    if not row_id:
        return None, [f"line {line_no}: missing id"]
    row_id_str = str(row_id)
    errors: list[str] = []
    if not ID_RE.fullmatch(row_id_str):
        errors.append(
            f"line {line_no}: id {row_id!r} must match "
            "[A-Za-z0-9][A-Za-z0-9._:-]* (stable id)"
        )
    if row_id_str in seen_ids:
        errors.append(f"line {line_no}: duplicate id {row_id!r}")
    seen_ids.add(row_id_str)
    return row_id_str, errors


def _name_list(
    expectations: dict[str, Any], row_id: str, field_name: str
) -> tuple[list[Any] | None, list[str]]:
    names = expectations.get(field_name)
    if names is None:
        if field_name == "forbidden_tools":
            return None, [f"{row_id}: missing {field_name}"]
        return [], []
    if not isinstance(names, list):
        return None, [f"{row_id}: {field_name} must be a list"]
    return names, []


def _one_turn(
    row_id: str, index: int, turn: Any
) -> tuple[_Block | None, int | None, list[str]]:
    label = f"turns[{index}].expectations"
    if not isinstance(turn, dict):
        return None, None, [f"{row_id}: {label} turn must be an object"]
    errors: list[str] = []
    sequence = turn.get("sequence")
    recorded = sequence if isinstance(sequence, int) and not isinstance(sequence, bool) else None
    if recorded is None:
        errors.append(f"{row_id}: turns[{index}].sequence must be an int")
    expectations = turn.get("expectations")
    if not isinstance(expectations, dict):
        errors.append(f"{row_id}: missing {label}")
        return None, recorded, errors
    turn_meta = turn.get("metadata") if isinstance(turn.get("metadata"), dict) else {}
    own_guardrail = _is_guardrail_metadata(turn_meta) or expectations.get("refusal") is True
    return (label, expectations, own_guardrail), recorded, errors


def _native_blocks(row_id: str, turns: list[Any]) -> tuple[_Blocks, list[str]]:
    blocks: _Blocks = []
    errors: list[str] = []
    sequences: list[int] = []
    for index, turn in enumerate(turns):
        block, sequence, turn_errors = _one_turn(row_id, index, turn)
        errors.extend(turn_errors)
        if sequence is not None:
            sequences.append(sequence)
        if block is not None:
            blocks.append(block)
    if sequences and sequences != list(range(len(sequences))):
        errors.append(
            f"{row_id}: turn sequence must be contiguous from 0; got {sequences}"
        )
    return blocks, errors


def _expectation_blocks(
    row: dict[str, Any], row_id: str, schema: str
) -> tuple[_Blocks, list[str]]:
    if schema == "legacy":
        expected = row.get("expected")
        if not isinstance(expected, dict):
            return [], [f"{row_id}: missing expected object"]
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        own_guardrail = _is_guardrail_metadata(metadata) or expected.get("refusal") is True
        return [("expected", expected, own_guardrail)], []

    turns = row.get("turns")
    if not isinstance(turns, list) or not turns:
        return [], [f"{row_id}: native row requires a non-empty turns list"]
    return _native_blocks(row_id, turns)


def _native_shape_errors(
    row: dict[str, Any],
    row_id: str,
    *,
    target_components: set[str],
    suites: set[str],
) -> list[str]:
    errors: list[str] = []
    component = row.get("target_component")
    if not isinstance(component, str) or not component:
        errors.append(f"{row_id}: native row requires target_component")
    elif target_components and component not in target_components:
        errors.append(
            f"{row_id}: target_component {component!r} not in "
            f"--target-components {sorted(target_components)}"
        )
    suite = row.get("suite")
    if not isinstance(suite, str) or not suite:
        errors.append(f"{row_id}: native row requires suite")
    elif suite not in suites:
        errors.append(f"{row_id}: suite {suite!r} not in {sorted(suites)}")
    return errors


def _legacy_component_errors(
    row: dict[str, Any], row_id: str, target_components: set[str]
) -> list[str]:
    if not target_components:
        return []
    target_input = row.get("input")
    if not isinstance(target_input, dict):
        return [f"{row_id}: missing input.target_agent"]
    component = target_input.get("target_agent")
    if component not in target_components:
        return [
            f"{row_id}: target_agent {component!r} not in "
            f"--target-components {sorted(target_components)}"
        ]
    return []


def _forbids_bound(expectations: dict[str, Any], bound: set[str]) -> bool:
    listed = expectations.get("forbidden_tools")
    if not isinstance(listed, list):
        return False
    return any(name in bound for name in listed)


def _row_guardrail_gap(
    row: dict[str, Any],
    row_id: str,
    schema: str,
    blocks: _Blocks,
    inventory: _Inventory,
) -> list[str]:
    if schema != "native" or inventory.agent_has_no_tools:
        return []
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    if not _is_guardrail_metadata(metadata):
        return []
    if any(_forbids_bound(expectations, inventory.bound) for _, expectations, _ in blocks):
        return []
    return [
        f"{row_id}: HARD FAIL - guardrail metadata requires at least one turn "
        "to forbid a tool this target can call"
    ]


def _placeholder_names(row_id: str, field_name: str, names: list[Any]) -> list[str]:
    return [
        f"{row_id}: placeholder left in {field_name}: {name!r}"
        for name in names
        if PLACEHOLDER_RE.search(str(name))
    ]


@dataclass(frozen=True)
class SuiteCheck:
    """Inputs for one validate_file() call."""

    known_tools: list[str] = field(default_factory=list)
    bound_tools: list[str] | None = None
    agent_has_no_tools: bool = False
    target_components: list[str] | None = None
    suites: list[str] | None = None
    schema: str = "auto"


@dataclass(frozen=True)
class _Inventory:
    known: set[str]
    bound: set[str]
    bound_explicit: bool
    agent_has_no_tools: bool


@dataclass(frozen=True)
class _BoundQuery:
    where: str
    expectations: dict[str, Any]
    forbidden: list[Any]
    expected: list[Any]
    inventory: _Inventory
    guardrail: bool


@dataclass
class _Run:
    errors: list[str]
    warnings: list[str]
    seen_ids: set[str]
    seen_schemas: set[str]
    inventory: _Inventory
    allowed_components: set[str]
    allowed_suites: set[str]
    schema: str


def _findings_when_empty(
    where: str, forbidden: list[Any], expected: list[Any]
) -> list[str]:
    if not forbidden and not expected:
        return []
    return [
        f"{where}: agent-has-no-tools but tools were listed "
        f"(forbidden={forbidden!r}, expected={expected!r})"
    ]


def _unknown_name_findings(
    where: str, forbidden: list[Any], expected: list[Any], known: set[str]
) -> list[str]:
    findings: list[str] = []
    unknown_forbidden = [name for name in forbidden if name not in known]
    unknown_expected = [name for name in expected if name not in known]
    if unknown_forbidden:
        findings.append(
            f"{where}: forbidden_tools not in --known-tools: {unknown_forbidden}"
        )
    if unknown_expected:
        findings.append(
            f"{where}: expected_tools not in --known-tools: {unknown_expected}"
        )
    return findings


def _bound_findings(query: _BoundQuery) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    inventory = query.inventory
    outside_bound = [name for name in query.expected if name not in inventory.bound]
    if outside_bound:
        errors.append(
            f"{query.where}: expected_tools not bound to this target: {outside_bound}"
        )
    if query.expectations.get("refusal") is True and query.expected:
        errors.append(
            f"{query.where}: refusal true cannot require "
            f"expected_tools={query.expected!r}"
        )
    if query.guardrail and not any(name in inventory.bound for name in query.forbidden):
        errors.append(
            f"{query.where}: HARD FAIL - guardrail/refusal forbids no tool this "
            "target can call; suite cannot detect tool abuse"
        )
    warnings: list[str] = []
    if inventory.bound_explicit:
        unbound = [
            name
            for name in query.forbidden
            if name in inventory.known and name not in inventory.bound
        ]
        if unbound:
            warnings.append(
                f"{query.where}: WARN - forbidden_tools names tools this target "
                f"cannot call (assertion observes nothing): {unbound}"
            )
    return errors, warnings


def _errors_for_expectations(
    where: str,
    expectations: dict[str, Any],
    guardrail: bool,
    inventory: _Inventory,
) -> tuple[list[str], list[str]]:
    forbidden, errors = _name_list(expectations, where, "forbidden_tools")
    expected, expected_errors = _name_list(expectations, where, "expected_tools")
    errors.extend(expected_errors)
    if forbidden is None or expected is None:
        return errors, []
    errors.extend(_placeholder_names(where, "forbidden_tools", forbidden))
    errors.extend(_placeholder_names(where, "expected_tools", expected))
    if inventory.agent_has_no_tools:
        listed = _findings_when_empty(where, forbidden, expected)
        return errors + listed, []
    errors.extend(_unknown_name_findings(where, forbidden, expected, inventory.known))
    bound_errors, warnings = _bound_findings(
        _BoundQuery(
            where=where,
            expectations=expectations,
            forbidden=forbidden,
            expected=expected,
            inventory=inventory,
            guardrail=guardrail,
        )
    )
    return errors + bound_errors, warnings


def _inventory_for(check: SuiteCheck) -> _Inventory:
    bound_list = list(check.bound_tools or [])
    known = set(check.known_tools or bound_list)
    bound = set(bound_list or check.known_tools)
    separated = bool(
        bound_list and check.known_tools and set(bound_list) < set(check.known_tools)
    )
    return _Inventory(
        known=known,
        bound=bound,
        bound_explicit=separated,
        agent_has_no_tools=check.agent_has_no_tools,
    )


def _reject_schema(run: _Run, line_no: int, row_schema: str) -> bool:
    if row_schema == "mixed":
        run.errors.append(
            f"line {line_no}: row mixes legacy input/expected with native turns"
        )
        return True
    if run.schema != "auto" and row_schema != run.schema:
        run.errors.append(
            f"line {line_no}: expected --schema {run.schema}, found {row_schema}"
        )
        return True
    run.seen_schemas.add(row_schema)
    return False


def _append_shape_errors(run: _Run, row: dict[str, Any], row_id: str, row_schema: str) -> None:
    if row_schema == "native":
        run.errors.extend(
            _native_shape_errors(
                row,
                row_id,
                target_components=run.allowed_components,
                suites=run.allowed_suites,
            )
        )
        return
    run.errors.extend(_legacy_component_errors(row, row_id, run.allowed_components))


def _append_expectation_findings(
    run: _Run, row: dict[str, Any], row_id: str, row_schema: str
) -> None:
    blocks, block_errors = _expectation_blocks(row, row_id, row_schema)
    run.errors.extend(block_errors)
    for label, expectations, own_guardrail in blocks:
        block_errors, block_warnings = _errors_for_expectations(
            f"{row_id} {label}", expectations, own_guardrail, run.inventory
        )
        run.errors.extend(block_errors)
        run.warnings.extend(block_warnings)
    run.errors.extend(
        _row_guardrail_gap(row, row_id, row_schema, blocks, run.inventory)
    )


def _collect_row(run: _Run, row: dict[str, Any], line_no: int) -> None:
    row_schema = _row_schema(row)
    if _reject_schema(run, line_no, row_schema):
        return
    row_id, id_errors = _row_id_errors(row, line_no, run.seen_ids)
    run.errors.extend(id_errors)
    if row_id is None:
        return
    _append_shape_errors(run, row, row_id, row_schema)
    _append_expectation_findings(run, row, row_id, row_schema)


def _mixed_schema_error(seen_schemas: set[str]) -> list[str]:
    if len(seen_schemas) < 2:
        return []
    names = ", ".join(sorted(seen_schemas))
    return [
        "mixed suite schemas in one file: "
        f"{names}. Split legacy rows from native rows."
    ]


def validate_file(path: Path, check: SuiteCheck) -> tuple[list[str], list[str]]:
    """Validates a JSONL file. Returns (errors, warnings)."""
    raw = path.read_text(encoding="utf-8")
    bound_list = list(check.bound_tools or [])
    mode_errors = _cli_mode_errors(check.known_tools, bound_list, check.agent_has_no_tools)
    if check.schema not in SCHEMAS:
        mode_errors.append(f"--schema must be auto, legacy, or native; got {check.schema!r}")
    run = _Run(
        errors=_placeholder_errors(raw) + mode_errors,
        warnings=[],
        seen_ids=set(),
        seen_schemas=set(),
        inventory=_inventory_for(check),
        allowed_components=set(check.target_components or []),
        allowed_suites=set(check.suites or DEFAULT_SUITES),
        schema=check.schema if check.schema in SCHEMAS else "auto",
    )
    for line_no, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        row, load_errors = _load_row(stripped, line_no)
        if row is None:
            run.errors.extend(load_errors)
            continue
        _collect_row(run, row, line_no)
    run.errors.extend(_mixed_schema_error(run.seen_schemas))
    return run.errors, run.warnings


class SuiteValidator:
    """Validates a generated (or hand-edited) suite.jsonl file."""

    def __init__(
        self,
        path: str,
        known_tools: list[str] | None = None,
        bound_tools: list[str] | None = None,
        agent_has_no_tools: bool = False,
        target_components: list[str] | None = None,
        suites: list[str] | None = None,
        schema: str = "auto",
    ) -> None:
        self.path = path
        cleaned_bound = _clean_names(bound_tools)
        self.check = SuiteCheck(
            known_tools=_clean_names(known_tools),
            bound_tools=cleaned_bound or None,
            agent_has_no_tools=agent_has_no_tools,
            target_components=_clean_names(target_components) or None,
            suites=_clean_names(suites) or None,
            schema=schema,
        )
        self.warnings: list[str] = []

    def validate_raise(self) -> bool:
        """Raises ValidationError when the suite is invalid."""
        errors = self.validate()
        if errors:
            raise ValidationError("\n".join(errors))
        return True

    def validate(self) -> list[str]:
        """Returns validation errors. Warnings land on ``self.warnings``."""
        source = Path(self.path)
        if not source.is_file():
            raise InputError(f"Arquivo não encontrado: {self.path}")
        errors, warnings = validate_file(source, self.check)
        self.warnings = warnings
        return errors
