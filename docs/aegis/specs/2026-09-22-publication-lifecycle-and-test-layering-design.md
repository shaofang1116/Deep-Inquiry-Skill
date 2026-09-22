# Publication Lifecycle and Test Layering Design

## Status

Proposed design. It is approved in conversation for the stated scope but does
not authorize runtime or test-tree edits until its implementation plan is
reviewed.

## Goal

Complete the roadmap's M2 and M4 outcomes by making every durable learning
attempt auditable through an explicit lifecycle and by organizing verification
assets into four responsibility-based layers.

## Scope

In scope:

- Persist immutable per-topic records for `proposed`, `reviewed`, `published`,
  `rejected`, and `retired` learning attempts.
- Add one `KnowledgePublisher` owner for state-transition decisions.
- Keep `KnowledgeStore` as the sole durable file/snapshot writer.
- Route host learning commits through the publisher.
- Directly migrate internal check scripts to four test directories with no
  compatibility wrappers.
- Preserve v1 import, public vNext commands, and existing durable topic
  semantics.

Out of scope:

- Deleting `MentorLoop`, `schema.py`, teaching assets, or the `ask` alias.
- Changing user-owned knowledge roots or retroactively rewriting existing topic
  history.
- Adding telemetry, a remote service, a database, or a generic knowledge
  management platform.
- Altering convergence policy or model-facing judgment formats beyond the
  lifecycle metadata needed by the publisher.

## Baseline and Authority

- Reference roadmap: `Autonomous Mentor 重构路线图`, 2026-09-18.
- Current progress: `docs/aegis/reports/2026-09-22-refactor-roadmap-progress.md`.
- One-way importer boundary: `docs/aegis/adr/0001-one-way-v1-import-boundary.md`.
- Public ownership and retirement boundary:
  `docs/aegis/adr/0002-vnext-default-entry-retirement.md`.
- Compatibility plan:
  `docs/aegis/plans/2026-09-21-post-m05-compatibility-window-retirement.md`.

Baseline Role Alignment:

- Product / Requirement Baseline: learning results must be quality-gated,
  auditable, and testable without preserving dual default paths.
- Architecture / Runtime Boundary Baseline: `VNextHost ->
  HostRuntimeCoordinator -> KnowledgeStore` is the public execution path, and
  `KnowledgeStore` is the only durable topic writer.
- Result: aligned, scope both.
- Next action: introduce lifecycle semantics without creating another writer or
  another public learning owner.

## First-Principles Decision

- Non-negotiable goal: every attempt to change durable knowledge has an
  immutable outcome record, while queries expose only published knowledge.
- Non-negotiable constraints: one durable writer, atomic topic state, no legacy
  fallback, one-way v1 import, and no mutation of existing user data.
- Historical assumptions to delete: a skeptic stage alone is sufficient audit
  evidence; passing scripts are sufficiently layered without explicit
  ownership.
- Smallest sufficient path: a publisher decides lifecycle transitions and asks
  the existing store to atomically append journal records and, for publication,
  save one new knowledge snapshot.
- Escalation signal: a design that needs a second durable writer, changes
  existing topic history, or makes `query` read non-published records returns
  to architecture review.

## Architecture

```text
HostRuntimeCoordinator
  -> creates proposed candidate from validated integration
  -> receives skeptic result
  -> KnowledgePublisher
       -> validates lifecycle transition
       -> KnowledgeStore
            -> append immutable audit record
            -> atomically save published TopicKnowledge when approved

query_knowledge -> KnowledgeStore.load -> published knowledge only
```

### Owners

| Owner | Responsibility | Must not own |
| --- | --- | --- |
| `HostRuntimeCoordinator` | stage sequencing, pending cursor, at-most-once request recovery | audit policy or direct published commit |
| `KnowledgePublisher` | candidate identity, transition validation, rejection reason classification, publication decision | file I/O, locks, or query projection |
| `KnowledgeStore` | locks, atomic writes, immutable audit records, current topic and version snapshots | lifecycle policy or model judgments |
| `TopicKnowledge` | current published knowledge projection | proposed/rejected payload history |
| `query_knowledge` | stateless published projection | candidates, rejected records, teaching state |

### Durable Layout

For a topic `<topic-id>`, retain existing files and add an append-only journal:

```text
topics/<topic-id>/
  knowledge.json
  history/v000001.json
  audit/
    000001-<candidate-id>-proposed.json
    000002-<candidate-id>-reviewed.json
    000003-<candidate-id>-published.json
```

Rejected candidates use the same sequence format and never create a new
`history/v*.json` topic version. A retired claim or knowledge version creates a
`retired` audit record and, when it changes the current knowledge projection,
one new published topic version.

Records are canonical JSON, immutable, and written while the existing topic
lock is held. Sequence values are monotonically increasing for a topic. Existing
topics without `audit/` remain readable; the directory is created only on the
first new lifecycle operation.

### Audit Record Contract

Each audit record has:

```json
{
  "schema_version": 1,
  "record_id": "000001-candidate-id-proposed",
  "candidate_id": "sha256-derived-id",
  "topic_id": "topic-id",
  "state": "proposed",
  "base_version": 3,
  "created_at": "ISO-8601 timestamp",
  "delta": {},
  "integration": {},
  "review": null,
  "rejection": null,
  "published_version": null
}
```

Rules:

- `candidate_id` is deterministic from canonical candidate payload, including
  topic ID, base version, cycle, integration, and host-run identity.
- `proposed` records carry validated integration payload and delta.
- `reviewed` records carry the skeptic result and may only follow `proposed`.
- `published` records may only follow `reviewed`, set `published_version`, and
  reference the saved immutable topic snapshot.
- `rejected` records may follow `proposed` or `reviewed`, contain a stable
  rejection code and a redacted human-readable reason, and set
  `published_version` to null.
- `retired` records identify the retired claims or prior published version and
  the successor publication where applicable.
- Audit records retain no raw proposition text, full topic graph, or
  user-specific file paths beyond the existing topic identifier.

### State Transitions

```text
proposed -> reviewed -> published
                    -> rejected
proposed -> rejected
published -> retired
```

- Schema or cross-reference failure before a valid candidate exists is a
  rejected record only if the candidate identity and safe redacted summary can
  be constructed. Otherwise the operation fails before durable mutation.
- Skeptic structural failure becomes `rejected` with code
  `skeptic_structural_hit`.
- Optimistic version conflict becomes `rejected` with code `version_conflict`.
- Store write failure produces no partial lifecycle transition: neither topic
  version nor audit record may claim success.
- Retrying the same candidate returns the existing immutable terminal record;
  it must not append duplicate publication or rejection records.

### Atomicity

For a successful publish, the store holds the topic lock and writes:

1. `proposed` record if absent.
2. `reviewed` record if absent.
3. next immutable topic snapshot and `knowledge.json`.
4. `published` record.

If an interruption occurs after a topic snapshot is written but before the
published record, recovery detects the deterministic candidate and completes
the missing record under the same lock. If the final record exists without the
matching topic snapshot, loading or publication recovery fails closed.

Rejected records do not modify `knowledge.json` or the topic version. They are
atomic single writes under the topic lock.

## Host Runtime Changes

The runtime keeps its existing stages and request contracts. The only ownership
change is at `commit_learning`:

- `integrate_learning` supplies a validated integration candidate.
- `skeptic_review` supplies the review outcome.
- `commit_learning` calls `KnowledgePublisher.publish_or_reject(...)`.
- The publisher returns a terminal audit result and, only for `published`, the
  new `TopicKnowledge` version.
- The existing commit marker is replaced or extended with deterministic
  candidate identity so retries detect an already-published terminal record.

`assess_convergence` runs only after a published result. A rejected candidate
returns a deterministic next pending state or error contract chosen by the
implementation plan; it must not falsely append a convergence record.

## Four Test Layers

The test tree becomes:

```text
examples/tests/
  core_contract/
  behavior/
  migration/
  adapter/
  fixtures/
```

Layer responsibilities:

| Layer | Purpose | Examples of existing assets |
| --- | --- | --- |
| `core_contract` | durable schemas, store atomicity, lifecycle transitions, convergence invariants | `knowledge_schema_checks`, `knowledge_store_checks`, `learning_delta_checks`, `convergence_checks` |
| `behavior` | autonomous learning across concept/mechanism/controversy cases and cross-model profiles | `autonomous_loop_checks`, `knowledge_first_acceptance_checks`, `eval_vnext_suite` |
| `migration` | v1 importer, parser input surface, immutable-source and evolved-topic protection | `migration_v1_checks`, `v1_import_surface_checks` |
| `adapter` | CLI routes, query alias, host recovery, work-host contract, package/smoke behavior | `cli_route_baseline_checks`, `query_checks`, `vnext_host_recovery_checks`, `work_host_*`, `package_vnext_checks` |

The migration is a direct physical move:

- Update imports, documentation, package checks, and every in-repository caller.
- Do not retain old-path wrapper scripts.
- Preserve check names and command semantics through a new layer manifest or
  layer runner; the exact command becomes a documented contract.
- Fixtures move only when their ownership is unambiguous. Shared fixtures remain
  in `examples/tests/fixtures/`.

Each test module declares one layer in a module constant or manifest entry. A
new test cannot enter the suite without a layer declaration. The implementation
records per-layer commands and elapsed-time baseline in a generated or checked
manifest, but does not fail solely on timing variance.

## Compatibility Boundary

- Existing topic files and snapshots remain valid and unmodified until a new
  lifecycle operation writes an audit record.
- Existing public CLI JSON envelopes, `query`, and `ask` behavior remain
  unchanged.
- Existing v1 importer outcomes remain unchanged.
- No frozen Skill, user installation, archive, ZIP, or user durable root is
  edited during repository migration tests.
- The test path change is internal and has no wrapper compatibility guarantee.
  Any discovered external caller is an explicit `compat-exception`, not a
  reason to retain wrappers by default.

## Verification

Lifecycle acceptance must prove:

1. Proposed, reviewed, published, rejected, and retired records are canonical,
   immutable, and per-topic sequence ordered.
2. A valid reviewed candidate creates exactly one new topic version and one
   published record despite retry or process reconstruction.
3. Skeptic failure, invalid references, and version conflict create a rejected
   record while the current topic bytes and version remain unchanged.
4. Partial publish recovery either completes the missing audit record for the
   matching snapshot or fails closed.
5. Query reads published knowledge only.
6. Existing v1 import tests retain all current outcomes.

Test-layer acceptance must prove:

1. Every check module belongs to exactly one declared layer.
2. The four layer commands execute from a fresh external caller.
3. Repository search finds no old `examples/*.py` invocation after migration.
4. Package and sandbox checks use the new commands.
5. The full suite maintains its existing public, migration, and host guarantees.

## Required Interruptions and Confirmations

| Trigger | Action |
| --- | --- |
| Audit schema cannot represent a required existing integration value without storing sensitive/full topic data | stop for design confirmation |
| Topic mutation and audit append cannot be made recoverable under one lock | stop for architecture review |
| A test path has a proven external consumer | stop for a bounded compatibility decision |
| Any plan proposes rewriting existing user topic history or deleting user data | require scoped human confirmation |
| A lifecycle or test migration check fails | stop the affected slice, diagnose, and repair before the next slice |

No manual confirmation is required between successful low-risk implementation
tasks. Human review is required before implementation planning and at the
specific escalation triggers above.

## Risks and Rollback

- Audit journal corruption: fail closed and preserve current topic history;
  recover only from immutable valid artifacts under the topic lock.
- Publisher duplication: prohibit publisher file I/O and keep the store as the
  one writer.
- Test move regression: use direct-path negative checks and a fresh-caller
  layer runner before removing old locations.
- Unbounded audit growth: accepted by scope; records are durable audit assets,
  not a cache. Retention policy is a future explicit data-governance decision.

Rollback is source-only: revert the focused implementation commit if its
development or sandbox acceptance fails. Do not delete audit records or user
knowledge during rollback.

## ADR Signal

This design introduces a durable audit artifact shape, a canonical publisher
owner, and a test-contract boundary. Implementation must create an ADR that
records the final artifact shape, transition semantics, and recovery rules after
the first passing implementation slice.
