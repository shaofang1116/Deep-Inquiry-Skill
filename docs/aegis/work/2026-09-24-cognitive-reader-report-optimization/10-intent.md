# Cognitive Reader Report Optimization: Execution Intent

## Requested Outcome

Implement the approved schema-v3 reader-document v2 upgrade through the six
tasks in
`docs/aegis/plans/2026-09-24-cognitive-reader-report-optimization-implementation.md`.
Each implementation task uses a fresh independent implementer, then independent
specification and code-quality reviews.

## Scope

- Grounded cognitive reader documents, skeptic review, deterministic rendering,
  completion retry semantics, equivalent public protocols, and release gates.
- Schema-v1 and schema-v2 topics, reports, and snapshots remain readable.

## Non-goals

- No new durable knowledge owner, ninth runtime stage, renderer inference,
  document-only publication, mutable report alias, commit, push, merge, or
  user-level Skill synchronization.

## Baseline Read Set

- `docs/aegis/specs/2026-09-24-cognitive-reader-report-optimization-design.md`
- `docs/aegis/plans/2026-09-24-cognitive-reader-report-optimization-implementation.md`
- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- `docs/aegis/adr/0005-reader-oriented-report.md`

## Risks

- Schema-v3 must not break legacy read paths.
- Renderer must only format the approved reader document.
- Completion must retain active run and pending cursor when report writing fails.
