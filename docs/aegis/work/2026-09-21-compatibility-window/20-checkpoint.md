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
- The evidence-triggered window, release evidence gap, named compatibility
  surfaces, receipt schema, and redaction rule are recorded in `10-intent.md`.
- ADR 0002 is clarified with the same window close gate; no public contract is
  changed.
- Task 2 now has an executable v1 input-surface contract. It separates mapped,
  provenance-only, and validated-only fields without changing importer parsing
  or `SessionState`.
- The v1 input-surface check and existing migration regression check both pass.

## Evidence Refs

- `docs/aegis/work/2026-09-21-compatibility-window/10-intent.md`
- `docs/aegis/work/2026-09-21-compatibility-window/90-evidence.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `skill/autonomous-mentor/examples/tests/adapter/cli_route_baseline_checks.py`
- `skill/autonomous-mentor/examples/tests/adapter/query_checks.py`

## Blocked-On Items

- There is no declared Git tag, remote release, or public version at window
  start. A concrete release/version identifier is required before Task 3 can
  decide whether `ask` may retire.
- No external dependency observation exists at window start. This remains
  unknown, not negative evidence.

## Next Step

Execute the Task 3 evidence review now. It may classify internal surfaces from
existing evidence, but it may not delete `ask` without a declared
release/version identifier or extract/delete importer/runtime code.

## Drift Check Draft

- Task intent: served. The slice establishes observation governance only.
- Compatibility boundary: held. No fallback, owner, adapter, or command was
  added.
- Retirement track: explicit. No source or state deletion is authorized.
- Evidence state: route/query and importer-surface verification are fresh;
  external observation remains open.
- Decision: Task 2 contract slice complete; enter Task 3 evidence review now.
