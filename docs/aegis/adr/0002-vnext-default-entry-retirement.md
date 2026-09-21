# ADR 0002: vNext Default Entry and Legacy Retirement Boundary

## Status

Accepted and implemented in M0.5. The current public ownership matrix is
recorded in `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`.

## Context

The vNext architecture has durable knowledge, an autonomous learning loop, and
a convergence owner. M0.5 routes public `init`, `learn`, `step`, `cancel`, and
`state` through `VNextHost`, which persists only `HostRun` and `PendingCursor`
runtime references and delegates stage semantics to
`HostRuntimeCoordinator`. `query` and `ask` remain durable stateless reads.

The v1 importer is intentionally one-way and `KnowledgeStore` is already the
only durable topic writer. Keeping both learning loops as default-capable
owners would preserve an ambiguous source of behavior and delay retirement.

## Decision

1. The default public learning entry for vNext is `VNextHost`, which delegates
   to `HostRuntimeCoordinator`; `AutonomousLearningLoop` is the direct
   scripted adapter over the same runtime semantics. Durable `TopicKnowledge`
   remains the knowledge source of truth.
2. `MentorLoop` and its teaching-era session schema are not a vNext default
   learning owner. They remain only while required to support the explicit
   one-way v1 import and documented compatibility window.
3. `query.py` remains the sole stateless query owner and reads only published
   durable topic versions.
4. M0.5 made the switch through the separately approved implementation plan
   and proved host recovery, durable topic initialization, and no main-path
   legacy imports.
5. The legacy route may not be retained as a silent fallback after the switch.
   Any external compatibility exception requires active dependency evidence,
   an observation point, and a retirement trigger.
6. The read-only compatibility window starts on 2026-09-21 and has a minimum
   30-calendar-day observation period. At the opening baseline there is no Git
   tag, remote release, or declared public version. Before any public
   compatibility retirement, the later decision must record a concrete
   release/version identifier, inspect redacted observation receipts, and
   record one per-surface outcome. This window is documented in
   `docs/aegis/work/2026-09-21-compatibility-window/`.

## Consequences

- The route matrix and golden fixture record the implemented vNext public
  ownership rather than an unimplemented target.
- Public learning commands do not import or instantiate `MentorLoop`.
- v1 import remains auditable without reintroducing teaching state into
  durable knowledge.
- The public host protocol uses a vNext-specific state and recovery adapter;
  legacy session state is not read, migrated, or deleted on the public path.

## Rejected Alternatives

- Keep both loops available as equal default routes: preserves ambiguity and
  enables accidental fallback.
- Rename the legacy loop as vNext: hides incompatible state and knowledge
  ownership behind a label.
- Delete legacy code in M0: removes import and compatibility evidence before
  its replacement entry has passed acceptance.
- Change schemas while switching the CLI: combines independent failure modes
  and prevents a focused rollback.

## Retirement Governance

- Deletion class: `code-retirement` and `contract-carrying code`.
- Retirement decision: `compat-exception` only for the documented v1 importer
  and any proven active external CLI dependency.
- No persistent knowledge or user session is deleted by this ADR.
- Retirement trigger: after M0.5 default-entry acceptance and a defined
  read-only compatibility window, remove legacy learning-path references and
  their adapter-only tests. The observation period alone is not sufficient:
  release/version evidence and the per-surface decision record are also
  required.

## Verification

- The M0.5 route fixture and source-routing checks establish the current
  baseline.
- M0.5 proves `init`, `learn`, and `step` reach the vNext owner.
- M0.5 proves no public default path imports `MentorLoop`.
- Migration checks must continue to prove that legacy inputs are read-only and
  do not overwrite evolved vNext topics.
