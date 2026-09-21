# Compatibility Window Checkpoint

## Current Todo

Task 1: establish the read-only compatibility window and its observation
receipt.

## Active Slice

Documentation-only compatibility governance. The public CLI, importer, source
tree, packages, archives, frozen Skills, and persistent knowledge are explicit
non-edits.

## Completed

- M0.5 default-entry acceptance established `VNextHost ->
  HostRuntimeCoordinator -> KnowledgeStore` as the public learning path.
- The public route baseline check passed from the isolated worktree.
- The stateless query and `ask` alias check passed from the isolated worktree.
- The window start, 30-day minimum period, release evidence gap, named
  compatibility surfaces, receipt schema, and redaction rule are recorded in
  `10-intent.md`.
- ADR 0002 is clarified with the same window close gate; no public contract is
  changed.

## Evidence Refs

- `docs/aegis/work/2026-09-21-compatibility-window/10-intent.md`
- `docs/aegis/work/2026-09-21-compatibility-window/90-evidence.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `skill/autonomous-mentor/examples/cli_route_baseline_checks.py`
- `skill/autonomous-mentor/examples/query_checks.py`

## Blocked-On Items

- There is no declared Git tag, remote release, or public version at window
  start. A concrete release/version identifier is required before Task 3 can
  decide whether `ask` may retire.
- No external dependency observation exists at window start. This remains
  unknown, not negative evidence.

## Next Step

Do not begin Task 2 in this slice. At or after 2026-10-21, gather the
observation receipt and release identifier, then execute the separately scoped
v1 importer-surface proof before the Task 3 decision gate.

## Drift Check Draft

- Task intent: served. The slice establishes observation governance only.
- Compatibility boundary: held. No fallback, owner, adapter, or command was
  added.
- Retirement track: explicit. No source or state deletion is authorized.
- Evidence state: focused baseline verification is fresh; external observation
  remains open.
- Decision: continue with Task 1 documentation verification, then pause for
  the scheduled observation window.
