# agent-eval-planner

[![PyPI version](https://badge.fury.io/py/agent-eval-planner.svg)](https://badge.fury.io/py/agent-eval-planner)
[![Python Versions](https://img.shields.io/pypi/pyversions/agent-eval-planner.svg)](https://pypi.org/project/agent-eval-planner/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Site:** [saulofilho.github.io/agent-eval-planner-python](https://saulofilho.github.io/agent-eval-planner-python/)

Python library that turns an **agent contract** (system prompt, tools, policy gates) into a guardrail evaluation pipeline:

1. **Action plan** — SCOPE / INJECT / ROLE / PII / TOOL / HALLUC / EXFIL vectors
2. **suite.jsonl** — executable cases with `forbidden_tools` filled
3. **Remediations** — prompt / gate / evaluator quick wins

Sibling of [`security-pentest-planner`](https://github.com/saulofilho/security-pentest-planner-python), applied to LLM agents. Port of the Ruby gem [`agent_eval_planner`](https://github.com/saulofilho/agent-eval-planner).

Canonical smoke test: **carrot cake** (off-topic). If the agent answers with a recipe, its scope is not limited.

## What it does

- Parses agent contracts (Markdown, text, JSON, YAML).
- Generates a Markdown eval plan, a JSONL suite, and remediations.
- Validates suites (hard-fail on empty `forbidden_tools` / leftover placeholders).

## What it does **NOT** do

- Execute the evaluation against a live agent.
- Replace pentest of APIs/infra (use `security-pentest-planner`).

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
# Full pipeline → directory (plan + suite + remediations)
agent-eval-planner agent.md --tools funnel_analytics,open_service_center_ticket \
  -t "Platform Team" -a analytics -o ./out

# Validate suite (hard-fail on empty forbidden_tools / placeholders)
agent-eval-planner validate ./out/suite.jsonl \
  --known-tools funnel_analytics,open_service_center_ticket

# Plan only to stdout
agent-eval-planner agent.md --plan-only --agent analytics
```

### Options

| Flag | Description |
|------|-------------|
| `-t, --team TEAM` | Team name in the document title |
| `-a, --agent NAME` | `target_agent` name |
| `--tools LIST` | Comma-separated real tool names |
| `--scope TEXT` | Declared scope summary |
| `--harness NAME` | `generic` or `marketing-copilot` |
| `-o, --output PATH` | Output directory or single file |
| `--plan-only` / `--suite-only` / `--remediations-only` | Emit a single artifact |
| `-v, --version` | Show version |

## Programmatic usage

```python
import agent_eval_planner

result = agent_eval_planner.generate(
    input_path="agent.md",
    team="Platform Team",
    tools=["funnel_analytics", "open_service_center_ticket"],
)

with open("evaluation-plan.md", "w", encoding="utf-8") as f:
    f.write(result.plan)
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

python -m pip install .
python -m unittest discover -s tests -v
```

## Recommended workflow

```
Agent contract  →  agent-eval-planner  →  Plan + suite.jsonl + remediations
                                                     ↓
                                            Harness / CI execution
                                                     ↓
                                            Failures + remediations
```

## License

MIT — see [LICENSE](LICENSE).
