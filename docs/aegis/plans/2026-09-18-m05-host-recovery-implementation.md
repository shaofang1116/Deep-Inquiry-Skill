# M0.5 Host Recovery and Durable Topic Initialization Plan

## Goal

Replace the public learning command path with resumable vNext host execution:
durable topic initialization, one-judgment-per-step recovery, and at-most-once
durable delta application.

## Execution Status

Completed on the Git integration baseline.

| Task | Status | Evidence |
| --- | --- | --- |
| 1. Durable origin and runtime cursor contracts | Complete | `vnext_host_recovery_checks.py` |
| 2. Idempotent durable topic initialization | Complete | recovery, store, and migration checks |
| 3. Resumable progression and at-most-once commits | Complete | recovery and autonomous loop checks |
| 4. Public CLI vNext host routing | Complete | Work-host and route baseline checks |
| 5. Isolation, ADR, and retirement verification | Complete | isolated caller and sandbox acceptance |

Integration commits: `b433904` captures the canonical M0.5 baseline and
`06e9ff7` records its Git-baseline revalidation. The next work is not another
M0.5 implementation task: it requires a separately scoped read-only
compatibility-window retirement decision under ADR 0002.

## Architecture

- `KnowledgeStore` remains the only durable writer.
- `TopicKnowledge` remains the canonical current knowledge state.
- A new `autonomous_runtime.py` owns vNext stage transition, recovery cursor
  validation, commit ordering, and result creation.
- `AutonomousLearningLoop` delegates to the new runtime for direct scripted
  execution, retaining one canonical learning semantics owner.
- A new `vnext_host.py` owns file-host command adaptation only.
- `cli.py` parses, emits envelopes, and dispatches public commands; it does not
  own learning policy or durable writes.

## Tech Stack

Python 3.10+ standard library, canonical JSON files, existing `KnowledgeStore`,
existing `StateStore` runtime file primitives, and no model SDK.

## Baseline / Authority Refs

- `docs/aegis/specs/2026-09-18-m05-host-recovery-design.md`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `docs/aegis/specs/2026-09-18-m0-entry-truth-brief.md`
- `docs/2026-09-17-knowledge-first-skill-plan.md`
- `ISOLATION.md`

## Compatibility Boundary

- Preserve the JSON host envelope fields and pending/error process exit classes.
- Retain `query`, `ask`, and `demo` behavior.
- Do not import or instantiate `MentorLoop` on the public `init`, `learn`,
  `step`, `cancel`, or `state` path.
- Do not read, migrate, or delete legacy runtime sessions.
- Do not add a fallback to legacy storage, legacy loop, or project-local
  knowledge.
- Do not install, package, or alter frozen Skills.

## TDD Route

- Mode: `auto`
- Decision: `strict`
- Reason: public command routing, persistence, crash recovery, and a durable
  schema extension are shared contract changes.
- Verification: focused RED/GREEN for each task, then host/query/loop/migration
  regressions and isolated bytecode scan.

## Architecture Integrity Lens

- Invariant: the runtime cursor is not knowledge truth; it can only reference
  the canonical durable topic and the next uncommitted stage.
- Canonical owner / contract: `autonomous_runtime.py` carries stage semantics
  and commit ordering; `vnext_host.py` carries host serialization only.
- Responsibility overlap: no CLI conditional may independently select gaps,
  validate autonomous responses, or decide post-commit recovery.
- Higher-level simplification: extract vNext runtime from the 1,395-line
  legacy/vNext `loop.py` instead of adding another public-path branch there.
- Retirement / falsifier: source checks must fail if public learning dispatch
  imports or instantiates `MentorLoop`.
- Verdict: proceed.

## Plan-Time Complexity Check

- Target files: `loop.py` (1,395 lines), `cli.py` (364 lines),
  `judgments.py` (765 lines), `knowledge_schema.py` (726 lines).
- Existing pressure: `loop.py` already mixes legacy and vNext control flow;
  `judgments.py` holds two unrelated protocol registries.
- Owner fit: recovery state is neither a CLI concern nor legacy loop behavior.
- Better file boundary: add `autonomous_runtime.py` and `vnext_host.py`;
  keep edits to existing files narrow and declarative.
- Recommendation: add owner files; do not add the coordinator to `loop.py`.

## Retirement Decision

- Deletion class: `code-retirement` and `contract-carrying code`.
- Old path: public command dispatch through `_run_legacy()` / `MentorLoop`.
- New canonical owner: vNext host plus resumable autonomous runtime.
- Expected preserved behavior: JSON envelope, explicit roots, named runtime
  paths, stateless queries, and `demo`.
- Expected retired behavior: public default learning path built on
  `SessionState`, teaching-era judgments, and legacy pending state.
- External boundary touched: yes, the public CLI file protocol.
- Source-of-truth data risk: none; no topic or legacy session is deleted.
- Path: `compat-exception` only for explicit v1 import and non-default
  compatibility evidence; no public fallback.

## Verification

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
python3 skill/autonomous-mentor/examples/autonomous_loop_checks.py
python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Expected: focused check and all regressions exit 0; the bytecode scan has no
output. The final route fixture is intentionally updated to record M0.5 vNext
ownership after source and command behavior prove the switch.

## Tasks

### 1. Define the durable origin and runtime cursor contracts

**Files**

- Modify: `skill/autonomous-mentor/scripts/knowledge_schema.py`
- Create: `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- Create: `skill/autonomous-mentor/examples/vnext_host_recovery_checks.py`
- Modify: `skill/autonomous-mentor/examples/knowledge_schema_checks.py`

**Why**

An interrupted initialization must be distinguishable from an unrelated topic,
and a host cursor must be validated before it controls recovery.

**Impact / Compatibility**

`origin_metadata` is optional and provenance-only. Existing topic fixtures,
v1 importer output, and convergence behavior must remain valid without it.

**Steps**

1. Write a focused `vnext_host_recovery_checks.py` assertion that imports the
   missing runtime coordinator, attempts to create an initialized topic, and
   fails because the coordinator and `origin_metadata` do not exist.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
   ```

   Confirm failure names the absent vNext runtime contract, not a fixture or
   import-path error.
3. Add optional JSON-compatible `origin_metadata` to `TopicKnowledge`, include
   it in `to_dict()` / `from_dict()`, and extend schema checks for round-trip
   preservation and legacy omission.
4. Create `autonomous_runtime.py` with validated dataclasses for a host run and
   pending cursor. Required cursor fields: schema version, `runtime_kind`,
   `run_id`, `topic_id`, canonical absolute `knowledge_root`, stage, expected
   durable version, commit marker, and stage-local payload. Reject unknown
   runtime kinds, relative roots, malformed UUID-like run IDs, unknown stages,
   and payloads containing a copied full topic graph.
5. Re-run the focused check; it must pass the topic-origin and cursor
   validation cases.
6. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/knowledge_schema_checks.py
   ```

   Confirm existing schema cases remain green.

### 2. Implement idempotent durable topic initialization

**Files**

- Modify: `skill/autonomous-mentor/scripts/judgments.py`
- Modify: `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- Modify: `skill/autonomous-mentor/examples/vnext_host_recovery_checks.py`

**Why**

The public `init` command must create a real, validated version-1 topic rather
than a legacy session with a detached topic reference.

**Impact / Compatibility**

The new `initialize_topic` host judgment is public-host-only. Direct
`AutonomousLearningLoop` scripted tests retain their current internal
`anchor` acknowledgement contract.

**Steps**

1. Add a focused assertion that `initialize_topic` emits a request with title,
   normalized proposition, dimensions, and full entity collections; assert an
   invalid cross-reference leaves no topic behind.
2. Run the focused check and confirm RED names the missing initialization
   request or durable creation behavior.
3. Add the `initialize_topic` request builder and validator to
   `judgments.py`. Its response must produce a valid `TopicKnowledge` version
   1 with initial timestamps and `origin_metadata.host_run_id`.
4. Implement coordinator initialization: write an initialization pending
   cursor first; on valid response call `KnowledgeStore.create()`. On retry,
   accept an existing version-1 topic only when its `origin_metadata.host_run_id`
   matches; reject every other existing topic.
5. Re-run the focused check; it must prove initial creation, invalid-response
   rollback, same-run retry idempotency, and unrelated-topic overwrite
   rejection.
6. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/knowledge_store_checks.py
   python3 skill/autonomous-mentor/examples/migration_v1_checks.py
   ```

   Confirm storage and one-way import boundaries remain green.

### 3. Implement resumable stage progression and at-most-once commits

**Files**

- Modify: `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- Modify: `skill/autonomous-mentor/scripts/loop.py`
- Modify: `skill/autonomous-mentor/examples/autonomous_loop_checks.py`
- Modify: `skill/autonomous-mentor/examples/vnext_host_recovery_checks.py`

**Why**

`AutonomousLearningLoop.run()` currently requires a synchronous callback and
cannot resume at the file-host judgment boundary.

**Impact / Compatibility**

Direct loop callers retain `run(topic_id)` behavior. They exercise the same
runtime transition functions through an in-memory scripted-response adapter.

**Steps**

1. Add focused cases that stop after each pending stage, reconstruct a fresh
   coordinator from runtime files, and resume. Include a forced interruption
   before durable commit and a simulated interruption after durable save but
   before the next request projection.
2. Run the focused check and confirm RED identifies missing stage-resume or
   duplicate-commit protection.
3. Implement coordinator transitions:
   `map_knowledge`, deterministic `select_gap`, `plan_investigation`,
   `integrate_learning`, `skeptic_review`, durable commit,
   `assess_convergence`, and `checkpoint_or_complete`. Validate every agent
   response before the transition. Persist an intent cursor before a commit and
   a post-commit marker after it; use the marker plus durable version to
   resume assessment instead of reapplying the integration.
4. Refactor `AutonomousLearningLoop.run()` into a thin scripted-response driver
   over the coordinator. Do not duplicate stage logic in `loop.py`.
5. Re-run the focused check; it must prove one response per host step, no
   durable write before a valid integration/skeptic pair, no duplicate version
   after post-commit recovery, and deterministic conflict error for an
   unexpected external version.
6. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/autonomous_loop_checks.py
   python3 skill/autonomous-mentor/examples/convergence_checks.py
   python3 skill/autonomous-mentor/examples/learning_delta_checks.py
   ```

   Confirm autonomous sequencing, stopping policy, and delta semantics remain
   green.

### 4. Switch public CLI commands to the vNext host adapter

**Files**

- Create: `skill/autonomous-mentor/scripts/vnext_host.py`
- Modify: `skill/autonomous-mentor/scripts/cli.py`
- Modify: `skill/autonomous-mentor/examples/work_host_vnext_checks.py`
- Modify: `skill/autonomous-mentor/examples/cli_route_baseline_checks.py`
- Modify: `skill/autonomous-mentor/examples/vnext_host_recovery_checks.py`

**Why**

The public entry must reach the vNext coordinator rather than binding durable
references into a legacy pending envelope.

**Impact / Compatibility**

Envelope keys, explicit root requirements, `query` / `ask`, `demo`, and
pending/error exit classes remain stable. The runtime state body changes from
legacy `SessionState` to vNext host-run reference.

**Steps**

1. Extend focused host cases to assert that public `init` returns
   `initialize_topic` pending, public `step` consumes its response, public
   `learn` creates/resumes vNext stage pending, and `state` reports the vNext
   run reference and canonical topic version.
2. Run the focused check and confirm RED identifies legacy public dispatch.
3. Implement `vnext_host.py` as the only adapter between `StateStore` runtime
   paths and `autonomous_runtime.py`. It may write runtime JSON but cannot
   write `knowledge.json` directly.
4. Change `cli.py` dispatch for `init`, `learn`, `step`, `cancel`, and `state`
   to use `vnext_host.py`. Remove `_bind_runtime_reference()` and prevent
   public command branches from importing `MentorLoop`. Keep the legacy
   dispatcher only for `demo` until a later explicit retirement slice.
5. Update host and route checks to assert the new owners and output semantics.
   Add an AST negative assertion that public branches contain no `MentorLoop`
   instantiation.
6. Re-run:

   ```bash
   python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
   python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
   python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
   ```

   Confirm the focused recovery and public route suites pass.

### 5. Run isolated regression, documentation, and retirement verification

**Files**

- Modify: `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- Modify: `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- Modify: `docs/aegis/work/2026-09-17-knowledge-first-vnext/20-checkpoint.md`
- Modify: `docs/aegis/work/2026-09-17-knowledge-first-vnext/90-evidence.md`

**Why**

The route switch is not complete until the new main path, retained
compatibility boundary, and unresolved legacy retirement window are auditable.

**Impact / Compatibility**

Documentation records the switch; it does not authorize deletion, packaging,
or installation.

**Steps**

1. Run all M0.5-focused checks from an isolated temporary caller directory and
   confirm the pre-final regression is green.
2. Refresh a disposable sandbox from the vNext development source. Run the
   focused recovery suite and its public CLI flows in the sandbox workspace
   using an explicit sandbox knowledge root.
3. Update the golden fixture to vNext ownership only after source and runtime
   behavior prove it. Update ADR 0002 status from implementation deferred to
   implementation accepted, while retaining its compatibility-window retirement
   trigger.
4. Record exact RED/GREEN commands, recovery scenarios, source route evidence,
   sandbox results, uncovered scope, and no-bytecode scan in the work evidence.
5. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
   python3 skill/autonomous-mentor/examples/autonomous_loop_checks.py
   python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
   python3 skill/autonomous-mentor/examples/query_checks.py
   python3 skill/autonomous-mentor/examples/migration_v1_checks.py
   python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
   find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
   ```

   Confirm all Python commands exit 0 and the final scan has no output.
6. Verify the retirement boundary with source and command checks: `init`,
   `learn`, `step`, `cancel`, and `state` have no main-path `MentorLoop`
   import/instantiation; `demo` remains the only temporary legacy dispatcher;
   legacy source and persistent user data remain intact.

## Risks and Rollback

- Risk: a crash between durable save and pending update. Mitigation: explicit
  pre-commit intent and post-commit marker verified against durable version.
- Risk: partial refactor changes direct loop semantics. Mitigation: direct
  scripted loop tests run against the shared coordinator.
- Risk: accidental legacy fallback. Mitigation: AST and command-level negative
  checks, with no fallback code path.
- Risk: external CLI client expects legacy `state.state` shape. M0.5 preserves
  the outer host envelope but intentionally replaces that inner state with a
  vNext runtime reference; this is the explicit public contract change.
- Rollback: restore the previous vNext development source only if focused and
  sandbox acceptance fail. Do not modify frozen Skills, user installations, or
  durable user knowledge as part of rollback.

## Completion Boundary

M0.5 is complete only when every acceptance item in
`2026-09-18-m05-host-recovery-design.md` has fresh development and sandbox
evidence. It does not complete legacy source deletion, compatibility-window
closure, archive generation, or user-level installation.
