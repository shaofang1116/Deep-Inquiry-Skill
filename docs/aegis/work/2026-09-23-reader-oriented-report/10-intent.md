# Task Intent Draft

## Outcome

Implement the approved reader-oriented report design: canonical,
skeptic-reviewed reader prose that renders deterministically at true
convergence.

## Success Evidence

- Schema-v1 topics stay readable.
- Schema-v2 topics validate complete reader documents against canonical claims,
  evidence, dimensions, and gaps.
- New reports teach the topic without presenting audit process as their main
  content.
- Existing single-writer, immutable-report, eight-stage, and retry invariants
  remain true.

## Stop Condition

Pause for design review if implementation requires a model call during
rendering, a second durable writer, a ninth vNext stage, a separate report
store, or a historical snapshot/report rewrite.

## Non-goals

- Delete or rewrite persistent knowledge, audits, snapshots, or old reports.
- Change legacy v1 importer behavior.
- Sync the installed user Skill before full verification.

## Baseline Read Set

- `docs/aegis/specs/2026-09-23-reader-oriented-knowledge-report-design.md`
- `docs/aegis/plans/2026-09-23-reader-oriented-knowledge-report-implementation.md`
- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- `skill/deep-inquiry/scripts/{knowledge_schema.py,learner.py,judgments.py,autonomous_runtime.py,convergence.py,renderer.py,vnext_host.py}`

## Impact Statement

Scope is requirements and architecture. The work changes canonical schema,
agent contracts, publication readiness, report projection, and public protocol.
`KnowledgePublisher` remains the lifecycle owner and `KnowledgeStore` remains
the sole durable writer.
