"""Exceptions for agent_eval_planner."""


class Error(Exception):
    """Base exception for agent_eval_planner."""


class ParseError(Error):
    """Raised when an OpenAPI document cannot be parsed."""


class InputError(Error):
    """Raised when input parameters or scope paths are invalid."""
