---
name: ag-generate
description: Generate or regenerate a Python API service from its api-specs/index.yaml contract using ag. Use for new service scaffolds or updates to generated interfaces.
---

# Generate with ag

Resolve the target service directory from the user's request or current project. Its required entry document is `api-specs/index.yaml`; identify that expected path if it is missing.

Verify `ag --help` identifies the API generator. If installation is needed, follow [ag-install](../../../../api-code-generator/agents/skills/ag-install/SKILL.md).

Run the generator against the service directory:

```sh
ag "/absolute/path/to/service"
```

On failure, report the source-location diagnostic and fix the contract when that change is within the user's request. Regenerate through `ag`; keep handwritten code and the `.api-code-generator.json` ownership record intact. Resolve ownership conflicts without deleting custom files or bypassing ownership checks.

On success, report the generated operation count and the CLI's next steps. Generation creates files; dependency installation and server startup are separate actions. If the user also requests a running service, follow the printed `uv lock`, `uv sync`, and startup instructions. Use an existing service's entrypoint when applicable.

For contract naming/examples, handwritten overrides, or existing-service adoption, read the [generator README](../../../../api-code-generator/README.md). An existing app needs the one-time `register_routers(app)` integration from `src.core.generated.routers` while retaining its configuration and lifecycle; generated output alone does not establish that it is wired or running.
