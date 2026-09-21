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
window. The receipt therefore blocks only public `ask` retirement; it does not
block the Task 3 evidence classification of internal surfaces.

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
- Claim not allowed now: that no external dependency exists, or that `ask` may
  be retired without a declared release/version boundary.
- Decision allowed now: classify internal legacy surfaces from the available
  evidence; unknown dependency is not active dependency evidence.

## v1 Import Surface Contract

RED command:

```bash
python3 skill/autonomous-mentor/examples/v1_import_surface_checks.py
```

Initial result: exit `1` because `scripts.v1_import_record` did not exist.
The failure reached the intended missing explicit contract, not importer setup.

GREEN commands:

```bash
python3 skill/autonomous-mentor/examples/v1_import_surface_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
```

Final result: both exit `0`.

- The contract classifies each declared v1 input path as `mapped`,
  `provenance_only`, or `validated_only`.
- Mapped fields cover the durable topic projection: proposition, coverage,
  rules, evidence, counterexamples, gaps, and timestamps.
- Teaching state, rule context, evidence version, and counterexample review
  context remain inert migration provenance.
- Runtime references, question tree, decision state, progress log, and
  teaching-unrelated legacy fields remain shape-validated only.
- `migration_v1_checks.py` passed all 8 existing cases, including source-hash
  protection, typed corrupt-input rejection, and evolved-topic overwrite
  protection.
- `migrate_v1.py` and `SessionState` were not modified.

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
