# fmt: off
"""Generated contract boundary. Renewed by api-code-generator."""

import json
import re
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from importlib import import_module
from importlib.util import find_spec
from inspect import (
    Parameter,
    Signature,
    getsourcefile,
    iscoroutinefunction,
    signature,
    unwrap,
)
from typing import Any, cast, get_type_hints
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, TypeAdapter, ValidationError
from starlette.routing import Host, Mount, WebSocketRoute
from starlette.types import Lifespan


@dataclass
class HandlerResponse[T]:
    payload: T
    headers: dict[str, str | int | float | bool] = field(
        default_factory=dict[str, str | int | float | bool]
    )


_OPERATIONS: dict[str, dict[str, Any]] = {}
_DEFAULT_ERROR = object()


class ContractError(Exception):
    """An implementer-owned decorator requests a declared, validated error response."""

    def __init__(self, status: int, payload: object):
        super().__init__(f"contract error {status}")
        self.status = status
        self.payload = payload


def model_adapter(target: str) -> TypeAdapter[Any]:
    module, name = target.rsplit(".", 1)
    return TypeAdapter(getattr(import_module(module), name))


def error_response(
    operation: dict[str, Any], status: int, payload: object = _DEFAULT_ERROR
) -> JSONResponse:
    error = operation["errors"].get(str(status))
    if error is None:
        raise ValueError(f"{operation['id']}: no contract response for {status}")
    if payload is _DEFAULT_ERROR:
        payload = error["payload"]
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(
            mode="json", by_alias=True, exclude_unset=True, warnings="error"
        )
    adapter = model_adapter(error["model"])
    validated = adapter.validate_json(json.dumps(payload, allow_nan=False), strict=True)
    return JSONResponse(
        adapter.dump_python(validated, mode="json", by_alias=True), status_code=status
    )


def wire_value(value: Any) -> Any:
    """Serialize supplied model values without trusting their validation history."""
    if isinstance(value, BaseModel):
        return value.model_dump(
            mode="json", by_alias=True, exclude_unset=True, warnings="error"
        )
    if isinstance(value, (UUID, datetime)):
        return str(value) if isinstance(value, UUID) else value.isoformat()
    raise TypeError(f"unsupported response value {type(value).__name__}")


def parse_parameters(operation: dict[str, Any], request: Request) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for parameter in operation["parameters"]:
        source = (
            request.path_params if parameter["in"] == "path" else request.query_params
        )
        raw = source.get(parameter["name"])
        if raw is None:
            if parameter["required"]:
                raise ValueError(f"missing parameter {parameter['name']}")
            continue
        kind = parameter["type"]
        if kind == "integer":
            if re.fullmatch(r"[+-]?[0-9]+", raw) is None:
                raise ValueError("expected integer parameter")
            value: Any = int(raw)
        elif kind == "number":
            value = float(raw)
        elif kind == "boolean":
            if raw not in {"true", "false"}:
                raise ValueError("expected boolean parameter")
            value = raw == "true"
        else:
            value = raw
        validated = model_adapter(parameter["model"]).validate_json(
            json.dumps(value, allow_nan=False), strict=True
        )
        if parameter["format"] == "uuid":
            validated = UUID(validated)
        values[parameter["attribute"]] = validated
    return values


def reject_nonfinite(value: str) -> Any:
    raise ValueError(f"invalid JSON constant {value}")


async def parse_body(
    operation: dict[str, Any], request: Request, arguments: dict[str, Any]
) -> None:
    body = operation.get("body")
    if body is None:
        return
    raw = await request.body()
    if not raw:
        if body["required"]:
            raise ValueError("request body is required")
        return
    content_type = (
        request.headers.get("content-type", "application/json")
        .split(";", 1)[0]
        .strip()
        .lower()
    )
    if content_type != "application/json":
        raise ValueError("request body must be application/json")
    json.loads(raw, parse_constant=reject_nonfinite)
    arguments[body["attribute"]] = model_adapter(body["model"]).validate_json(
        raw, strict=True
    )


def validate_headers(operation: dict[str, Any], headers: object) -> dict[str, str]:
    """Validate Header Objects before their scalar values are serialized for HTTP."""
    if not isinstance(headers, dict):
        raise ValueError("response headers must be a mapping")
    actual: dict[str, tuple[str, Any]] = {}
    for name, value in cast(dict[Any, Any], headers).items():
        if not isinstance(name, str) or not re.fullmatch(
            r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name
        ):
            raise ValueError("invalid HTTP response header name")
        key = name.lower()
        if key in actual:
            raise ValueError(f"duplicate response header {name}")
        actual[key] = (name, value)
    for name, definition in operation.get("response_headers", {}).items():
        supplied = actual.get(name.lower())
        if supplied is None:
            if definition["required"]:
                raise ValueError(f"missing required response header {name}")
            continue
        adapter = model_adapter(definition["model"])
        validated = adapter.validate_json(
            json.dumps(supplied[1], allow_nan=False), strict=True
        )
        actual[name.lower()] = (
            name,
            adapter.dump_python(validated, mode="json", warnings="error"),
        )
    encoded: dict[str, str] = {}
    for name, value in actual.values():
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"response header {name} must be scalar")
        text = ("true" if value else "false") if isinstance(value, bool) else str(value)
        if any(ord(char) < 32 and char != "\t" or ord(char) == 127 for char in text):
            raise ValueError(
                f"response header {name} contains a forbidden control character"
            )
        text.encode("latin-1")
        encoded[name] = text
    return encoded


def endpoint(operation_id: str) -> Callable[..., Any]:
    """Keep contract enforcement outside generated and handwritten behavior."""

    def decorate(implementation: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(implementation)
        async def validated(*args: Any, **kwargs: Any) -> JSONResponse:
            operation = _OPERATIONS[operation_id]
            try:
                request = kwargs.get("request")
                if request is None and args:
                    request = args[0]
                if not isinstance(request, Request):
                    raise TypeError("generated endpoint requires a request")
                operation = cast(
                    dict[str, dict[str, Any]], request.app.state.contract_operations
                )[operation_id]
                arguments = parse_parameters(operation, cast(Request, request))
                await parse_body(operation, cast(Request, request), arguments)
            except (ValidationError, ValueError, TypeError):
                return error_response(operation, 400)
            try:
                result = await operation.get("implementation", implementation)(
                    **arguments
                )
                if not isinstance(result, HandlerResponse):
                    raise ValueError("implementation must return HandlerResponse")
                adapter = model_adapter(operation["response_model"])
                typed_result = cast(HandlerResponse[Any], result)
                wire = json.dumps(
                    typed_result.payload, default=wire_value, allow_nan=False
                )
                payload = adapter.validate_json(wire, strict=True)
                dumped = adapter.dump_python(
                    payload,
                    mode="json",
                    by_alias=True,
                    exclude_unset=True,
                    warnings="error",
                )
                adapter.validate_json(json.dumps(dumped, allow_nan=False), strict=True)
                return JSONResponse(
                    dumped,
                    status_code=operation["status"],
                    headers=validate_headers(operation, typed_result.headers),
                )
            except ContractError as error:
                try:
                    return error_response(operation, error.status, error.payload)
                except (ValidationError, ValueError, TypeError):
                    return error_response(operation, 500)
            except Exception:
                return error_response(operation, 500)

        cast(Any, validated).__signature__ = Signature(
            [Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)]
        )
        return validated

    return decorate


def resolve_implementation(
    operation: dict[str, Any], generated: Callable[..., Any]
) -> Callable[..., Any]:
    """Only absence means mock; import defects in an existing counterpart fail startup."""
    target = f"src.handlers.{operation['module']}"
    try:
        spec = find_spec(target)
    except Exception as error:
        raise RuntimeError(
            f"{operation['id']}: cannot inspect override module {target}"
        ) from error
    if spec is None:
        return unwrap(generated)
    try:
        module = import_module(target)
    except Exception as error:
        raise RuntimeError(
            f"{operation['id']}: importing override {spec.origin or target} failed: {error}"
        ) from error
    if not hasattr(module, operation["function"]):
        return unwrap(generated)
    override = getattr(module, operation["function"])
    expected_function = unwrap(generated)
    expected = signature(expected_function)
    location = getattr(module, "__file__", target)
    try:
        if not callable(override) or not iscoroutinefunction(override):
            raise ValueError("override must be an async function")
        location = getsourcefile(unwrap(override)) or location
        actual = signature(override)
        expected_types = get_type_hints(expected_function)
        actual_types = get_type_hints(unwrap(override))
        if list(actual.parameters) != list(expected.parameters):
            raise ValueError(f"parameter names differ: {actual}")
        for name, parameter in expected.parameters.items():
            supplied = actual.parameters[name]
            if supplied.kind != parameter.kind or supplied.default != parameter.default:
                raise ValueError(f"parameter kind/default differs: {name}")
            if actual_types.get(name) != expected_types.get(name):
                raise ValueError(f"parameter annotation differs: {name}")
        if actual_types.get("return") != expected_types.get("return"):
            raise ValueError("return annotation differs")
    except Exception as error:
        raise RuntimeError(
            f"{operation['id']}: incompatible override {location}; expected {expected}: {error}"
        ) from error
    return override


def validate_routes(
    app: FastAPI, expected: dict[tuple[str, str], Callable[..., Any]]
) -> None:
    """Inspect includes, mounts, hosts, and plain routes; reject unknown routing layers."""
    seen: set[tuple[str, str]] = set()
    active: set[int] = set()

    def walk(routes: list[Any], prefix: str = "") -> None:
        for route in routes:
            if id(route) in active:
                raise RuntimeError("cyclic HTTP route registration")
            active.add(id(route))
            try:
                if hasattr(route, "original_router") and hasattr(
                    route, "include_context"
                ):
                    context = route.include_context
                    walk(route.original_router.routes, prefix + context.prefix)
                elif isinstance(route, (Mount, Host)):
                    children = getattr(route, "routes", None)
                    if children is None:
                        children = getattr(route.app, "routes", None)
                    if not children:
                        raise RuntimeError(
                            f"uninspectable mounted HTTP application at {prefix}{getattr(route, 'path', '')}"
                        )
                    walk(children, prefix + getattr(route, "path", ""))
                elif isinstance(route, WebSocketRoute):
                    continue
                elif getattr(route, "methods", None) is not None:
                    path = prefix + route.path
                    for method in route.methods:
                        key = (path, method.upper())
                        if key not in expected:
                            raise RuntimeError(
                                f"HTTP endpoint outside contract: {method} {path}"
                            )
                        if key in seen:
                            raise RuntimeError(
                                f"duplicate HTTP endpoint: {method} {path}"
                            )
                        if route.endpoint is not expected[key]:
                            raise RuntimeError(
                                f"HTTP endpoint bypasses generated contract enforcement: {method} {path}"
                            )
                        seen.add(key)
                else:
                    raise RuntimeError(
                        f"unsupported HTTP routing layer {type(route).__name__}"
                    )
            finally:
                active.remove(id(route))

    walk(app.routes)
    if seen != set(expected):
        raise RuntimeError(
            f"missing generated contract routes: {sorted(set(expected) - seen)}"
        )


def register_routes(app: FastAPI, operations: list[dict[str, Any]]) -> None:
    """One registry owns routes and composes the existing resource lifecycle."""
    operation_map = {operation["id"]: dict(operation) for operation in operations}
    _OPERATIONS.update(operation_map)
    app.state.contract_operations = operation_map
    expected: dict[tuple[str, str], Callable[..., Any]] = {}
    handlers: dict[str, Callable[..., Any]] = {}
    for operation in operation_map.values():
        module = import_module(f"src.handlers.generated.{operation['module']}")
        handler = getattr(module, operation["function"])
        handlers[operation["id"]] = handler
        key = (operation["path"], operation["method"])
        if key in expected:
            raise RuntimeError(f"duplicate contract route {key}")
        expected[key] = handler
        app.add_api_route(
            operation["path"],
            handler,
            methods=[operation["method"]],
            response_model=None,
            status_code=operation["status"],
        )

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        for operation in operation_map.values():
            operation["implementation"] = resolve_implementation(
                operation, handlers[operation["id"]]
            )
        validate_routes(application, expected)
        async with original_lifespan(application) as state:
            validate_routes(application, expected)
            yield state

    app.router.lifespan_context = cast(Lifespan[Any], lifespan)

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Any, exc: RequestValidationError) -> JSONResponse:
        route = request.scope.get("route")
        for operation in operation_map.values():
            if (
                operation["path"] == getattr(route, "path", None)
                and operation["method"] == request.method
            ):
                return error_response(operation, 400)
        raise exc
