# Videos service

Python backend for the videos domain.

- Before extending or regenerating the service, read `README.md` for layer responsibilities and checks.
- `api-specs/index.yaml` owns the generated HTTP interfaces.
- The generator owns generated packages; handwritten handlers live outside those packages.
- Run `make lint-api` after contract changes.
