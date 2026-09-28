# ADR 0006: Cognitive Reader Document v2

Status: accepted
Date: 2026-09-24

## Context

ADR 0005 established `TopicKnowledge.reader_document` as the canonical
reader-facing projection and retained deterministic immutable Markdown
rendering. Reader-document v1 can ground explanatory prose, but it cannot
represent the compact cognitive organization needed for a reader to reconstruct
and apply the learned model.

The schema-v3 upgrade needs concepts, grounded typed relationships,
prerequisite order, mechanism chains, key variables, transfer guidance, and
typed boundaries without adding another durable knowledge owner or report
lifecycle.

## Decision

New schema-v3 publications store reader-document v2 in
`TopicKnowledge.reader_document`. The document is the sole reader-facing
cognitive organization; durable facts remain claims, evidence, gaps, and
counterexamples.

`integrate_learning` authors the complete document. `skeptic_review` records
one structured `reader_document_review` and rejects non-empty findings in
`cognitive_map`, `mechanism_depth`, `dependency_order`, `synthesis`,
`transfer`, `boundary_expression`, or `audit_leakage`. `KnowledgePublisher`
remains the lifecycle owner, `KnowledgeStore` remains the sole durable writer,
and `renderer.py` deterministically formats only the approved document.

The eight-stage lifecycle remains unchanged. An invalid document blocks
convergence with `reader_document_not_ready`; no ninth stage is introduced.

## Alternatives Considered

1. Add a separate `knowledge_model`: rejected because it duplicates the
   reader document's organizational role and creates a second durable owner.
2. Infer a map in the renderer: rejected because presentation would become a
   new source of semantic judgment and could not be skeptic-approved.
3. Permit document-only revisions after convergence: deferred because this
   requires a separate lifecycle, authority boundary, and immutable version
   policy.
4. Keep v1 prose as the new canonical shape: rejected because coverage prose
   alone cannot validate cognitive dependencies, mechanisms, variables, or
   transfer.

## Owners

- Durable facts: `TopicKnowledge` claims, evidence, gaps, and counterexamples.
- Reader-facing cognitive organization and validation:
  `TopicKnowledge.reader_document` and `reader_document.py`.
- Host authorship: `integrate_learning`.
- Skeptical acceptance: `skeptic_review`.
- Publication lifecycle: `KnowledgePublisher`.
- Durable I/O: `KnowledgeStore`.
- Deterministic presentation: `renderer.py`.
- Completion decision: `evaluate_convergence()` and `VNextHost`.

## Compatibility Exception

Schema-v1 audit topics and schema-v2 topics carrying reader-document v1 remain
readable through explicit compatibility paths. Existing reports, snapshots,
lifecycle records, paths, query behavior, and retry semantics are not
rewritten. This exception is limited to historical artifacts; new schema-v3
publications must use reader-document v2.

## Retirement Trigger

The unstructured reader-document v1 shape is retired for every new
schema-v3 publication immediately. The legacy read paths remain only while
immutable schema-v1 or schema-v2 artifacts exist. A future migration proposal
must show active artifact inventory, a read-compatibility replacement, and
passing legacy rendering tests before removing either compatibility path.

## Non-goals

- Graph visualization or a graph-oriented output surface.
- Mutable completed reports or document-only publication.
- A separate knowledge model, independent document version, or report revision
  axis.
- Renderer inference, a model call during rendering, or a ninth lifecycle
  stage.
- Cross-topic ontology merging, HTML/PDF output, or reader profiling.

## Future Document-Only Revision Evidence

Document-only revision remains deferred. It may be reconsidered only with all
of the following evidence:

1. Repeated, concrete user demand to correct presentation without changing
   accepted knowledge.
2. A reviewed lifecycle design naming the canonical owner, writer, immutable
   version policy, query semantics, audit record, and rollback behavior.
3. Compatibility and retirement analysis for existing report paths and
   snapshots.
4. Focused tests proving that a revision cannot bypass skeptic approval,
   `KnowledgePublisher`, or `KnowledgeStore`.
5. Blind-reader evidence that the proposed revision solves a real
   comprehension problem not addressed by a normal knowledge publication.

## Evidence

The implementation plan requires focused schema, runtime, renderer,
completion-retry, and protocol checks. Cross-topic fixtures and blind-reader
acceptance remain a separate Task 6 release-evidence boundary; they are not a
runtime feature or a prerequisite for recording this decision.
