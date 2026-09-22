# Publication Lifecycle and Test Layering Implementation Plan

## Goal

Implement the approved durable publication lifecycle and direct four-layer test
tree migration without creating a second writer, a public fallback, or a
compatibility wrapper for old internal test paths.

## Architecture

- `KnowledgePublisher` owns lifecycle transition policy and returns terminal
  publication outcomes.
- `KnowledgeStore` remains the only topic lock and durable file writer. It
  atomically appends immutable audit records and saves published snapshots.
- `HostRuntimeCoordinator` supplies validated integration and skeptic review to
  the publisher; it no longer applies a delta directly through `Learner`.
- `TopicKnowledge` remains the current published projection. It does not carry
  proposed or rejected payload history.
- `examples/tests/{core_contract,behavior,migration,adapter}` becomes the only
  active internal check tree. Historical work/evidence documents retain old
  paths as historical records and are not rewritten.

## Tech Stack

Python 3.10+ standard library, canonical JSON, existing `KnowledgeStore` topic
locks and immutable snapshots, focused executable checks, and Git worktree
isolation.

## Baseline / Authority Refs

- `docs/aegis/specs/2026-09-22-publication-lifecycle-and-test-layering-design.md`
- `docs/aegis/reports/2026-09-22-refactor-roadmap-progress.md`
- `docs/aegis/adr/0001-one-way-v1-import-boundary.md`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `docs/aegis/plans/2026-09-21-post-m05-compatibility-window-retirement.md`
- M0.5 runtime baseline `b433904`

## Compatibility Boundary

- `KnowledgeStore` remains the only durable topic writer and lock owner.
- `query` reads only published `knowledge.json` and preserves `ask` alias
  behavior.
- Existing topics lacking `audit/` must remain readable without rewrite.
- Existing v1 importer outcomes must remain byte/source-hash and
  evolved-topic safe.
- Public CLI envelopes, frozen Skills, user installation, ZIP/archive, and
  persistent user knowledge are non-edits.
- Test paths are an internal contract: direct move, all in-repository callers
  updated, no old-path wrapper.
- No source retirement occurs in this plan. `ask`, `MentorLoop`, teaching
  evaluators, and `SessionState` remain governed by the existing compatibility
  decision plan.

## Plan Basis

Facts:

- `HostRuntimeCoordinator.commit_learning()` is the public durable commit
  boundary and currently calls `Learner.apply_knowledge_delta()`.
- `KnowledgeStore` already has one per-topic lock, immutable snapshots, and
  recovery for `knowledge.json`.
- `TopicKnowledge` has no audit journal and must remain the published
  projection.
- Package and validation manifests enumerate old `examples/*.py` paths.

Assumptions:

- No active external consumer of internal example-script paths is known.
- Existing topic data can remain untouched until a new lifecycle action occurs.

Unknowns and stop conditions:

- If one lock cannot make topic snapshot and journal recovery coherent, stop
  before host integration for architecture review.
- If a proven external consumer requires an old test path, stop test migration
  for a bounded compatibility decision; do not add a wrapper by default.
- If planned work would rewrite user topic history or remove user data, stop
  and obtain scoped confirmation.

## Architecture Integrity Lens

- Invariant: each topic has one canonical published projection and one durable
  writer; every attempted update has an immutable terminal audit trail.
- Canonical owner / contract: `KnowledgePublisher` decides transitions;
  `KnowledgeStore` persists them under its existing lock.
- Responsibility overlap: `Learner` currently combines candidate construction,
  validation, and direct durable commit. Its candidate application logic
  remains reusable, but durable publication moves to the publisher.
- Higher-level simplification: the publisher calls the store once for a
  publish/reject transaction instead of adding host-side journal files or
  caller-side retry branches.
- Retirement / falsifier: any direct host call to
  `Learner.apply_knowledge_delta`, or a successful topic version without its
  matching published audit record, fails the design.
- Verdict: proceed with one publisher owner and store-owned transaction.

## Plan Pressure Test

- Owner / contract / retirement: new `KnowledgePublisher` is justified because
  transition policy must not live in `HostRuntimeCoordinator` or
  `KnowledgeStore`; direct host-to-learner commit becomes inactive.
- Architecture integrity / higher-level path: the store transaction is the
  only acceptable place for file atomicity and recovery.
- Verification scope: lifecycle state, immutable records, rejection
  non-mutation, recovery, host retry, layer path, package, and sandbox checks.
- Task executability: four slices align to durable transaction, public runtime,
  internal test path, and final integration boundaries.
- Pressure result: proceed.

## Plan-Time Complexity Check

- Target files: `knowledge_schema.py` (735 lines), `knowledge_store.py`
  (361), `learner.py` (666), `autonomous_runtime.py` (709), package and
  manifest scripts, and all example checks.
- Existing size / shape signals: `autonomous_runtime.py` and legacy
  `learner.py` are large; lifecycle policy must not be added inline to either.
- Owner fit: create `scripts/knowledge_publisher.py`; add focused store methods
  rather than a second persistence helper.
- Add-in-place risk: embedding audit paths or rejection policy into
  `HostRuntimeCoordinator` would make host recovery own durable semantics.
- Better file boundary: dedicated publisher plus store transaction and a
  dedicated core-contract lifecycle check.
- Recommendation: add owner file; retain `Learner` as candidate projection
  helper initially; do not refactor unrelated legacy teaching code.

## Tasks

### Task 1: Add Immutable Lifecycle Contracts and Store Transaction

**Files**

- Create: `skill/autonomous-mentor/scripts/knowledge_publisher.py`
- Modify: `skill/autonomous-mentor/scripts/knowledge_schema.py`
- Modify: `skill/autonomous-mentor/scripts/knowledge_store.py`
- Modify: `skill/autonomous-mentor/scripts/learner.py`
- Create: `skill/autonomous-mentor/examples/tests/core_contract/publication_lifecycle_checks.py`
- Move: `skill/autonomous-mentor/examples/tests/core_contract/learning_delta_checks.py` to
  `skill/autonomous-mentor/examples/tests/core_contract/learning_delta_checks.py`
- Create: `docs/aegis/adr/0003-publication-audit-journal.md`

**Why**

The roadmap requires proposed/reviewed/published/rejected/retired lifecycle
states as durable audit records. The current direct delta save proves a valid
change, but cannot prove a rejected attempt or a review-to-publication chain.

**Impact / Compatibility**

This is the persistence-risk slice. Existing topics without an `audit/`
directory remain valid. New lifecycle operations create audit records under the
existing topic lock. No existing durable topic is rewritten merely to add
history.

**Repair Track**

- Root cause: direct `Learner.apply_knowledge_delta()` writes a topic version
  without a first-class candidate or rejection record.
- Canonical owner: `KnowledgePublisher` decides transition; `KnowledgeStore`
  atomically persists it.
- Minimal stable repair: create lifecycle dataclasses/validation, a store
  transaction, and a publisher that reuses the existing candidate projection.
- Compatibility boundary: direct learner application remains available only to
  internal tests until Task 2 switches the host; public execution remains
  unchanged in this task.

**Steps**

1. Write RED checks for one valid publish, skeptic rejection, malformed delta
   rejection, stale-version rejection, duplicate retry, retirement, and
   interrupted publish recovery. Assert that rejection leaves both
   `knowledge.json` bytes and topic version unchanged, and that a successful
   result has exactly one snapshot plus a matching immutable audit chain.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/core_contract/publication_lifecycle_checks.py
   ```

   Expected: non-zero exit because lifecycle contracts, publisher, and audit
   transaction do not yet exist.
3. Add `PublicationState`, `PublicationRecord`, terminal outcome types, and
   strict JSON-compatible validation in `knowledge_schema.py`. Add
   `KnowledgeStore` methods that, while holding `_topic_lock`, append an
   exclusive ordered audit record and save/recover a published topic snapshot.
   Add `KnowledgePublisher.publish_or_reject()` to:

   ```python
   publish_or_reject(
       *,
       topic_id: str,
       base_version: int,
       candidate: dict[str, object],
       review: dict[str, object],
       candidate_id: str,
   ) -> PublicationOutcome
   ```

   It records `proposed`, then `reviewed`, then either `published` or
   `rejected`; it never performs file I/O itself. Extract only candidate
   projection from `Learner` as needed so it can construct a validated next
   `TopicKnowledge` without saving it directly.
4. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/core_contract/publication_lifecycle_checks.py
   python3 skill/autonomous-mentor/examples/tests/core_contract/learning_delta_checks.py
   python3 skill/autonomous-mentor/examples/tests/core_contract/knowledge_store_checks.py
   python3 skill/autonomous-mentor/examples/tests/core_contract/convergence_checks.py
   ```

   Expected: lifecycle cases pass; existing delta/store/convergence semantics
   stay green.
5. Record ADR 0003 with artifact layout, transition rules, crash recovery, and
   one-writer boundary. Commit this task.

**Required Stop**

Stop before Task 2 if recovery cannot distinguish a completed topic snapshot
from a partial audit transition under one lock. Do not invent a second journal
writer or mark a topic published without the matching record.

### Task 2: Route Host Commit and Recovery Through the Publisher

**Files**

- Modify: `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- Modify: `skill/autonomous-mentor/scripts/vnext_host.py` only if its outcome
  projection needs the terminal publication result
- Move and modify:
  `skill/autonomous-mentor/examples/tests/adapter/vnext_host_recovery_checks.py` to
  `skill/autonomous-mentor/examples/tests/adapter/vnext_host_recovery_checks.py`
- Move and modify:
  `skill/autonomous-mentor/examples/tests/behavior/autonomous_loop_checks.py` to
  `skill/autonomous-mentor/examples/tests/behavior/autonomous_loop_checks.py`
- Create:
  `skill/autonomous-mentor/examples/tests/adapter/publication_host_recovery_checks.py`

**Why**

The public path must not retain a second durable commit owner after Task 1.
Commit marker retries must recognize both published and rejected terminal
records without duplicate audit writes.

**Impact / Compatibility**

Public command names and envelopes remain unchanged. The only behavioral
extension is durable lifecycle evidence. `assess_convergence` follows only a
published candidate; a rejected candidate must return the explicitly designed
pending/error outcome without appending a false convergence record.

**Repair Track**

- Root cause: `HostRuntimeCoordinator.commit_learning()` directly invokes
  `Learner.apply_knowledge_delta()`.
- Canonical owner: `KnowledgePublisher`.
- Minimal stable repair: derive a deterministic candidate ID from the existing
  host payload/commit marker and delegate one terminal decision.
- Retirement track: remove the direct host-to-learner save call; retain
  `Learner` only as candidate projection logic.

**Steps**

1. Extend adapter RED checks to require a proposed/reviewed/published chain for
   a recovered host commit, exactly one terminal record on retry, and no topic
   version increase for a skeptic-rejected candidate. Require
   `assess_convergence` only after a published record.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/adapter/publication_host_recovery_checks.py
   ```

   Expected: non-zero exit because the host still directly saves through
   `Learner`.
3. Inject `KnowledgePublisher` into `HostRuntimeCoordinator`, replace direct
   `Learner.apply_knowledge_delta()` invocation in `commit_learning()`, and
   extend the commit-marker recovery predicate to verify the terminal audit
   record plus the matching published snapshot. Keep pending cursor payloads
   free of topic graphs and keep existing request names unchanged.
4. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/adapter/publication_host_recovery_checks.py
   python3 skill/autonomous-mentor/examples/tests/adapter/vnext_host_recovery_checks.py
   python3 skill/autonomous-mentor/examples/tests/behavior/autonomous_loop_checks.py
   python3 skill/autonomous-mentor/examples/tests/adapter/work_host_vnext_checks.py
   python3 skill/autonomous-mentor/examples/tests/adapter/cli_route_baseline_checks.py
   ```

   Expected: recovery is at-most-once for both topic and audit chain; public
   route ownership remains vNext.
5. Search for direct public-path delta save and commit:

   ```bash
   grep -R -n "apply_knowledge_delta" skill/autonomous-mentor/scripts
   ```

   Expected: no call from `autonomous_runtime.py`; only candidate-projection
   and non-public test references remain. Commit this task.

**Required Stop**

Stop if the existing public JSON envelope must change to expose audit data, or
if rejected candidates cannot return a deterministic recoverable state without
altering the documented host contract. That is a public-contract design review,
not a local patch.

### Task 3: Directly Migrate All Checks to Four Owned Layers

**Files**

- Create:
  `skill/autonomous-mentor/examples/tests/{core_contract,behavior,migration,adapter}/__init__.py`
- Move all check scripts from `skill/autonomous-mentor/examples/` into exactly
  one of the four layer directories.
- Move `examples/eval/`, `examples/eval_vnext/`, `eval_suite.py`,
  `eval_vnext_suite.py`, `realhost_*`, and `scripted_judge.py` under
  `examples/tests/behavior/`; move `smoke_run.py` under
  `examples/tests/adapter/`.
- Move shared fixture modules from `examples/fixtures/` to
  `examples/tests/fixtures/` where they support only the layered checks.
- Create: `skill/autonomous-mentor/examples/tests/layer_manifest.json`
- Create: `skill/autonomous-mentor/examples/tests/run_layer.py`
- Modify:
  `skill/autonomous-mentor/examples/tests/adapter/package_vnext_checks.py`
- Modify:
  `skill/autonomous-mentor/sessions/knowledge-first-vnext/validation_manifest.json`
- Modify active sources/docs that execute checks:
  `skill/autonomous-mentor/SKILL.md`,
  `docs/aegis/specs/2026-09-22-publication-lifecycle-and-test-layering-design.md`,
  `docs/aegis/plans/2026-09-21-post-m05-compatibility-window-retirement.md`,
  `docs/aegis/reports/2026-09-22-refactor-roadmap-progress.md`, and
  `docs/aegis/work/2026-09-21-compatibility-window/`.

**Why**

The roadmap requires independently owned core-contract, behavior, migration,
and adapter suites. Keeping old paths plus wrappers would retain a false
compatibility boundary and make retirement proof impossible.

**Impact / Compatibility**

This is an internal repository-path contract change. Do not edit historical M0
and M0.5 evidence logs merely to replace historical commands. Update only live
entry points, manifests, current plans, current report, and current
compatibility-window records.

**Steps**

1. Create `layer_manifest.json` that assigns every active executable check to
   exactly one layer and names a command for each layer. Add RED checks in
   `run_layer.py` that fail if a module is unassigned, multiply assigned, or an
   old root-level `*_checks.py` wrapper remains.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/run_layer.py --verify-manifest
   ```

   Expected: non-zero exit because current checks are root-level and no layer
   manifest exists.
3. Move modules directly: core contract owns schema/store/index/delta/
   convergence checks; behavior owns autonomous loop, acceptance, eval,
   real-host, and judge assets; migration owns v1 checks; adapter owns CLI,
   query, Work-host, host-recovery, package, and smoke assets. Repair imports
   using package-relative or explicit `SKILL_ROOT` paths, move fixtures only to
   `examples/tests/fixtures`, and update package/validation manifests plus live
   invocation documentation. Do not create files at former script paths.
4. Run all layers from a fresh caller:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/run_layer.py --layer core_contract
   python3 skill/autonomous-mentor/examples/tests/run_layer.py --layer behavior
   python3 skill/autonomous-mentor/examples/tests/run_layer.py --layer migration
   python3 skill/autonomous-mentor/examples/tests/run_layer.py --layer adapter
   ```

   Expected: every declared module passes under exactly one layer.
5. Prove direct migration and commit:

   ```bash
   find skill/autonomous-mentor/examples -maxdepth 1 -name '*_checks.py' -print
   grep -R -n 'examples/[a-z_]*_checks\.py' skill/autonomous-mentor \
     docs/aegis --exclude-dir=.git || true
   ```

   Expected: no root-level check wrappers and no active contract reference to
   an old path. Historical evidence references are allowed only under
   `docs/aegis/work/2026-09-17-knowledge-first-vnext/`.

**Required Stop**

Stop only if a non-repository consumer of an old path is demonstrated. Record
the consumer and decide a bounded `compat-exception`; do not silently recreate
the old path.

### Task 4: Full Regression, Sandbox Acceptance, and Compatibility Decision

**Files**

- Modify: `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- Modify:
  `docs/aegis/work/2026-09-21-compatibility-window/{20-checkpoint.md,90-evidence.md}`
- Modify:
  `docs/aegis/reports/2026-09-22-refactor-roadmap-progress.md`
- Modify: `docs/aegis/INDEX.md` if new ADR/work records are added.

**Why**

Lifecycle and test migration are complete only if the system passes from a
fresh sandbox and compatibility surfaces receive a current evidence-based
classification. This task records decisions; it does not delete legacy source.

**Impact / Compatibility**

No public alias or legacy source deletion occurs. `ask` remains deferred until
a concrete release/version identifier exists. Internal candidates receive one
of `extract`, `retain with trigger`, or `defer with evidence gap`.

**Steps**

1. Run complete layered acceptance and package/sandbox checks:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/run_layer.py --all
   python3 skill/autonomous-mentor/examples/tests/adapter/package_vnext_checks.py
   ```

   Expected: all layer modules and package checks pass from a rebuilt sandbox;
   frozen and user-level hashes remain unchanged.
2. Run public boundary and bytecode checks from a fresh temporary caller:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/adapter/cli_route_baseline_checks.py
   python3 skill/autonomous-mentor/examples/tests/adapter/query_checks.py
   python3 skill/autonomous-mentor/examples/tests/migration/migration_v1_checks.py
   python3 skill/autonomous-mentor/examples/tests/migration/v1_import_surface_checks.py
   if find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc' | grep -q .; then exit 1; fi
   ```

   Expected: public ownership, stateless query, v1 importer, and bytecode
   boundaries pass.
3. Record a per-surface compatibility decision: `ask` remains release-bound;
   `SessionState` moves to a separately planned parser extraction slice;
   `MentorLoop` and evaluator retirement remain deferred until parser and
   archive evidence are complete. Update the progress score with evidence, not
   aspiration.
4. Run a source ownership scan:

   ```bash
   grep -R -nE 'MentorLoop|_run_legacy|_bind_runtime_reference' \
     skill/autonomous-mentor/scripts/cli.py && exit 1 || true
   grep -R -n 'apply_knowledge_delta' \
     skill/autonomous-mentor/scripts/autonomous_runtime.py && exit 1 || true
   ```

   Expected: public CLI has no legacy default owner; runtime has no direct
   durable learner commit.
5. Commit documentation/evidence only after all checks pass. Mark this plan
   complete as an implementation milestone, not as legacy retirement.

**Required Stop**

Stop and diagnose if any fresh-caller, sandbox, package, v1 migration, or
public-route check fails. Do not collapse the failure into a broad legacy
deletion or alter persistent user data.

## Anti-Entropy Declaration

- Deletion Class: `code-retirement` for old test paths; future
  `contract-carrying code` retirement remains out of scope.
- Old Path/Object: root-level internal check scripts and direct
  host-to-learner durable commit.
- New Canonical Owner: layered test tree, `KnowledgePublisher`, and
  `KnowledgeStore`.
- Expected Preserved Behavior: vNext public learning, published query results,
  at-most-once commit, one-way v1 import, and sandbox package integrity.
- Expected Retired Behavior: old internal test paths and direct public runtime
  durable commit through `Learner`.
- External Boundary Touched: no known external boundary; a proven consumer
  triggers a bounded compatibility decision.
- Source-of-Truth Data Risk: possible only for new audit writes; no existing
  user data deletion or rewrite is permitted.
- User Confirmation Required: no for source/test migration; yes if scope ever
  changes to persistent-state deletion or historical user-data rewrite.

## Verification

Task-specific RED/GREEN commands are defined above. The final gate is:

```bash
python3 skill/autonomous-mentor/examples/tests/run_layer.py --all
python3 skill/autonomous-mentor/examples/tests/adapter/package_vnext_checks.py
```

plus fresh-caller public route, query, migration, and bytecode checks from Task
4. Expected result: all exit 0, no old root-level check wrappers, no public
legacy route, no direct host durable learner commit, and no bytecode artifacts.

## Risks and Rollback

- Audit transaction mismatch: revert the focused source commit if development
  or sandbox recovery fails; do not delete topic files.
- Rejection audit over-collection: stop if the record requires raw full topic
  content or sensitive paths; revise the schema before writing more records.
- Test path breakage: fix in-repository callers in the same task; no wrapper
  creation.
- External old-path consumer: pause for `compat-exception` decision with
  evidence and a retirement trigger.
- User durable data risk: stop and request scoped confirmation before any
  destructive action.

## Completion Boundary

This plan completes the publication lifecycle and four-layer test architecture
only after Task 4 fresh-caller and sandbox evidence passes. It does not
authorize legacy runtime, `ask`, or user-data deletion.

## Implementation Milestone Record

Completed 2026-09-22 on `docs/compatibility-window`:

- Tasks 1-3 implemented the store-owned publication audit lifecycle,
  publisher-owned host commit, and direct four-layer test-tree migration.
- Task 4 passed full layered acceptance, package sandbox acceptance, public
  route/query checks, v1 migration checks, bytecode absence, and negative
  source-ownership scans.
- Compatibility classification retains `ask` as release-bound, plans
  `SessionState` parser extraction separately, and defers `MentorLoop` plus
  evaluator retirement pending parser and archive evidence.

This is an implementation milestone, not authorization to delete legacy source
or persistent user data.
