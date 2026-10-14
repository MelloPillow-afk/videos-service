.PHONY: install run db-up db-down test-db-up migrate migrations check lint lint-api format format-check typecheck test test-integration test-all

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

migrate:
	uv run --locked python -m src.repositories.migrate apply

migrations:
	uv run --locked python -m src.repositories.migrate list

check: lint format-check typecheck

lint: lint-api
	uv run --locked ruff check src tests/unit tests/integration

format:
	uv run --locked ruff format src tests/unit tests/integration

format-check:
	uv run --locked ruff format --check src tests/unit tests/integration

typecheck:
	uv run --locked pyright

test:
	uv run --locked pytest -m 'not integration' --cov --cov-report=term-missing

test-integration:
	uv run --locked pytest -m integration

test-all:
	uv run --locked pytest --cov --cov-report=term-missing --cov-report=xml

lint-api:
	uv run --locked yamllint api-specs
	uv run --locked openapi-spec-validator --schema 3.2 api-specs/index.yaml
	uv run --locked python scripts/check_examples.py
