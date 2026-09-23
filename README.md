# agent-eval-planner

[![PyPI version](https://badge.fury.io/py/agent-eval-planner.svg)](https://badge.fury.io/py/agent-eval-planner)
[![Python Versions](https://img.shields.io/pypi/pyversions/agent-eval-planner.svg)](https://pypi.org/project/agent-eval-planner/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Site:** [saulofilho.github.io/agent-eval-planner-python](https://saulofilho.github.io/agent-eval-planner-python/)

Generates **evaluation plans for AI agents** based on specification files. It helps AI‑engineers design systematic test suites, define metrics, and produce reproducible evaluation reports.

## What it does

- Parses specification files (YAML/JSON) describing agent capabilities, goals, and constraints.
- Generates a structured evaluation plan in Markdown with:
  - Test scenarios and success criteria
  - Metric definitions and aggregation methods
  - Suggested data collection procedures
- Supports custom extensions for tool‑specific assessments (LLM, reinforcement‑learning, tool‑use, etc.).

## What it does **NOT** do

- Execute the evaluation (the generated plan is for manual or CI execution).
- Provide benchmark data or ground‑truth datasets.

## Installation

```bash
pip install agent-eval-planner
```

Or using `uv` / `poetry`:

```bash
uv add agent-eval-planner
# or
poetry add agent-eval-planner
```

## CLI usage

```bash
# Generate plan from a spec file
agent-eval-planner spec.yaml -o evaluation-plan.md
```

### Options

| Flag | Description |
|------|-------------|
| `-o, --output FILE` | Write the generated plan to a file |
| `-v, --version` | Show version |
| `-h, --help` | Show help |

## Programmatic usage

```python
import agent_eval_planner

plan = agent_eval_planner.generate(
    spec_path="spec.yaml",
    include_metrics=True,
)

with open("evaluation-plan.md", "w", encoding="utf-8") as f:
    f.write(plan)
```

## Publish to PyPI

```bash
python -m pip install build twine
python -m build
python -m twine upload dist/*
```

## Development and testing

```bash
git clone https://github.com/saulofilho/agent-eval-planner-python.git
cd agent-eval-planner-python

# Run unit tests
python -m unittest discover -s tests -v
```

## Recommended workflow

```
Spec file  →  agent-eval-planner  →  Evaluation Plan (Markdown)
                                                     ↓
                                            Manual execution / CI
                                                     ↓
                                            Results + analysis
```

## License

MIT — see [LICENSE](LICENSE).

