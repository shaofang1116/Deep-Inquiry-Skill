# Converged Markdown Report Intent

## TaskIntentDraft

- Outcome: every genuinely converged vNext learning run emits a deterministic
  Markdown document and returns its path.
- Success evidence: renderer/store/host failure-first tests pass; all four test
  layers and sandbox package checks pass.
- Stop condition: done when the approved spec is implemented and verified;
  stop for review if a second writer, publication rollback, or compatibility
  fallback becomes necessary.
- Non-goals: model-authored summary, manual export command, `latest.md` alias,
  checkpoint report, schema migration, or changes to query/v1 behavior.

## BaselineReadSetHint

- `docs/aegis/specs/2026-09-23-converged-markdown-report-brief.md`
- `docs/aegis/adr/0003-publication-audit-journal.md`
- `docs/aegis/specs/2026-09-22-publication-lifecycle-and-test-layering-design.md`

## ImpactStatementDraft

- Product: learning completion gains a directly usable Markdown artifact.
- Runtime: `VNextHost` generates the artifact only after true convergence.
- Persistence: `KnowledgeStore` remains the sole durable writer.
- Projection: existing `renderer.py` remains the sole Markdown renderer owner.
- Compatibility: additive `result.report_path`; no existing result is removed.
