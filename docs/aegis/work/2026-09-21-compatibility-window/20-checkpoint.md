# Compatibility Window Checkpoint

## Current Todo

Task 4: record full regression acceptance and the per-surface compatibility
decision.

## Active Slice

Compatibility decision recorded after implementation acceptance. The public CLI,
importer, source tree, packages, archives, frozen Skills, and persistent
knowledge remain explicit non-edits.

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
- The complete four-layer acceptance passed: `core_contract` 7/7, `behavior`
  9/9, `migration` 2/2, and `adapter` 8/8.
- Package sandbox acceptance passed 14/14 and preserved frozen and user-level
  Skill hashes.
- Fresh public-route, stateless-query, v1 migration, v1 input-surface,
  bytecode-absence, and source-ownership checks passed.
- Compatibility decision: `ask` remains release-bound; `SessionState` moves to
  a separately planned parser-extraction slice; `MentorLoop` and evaluator
  retirement remain deferred until parser and archive evidence are complete.

## Evidence Refs

- `docs/aegis/work/2026-09-21-compatibility-window/10-intent.md`
- `docs/aegis/work/2026-09-21-compatibility-window/90-evidence.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `skill/autonomous-mentor/examples/tests/adapter/cli_route_baseline_checks.py`
- `skill/autonomous-mentor/examples/tests/adapter/query_checks.py`
- `skill/autonomous-mentor/examples/tests/run_layer.py`
- `skill/autonomous-mentor/examples/tests/adapter/package_vnext_checks.py`

## Blocked-On Items

- There is no declared Git tag, remote release, or public version at window
  start. A concrete release/version identifier is required before Task 3 can
  decide whether `ask` may retire.
- No external dependency observation exists at window start. This remains
  unknown, not negative evidence.

## Next Step

Plan the narrow v1 parser-extraction slice. It may not delete `ask` without a
declared release/version identifier or extract/delete importer/runtime code
outside that separately approved slice.

## Drift Check Draft

- Task intent: served. Acceptance and per-surface classifications are recorded.
- Compatibility boundary: held. No fallback, owner, adapter, or command was
  added.
- Retirement track: explicit. No source or state deletion is authorized.
- Evidence state: full layered, sandbox, public-route, migration, bytecode,
  and ownership verification are fresh; external observation remains open.
- Decision: implementation milestone complete; proceed only with the separate
  parser-extraction planning slice.
