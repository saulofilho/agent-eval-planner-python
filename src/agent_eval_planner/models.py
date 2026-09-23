"""Data models for agent_eval_planner."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

TENANT_HEADER_PATTERN = re.compile(r"tenant", re.IGNORECASE)
DATE_PARAM_PATTERN = re.compile(r"date|start|end|from|to|period|range", re.IGNORECASE)
TIMEZONE_HEADER_PATTERN = re.compile(r"timezone|time_zone|tz", re.IGNORECASE)


@dataclass
class Parameter:
    """Represents an OpenAPI operation parameter."""

    name: str
    location: str
    required: bool = False
    schema: dict[str, Any] = field(default_factory=dict)
    description: str | None = None

    @property
    def enum_values(self) -> list[Any]:
        """Returns enum values from the schema or its items."""
        if not isinstance(self.schema, dict):
            return []
        enum = self.schema.get("enum")
        if enum:
            return list(enum)
        items = self.schema.get("items")
        if isinstance(items, dict) and items.get("enum"):
            return list(items["enum"])
        return []

    @property
    def type(self) -> str | None:
        """Returns the schema type if defined."""
        if isinstance(self.schema, dict):
            return self.schema.get("type")
        return None

    @property
    def is_tenant_header(self) -> bool:
        """Checks if parameter is a tenant header."""
        return self.location == "header" and bool(TENANT_HEADER_PATTERN.search(self.name))

    @property
    def is_date_param(self) -> bool:
        """Checks if parameter is a date/time range query parameter."""
        return self.location == "query" and bool(DATE_PARAM_PATTERN.search(self.name))

    @property
    def is_timezone_header(self) -> bool:
        """Checks if parameter is a timezone header."""
        return self.location == "header" and bool(TIMEZONE_HEADER_PATTERN.search(self.name))

    @property
    def is_enum_param(self) -> bool:
        """Checks if parameter restricts values using an enum."""
        return bool(self.enum_values)


@dataclass
class Endpoint:
    """Represents an API endpoint operation."""

    path: str
    method: str
    operation_id: str | None = None
    summary: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    security: list[Any] | None = None


@dataclass
class RedFlag:
    """Represents a security design smell or missing control in the OpenAPI contract."""

    message: str
    severity: str  # "high", "medium", "low"


@dataclass
class Category:
    """Represents a pentest category."""

    slug: str
    title: str
    layer: str  # "api" or "datalake"


@dataclass
class Vector:
    """Represents a specific offensive security test vector."""

    id: str
    name: str
    category_slug: str
    category_title: str
    layer: str  # "api" or "datalake"
    triggers: list[str]
    objective: str
    procedure: list[str]
    payload: str
    payload_type: str
    expected_validation: str
    failure_criteria: str
    risk: str
