# M0.5 vNext Host Recovery and Durable Topic Initialization

## Status

Approved for implementation on 2026-09-18. This design implements the target
direction accepted in ADR 0002; it does not authorize package installation,
user-level Skill replacement, or deletion of user knowledge.

## Goal

Move the public learning commands from the legacy `MentorLoop` to the vNext
durable learning owner while preserving the file-host protocol:

1. `init` obtains a validated topic seed and atomically creates one durable
   `TopicKnowledge` version 1.
2. `learn` and `step` advance a durable autonomous run one agent stage at a
   time through `request.json` and `judgment.json`.
3. A process restart recovers from runtime pending state and canonical durable
   topic state without replaying an already committed learning delta.

## Authority

- `docs/2026-09-17-knowledge-first-skill-plan.md`
- `docs/aegis/specs/2026-09-18-m0-entry-truth-brief.md`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `ISOLATION.md`
- `skill/autonomous-mentor/scripts/knowledge_store.py`
- `skill/autonomous-mentor/scripts/loop.py`

## Baseline Alignment

- Product / Requirement Baseline: durable autonomous learning is the main
  product path; teaching is not a completion dependency.
- Architecture / Runtime Boundary Baseline: `KnowledgeStore` is the sole
  durable writer, `TopicKnowledge` is the knowledge truth, and
  `AutonomousLearningLoop` is the vNext learning owner.
- Current implementation: public learning commands instantiate `MentorLoop`
  and only attach a vNext topic reference to legacy pending state.
- Result: `Implementation Drift`, scope `architecture`. M0.5 returns the
  public main path to the unchanged vNext ownership baseline.

## First-Principles and Integrity Review

- Non-negotiable goal: a restarted host must know exactly which durable version
  is canonical and must never apply the same delta twice.
- Non-negotiable constraints: no model API in the kernel, no knowledge stored
  in runtime files, no fallback to project-local storage, and no silent legacy
  route.
- Historical assumptions to delete: the teaching-era `SessionState` is not a
  valid cursor for vNext autonomous learning.
- Canonical owner: a resumable vNext coordinator owns stage transition and
  durable commit ordering; `KnowledgeStore` owns all canonical writes.
- Responsibility overlap: CLI may serialize host envelopes but must not decide
  convergence, select gaps, or commit topic deltas.
- Retirement/falsifier: any public `init`, `learn`, or `step` import or
  instantiation of `MentorLoop` after the switch falsifies this design.
- Verdict: proceed with a new coordinator module rather than extending the
  1,395-line mixed legacy/vNext `loop.py`.

## Runtime Protocol

The host retains its existing outer JSON envelope:

```json
{
  "status": "pending | done | error | cancelled | state",
  "next_action": "write_judgment_and_step | read_result | complete | correct_error",
  "knowledge_root": "/absolute/path",
  "topic_id": "stable-topic-id",
  "request_path": "/absolute/path/request.json",
  "request_paths": {
    "state": "/absolute/path/session.json",
    "pending": "/absolute/path/pending.json",
    "request": "/absolute/path/request.json",
    "judgment": "/absolute/path/judgment.json"
  }
}
```

`session.json` is no longer a legacy `SessionState` on the vNext public path.
It stores only a validated host-run reference:

```json
{
  "schema_version": 1,
  "runtime_kind": "vnext_host_run",
  "run_id": "opaque stable ID",
  "topic_id": "stable-topic-id",
  "knowledge_root": "/absolute/path",
  "base_version": 1,
  "status": "active | complete | cancelled",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

`pending.json` is the crash-recovery cursor. It contains `runtime_kind`,
`run_id`, required agent judgment name, stage-local context, and the durable
base version expected before the next commit. `request.json` is a projection of
that cursor and may always be regenerated. `judgment.json` is consumed only
after its response validates and the next cursor or completed result has been
atomically written.

## Durable Topic Initialization

`init "<proposition>"` creates a pending `initialize_topic` request. Its
response must supply:

- normalized `title`;
- normalized `proposition`;
- two or more `coverage_dimensions`;
- zero or more initial claims, evidence, gaps, and counterexamples, all
  satisfying `TopicKnowledge` cross-reference validation.

The coordinator constructs `TopicKnowledge` version 1, stamps creation time,
and persists it through `KnowledgeStore.create()`. A topic origin record with
the pending `run_id` is stored in explicit initialization metadata so a retry
can distinguish the same interrupted initialization from an unrelated existing
topic. `TopicKnowledge` gains an optional `origin_metadata` JSON object for
this purpose; `migration_metadata` remains reserved for the one-way v1
importer. Both metadata objects are provenance only and are not read by
convergence.

The new initialization contract replaces the vNext autonomous `anchor`
acknowledgement for public host initialization. Existing direct-loop tests may
continue to use `anchor` internally; the public host never creates a placeholder
topic with invented dimensions.

## Resumable Learning

After initialization, `learn` starts or resumes a run. `step` accepts exactly
the pending stage response and validates it before any durable write.

The coordinator schedules stages in this order:

1. `map_knowledge`
2. `select_gap` (deterministic, no model response)
3. `plan_investigation`
4. `integrate_learning`
5. `skeptic_review`
6. durable delta commit through `KnowledgeStore.save()`
7. `assess_convergence`
8. `checkpoint_or_complete`

Before the durable commit, the pending cursor includes the validated integration
and skeptic responses. The coordinator commits once from its recorded
`base_version`, then immediately writes a post-commit cursor with the new
version and no reusable integration payload. If the process stops:

- before a commit, replaying `step` is safe because no durable version changed;
- after a commit but before the next request is emitted, recovery observes the
  advanced durable version and transitions to `assess_convergence` without
  applying the delta again;
- if durable topic version differs from the recorded cursor without the
  coordinator's matching post-commit marker, the host returns a conflict error
  rather than guessing or merging.

`AutonomousLearningLoop` is refactored to delegate its stage semantics to this
coordinator so direct scripted-agent tests and Work-host execution share gap
selection, validation, durable commits, and convergence decisions.

## Command Ownership

| Command | M0.5 owner | Durable effect | Runtime effect |
| --- | --- | --- | --- |
| `init` | vNext host coordinator | creates topic v1 after valid seed | creates initialization pending cursor |
| `learn` | vNext host coordinator | reads current topic | creates/resumes learning pending cursor |
| `step` | vNext host coordinator | commits at most one delta | consumes one response, advances cursor |
| `cancel` | vNext host coordinator | none | marks run cancelled and clears active pending |
| `state` | vNext host coordinator | reads current topic version | reports vNext run reference |
| `query` / `ask` | `query_knowledge` | stateless durable read | none |
| `demo` | existing smoke entry | fixture-owned | temporary fixtures |

## Compatibility and Retirement

- `query`, `ask`, and `demo` retain M0 behavior.
- The public `init`, `learn`, `step`, `cancel`, and `state` paths must not
  import or instantiate `MentorLoop`.
- No fallback to legacy runtime files or session schema is allowed.
- Legacy `MentorLoop` remains only for the explicit v1 importer and
  non-default compatibility evidence. Its source is not deleted in M0.5.
- Existing legacy runtime sessions are not migrated, read, or deleted by M0.5.
  A user must use the explicit v1 importer to create durable knowledge.

## Non-Goals

- Delete legacy code or its historical evaluators.
- Migrate a legacy session automatically.
- Change `TopicKnowledge` learning semantics, convergence policy, query
  behavior, or the one-way v1 importer.
- Add fallback, retry merging, background execution, model SDKs, package
  installation, or ZIP generation.

## Acceptance

1. `init` produces an initialization request, then creates a valid durable
   version-1 topic only after a valid response.
2. Duplicate `init` cannot overwrite an existing unrelated topic; retry of the
   same interrupted initialization is idempotent.
3. `learn` / `step` progress one stage per host exchange and preserve the
   existing JSON pending/done/error envelope and exit-code classes.
4. An interrupted pre-commit response is recoverable without a durable write.
5. An interrupted post-commit response is recoverable without duplicate delta
   application.
6. Public learning commands contain no `MentorLoop` main-path import or
   instantiation.
7. `query` and `ask` remain byte-equivalent, stateless durable reads.
8. Existing autonomous-loop, work-host, query, migration, and route-baseline
   checks pass with the updated routing expectations.
9. All runtime tests use isolated temporary or sandbox caller directories;
   no bytecode cache appears in the Skill tree.

## ADR Signal

ADR 0002 already records the default-entry and legacy-retirement decision. M0.5
does not amend that decision; completion evidence must update its implementation
status and confirm the retirement trigger remains pending until a defined
read-only compatibility window closes.
