# Autonomous Mentor Refactor Roadmap Progress Report

## Snapshot

- Assessment date: 2026-09-22.
- Assessed branch: `docs/compatibility-window` at `ee45e8c` before this
  acceptance-record commit.
- Runtime baseline on `main`: `b433904` (`M0.5 vNext host baseline`).
- Reference roadmap: `Autonomous Mentor 重构路线图`, version 1.0
  (2026-09-18).
- Overall roadmap completion: **85%**.

The percentage is a weighted implementation assessment, not a count of files
or passing scripts. It gives greatest weight to the roadmap's two highest-risk
outcomes: one public learning owner and durable knowledge integrity. It does
not treat retained legacy code, an undocumented lifecycle, or unlayered tests
as complete merely because the public path works.

## Executive Summary

The project has completed the architectural correction that matters most:
public learning now has one canonical path,

```text
VNextHost -> HostRuntimeCoordinator -> KnowledgeStore
```

`init`, `learn`, `step`, `cancel`, and `state` are owned by that path.
`query` is stateless, and `ask` is a byte-equivalent compatibility alias.
The public CLI does not import or instantiate `MentorLoop`. Durable knowledge
is versioned and protected by validation, optimistic conflict rejection, source
hash checks for v1 import, and a skeptic-before-commit sequence.

The publication lifecycle and test layering are now implemented and accepted.
The remaining work is retirement-oriented:

1. Extract the v1 import parser from the full teaching-era `SessionState`.
2. Classify and retire legacy runtime/evaluator assets through separate,
   evidence-backed slices.
3. Obtain release and observation evidence before making a public `ask`
   retirement decision.

No current evidence justifies deleting public `ask`; the project has no declared
release/version boundary or external-consumer inventory. That does not block
internal compatibility classification or parser extraction.

## Scoring Method

| Area | Weight | Completion | Weighted contribution |
| --- | ---: | ---: | ---: |
| M0: baseline and default-entry decision | 15 | 100% | 15.0 |
| M1: host adapter and recovery | 20 | 85% | 17.0 |
| M2: knowledge-quality publication boundary | 25 | 90% | 22.5 |
| M3: responsibility and compatibility boundary | 20 | 60% | 12.0 |
| M4: evaluation-asset layering | 10 | 90% | 9.0 |
| Integration acceptance and freeze | 10 | 90% | 9.0 |
| **Total** | **100** |  | **84.5%** |

The host and default-entry scores measure outcome parity with the roadmap, not
literal file names. The quality, compatibility, and test-layer scores require
the explicit boundaries requested by the roadmap, which are only partial today.

## Roadmap Phase Mapping

### M0: Baseline Decision and Unique Default Path

**Status: complete (100%).**

Completed outcomes:

- ADR 0002 records `VNextHost` as the default public learning owner and makes
  `MentorLoop` non-default.
- The normalized route fixture covers all eight public commands.
- `cli_route_baseline_checks.py` proves the owner mapping and confirms that the
  public CLI has no `MentorLoop`, `_run_legacy`, or
  `_bind_runtime_reference` reference.
- The M0 schema matrix distinguishes `SessionState` runtime concerns from
  `TopicKnowledge` durable concerns.
- M0.5 implementation moved the public commands to the canonical owner and
  refreshed the fixture.

Evidence:

- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `skill/autonomous-mentor/examples/tests/adapter/cli_route_baseline_checks.py`

Current verification: route baseline passed **4/4**.

### M1: Host Adapter and Recovery

**Status: substantially complete (85%).**

Completed outcomes:

- `VNextHost` provides public `initialize`, `learn`, `step`, `cancel`, and
  `state` operations.
- `HostRuntimeCoordinator` owns stage progression and commit order.
- Runtime persistence contains `HostRun` and `PendingCursor` references rather
  than copied durable knowledge.
- Initialization is idempotent for the same run.
- Post-save retry recognizes the commit marker and does not replay a durable
  commit.
- Work-host contracts retain JSON envelopes and recovery semantics.

Evidence:

- `skill/autonomous-mentor/scripts/vnext_host.py`
- `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- `skill/autonomous-mentor/examples/tests/adapter/vnext_host_recovery_checks.py`
- `skill/autonomous-mentor/examples/tests/adapter/work_host_contract_checks.py`

Current verification: host recovery passed **12/12**.

Gap against the reference design:

- The roadmap named distinct `host_facade.py` and `protocol_errors.py` modules.
  Their behavioral responsibilities exist, but are not separated under those
  explicit owner files.
- Error recovery remains verified by focused host checks rather than a
  standalone structured error taxonomy.

### M2: Knowledge Quality and Publication Boundary

**Status: substantially complete (90%).**

Completed outcomes:

- Durable `TopicKnowledge` is versioned and validated by `KnowledgeStore`.
- `LearningDelta` supports new, revised, disputed, and retired claim effects.
- Evidence, counterexamples, gaps, cross-reference integrity, and optimistic
  version conflicts are validated.
- The autonomous path includes skeptic review before `commit_learning`.
- Commit order supports at-most-once durable application through a marker.
- Convergence is a separate deterministic owner.
- `KnowledgePublisher` now owns explicit
  `proposed -> reviewed -> published/rejected -> retired` lifecycle policy.
- `KnowledgeStore` remains the only durable writer and appends immutable audit
  records with the published topic projection under its topic lock.
- Publication checks cover skeptic and malformed-candidate rejection,
  stale-version rejection, duplicate retries, retirement, and interrupted
  publication recovery.

Evidence:

- `skill/autonomous-mentor/scripts/knowledge_schema.py`
- `skill/autonomous-mentor/scripts/knowledge_store.py`
- `skill/autonomous-mentor/scripts/knowledge_publisher.py`
- `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- `skill/autonomous-mentor/examples/tests/core_contract/learning_delta_checks.py`
- `skill/autonomous-mentor/examples/tests/core_contract/convergence_checks.py`
- `skill/autonomous-mentor/examples/tests/core_contract/publication_lifecycle_checks.py`

Remaining gap against the reference design:

- Candidate projection remains a focused publisher input rather than a
  separately persisted candidate-area store; current immutable records are
  sufficient for attempted-update auditability.

### M3: Responsibility and Compatibility Boundaries

**Status: partially complete (60%).**

Completed outcomes:

- Public CLI execution no longer imports or instantiates `MentorLoop`.
- `query.py` is a stateless read owner.
- The v1 importer is explicit, one-way, source-read-only, and writes only
  through `KnowledgeStore`.
- Re-import cannot overwrite a topic that has evolved under vNext.
- The new v1 input-surface contract classifies every top-level `SessionState`
  field as `mapped`, `provenance_only`, or `validated_only`.
- The compatibility window now records per-surface outcomes without authorizing
  public alias or legacy-source deletion.

Evidence:

- `docs/aegis/adr/0001-one-way-v1-import-boundary.md`
- `skill/autonomous-mentor/scripts/migrate_v1.py`
- `skill/autonomous-mentor/scripts/v1_import_record.py`
- `skill/autonomous-mentor/examples/tests/migration/migration_v1_checks.py`
- `skill/autonomous-mentor/examples/tests/migration/v1_import_surface_checks.py`

Current verification: v1 migration passed **8/8**; the input-surface contract
also passed.

Gaps:

- `migrate_v1.py` still validates and imports full `SessionState`; the narrow
  parser/DTO boundary is documented but not extracted.
- `loop.py`, `schema.py`, and `judgments.py` still co-locate historical
  teaching and legacy runtime responsibilities with retained compatibility
  semantics. Their current sizes are 1,364, 846, and 853 lines respectively.
- Historical evaluator assets have not yet received an archive or deletion
  disposition.
- `ask` cannot be retired until a release/version identifier exists and the
  per-surface retirement decision is recorded.

### M4: Evaluation Asset Layering

**Status: substantially complete (90%).**

Completed outcomes:

- Focused checks already exist for routing, query behavior, host recovery,
  migration, schema, store integrity, learning deltas, convergence, autonomous
  loop behavior, packaging, and cross-model evidence.
- Each major verification family has a dedicated script instead of relying on
  one monolithic runner.
- Checks are directly organized under
  `examples/tests/{core_contract,behavior,migration,adapter}`, and
  `run_layer.py --all` reports each layer independently.
- The old root-level internal check paths have no compatibility wrappers.

Gaps:

- No test-duration baseline or intended blast-radius matrix exists.
- Legacy retirement has not demonstrated that it affects only migration and
  adapter suites.

### Integration Acceptance and Freeze

**Status: substantially complete (90%).**

Completed outcomes:

- M0.5 has a Git baseline and fresh isolated-worktree verification.
- The project has verified public routing, stateless query, v1 migration,
- durable initialization, recovery, at-most-once commit, and package/sandbox
  paths in prior acceptance runs.
- No public fallback to `MentorLoop` has been reintroduced.
- The final implementation acceptance passed all four test layers, package
  sandbox checks, public route/query checks, v1 migration checks, bytecode
  absence, and negative source-ownership scans from the isolated worktree.

Remaining conditions for a final roadmap freeze:

- Narrow v1 parser extraction or a documented decision to retain the full
  schema with a new trigger.
- Legacy runtime and evaluator disposition with archive evidence.
- A release/version-bound public `ask` retirement decision.

## Current Verification Snapshot

The following commands were re-run from the isolated worktree for this report:

```bash
python3 skill/autonomous-mentor/examples/tests/adapter/cli_route_baseline_checks.py
python3 skill/autonomous-mentor/examples/tests/adapter/query_checks.py
python3 skill/autonomous-mentor/examples/tests/migration/v1_import_surface_checks.py
python3 skill/autonomous-mentor/examples/tests/migration/migration_v1_checks.py
python3 skill/autonomous-mentor/examples/tests/adapter/vnext_host_recovery_checks.py
python3 skill/autonomous-mentor/examples/tests/run_layer.py --all
python3 skill/autonomous-mentor/examples/tests/adapter/package_vnext_checks.py
```

Results:

| Check | Result | What it establishes |
| --- | --- | --- |
| CLI route baseline | 4/4 pass | public owners and `ask` alias behavior |
| Stateless query | 5/5 pass | no learner mutation, no teaching action, alias parity |
| v1 input surface | pass | complete top-level `SessionState` classification |
| v1 migration | 8/8 pass | one-way mapping, rejection, race, and overwrite guarantees |
| Host recovery | 12/12 pass | durable initialization and commit-marker recovery |
| Layered acceptance | 7/7, 9/9, 2/2, 8/8 pass | direct core-contract, behavior, migration, and adapter tree |
| Package sandbox | 14/14 pass | rebuilt sandbox, explicit root, hash, cache, and package boundaries |
| Negative boundaries | pass | no bytecode, public legacy owner, or direct runtime learner commit |

These are current point-in-time checks. They prove the lifecycle and four-layer
test migration acceptance, but do not prove parser extraction, archive
disposition, or public alias retirement.

## Compatibility and Retirement State

| Surface | Current owner/status | Decision state | Required next evidence |
| --- | --- | --- | --- |
| `ask` | public `query` alias | retain, release-bound | declared release/version plus no active dependency evidence |
| former `state.state` shape | no current public writer | classify | document any actual reader or retire by source proof |
| `SessionState` for v1 import | read-only importer input | separate extraction slice | parser parity matrix and narrow DTO plan |
| `MentorLoop` runtime | non-public legacy candidate | defer | importer decoupling and archived evaluator disposition |
| teaching evaluators | historical evidence candidate | defer | archive/disposition decision |

There is no telemetry service, external-consumer inventory, Git tag, remote
release, or declared public version. Absence of such telemetry is not proof of
no users, but it is also not a reason to preserve a second public learning
owner. It prevents only public alias deletion, not internal classification.

## Principal Risks

| Risk | Impact | Current control | Remaining work |
| --- | --- | --- | --- |
| Parser extraction loses v1 edge cases | import regression | 8 migration cases and input-surface contract | expand parity matrix before changing parser |
| Broad legacy deletion conflates concerns | runtime/import breakage | retirement plan requires separate slices | extract parser before runtime deletion |
| Publication audit recovery regresses | durable trace inconsistency | publisher/store transaction and lifecycle checks | retain fresh sandbox recovery coverage |
| Tests remain coupled by convention | high change blast radius | direct four-layer runner | add duration and blast-radius baselines |
| External alias dependency is unknown | CLI breakage | no deletion authorized | bind decision to declared release/version |

## Recommended Execution Order

1. **v1 parser extraction slice:** strict TDD parity tests, then introduce a
   narrow immutable import record/parser. Do not remove `SessionState` yet.
2. **Retirement slices:** only after parser extraction and archival decisions;
   handle `ask` separately when a release/version exists.
3. **Final integration freeze:** repeat recovery, public route, migration,
   lifecycle, and sandbox checks from a fresh caller after retirement work.

## Completion Criteria

The roadmap should be considered complete only when all of the following are
true:

- A single public learning owner and a single durable writer remain verified.
- v1 import no longer depends on the teaching-era runtime schema, or an ADR
  records why that dependency is intentionally retained.
- Legacy runtime and evaluator assets have a completed retain/archive/delete
  disposition.
- Public alias retirement is tied to an actual release/version decision.
- A fresh sandbox acceptance verifies all retained contracts without legacy
  fallback.
