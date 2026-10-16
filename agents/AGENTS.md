# Videos service

Python backend for the videos domain.

- Before extending or regenerating the service, read `README.md` for layer responsibilities and checks.
- Follow contract-first architecture: `api-specs/index.yaml` and its referenced files are authoritative for HTTP behavior. For HTTP changes, update and validate the contract, regenerate, then implement the behavior.
- Use `docs/specs/pilgrims-progress-video-api-spec.md` for business requirements; resolve conflicts in favor of the current OpenAPI contract and flag ambiguous business rules for discussion.
- The generator owns generated packages; handwritten handlers live outside those packages.
- Run `make lint-api` after contract changes.
