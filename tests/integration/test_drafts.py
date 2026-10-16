"""Draft management through HTTP, signed provider identity, and PostgreSQL."""

from collections.abc import AsyncIterator
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

from tests.providers import LocalSigningKeys

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client,
    ):
        yield client


async def test_administrator_creates_a_persisted_draft(
    client: AsyncClient, signing_keys: LocalSigningKeys
) -> None:
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    response = await client.post("/v1/videos", json={"title": "A persisted draft"}, headers=headers)
    assert response.status_code == 201
    draft = response.json()
    assert draft["title"] == "A persisted draft"
    assert draft["status"] == "CREATED" and draft["publication_status"] == "DRAFT"
    assert (
        draft["description"]
        is draft["size_bytes"]
        is draft["duration_seconds"]
        is draft["published_at"]
        is None
    )
    assert draft["thumbnail"] == {"status": "PENDING", "source": "NONE", "url": None}
    assert datetime.fromisoformat(draft["created_at"]).utcoffset() == timedelta(0)
    assert draft["created_at"] == draft["updated_at"]
    detail = await client.get(response.headers["Location"], headers=headers)
    assert detail.json() == draft


async def test_anonymous_cannot_create_drafts(client: AsyncClient) -> None:
    response = await client.post("/v1/videos", json={"title": "Private"})
    assert response.status_code == 401


async def test_metadata_edits_persist_and_allow_clearing_description(
    client: AsyncClient, signing_keys: LocalSigningKeys
) -> None:
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    created = await client.post(
        "/v1/videos", json={"title": "Before", "description": "Remove me"}, headers=headers
    )
    path = created.headers["Location"]
    updated = await client.patch(
        path, json={"title": "After", "description": None}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "After" and updated.json()["description"] is None
    assert updated.json()["created_at"] == created.json()["created_at"]
    assert updated.json()["updated_at"] > created.json()["updated_at"]
    assert (await client.get(path, headers=headers)).json() == updated.json()


async def test_demotion_denies_next_request_with_same_valid_token(
    client: AsyncClient, signing_keys: LocalSigningKeys, test_database: tuple[str, str]
) -> None:
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    created = await client.post("/v1/videos", json={"title": "Private"}, headers=headers)
    path = created.headers["Location"]
    assert (await client.get(path)).status_code == 404
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.\"user\" SET role='user'").format(sql.Identifier(schema + "_auth"))
        )
    assert (
        await client.patch(path, json={"title": "Forbidden"}, headers=headers)
    ).status_code == 403
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (
        await client.post("/v1/videos", json={"title": "Forbidden"}, headers=headers)
    ).status_code == 403


@pytest.mark.parametrize(
    "failure", ["expired", "issuer", "audience", "signature", "malformed", "unknown-key"]
)
async def test_invalid_identity_is_rejected(
    client: AsyncClient, signing_keys: LocalSigningKeys, failure: str
) -> None:
    tokens = {
        "expired": signing_keys.token(seconds=-1),
        "issuer": signing_keys.token(issuer="https://attacker.test"),
        "audience": signing_keys.token(audience="https://another.test"),
        "signature": LocalSigningKeys().token(),
        "malformed": "not.a.valid.jwt",
        "unknown-key": "eyJhbGciOiJFZERTQSIsImtpZCI6Im5vdC1hLWtleSJ9.e30.eA",
    }
    response = await client.post(
        "/v1/videos",
        json={"title": "Forbidden"},
        headers={"Authorization": "Bearer " + tokens[failure]},
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("role,status", [("superadmin", 403), ("user,admin", 201), (None, 403)])
async def test_current_role_requires_exact_admin_membership(
    client: AsyncClient,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    role: str | None,
    status: int,
) -> None:
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL('UPDATE {}."user" SET role=%s').format(sql.Identifier(schema + "_auth")),
            (role,),
        )
    response = await client.post(
        "/v1/videos",
        json={"title": "Role check"},
        headers={"Authorization": "Bearer " + signing_keys.token()},
    )
    assert response.status_code == status


async def test_role_lookup_outage_fails_closed_and_health_stays_available(
    client: AsyncClient, signing_keys: LocalSigningKeys, test_database: tuple[str, str]
) -> None:
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL('DROP TABLE {}."user"').format(sql.Identifier(schema + "_auth"))
        )
    assert (
        await client.post(
            "/v1/videos",
            json={"title": "Forbidden"},
            headers={"Authorization": "Bearer " + signing_keys.token()},
        )
    ).status_code == 503
    assert (await client.get("/v1/videos/550e8400-e29b-41d4-a716-446655440000")).status_code == 404
    assert (await client.get("/ping")).json() == {"status": "ok"}


@pytest.mark.parametrize(
    "body", [{}, {"title": ""}, {"title": "   "}, {"title": None}, {"title": "a" * 201}]
)
async def test_draft_native_validation(
    client: AsyncClient, signing_keys: LocalSigningKeys, body: dict[str, object]
) -> None:
    response = await client.post(
        "/v1/videos", json=body, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
