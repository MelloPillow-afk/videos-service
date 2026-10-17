# Videos service

Python backend for the videos domain.

- Before extending or regenerating the service, read `README.md` for layer responsibilities and checks.
- `api-specs/index.yaml` owns the generated HTTP interfaces.
- The generator owns generated packages; handwritten handlers live outside those packages.
- Run `make lint-api` after contract changes.

## Verification

Done means both pass with the PostgreSQL test database running (`make test-db-up`):

- `make check`, which includes the `make dead-code` scan.
- `make coverage`: handwritten code at 95% or more, aiming for 98%. Reach it through
  behavior tests; writing, changing, or reviewing tests → load the `test-behavior` skill.

When `make dead-code` flags a name or a handwritten file sits at 0% coverage, confirm
nothing reaches it indirectly (string imports, entry points, config), then delete it in
the same change. The `[tool.vulture]` allowlist in `pyproject.toml` holds only names a
framework reaches, each with its reason.
