.PHONY: install run db-up db-down test-db-up storage-up local-ca worker-build migrate migrations check lint lint-api format format-src format-check typecheck test test-integration coverage dead-code

install:
	uv sync --locked

run:
	uv run --locked uvicorn src.app:create_app --factory --reload

db-up:
	docker compose up -d --wait postgres

db-down:
	docker compose --profile test down

test-db-up:
	docker compose --profile test up -d --wait postgres-test

storage-up:
	docker compose up -d --wait seaweedfs storage-https
	docker compose run --rm storage-buckets

local-ca:
	mkdir -p .local
	docker compose cp storage-https:/data/caddy/pki/authorities/local/root.crt .local/caddy-root.crt

worker-build:
	docker compose build worker

migrate:
	uv run --locked python -m src.repositories.migrate apply

migrations:
	uv run --locked python -m src.repositories.migrate list

check: lint format-check typecheck

lint: lint-api dead-code
	uv run --locked ruff check src tests/unit tests/integration tests/conftest.py tests/generated

format: format-src
	uv run --locked ruff format tests/unit tests/integration tests/conftest.py tests/generated

format-src:
	uv run --locked ruff format src

format-check:
	uv run --locked ruff format --check src tests/unit tests/integration tests/conftest.py tests/generated

typecheck:
	uv run --locked pyright

test:
	uv run --locked pytest -m 'not integration'

test-integration:
	uv run --locked pytest -m integration

coverage:
	uv run --locked pytest --cov --cov-report=term-missing:skip-covered --cov-report=xml --cov-report=html
	@echo "HTML report: htmlcov/index.html"

dead-code:
	uv run --locked vulture

lint-api:
	uv run --locked yamllint api-specs
	uv run --locked openapi-spec-validator --schema 3.2 api-specs/index.yaml
	uv run --locked python scripts/check_examples.py
