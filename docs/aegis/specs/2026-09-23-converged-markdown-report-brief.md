# Converged Markdown Report Spec Brief

## Status

Approved in conversation on 2026-09-23.

## Goal

When a vNext learning run genuinely converges, automatically render the current
published `TopicKnowledge` as a durable Markdown document and return its path in
the completed host result.

## Requirements

1. Generate a report only when `ConvergenceDecision.converged` is true.
   A checkpoint-required terminal run is not learning completion and must not
   create a report.
2. Render only canonical published knowledge. The renderer must not call a
   model, perform research, infer missing prose, or mutate topic state.
3. Store each report at
   `topics/<topic-id>/reports/v<six-digit-version>.md`.
4. Reports are immutable per topic version. Repeating completion for the same
   version returns the existing identical report; different existing bytes fail
   closed.
5. `KnowledgeStore` remains the only durable file writer and performs atomic
   report writes.
6. The successful learning result adds an absolute `report_path`.
7. A report write failure must prevent the host run from being marked complete
   and retain the pending completion cursor so the operation can be retried.
   Already published knowledge is not rolled back.

## Report Shape

The deterministic document contains:

- title, proposition, topic ID, knowledge version, and update time;
- coverage dimensions;
- active, disputed, and retired claims grouped by dimension, including
  confidence and references;
- evidence sources and supported claims;
- counterexamples and affected claims;
- open, deferred, and resolved knowledge gaps;
- convergence history.

All content is derived directly from `TopicKnowledge`. Markdown-sensitive inline
text is normalized so durable data cannot break document structure.

## Architecture

- `renderer.py`: existing projection owner gains the pure
  `TopicKnowledge -> UTF-8 Markdown bytes` report projection.
- `KnowledgeStore`: report path ownership, immutable comparison, and atomic
  write.
- `VNextHost`: completion orchestration and `report_path` result field.
- `KnowledgePublisher`: unchanged; publication lifecycle remains independent
  from the derived completion report.

## Compatibility

- Existing topic JSON, audit records, query behavior, initialization results,
  checkpoint results, and v1 import behavior remain unchanged.
- The new `result.report_path` field is additive.
- No `latest.md` alias, fallback report path, or manual export command is added.

## Acceptance

- A pure renderer check proves stable sections, grouping, references, and
  deterministic bytes.
- A store check proves atomic immutable creation, idempotent reuse, mismatch
  rejection, and path containment.
- An adapter check proves converged completion returns an existing report,
  checkpoint completion does not create one, and write failure remains
  retryable.
- All four test layers and package/sandbox checks remain green.

## Architecture Review

`ArchitectureReviewRequired: yes`

The review must confirm one writer, no duplicate knowledge owner, additive host
contract, no report generation before true convergence, and no compatibility
fallback.
