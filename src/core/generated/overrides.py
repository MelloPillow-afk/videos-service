"""Select handwritten endpoints before FastAPI registers their dependencies."""

from collections.abc import Callable
from importlib import import_module
from importlib.util import find_spec
from inspect import Parameter, iscoroutinefunction, signature, unwrap
from types import UnionType
from typing import (
    Annotated,
    Any,
    TypeAliasType,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from fastapi import BackgroundTasks, Request, Response, WebSocket
from fastapi.params import Depends
from fastapi.security import SecurityScopes
from starlette.requests import HTTPConnection


def _underlying(annotation: Any) -> Any:
    """Compare schema aliases by value while retaining their binding metadata later."""
    if isinstance(annotation, TypeAliasType):
        return _underlying(annotation.__value__)
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Annotated:
        return _underlying(arguments[0])
    if origin in (Union, UnionType):
        return (UnionType, frozenset(_underlying(value) for value in arguments))
    if origin is not None:
        return (origin, tuple(_underlying(value) for value in arguments))
    return annotation


def _injected(parameter: Parameter) -> bool:
    annotation = parameter.annotation
    metadata = ()
    if get_origin(annotation) is Annotated:
        annotation, *metadata = get_args(annotation)
    if isinstance(parameter.default, Depends) or any(
        isinstance(value, Depends) for value in metadata
    ):
        return True
    return isinstance(annotation, type) and issubclass(
        annotation,
        (Request, Response, WebSocket, HTTPConnection, BackgroundTasks, SecurityScopes),
    )


def select_endpoint(operation_id: str) -> Callable[..., Any]:
    """Use a compatible async counterpart, falling back only when it is absent."""
    module_name, function_name = operation_id.rsplit(".", 1)
    target = f"src.handlers.{module_name}"

    def select(generated: Callable[..., Any]) -> Callable[..., Any]:
        try:
            module_spec = find_spec(target)
        except ModuleNotFoundError as error:
            if error.name and target.startswith(error.name + "."):
                return generated
            raise RuntimeError(f"{operation_id}: cannot inspect override {target}") from error
        except Exception as error:
            raise RuntimeError(f"{operation_id}: cannot inspect override {target}") from error
        if module_spec is None:
            return generated
        try:
            module = import_module(target)
        except Exception as error:
            raise RuntimeError(
                f"{operation_id}: importing override {target} failed: {error}"
            ) from error
        try:
            override = getattr(module, function_name)
        except AttributeError:
            return generated
        except Exception as error:
            raise RuntimeError(
                f"{operation_id}: reading override {target}.{function_name} failed: {error}"
            ) from error

        expected = signature(generated)
        try:
            if not callable(override) or not iscoroutinefunction(override):
                raise ValueError("override must be an async function")
            actual = signature(override)
            expected_types = get_type_hints(generated)
            actual_types = get_type_hints(unwrap(override))
            expected_metadata = get_type_hints(generated, include_extras=True)
            actual_metadata = get_type_hints(unwrap(override), include_extras=True)
            effective: list[Parameter] = []
            for name, parameter in actual.parameters.items():
                if name in expected.parameters:
                    contract_parameter = expected.parameters[name]
                    if parameter.kind != contract_parameter.kind:
                        raise ValueError(f"parameter kind differs: {name}")
                    if parameter.default != contract_parameter.default:
                        raise ValueError(f"parameter default differs: {name}")
                    if _underlying(actual_types.get(name, parameter.annotation)) != _underlying(
                        expected_types.get(name)
                    ):
                        raise ValueError(f"parameter annotation differs: {name}")
                    effective.append(contract_parameter.replace(annotation=expected_metadata[name]))
                else:
                    parameter = parameter.replace(
                        annotation=actual_metadata.get(name, parameter.annotation)
                    )
                    if parameter.kind in (
                        Parameter.VAR_POSITIONAL,
                        Parameter.VAR_KEYWORD,
                    ):
                        raise ValueError(f"uninspectable extra parameter: {name}")
                    if not _injected(parameter):
                        raise ValueError(f"extra parameter must use native injection: {name}")
                    effective.append(parameter)
            missing = expected.parameters.keys() - actual.parameters.keys()
            if missing:
                raise ValueError(f"missing contract parameters: {', '.join(sorted(missing))}")
            if _underlying(actual_types.get("return", actual.return_annotation)) != _underlying(
                expected_types.get("return")
            ):
                raise ValueError("return annotation differs")
            # FastAPI inspects and executes this callable directly. Resolved annotations
            # also preserve decorators whose wrapper has different module globals.
            cast(Any, override).__signature__ = actual.replace(
                parameters=effective, return_annotation=expected_types["return"]
            )
        except Exception as error:
            raise RuntimeError(
                f"{operation_id}: incompatible override {target}.{function_name}; "
                f"expected {expected}: {error}"
            ) from error
        return override

    return select
