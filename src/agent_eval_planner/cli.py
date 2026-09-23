# src/agent_eval_planner/cli.py
"""Command‑line interface for **agent‑eval‑planner**.

The gem you referenced provides a binary called ``agent-eval-planner`` that
accepts a spec file and writes a Markdown evaluation plan. This module mimics
that behaviour:

```bash
agent-eval-planner spec.yaml -o evaluation-plan.md
```

If ``-o/--output`` is omitted, the plan is printed to STDOUT.
"""

import argparse
import sys
from pathlib import Path

from .generator import generate_plan


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent-eval-planner",
        description="Generate an evaluation plan for AI agents from a YAML/JSON spec.",
    )
    parser.add_argument(
        "spec",
        help="Path to the specification file (JSON or YAML).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write the generated plan to FILE (default: print to stdout)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="agent-eval-planner 0.1.0",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    try:
        plan = generate_plan(args.spec)
    except Exception as exc:
        sys.stderr.write(f"Error generating plan: {exc}\n")
        sys.exit(1)

    if args.output:
        args.output.write_text(plan, encoding="utf-8")
    else:
        sys.stdout.write(plan)


if __name__ == "__main__":
    main()

