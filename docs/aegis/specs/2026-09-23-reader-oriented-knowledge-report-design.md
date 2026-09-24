# Reader-Oriented Knowledge Report Design

Status: `proposed for user review`
Date: `2026-09-23`
ArchitectureReviewRequired: `yes`

## 1. Decision Summary

Deep Inquiry will persist a reader-oriented knowledge document inside canonical
`TopicKnowledge`. The host agent authors and revises that document during
`integrate_learning`; the existing `skeptic_review` stage reviews it together
with the factual delta. Only an approved integration is published.

The convergence renderer remains deterministic. It formats the published reader
document and never asks a model to invent prose. Audit history remains durable
but is not emitted as the primary knowledge report.

This design supersedes the report-shape decision in historical ADR 0004 from
commit `2231e76`. It preserves that ADR's storage, immutability, retry, and
single-writer guarantees.

## 2. Problem

The current converged report is a faithful export of internal state:

- claim IDs, kinds, statuses, and confidence;
- raw evidence and counterexample registries;
- knowledge-gap records;
- convergence cycles and delta metadata.

That artifact is useful for audit but is not a document from which a reader can
learn. Removing the audit sections is insufficient because the remaining claim
statements are intentionally atomic and too coarse to provide:

- a connected explanation of how the subject works;
- conditions and decision branches;
- relationships across coverage dimensions;
- practical use or evaluation steps;
- boundaries, exceptions, and unresolved uncertainty.

Earlier satisfactory reports obtained this depth through a separate
model-authored synthesis after the durable topic was produced. The current
deterministic renderer exposed the underlying granularity instead. In addition,
the canonical English protocol compresses important depth guidance present in
the Chinese companion, increasing model-dependent variation.

Baseline classification:

- Result: `Design Defect`
- Scope: `both`
- Requirement defect: "human-readable" was interpreted as "complete audit
  projection" instead of "reader-oriented learning document".
- Architecture defect: the canonical topic had no reviewed representation for
  connected explanatory prose, leaving the renderer only atomic claims.

## 3. Task Intent

### Outcome

Every genuinely converged topic produces an immutable Markdown document that a
reader can use to understand and apply the learned knowledge without reading
the learning process.

### Success Evidence

1. The report opens with a concise orientation and then develops coherent
   subject-matter sections.
2. Each coverage dimension is explained, not merely named or represented by
   isolated claims.
3. The report includes cross-dimension synthesis, practical application, and
   explicit boundaries or uncertainty.
4. The report omits investigation plans, gates, cycle history, delta bookkeeping,
   internal IDs as headings, and host workflow narration.
5. Every substantive section is traceable to active or disputed durable claims
   and evidence that passed skeptic review.
6. Rendering the same topic version always produces identical UTF-8 bytes.

### Stop Condition

Stop and return to architecture review if implementation requires:

- a model call after publication or inside `renderer.py`;
- a durable writer other than `KnowledgeStore`;
- a ninth vNext stage;
- an independent report knowledge source;
- silent use of reader prose that did not pass skeptic review.

### Non-goals

- Personalized teaching or user modeling
- A universal article template for every domain
- Rewriting previously stored topic versions
- Hiding or deleting audit history
- Generating a report at a checkpoint

## 4. Baseline Read Set

- `README.md`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- `skill/deep-inquiry/scripts/judgments.py`
- `skill/deep-inquiry/scripts/knowledge_schema.py`
- `skill/deep-inquiry/scripts/learner.py`
- `skill/deep-inquiry/scripts/knowledge_publisher.py`
- `skill/deep-inquiry/scripts/knowledge_store.py`
- `skill/deep-inquiry/scripts/renderer.py`
- `skill/deep-inquiry/scripts/autonomous_runtime.py`
- `skill/deep-inquiry/scripts/vnext_host.py`
- Historical report specification and ADR in commit `2231e76`

## 5. Product Risk Lens

- Value: restore an end product that transfers knowledge, not merely exposes
  internal state.
- Non-goals: do not turn the Skill back into a teaching-profile system or add
  free-form post-processing.
- Trade-off: integration responses become larger because they carry a complete
  reader-document candidate.
- Decision: prefer reviewed durable prose over cheaper but shallow projection.

## 6. First-Principles and Architecture Review

### First-principles Invariants

- Non-negotiable goal: the completed artifact must teach the topic coherently.
- Non-negotiable constraints: published grounding, skeptic review,
  deterministic rendering, one writer, and immutable versioned output.
- Historical assumption to delete: atomic claims alone are a sufficient source
  for a reader-quality document.

### Owner and Retirement Matrix

- Canonical knowledge owner: `TopicKnowledge`, including its reader
  representation.
- Epistemic author: the host agent responding to `integrate_learning`.
- Review owner: the existing `skeptic_review` stage.
- Lifecycle owner: `KnowledgePublisher`.
- Durable writer: `KnowledgeStore`.
- Presentation owner: `renderer.py`.
- Old audit-style report shape: retired for newly converged schema-v2 topics.
- Compatibility carrier: schema-v1 topics remain readable; their existing
  immutable reports are not rewritten.

### Architecture Integrity Lens

- Invariant: all report assertions must already exist in the reviewed canonical
  topic version.
- Responsibility overlap: the renderer must not summarize, infer, or repair
  reader prose.
- Higher-level simplification: extend the canonical topic contract instead of
  adding a post-processing pipeline or a second report store.
- Falsifier: a report sentence that cannot be traced to the published
  `reader_document`, or reader prose published without skeptic approval,
  disproves the design.
- Verdict: proceed with one structured reader representation inside
  `TopicKnowledge`.

## 7. Alternatives

### A. Structured Reader Document in `TopicKnowledge` — Selected

The integration candidate supplies a complete structured reader document. It is
reviewed and atomically published with the same factual delta.

Advantages:

- one canonical source;
- reviewed prose;
- deterministic rendering;
- no new stage or writer;
- flexible enough for different domains.

Costs:

- larger integration payloads;
- schema evolution and compatibility checks;
- each accepted delta must keep the reader document coherent.

### B. Store Complete Markdown

The agent would publish a Markdown body directly.

Rejected because formatting and knowledge would be mixed, structural validation
would be weak, and future presentation changes would require rewriting canonical
knowledge.

### C. Model-authored Post-processing at Convergence

The host would call a model after convergence to write the document.

Rejected because the prose would bypass the existing skeptic review, create a
second epistemic output path, and make retries non-deterministic.

## 8. Canonical Data Contract

### 8.1 Schema Evolution

`TopicKnowledge` gains an optional `reader_document` field and advances to
schema version 2 when a new learning delta is published.

- Schema-v1 topics without `reader_document` remain readable.
- Initial topic creation may store `reader_document: null`.
- A vNext learning publication must supply a complete valid reader document.
- The first accepted learning delta upgrades the topic projection to schema v2.
- Historical snapshots and reports are never rewritten.

### 8.2 Reader Document

The canonical shape is:

```json
{
  "schema_version": 1,
  "overview": {
    "paragraphs": ["reader-facing paragraph"],
    "claim_ids": ["active-or-disputed-claim-id"],
    "evidence_ids": ["evidence-id"]
  },
  "sections": [
    {
      "id": "stable-section-id",
      "heading": "reader-facing heading",
      "paragraphs": ["connected explanatory paragraph"],
      "key_points": ["optional concise decision or takeaway"],
      "dimension_refs": ["coverage dimension"],
      "claim_ids": ["active-or-disputed-claim-id"],
      "evidence_ids": ["evidence-id"]
    }
  ],
  "synthesis": {
    "paragraphs": ["cross-dimension explanatory paragraph"],
    "claim_ids": ["active-or-disputed-claim-id"],
    "evidence_ids": ["evidence-id"]
  },
  "application_guidance": [
    {
      "text": "ordered practical action or decision rule",
      "claim_ids": ["active-or-disputed-claim-id"],
      "evidence_ids": ["evidence-id"]
    }
  ],
  "boundary_notes": [
    {
      "text": "reader-facing limitation, exception, or uncertainty",
      "claim_ids": ["active-or-disputed-claim-id"],
      "gap_ids": ["open-or-deferred-gap-id"]
    }
  ]
}
```

All prose fields contain plain text, not authored Markdown. The renderer owns
Markdown escaping, headings, lists, and source numbering.

### 8.3 Structural Validation

The kernel deterministically rejects a reader document when:

1. `overview`, `sections`, `synthesis`, `application_guidance`, or
   `boundary_notes` is empty;
2. any coverage dimension is absent from all `dimension_refs`;
3. an active claim is not referenced by at least one section, synthesis support
   record, application item, or boundary note;
4. a section references an unknown or retired claim;
5. an evidence ID is unknown or is not linked to one of the section's claims;
6. a boundary note references an unknown, resolved-only, or unrelated gap;
7. section IDs are duplicated or a section has no claim reference;

Workflow narration is a semantic defect rather than a language-independent
schema error. The agent contract prohibits it and the skeptic must reject it.

Semantic quality cannot be proven by character counts. It is governed by the
agent contract and skeptic review described below.

### 8.4 Update Semantics

Each `integrate_learning` response carries the complete candidate
`reader_document`, not an unvalidated patch.

- The agent starts from the current reader document and revises only what the
  new delta changes, while returning a coherent full snapshot.
- New or revised claims must be incorporated into explanatory context.
- Retired claims must be removed or explicitly replaced before publication.
- The candidate document is recorded in the existing publication audit
  integration payload, then published atomically with the topic version.
- Rejected candidates do not change either claims or reader prose.

A direct claim-retirement operation that cannot supply reviewed replacement
prose invalidates `reader_document` for the new topic version. That version
remains queryable but cannot converge or generate a new reader report until a
later reviewed integration restores a valid document.

## 9. Agent and Review Contracts

### 9.1 `integrate_learning`

The instruction must require the agent to produce both the factual delta and a
complete reader-document candidate. The prose must:

- explain mechanisms and causal relationships rather than restate claims;
- make conditions and decision branches explicit;
- connect related coverage dimensions;
- include concrete application or evaluation steps;
- state boundaries, counterexamples, and unresolved uncertainty;
- distinguish evidence-backed facts from heuristics;
- avoid gates, action plans, cycle history, and process narration;
- preserve the topic's working language.

The response template adds required field `reader_document`.

### 9.2 `skeptic_review`

The skeptic receives the complete integration proposal, including
`reader_document`, and must assess:

- unsupported synthesis or advice;
- contradictions with active claims or evidence;
- omitted dimensions or important claims;
- misleading certainty or hidden counterexamples;
- shallow enumeration where a mechanism or decision chain is required;
- prose that exposes internal workflow instead of teaching the topic.

The response adds:

```json
{
  "reader_document_approved": true,
  "reader_document_defects": []
}
```

Publication requires:

- normal candidate approval;
- no structural hit;
- `reader_document_approved: true`;
- an empty `reader_document_defects` list.

### 9.3 `assess_convergence`

The deterministic convergence preconditions add reader-document readiness:

- schema and references are valid;
- every coverage dimension is represented;
- all active claims are dispositioned;
- application and boundary material exist;
- the latest skeptic review approved the same candidate document.

Failure returns to `integrate_learning`; it does not create a report.

No ninth stage is introduced.

## 10. Reader Report Contract

For schema-v2 topics, `renderer.py` emits:

1. title;
2. overview;
3. explanatory sections in stored order;
4. cross-dimension synthesis;
5. practical application;
6. boundaries and remaining uncertainty;
7. compact source notes.

The main report must not contain:

- proposition metadata tables;
- claim IDs as headings;
- claim kind, status, or version bookkeeping;
- investigation plans or action plans;
- gate decisions;
- convergence history or cycle-by-cycle deltas;
- internal cursor, host, or protocol terminology.

Evidence references may appear as stable numbered source notes derived
deterministically from each block's `evidence_ids`. Internal evidence IDs are
not used as reader-facing headings.

Schema-v1 topics retain the existing audit-style renderer only for compatibility
when explicitly re-rendered. New convergence is forbidden until a reviewed
reader document upgrades the topic.

## 11. Protocol Parity

`SKILL.md` remains canonical English, and `SKILL.zh-CN.md` remains a complete
Chinese semantic mirror.

Both documents must state the same requirements for:

- explanatory depth;
- conditions and branches;
- mechanisms and cross-dimension synthesis;
- practical application;
- boundaries, counterexamples, and uncertainty;
- reviewed durable reader prose;
- deterministic rendering and prohibited audit content.

Regression checks must compare stable protocol markers and required concepts
across both files. Translation may differ in wording but not in obligations,
stage count, field names, or failure behavior.

## 12. Error Handling and Compatibility

- Invalid reader content rejects the candidate before any topic write.
- Skeptic rejection records the normal immutable rejection trail.
- Report-write failure retains the completion cursor and does not mark the run
  complete.
- Identical retries reuse the immutable report.
- Different bytes at an existing report path fail closed.
- Existing query behavior remains based on canonical topic data and does not
  become personalized teaching.
- Existing schema-v1 snapshots, v1 imports, and audit records remain loadable.
- No `latest.md`, alternate writer, fallback report, or silent post-processing
  path is added.

## 13. Verification Strategy

### Schema and Integration

- Schema-v1 fixture loads without a reader document.
- Valid schema-v2 document round-trips exactly.
- Unknown, retired, unsupported, or uncovered references fail.
- An accepted delta and reader document publish atomically.
- Skeptic rejection leaves both unchanged.
- Retirement invalidates stale reader prose.

### Agent Contract

- `integrate_learning` requests the complete reader document.
- `skeptic_review` explicitly approves or rejects it.
- English and Chinese protocols preserve the same depth requirements.

### Renderer

- A representative multi-dimension fixture renders overview, explanatory
  sections, synthesis, application, boundaries, and source notes.
- Output contains no audit-history headings or internal claim headings.
- Repeated rendering is byte-identical.
- Markdown-sensitive durable text cannot break document structure.

### Completion

- True convergence requires reader-document readiness and returns
  `report_path`.
- A checkpoint creates no report.
- A schema-v1 topic cannot newly converge without an approved upgrade.
- Report-write failure remains retryable.

### Quality Acceptance

Automated structural assertions are necessary but not sufficient. Before
release, run at least two end-to-end propositions from different domains and
perform a blind reader review against these questions:

1. Can a reader explain the central mechanism after reading?
2. Can a reader identify when the conclusions apply and when they fail?
3. Can a reader perform or evaluate a concrete next action?
4. Does the document connect dimensions rather than list isolated facts?
5. Is internal learning-process machinery absent from the main narrative?

All five must pass for both samples. One sample should be compared with the
previously accepted lodging or climbing-camera-robot report style as a quality
reference, not as a text template.

## 14. Impact Statement

### Affected Layers

- Public Skill protocol in both languages
- vNext judgment request and response contracts
- Canonical knowledge schema
- Candidate integration and publication validation
- Convergence readiness
- Deterministic report projection
- Core, behavior, migration, adapter, package, and sandbox tests

### Invariants Preserved

- Eight vNext stages
- One delta per learning round
- `KnowledgePublisher` lifecycle ownership
- `KnowledgeStore` single-writer ownership
- Immutable topic versions, audit records, and report paths
- Stateless query behavior

### Main Risks

- Larger judgment payloads may increase host-model variance or context use.
- Full-document replacement can accidentally omit previously covered material.
- Mechanical reference coverage can pass while prose remains semantically weak.
- Protocol translations can drift again.

### Mitigations

- Return the current reader document in the integration snapshot.
- Validate full claim and dimension disposition.
- Require explicit skeptic approval of reader quality.
- Add cross-language contract checks.
- Use two-domain end-to-end reader acceptance before release.

## 15. Plan-Time Complexity Check

- `knowledge_schema.py` and `learner.py` are already large and should receive
  only integration hooks.
- Add a dedicated `reader_document.py` owner for reader schema validation,
  reference coverage, and readiness checks.
- Keep renderer formatting in `renderer.py`.
- Keep lifecycle policy in `KnowledgePublisher`; do not add document policy to
  `KnowledgeStore`.
- Recommendation: add one focused owner module and narrow edits to existing
  owners.

## 16. ADR and Baseline Signals

After implementation and verification:

- supersede historical ADR 0004's report-shape decision while retaining its
  immutable storage and retry decisions;
- record the reader document as part of canonical `TopicKnowledge`;
- update the architecture baseline with schema-v2 compatibility and retirement
  behavior;
- do not mark the ADR accepted before implementation evidence exists.
