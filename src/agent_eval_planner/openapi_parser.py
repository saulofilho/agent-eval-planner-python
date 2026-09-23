"""OpenAPI contract parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .errors import ParseError
from .models import Endpoint, Parameter

VALID_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


class OpenAPIParser:
    """Parses OpenAPI 3.x specifications in YAML or JSON."""

    def __init__(self, content: dict[str, Any], source_path: str | None = None) -> None:
        self.raw: dict[str, Any] = content or {}
        self.source_path: str | None = source_path
        self._endpoints: list[Endpoint] | None = None

    @classmethod
    def parse_file(cls, path_str: str) -> OpenAPIParser:
        """Parses an OpenAPI spec from a file path."""
        path = Path(path_str)
        if not path.is_file():
            raise ParseError(f"Arquivo não encontrado: {path_str}")

        content = path.read_text(encoding="utf-8")
        ext = path.suffix.lower()

        try:
            if ext in {".yaml", ".yml"}:
                parsed = yaml.safe_load(content)
            elif ext == ".json":
                parsed = json.loads(content)
            else:
                raise ParseError(f"Unsupported file extension: {path_str}. Use .yaml, .yml or .json")
        except Exception as exc:
            if isinstance(exc, ParseError):
                raise
            raise ParseError(f"Erro ao processar contrato OpenAPI em {path_str}: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ParseError(f"Conteúdo OpenAPI inválido em {path_str} (esperado objeto/dicionário).")

        return cls(parsed, source_path=path_str)

    @property
    def info(self) -> dict[str, Any]:
        """Returns the info section of the OpenAPI spec."""
        info_data = self.raw.get("info")
        return info_data if isinstance(info_data, dict) else {}

    @property
    def title(self) -> str | None:
        """API Title."""
        return self.info.get("title")

    @property
    def version(self) -> str | None:
        """API Version."""
        return self.info.get("version")

    @property
    def servers(self) -> list[str]:
        """List of server URLs."""
        servers_data = self.raw.get("servers")
        if not isinstance(servers_data, list):
            return []
        urls = []
        for s in servers_data:
            if isinstance(s, dict) and "url" in s and s["url"]:
                urls.append(s["url"])
        return urls

    @property
    def security_schemes(self) -> dict[str, Any]:
        """Returns security schemes defined in components."""
        components = self.raw.get("components")
        if isinstance(components, dict):
            schemes = components.get("securitySchemes")
            if isinstance(schemes, dict):
                return schemes
        return {}

    @property
    def endpoints(self) -> list[Endpoint]:
        """Returns all parsed endpoints/operations."""
        if self._endpoints is None:
            self._endpoints = self._build_endpoints()
        return self._endpoints

    def parameters_for(self, endpoint: Endpoint) -> list[Parameter]:
        """Merges global path-level parameters with endpoint-level parameters."""
        paths = self.raw.get("paths")
        global_params: list[Any] = []
        if isinstance(paths, dict):
            path_item = paths.get(endpoint.path)
            if isinstance(path_item, dict):
                gp = path_item.get("parameters")
                if isinstance(gp, list):
                    global_params = gp

        all_params = global_params + list(endpoint.parameters)
        return self._merge_parameters(all_params)

    def _build_endpoints(self) -> list[Endpoint]:
        paths = self.raw.get("paths")
        if not isinstance(paths, dict):
            return []

        endpoints: list[Endpoint] = []
        for path_str, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in VALID_HTTP_METHODS or not isinstance(operation, dict):
                    continue

                raw_params = operation.get("parameters")
                param_objs: list[Parameter] = []
                if isinstance(raw_params, list):
                    for p in raw_params:
                        built = self._build_parameter(p)
                        if built:
                            param_objs.append(built)

                summary = operation.get("summary") or operation.get("description")
                endpoints.append(
                    Endpoint(
                        path=path_str,
                        method=method.upper(),
                        operation_id=operation.get("operationId"),
                        summary=summary,
                        parameters=param_objs,
                        security=operation.get("security"),
                    )
                )

        return endpoints

    def _build_parameter(self, param: Any) -> Parameter | None:
        if isinstance(param, Parameter):
            return param
        resolved = self._resolve_ref(param)
        if not isinstance(resolved, dict) or "name" not in resolved:
            return None

        schema = resolved.get("schema")
        if not isinstance(schema, dict):
            schema = {}

        return Parameter(
            name=resolved["name"],
            location=resolved.get("in", ""),
            required=resolved.get("required") is True,
            schema=schema,
            description=resolved.get("description"),
        )

    def _resolve_ref(self, obj: Any) -> Any:
        if not isinstance(obj, dict) or "$ref" not in obj:
            return obj

        ref = obj["$ref"]
        if not isinstance(ref, str):
            return obj

        if ref.startswith("#/"):
            clean_ref = ref[2:]
        elif ref.startswith("#"):
            clean_ref = ref[1:]
        else:
            clean_ref = ref

        parts = [p.replace("~1", "/").replace("~0", "~") for p in clean_ref.split("/") if p]
        node: Any = self.raw
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return obj
        return node

    def _merge_parameters(self, params: list[Any]) -> list[Parameter]:
        merged: list[Parameter] = []
        seen: set[tuple[str, str]] = set()

        for p in params:
            built = self._build_parameter(p)
            if not built:
                continue
            key = (built.location, built.name)
            if key not in seen:
                seen.add(key)
                merged.append(built)

        return merged
