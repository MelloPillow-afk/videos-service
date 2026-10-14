---
name: validate-service-spec
description: Validate a service's OpenAPI contract using the existing Python lint pipeline. Use when asked to validate or verify api-specs/index.yaml or check a service API contract.
---

# Validate service spec

1. Use the requested service directory; default to `videos-service` in this
   workspace. Read its `Makefile` and `pyproject.toml` for the validation commands
   and Python requirements. The default contract is `api-specs/index.yaml`, with local
   schemas in `api-specs/schemas/` and parameter definitions in `api-specs/parameters/`.
2. From the service directory, run `uv sync --locked` if the validation environment
   needs setup, then run:

   ```sh
   make lint-api
   ```

   This checks YAML syntax/style and duplicate keys, OpenAPI structure,
   references, and examples against their schemas, including formats.
3. Report the contract path, OpenAPI version, and check results. Claim validation
   passed only when every check succeeds. Report failures with file locations and
   diagnostics; identify environment blockers as validation incomplete. Change
   the contract only when fixes are requested, then rerun the checks.

Contract validation does not verify backend implementation or runtime behavior.
