# src/agent_eval_planner/generator.py
"""Core logic for generating evaluation plans.

This mirrors the behavior of the original Ruby gem, providing a lightweight
Python implementation that:

1. Loads a specification file (YAML or JSON).
2. Renders a Markdown template with a title, description, and a table of test
   scenarios derived from the top‑level keys of the spec.
3. Returns the rendered Markdown string.

The implementation uses only the standard library, falling back to ``json`` for
JSON files and optionally ``yaml`` (PyYAML) for YAML files.
"""

import json
from pathlib import Path
from typing import Any, Dict

# Optional import of PyYAML – if the user wants YAML support they can install it.
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def _load_spec(filepath: str) -> Dict[str, Any]:
    """Load a specification file.

    Supported extensions:
    - ``.json`` → parsed with :mod:`json`
    - ``.yaml`` / ``.yml`` → parsed with :mod:`yaml` if available
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Specification file not found: {filepath}")

    text = path.read_text(encoding="utf-8")
    ext = path.suffix.lower()
    if ext == ".json":
        return json.loads(text)
    if ext in {".yaml", ".yml"}:
        if yaml is None:
            raise ImportError(
                "PyYAML is required to parse YAML files – install with 'pip install pyyaml'"
            )
        return yaml.safe_load(text) or {}
    raise ValueError(
        f"Unsupported specification file extension '{ext}'. Use .json, .yaml or .yml"
    )


def _render_markdown(spec: Dict[str, Any]) -> str:
    """Render a simple Markdown plan from *spec*.

    The output follows the same structure as the Ruby gem:
    - Title & description
    - Table of test scenarios (one row per top‑level key)
    - Placeholder for detailed steps & metrics
    """
    title = spec.get("title", "Agent Evaluation Plan")
    description = spec.get("description", "Generated evaluation plan.")

    lines = [
        f"# {title}\n",
        f"_{description}_\n",
        "---\n",
        "## Test Scenarios\n",
        "| Scenario | Detail |\n",
        "|----------|--------|\n",
    ]

    for key, value in spec.items():
        if key in {"title", "description"}:
            continue
        preview = json.dumps(value, ensure_ascii=False)
        if len(preview) > 60:
            preview = preview[:57] + "..."
        lines.append(f"| {key} | {preview} |\n")

    lines.append("\n---\n")
    lines.append("*Add concrete test steps, metrics, and success criteria below.*\n")
    return "".join(lines)


def generate_plan(spec_path: str) -> str:
    """Public API – generate a Markdown evaluation plan from *spec_path*.

    This function is used by the CLI entry point and can also be imported by
    other Python code.
    """
    spec = _load_spec(spec_path)
    return _render_markdown(spec)

