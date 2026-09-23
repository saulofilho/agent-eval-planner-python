"""Exceptions for agent_eval_planner."""


class Error(Exception):
    """Base exception for agent_eval_planner."""


class InputError(Error):
    """Raised when input path or arguments are invalid."""


class ValidationError(Error):
    """Raised when a suite JSONL fails validation."""
