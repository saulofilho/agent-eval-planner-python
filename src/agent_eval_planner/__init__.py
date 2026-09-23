# src/agent_eval_planner/__init__.py
"""Agent Eval Planner package.

Provides a CLI (`agent-eval-planner`) that reads a specification file (YAML or JSON)
and generates a Markdown evaluation plan for AI agents.

The implementation is intentionally lightweight – it focuses on parsing the spec
and rendering a basic Markdown template. Users can extend the logic in
`generator.py` for custom metrics, test scenarios, or CI integrations.
"""

from .generator import generate_plan

__all__ = ["generate_plan"]

