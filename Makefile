.PHONY: lint lint-api

lint: lint-api

lint-api:
	uv run --locked yamllint api
	uv run --locked openapi-spec-validator --schema 3.2 api/index.yaml
	uv run --locked python scripts/check_examples.py
