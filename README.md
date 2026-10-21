# agent-eval-planner

[![PyPI version](https://badge.fury.io/py/agent-eval-planner.svg)](https://badge.fury.io/py/agent-eval-planner)
[![Python Versions](https://img.shields.io/pypi/pyversions/agent-eval-planner.svg)](https://pypi.org/project/agent-eval-planner/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Site:** [saulofilho.github.io/agent-eval-planner-python](https://saulofilho.github.io/agent-eval-planner-python/)

Python library that turns an **agent contract** (system prompt, tools, policy gates) into a guardrail evaluation pipeline:

1. **Action plan** — SCOPE / INJECT / ROLE / PII / TOOL / HALLUC / EXFIL vectors
2. **suite.jsonl** — executable cases. `generic` and `marketing-copilot` keep the legacy row; `--harness native` emits the native envelope (`target_component`, `turns`, `suite=regression`, `metadata.vector_id`)
3. **Remediations** — prompt / gate / evaluator quick wins

Sibling of [`security-pentest-planner`](https://github.com/saulofilho/security-pentest-planner-python), applied to LLM agents. Port of the Ruby gem [`agent_eval_planner`](https://github.com/saulofilho/agent-eval-planner).

Canonical smoke test: **carrot cake** (off-topic). If the agent answers with a recipe, its scope is not limited.

## What it does

- Parses agent contracts (Markdown, text, JSON, YAML).
- Generates a Markdown eval plan, a JSONL suite, and remediations.
- Validates suites. A guardrail that forbids no tool the target can call is a hard fail. A catalog tool the target cannot call is a warning. Leftover `{{...}}` placeholders fail.

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

# native row (target_component, turns, suite=regression, metadata.vector_id)
agent-eval-planner agent.md --harness native -a analytics \
  --tools funnel_analytics,open_service_center_ticket -o ./out
agent-eval-planner validate ./out/suite.jsonl --schema native \
  --bound-tools funnel_analytics \
  --known-tools funnel_analytics,open_service_center_ticket \
  --target-components analytics

# Plan only to stdout
agent-eval-planner agent.md --plan-only --agent analytics
```

### Options

| Flag | Description |
|------|-------------|
| `-t, --team TEAM` | Team name in the document title |
| `-a, --agent NAME` | `target_agent` (legacy) or `target_component` (`native`) |
| `--tools LIST` | Comma-separated real tool names. On `native` these are the tools bound to the target |
| `--scope TEXT` | Declared scope summary |
| `--harness NAME` | `generic`, `marketing-copilot`, or `native` |
| `-o, --output PATH` | Output directory or single file |
| `--plan-only` / `--suite-only` / `--remediations-only` | Emit a single artifact |
| `-v, --version` | Show version |

### `validate`

| Flag | Description |
|------|-------------|
| `--known-tools LIST` | Product catalog. With only this flag, every name is treated as bound (legacy suites) |
| `--bound-tools LIST` | Tools wired to this target. Must be a subset of `--known-tools` |
| `--schema NAME` | `auto` (default), `legacy`, or `native`. A file that mixes the two shapes fails |
| `--target-components LIST` | Allowed `target_component` or legacy `target_agent` values |
| `--suites LIST` | Allowed native `suite` values. Default: `golden,regression,routing,calibration,production-sample` |
| `--agent-has-no-tools` | Agent truly has no tools. Do not combine with tool flags |

`suite: smoke` is invalid on a native row; smoke lives in `metadata.split`. `OK WITH WARNINGS` does not mean the suite is ready to hand off. Any `{{...}}` left in the file fails, including runtime slots such as `{{today_date}}`.

## Programmatic usage

```python
import agent_eval_planner

result = agent_eval_planner.generate(
    input_path="agent.md",
    team="Platform Team",
    agent_name="analytics",
    tools=["funnel_analytics"],
    harness="native",
)

with open("evaluation-plan.md", "w", encoding="utf-8") as f:
    f.write(result.plan)

errors = agent_eval_planner.validate_suite(
    "out/suite.jsonl",
    known_tools=["funnel_analytics", "docs_search"],
    bound_tools=["funnel_analytics"],
    target_components=["analytics"],
    schema="native",
)
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
