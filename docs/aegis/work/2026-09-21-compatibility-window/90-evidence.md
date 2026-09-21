# Compatibility Window Evidence Bundle

## Isolation

- Worktree: `.worktrees/docs-compatibility-window`
- Branch: `docs/compatibility-window`
- Base commit: `3accc78`
- Main-worktree untracked files were not staged or modified.

## Release Boundary Inspection

Command:

```bash
git tag --list
git remote -v
```

Observed on 2026-09-21:

- No Git tags were present.
- No Git remote was configured.
- The latest local commit was `3accc78`.

Interpretation: there is no release/version identifier at the opening of this
window. The receipt therefore records a release evidence gap and blocks any
future retirement decision until a concrete version identifier is supplied.

## Public Route Baseline

Command:

```bash
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
```

Result: exit `0`.

Passed assertions:

1. AST route ownership matches the vNext fixture and fixture-owned smoke path.
2. CLI help exposes exactly the eight public baseline commands.
3. `demo` reaches the fixture-owned vNext smoke.
4. `query` and `ask` retain identical stateless missing-topic behavior.

## Query Compatibility Baseline

Command:

```bash
python3 skill/autonomous-mentor/examples/query_checks.py
```

Result: exit `0`.

Passed assertions:

1. `query` reads the current version without mutation.
2. The result has no learner profile or teaching action.
3. CLI query is stateless in the caller workspace.
4. `ask` is an exact compatibility alias of `query`.
5. `feedback` is absent from the default CLI graph.

## Observation Receipt Status

- Window state: open.
- Observation receipts: none.
- Active external dependencies: none demonstrated.
- Claim allowed now: public ownership and alias behavior retain their verified
  baseline.
- Claim not allowed now: that no external dependency exists or that any
  compatibility surface may be retired.

## Anti-Entropy Declaration

- Deletion Class: not executed; future candidates are `code-retirement` and
  `contract-carrying code`.
- Old Path/Object: `ask`, former `state.state`, teaching-era runtime, and
  evaluator-only assets, each independently scoped.
- New Canonical Owner: `VNextHost`, `HostRuntimeCoordinator`,
  `KnowledgeStore`, `query_knowledge`, and the explicit v1 importer.
- Expected Preserved Behavior: vNext public learning, stateless `query`, and
  one-way read-only v1 import.
- Expected Retired Behavior: legacy public learning and teaching-era default
  execution.
- External Boundary Touched: yes.
- Source-of-Truth Data Risk: none in this documentation slice.
- User Confirmation Required: no; no deletion is performed.

## Retirement Decision

- Path: no retirement decision in this slice.
- Why: the observation window is open, release evidence is not yet declared,
  and Task 2 has not measured the minimum v1 importer surface.
- Non-edits: source, public commands, packages, archives, frozen Skills, and
  persistent knowledge.

## Verification Plan for Later Decision

- Main-path check: rerun vNext host and route fixtures.
- Lingering-reference check: prove public paths do not refer to retired owners.
- Negative check: prove a retired alias or runtime trigger is absent.
- Boundary check: preserve explicit v1 import and durable knowledge contracts.
