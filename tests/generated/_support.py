# fmt: off
"""Generated pytest support. Customize fixtures in tests/conftest.py, never here."""

from collections.abc import AsyncIterator
from copy import deepcopy
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any
from urllib.parse import quote

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from pydantic import TypeAdapter


def _adapter(target: str) -> TypeAdapter[Any]:
    module, name = target.rsplit(".", 1)
    return TypeAdapter(getattr(import_module(module), name))


@dataclass
class APICase:
    """Mutable Arrange values; response is available to yield fixtures for cleanup."""

    operation_id: str
    method: str
    path: str
    path_params: dict[str, Any]
    query: dict[str, Any]
    body: Any
    expected_body: Any
    parameters: list[dict[str, Any]]
    body_model: dict[str, Any] | None
    response_model: str | None
    expected_status: int
    mutation: dict[str, Any] | None = None
    authentication: str | None = None
    unauthenticated: bool = False
    headers: dict[str, str] = field(default_factory=dict[str, str])
    response: Response | None = None
    _expected: Any = field(default=None, init=False)

    def prepare_request(self) -> dict[str, Any]:
        """Validate Arrange, freeze expectations, then corrupt one parameter."""
        self._expected = deepcopy(self.expected_body)
        path_params, query = deepcopy(self.path_params), deepcopy(self.query)
        for parameter in self.parameters:
            values = path_params if parameter["in"] == "path" else query
            name = parameter["name"]
            assert name in values or not parameter["required"], (
                f"{self.operation_id}: Arrange omitted required {parameter['in']} {name}"
            )
            if name in values:
                _adapter(parameter["model"]).validate_python(values[name])
        if self.body_model is not None and (
            self.body is not None or self.body_model["required"]
        ):
            _adapter(self.body_model["model"]).validate_python(self.body)
        assert not (
            self.body_model is not None
            and self.body_model["required"]
            and self.body is None
        ), (
            f"{self.operation_id}: Arrange must supply a non-null body; FastAPI treats null as missing"
        )
        if self.mutation is not None:
            values = path_params if self.mutation["in"] == "path" else query
            if self.mutation.get("omit"):
                values.pop(self.mutation["name"], None)
            else:
                values[self.mutation["name"]] = self.mutation["value"]
        path = self.path
        for name, value in path_params.items():
            text = _wire(value)
            assert text and "/" not in text, (
                f"{self.operation_id}: path parameter {name} must occupy one URL segment"
            )
            path = path.replace("{" + name + "}", quote(text, safe=""))
        headers = {
            name: value
            for name, value in self.headers.items()
            if not (self.unauthenticated and name.lower() == "authorization")
        }
        request: dict[str, Any] = {
            "method": self.method,
            "url": path,
            "params": {name: _wire(value) for name, value in query.items()},
            "headers": headers,
        }
        if self.body is not None:
            request["json"] = deepcopy(self.body)

        return request

    def assert_response(self) -> None:
        response = self.response
        assert response is not None
        context = (
            f"{self.operation_id}: {response.status_code} {response.text}; "
            f"arrange fixture: arrange_{self.operation_id.replace('.', '_')}"
        )
        if response.status_code == 401 and self.authentication and not self.unauthenticated:
            context += "; bearer token fixture: api_bearer_token"
        assert response.status_code == self.expected_status, context
        if self.unauthenticated:
            challenge = response.headers.get("WWW-Authenticate", "")
            assert challenge.lower().startswith("bearer"), context
        elif self.mutation is not None:
            detail: list[dict[str, Any]] = response.json().get("detail")
            assert isinstance(detail, list), context
            location = [self.mutation["in"], self.mutation["name"]]
            assert any(
                isinstance(error, dict)
                and error.get("loc") == location
                and error.get("type") in self.mutation["error_types"]
                for error in detail
            ), context
        elif self.expected_status == 204:
            assert response.content == b"", context
        else:
            assert self.response_model is not None
            _adapter(self.response_model).validate_json(response.content)
            assert response.json() == self._expected, context


def _wire(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


@pytest.fixture
def api_app() -> FastAPI:
    """Override in tests/conftest.py to configure real test infrastructure."""
    from src.app import create_app

    return create_app()


@pytest_asyncio.fixture
async def api_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app), base_url="http://testserver"
        ) as client,
    ):
        yield client


@pytest.fixture
def api_bearer_token() -> str | None:
    """Override in tests/conftest.py to authenticate operations declaring security."""
    return None


@pytest_asyncio.fixture
async def api_case(
    request: Any, api_client: AsyncClient, api_bearer_token: str | None
) -> APICase:
    marker: pytest.Mark | None = request.node.get_closest_marker("api_case")
    assert marker is not None, "generated API tests require an api_case marker"
    values: dict[str, Any] = deepcopy(marker.args[0])
    values.update(deepcopy(marker.kwargs))
    if values.get("mutation") is not None:
        values["expected_status"] = 422
    if values.get("unauthenticated"):
        values["expected_status"] = 401
    case = APICase(**values)
    if case.authentication and api_bearer_token is not None:
        case.headers["Authorization"] = f"Bearer {api_bearer_token}"
    return case


MODULES = ["admin.thumbnails", "admin.videos", "health", "jobs", "playback", "videos"]


@pytest.fixture
def arrange_admin_thumbnails_complete_upload(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_thumbnails_delete_thumbnail(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_thumbnails_upload_url(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_videos_create_video(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_videos_delete_video(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_videos_get_video(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_videos_list_videos(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_videos_update_video(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_admin_videos_upload_url(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_health_ping(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_jobs_get_job(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_playback_get_playback(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""


@pytest.fixture
def arrange_videos_list_videos(api_case: APICase) -> None:
    """Override this fixture in tests/conftest.py to arrange the operation."""
