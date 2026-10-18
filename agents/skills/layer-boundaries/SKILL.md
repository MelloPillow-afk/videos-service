---
name: layer-boundaries
description: Layer placement and import direction for videos-service. Use when adding a module under src/, moving code between layers, adding an import across layers, or reviewing a diff that touches src/.
---

# Layer boundaries

Read `docs/architecture/layers.md` first. It holds the principles, the layer table, and the
placement questions; this skill is how to apply them to a change.

For every piece of code the change adds or moves:

1. **Place it.** Walk the four questions in *Where does this code go?* in order and put the
   code where the first yes lands. Tie-breaker: the handler, until a second caller appears.
2. **Point it inward.** Each new import follows an arrow in the layer diagram. When a
   handler or worker needs storage or an outside service, it calls a service function for
   it, a pass-through when that is all it needs.
3. **Pass entities.** Layers hand each other whole `domain` entities. Rows become entities
   in the repository; outer layers derive changed ones with `dataclasses.replace`.
4. **Watch the seam.** When a change needs a second implementation behind a repository or
   client (another storage backend, a fake the real thing can't replace in tests), stop
   and raise Dependency Inversion with the user: that is the trigger in *Our one shortcut*.

Done when every added or moved piece answers to a placement question and `make layers`
reports every contract kept. A broken contract is fixed by moving the code; an
`ignore_imports` entry is for the composition root only.

When reviewing, report each piece that fails a placement question with the question it
fails and where it belongs.
