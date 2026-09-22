# Autonomous Mentor Refactor Roadmap Progress Report

## Snapshot

- Assessment date: 2026-09-22.
- Assessed branch: `docs/compatibility-window` at `2f6c9e6`.
- Runtime baseline on `main`: `b433904` (`M0.5 vNext host baseline`).
- Reference roadmap: `Autonomous Mentor 重构路线图`, version 1.0
  (2026-09-18).
- Overall roadmap completion: **67%**.

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

The remaining work is principally structural and retirement-oriented:

1. Make candidate-review-publish lifecycle states explicit rather than
   representing the successful path only through a direct durable commit.
2. Extract the v1 import parser from the full teaching-era `SessionState`.
3. Classify and retire legacy runtime/evaluator assets through separate,
   evidence-backed slices.
4. Reorganize verification into the four test layers named by the roadmap.

No current evidence justifies deleting public `ask`; the project has no declared
release/version boundary or external-consumer inventory. That does not block
internal compatibility classification or parser extraction.

## Scoring Method

| Area | Weight | Completion | Weighted contribution |
| --- | ---: | ---: | ---: |
| M0: baseline and default-entry decision | 15 | 100% | 15.0 |
| M1: host adapter and recovery | 20 | 85% | 17.0 |
| M2: knowledge-quality publication boundary | 25 | 55% | 13.8 |
| M3: responsibility and compatibility boundary | 20 | 55% | 11.0 |
| M4: evaluation-asset layering | 10 | 40% | 4.0 |
| Integration acceptance and freeze | 10 | 65% | 6.5 |
| **Total** | **100** |  | **67.3%** |

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
- `skill/autonomous-mentor/examples/cli_route_baseline_checks.py`

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
- `skill/autonomous-mentor/examples/vnext_host_recovery_checks.py`
- `skill/autonomous-mentor/examples/work_host_contract_checks.py`

Current verification: host recovery passed **12/12**.

Gap against the reference design:

- The roadmap named distinct `host_facade.py` and `protocol_errors.py` modules.
  Their behavioral responsibilities exist, but are not separated under those
  explicit owner files.
- Error recovery remains verified by focused host checks rather than a
  standalone structured error taxonomy.

### M2: Knowledge Quality and Publication Boundary

**Status: partially complete (55%).**

Completed outcomes:

- Durable `TopicKnowledge` is versioned and validated by `KnowledgeStore`.
- `LearningDelta` supports new, revised, disputed, and retired claim effects.
- Evidence, counterexamples, gaps, cross-reference integrity, and optimistic
  version conflicts are validated.
- The autonomous path includes skeptic review before `commit_learning`.
- Commit order supports at-most-once durable application through a marker.
- Convergence is a separate deterministic owner.

Evidence:

- `skill/autonomous-mentor/scripts/knowledge_schema.py`
- `skill/autonomous-mentor/scripts/knowledge_store.py`
- `skill/autonomous-mentor/scripts/autonomous_runtime.py`
- `skill/autonomous-mentor/examples/learning_delta_checks.py`
- `skill/autonomous-mentor/examples/convergence_checks.py`

Gap against the reference design:

- There is no explicit persisted lifecycle for
  `proposed -> reviewed -> published/rejected -> retired`.
- There is no candidate-area store, independent `knowledge_publisher.py`, or
  rejected-delta reason model.
- Consequently, the system has a strong commit gate but not the roadmap's
  separately auditable publication workflow.

### M3: Responsibility and Compatibility Boundaries

**Status: partially complete (55%).**

Completed outcomes:

- Public CLI execution no longer imports or instantiates `MentorLoop`.
- `query.py` is a stateless read owner.
- The v1 importer is explicit, one-way, source-read-only, and writes only
  through `KnowledgeStore`.
- Re-import cannot overwrite a topic that has evolved under vNext.
- The new v1 input-surface contract classifies every top-level `SessionState`
  field as `mapped`, `provenance_only`, or `validated_only`.

Evidence:

- `docs/aegis/adr/0001-one-way-v1-import-boundary.md`
- `skill/autonomous-mentor/scripts/migrate_v1.py`
- `skill/autonomous-mentor/scripts/v1_import_record.py`
- `skill/autonomous-mentor/examples/migration_v1_checks.py`
- `skill/autonomous-mentor/examples/v1_import_surface_checks.py`

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

**Status: started, not structurally complete (40%).**

Completed outcomes:

- Focused checks already exist for routing, query behavior, host recovery,
  migration, schema, store integrity, learning deltas, convergence, autonomous
  loop behavior, packaging, and cross-model evidence.
- Each major verification family has a dedicated script instead of relying on
  one monolithic runner.

Gaps:

- The repository has not been reorganized into the roadmap's explicit
  `core-contract`, `behavior`, `migration`, and `adapter` layers.
- New tests do not yet declare a layer or a layer-specific deletion condition.
- No test-duration baseline or intended blast-radius matrix exists.
- Legacy retirement has not demonstrated that it affects only migration and
  adapter suites.

### Integration Acceptance and Freeze

**Status: partially complete (65%).**

Completed outcomes:

- M0.5 has a Git baseline and fresh isolated-worktree verification.
- The project has verified public routing, stateless query, v1 migration,
  durable initialization, recovery, at-most-once commit, and package/sandbox
  paths in prior acceptance runs.
- No public fallback to `MentorLoop` has been reintroduced.

Remaining conditions for a final roadmap freeze:

- Explicit candidate publication lifecycle and rejection audit trail.
- Narrow v1 parser extraction or a documented decision to retain the full
  schema with a new trigger.
- Test-layer boundaries and retirement-specific deletion proof.
- A completed per-surface compatibility decision.

## Current Verification Snapshot

The following commands were re-run from the isolated worktree for this report:

```bash
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
python3 skill/autonomous-mentor/examples/v1_import_surface_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
```

Results:

| Check | Result | What it establishes |
| --- | --- | --- |
| CLI route baseline | 4/4 pass | public owners and `ask` alias behavior |
| Stateless query | 5/5 pass | no learner mutation, no teaching action, alias parity |
| v1 input surface | pass | complete top-level `SessionState` classification |
| v1 migration | 8/8 pass | one-way mapping, rejection, race, and overwrite guarantees |
| Host recovery | 12/12 pass | durable initialization and commit-marker recovery |

These are current point-in-time checks. They do not prove the missing lifecycle,
parser extraction, or test reorganization because those capabilities do not yet
exist to test.

## Compatibility and Retirement State

| Surface | Current owner/status | Decision state | Required next evidence |
| --- | --- | --- | --- |
| `ask` | public `query` alias | defer | declared release/version plus no active dependency evidence |
| former `state.state` shape | no current public writer | classify | document any actual reader or retire by source proof |
| `SessionState` for v1 import | read-only importer input | extract candidate | parser parity matrix and narrow DTO plan |
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
| Direct durable commit lacks audit lifecycle | insufficient publication traceability | skeptic gate and commit marker | add candidate/review/publish/reject states |
| Tests remain coupled by convention | high change blast radius | focused scripts | declare and reorganize formal layers |
| External alias dependency is unknown | CLI breakage | no deletion authorized | bind decision to declared release/version |

## Recommended Execution Order

1. **Task 3 evidence decision:** record one outcome per retained compatibility
   surface. This is documentation-only and may proceed immediately.
2. **M2 publication-lifecycle design:** decide whether an independent
   `knowledge_publisher` is necessary or whether the current coordinator can
   own an explicit, persisted lifecycle without becoming a second source of
   truth. This decision must precede implementation.
3. **v1 parser extraction slice:** strict TDD parity tests, then introduce a
   narrow immutable import record/parser. Do not remove `SessionState` yet.
4. **Test-layer reorganization:** classify existing checks first; move them
   only after proving that invocation and coverage remain stable.
5. **Retirement slices:** only after parser extraction and archival decisions;
   handle `ask` separately when a release/version exists.
6. **Final integration freeze:** repeat recovery, public route, migration,
   quality-lifecycle, and sandbox checks from a fresh caller.

## Completion Criteria

The roadmap should be considered complete only when all of the following are
true:

- A single public learning owner and a single durable writer remain verified.
- Candidate deltas have explicit review, publication, rejection, and retirement
  semantics with immutable auditability.
- v1 import no longer depends on the teaching-era runtime schema, or an ADR
  records why that dependency is intentionally retained.
- Legacy runtime and evaluator assets have a completed retain/archive/delete
  disposition.
- Tests have independent core-contract, behavior, migration, and adapter
  owners with clear deletion conditions.
- Public alias retirement is tied to an actual release/version decision.
- A fresh sandbox acceptance verifies all retained contracts without legacy
  fallback.
