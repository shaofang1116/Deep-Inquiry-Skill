# ADR 0004: Converged Markdown Report

## Status

Accepted on 2026-09-23.

## Context

vNext learning persisted structured `TopicKnowledge`, but completing a learning
run did not produce a directly readable deliverable. Manual report generation
was repeat work and could introduce prose not present in durable knowledge.

The report must not create a second knowledge source, weaken publication
atomicity, or certify a topic version that was not assessed for convergence.

## Decision

- Only a genuinely converged vNext run generates a Markdown report.
  Checkpoint-required termination does not.
- The existing `renderer.py` is the sole Markdown projection owner. Rendering
  is deterministic and uses only canonical published `TopicKnowledge`.
- `KnowledgeStore` remains the sole durable writer. It writes reports
  atomically at
  `topics/<topic-id>/reports/v<six-digit-version>.md`.
- A report is immutable for its topic version. Identical retries reuse it;
  different existing bytes fail closed.
- The host verifies that the completion cursor's expected version still equals
  the canonical topic version before rendering.
- The host writes the report before marking the run complete. Failure preserves
  the completion cursor for retry and does not roll back already published
  knowledge.
- Successful completion adds the absolute `report_path` to the result.

## Alternatives Rejected

- Model-authored post-processing: richer prose, but creates another judgment
  stage and can add unsupported claims.
- Manual export command: avoids completion coupling, but does not satisfy
  automatic delivery.
- Mutable `latest.md`: convenient, but adds a second alias and weakens immutable
  version provenance.
- Publisher-owned report generation: conflates knowledge lifecycle policy with
  a derived presentation artifact.

## Consequences

Every converged version has a stable human-readable artifact whose content is
reproducible from canonical knowledge. A report write failure can leave
published knowledge ahead of host completion, but the retained cursor makes the
derived write idempotently retryable.

The report format is now a durable artifact contract. A future incompatible
format change must use an explicit format/version decision rather than
overwriting existing reports.

## Baseline Sync

The current architecture remains:

- `KnowledgePublisher` owns publication lifecycle decisions.
- `KnowledgeStore` owns all durable writes.
- `renderer.py` owns human-readable projections.
- `VNextHost` owns completion orchestration.

No fallback, compatibility carrier, or old report path is retained.
