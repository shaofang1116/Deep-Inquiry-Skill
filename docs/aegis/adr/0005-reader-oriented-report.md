# ADR 0005: Reader-Oriented Convergence Reports

Status: accepted
Date: 2026-09-23

## Context

The report design introduced in historical ADR 0004 correctly established
immutable, versioned Markdown output, retry-safe persistence, and
`KnowledgeStore` as the sole durable writer. Its schema-v2 presentation,
however, exported claim, evidence, gap, and convergence registries. That
format was auditable but did not provide the connected explanation, conditions,
application, and boundaries required by a reader learning the topic.

## Decision

Store a structured `reader_document` inside canonical `TopicKnowledge`.
`integrate_learning` supplies a complete candidate, `skeptic_review` explicitly
approves or rejects it, and `KnowledgePublisher` publishes it atomically with
the factual delta. `renderer.py` deterministically formats only the published
document for schema-v2 reports.

Schema-v2 reports contain an overview, explanatory sections, synthesis,
application guidance, boundaries or uncertainty, and source notes. They do not
present an audit registry, internal IDs, lifecycle history, or host workflow as
the primary narrative.

## Consequences

- ADR 0004 is superseded only for the schema-v2 report shape.
- Immutable paths, byte-comparison retry behavior, and
  `KnowledgeStore.write_markdown_report()` ownership remain unchanged.
- Schema-v1 topics and existing immutable reports remain readable through the
  explicit audit compatibility renderer; no historical topic or report is
  rewritten.
- Schema-v1 and unready schema-v2 topics cannot complete a new converged
  report.
- The renderer makes no model call and creates no knowledge.

## Evidence

- Focused schema, runtime, renderer, host, protocol, and cross-domain tests
  passed.
- Cross-domain reader review passed all five criteria for lodging construction
  and a small climbing-camera robot: mechanism, applicability and failure
  conditions, concrete action, cross-dimension connection, and absence of
  internal process machinery.
- Retirement scan confirms audit headings are confined to the named schema-v1
  compatibility function or negative-test expectations.
