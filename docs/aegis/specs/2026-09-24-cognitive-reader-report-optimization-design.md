# Cognitive Reader Report Optimization Design

Status: `proposed for user review`
Date: `2026-09-24`
ArchitectureReviewRequired: `yes`

## 1. Decision Summary

Deep Inquiry will extend the existing canonical `TopicKnowledge.reader_document`
instead of adding an independent knowledge-graph subsystem or a separate report
lifecycle. A schema-v3 topic will carry a schema-v2 reader document with a
small, grounded cognitive map: core concepts, typed relationships, prerequisite
order, mechanism chains, key variables, and reader-facing transfer prompts.

The existing eight-stage graph remains unchanged. The host proposes the complete
document during `integrate_learning`; `skeptic_review` retains its role and
adds explicit cognitive-document findings; `KnowledgePublisher` atomically
publishes only approved candidates; and `renderer.py` remains deterministic.

This is a scoped correction to report quality. It does not turn Deep Inquiry
into a course generator, ontology platform, or independently editable report
system.

## 2. Task Intent Draft

### Outcome

For newly accepted learning publications, produce an immutable Markdown report
that lets a reader identify the subject boundary, form a small domain map,
follow the main mechanisms in dependency order, reason about changing
variables, and apply the model to an adjacent case.

### Success Evidence

1. The report opens with the central question, scope, main conclusion, and
   reader-relevant uncertainty.
2. A compact domain map makes the principal concepts, relationships, and
   variables visible before detailed explanation.
3. Three to seven keystone concepts normally form the explanatory spine;
   genuinely narrow propositions may use two without fabricating concepts.
4. A mechanism section connects conditions or inputs to intermediate effects,
   consequences, and implications.
5. At least one transfer prompt asks the reader to use the model on a new
   scenario or variable change.
6. Important limits are expressed near the conclusion they constrain and are
   classified for the reader.
7. The report remains deterministic, grounded, immutable, and free of audit
   workflow narration.

### Stop Condition

Stop and return to architecture review if this work requires a new durable
knowledge owner, a ninth vNext stage, a model call inside rendering, a new
mutable report channel, or automatic inference of semantic relationships from
claims without host judgment and skeptic review.

### Non-goals

- Independent document-only publication after knowledge convergence
- Separate `knowledge_model` persistence outside `reader_document`
- `knowledge_version` and `document_revision` version axes
- Graph visualization, HTML/PDF output, or cross-topic ontology merging
- A fixed universal report template or mandatory project-management modules
- Evidence metadata expansion, professional advice, or reader profiling

## 3. Baseline Read Set Hint

- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- `docs/aegis/adr/0005-reader-oriented-report.md`
- `docs/aegis/specs/2026-09-23-reader-oriented-knowledge-report-design.md`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- `skill/deep-inquiry/scripts/knowledge_schema.py`
- `skill/deep-inquiry/scripts/reader_document.py`
- `skill/deep-inquiry/scripts/judgments.py`
- `skill/deep-inquiry/scripts/knowledge_publisher.py`
- `skill/deep-inquiry/scripts/convergence.py`
- `skill/deep-inquiry/scripts/renderer.py`

## 4. Baseline Role Alignment

- Product / Requirement Baseline: reports must let a reader understand and
  apply skeptic-reviewed knowledge, not merely inspect a clean audit export.
- Architecture / Runtime Boundary Baseline: `TopicKnowledge` is canonical,
  `KnowledgePublisher` owns lifecycle, `KnowledgeStore` is the sole writer,
  the eight stages remain stable, and rendering is deterministic.
- Result: `Design Defect`, scope `both`.
- Requirement cause: schema-v2 ensures grounded prose and coverage breadth but
  does not express the minimum cognitive organization needed to consistently
  meet the existing reader-understanding outcome.
- Architecture cause: meeting that outcome requires a schema, validation,
  publication-review, convergence-readiness, renderer, and host-completion
  contract migration while preserving the existing owners.
- Next action: evolve the existing reader-document contract rather than create
  a second knowledge owner.

## 5. Product and Architecture Lenses

### Product Risk Lens

- Value: readers receive an understandable knowledge artifact rather than a
  polished collection of disconnected sections.
- Non-goals: personalized teaching, encyclopedic coverage, or project
  management output.
- Trade-off: integration and review payloads become moderately richer.
- Decision: favor a small validated map over a large generic report framework.

### First-Principles Review

- First Principle: a completed report must enable a reader to reconstruct and
  use the central knowledge model.
- Non-negotiables: reviewed grounding, deterministic rendering, one writer,
  immutable output, and the eight-stage runtime.
- Assumptions to Drop: coverage dimensions imply cognitive structure; a
  document reviewer must be a new runtime stage; report editing requires its
  own lifecycle.
- Smallest Sufficient Path: persist a compact cognitive map inside the already
  reviewed reader document and review it in the existing skeptic stage.
- Escalation Signal: recurring demand to revise completed reports with no new
  knowledge merits a separate document-publication design, not an ad hoc
  writer bypass.

### Architecture Integrity Lens

- Invariant: all reader-facing statements and cognitive relationships are
  traceable to the accepted canonical topic.
- Canonical owner / contract: `TopicKnowledge.reader_document`; durable facts
  remain owned by claims, evidence, gaps, and counterexamples.
- Responsibility overlap: a top-level `knowledge_model` would duplicate the
  reader document's organizational role; renderer inference would duplicate
  host judgment.
- Higher-level simplification: validate the cognitive map as part of the
  existing document contract and publish it through the existing candidate.
- Retirement / falsifier: any schema-v3 renderer that derives a relationship
  not in the published document, or a second writer for document-only edits,
  falsifies this design.
- Verdict: proceed with a nested cognitive map.

## 6. Canonical Contract

### 6.1 Schema Evolution

`TopicKnowledge.schema_version` advances from `2` to `3` for a newly accepted
learning publication. Its `reader_document.schema_version` advances from `1`
to `2`.

- Schema-v1 and schema-v2 topics remain readable.
- Existing immutable reports and snapshots are never rewritten.
- A schema-v2 topic upgrades only through a normal accepted learning
  publication containing a complete reader-document v2.
- The storage snapshot `topic.version` remains the only version number in this
  phase. New reports retain the `vNNNNNN.md` path format.
- Document-only revisions are intentionally unsupported. A candidate rejected
  before publication may be revised and resubmitted, but a completed topic is
  not reopened merely for presentation edits.

### 6.2 Reader Document v2

All prose remains plain text. The renderer owns Markdown escaping, headings,
lists, compact tables, source numbering, and localization.

```text
reader_document
├── schema_version: 2
├── orientation
│   ├── central_question
│   ├── scope
│   ├── current_conclusion
│   ├── paragraphs
│   ├── claim_ids
│   └── evidence_ids
├── domain_map
│   ├── concepts
│   ├── relationships
│   ├── keystone_concept_ids
│   ├── prerequisite_edges
│   └── key_variables
├── sections
│   ├── cognitive_question
│   ├── concept_refs
│   ├── paragraphs
│   ├── mechanism_chain
│   └── claim_ids / evidence_ids / dimension_refs
├── synthesis
├── transfer_guidance
├── boundary_notes
└── further_learning
```

#### Orientation

`orientation` contains a neutral `central_question`, reader scope, a grounded
`current_conclusion`, and a small number of opening paragraphs. The conclusion
contains plain text plus explicit claim and evidence references. It states the
strongest supported answer available at the topic's current boundary and must
name a material uncertainty when one exists in canonical knowledge. It may not
repeat the later synthesis: the conclusion answers the central question, while
synthesis explains an interaction or consequence unavailable from one section
alone.

#### Domain Map

`concepts` contains only concepts required to understand the proposition. Each
concept has a stable local ID, label, concise definition, related claim IDs,
and optional evidence IDs. It does not create a durable fact independently of
those references. Concepts have no independent retirement lifecycle in this
phase: a replacement reader document may omit a concept, and every relation,
section, variable, or transfer reference must resolve within its own published
document.

`relationships` uses the following stable types:

- `depends_on`
- `causes`
- `constrains`
- `trades_off_with`
- `exception_to`

Each relation references known concept IDs, includes a plain-language
condition when relevant, and links to supporting claims and evidence.

`keystone_concept_ids` normally contains three to seven concepts. The
validator permits two only where the document explicitly identifies the
proposition as narrow; the skeptic determines whether that exception is
credible.

`prerequisite_edges` are directed `before -> after` concept references. They
describe explanatory order, not causal direction.

`key_variables` records a variable name, the concepts it affects, the relevant
change direction, a plain-language effect, supporting claims, and whether
project-specific input is required.

#### Explanatory Sections

Sections are ordered by prerequisite dependencies and each must answer one
`cognitive_question`. They reference one or more concepts and include a
mechanism chain when explaining a keystone concept:

```text
condition or input -> intermediate effect -> consequence -> implication
```

The host can use ordinary prose for a simple definition. It must not invent a
mechanism chain merely to fill the shape.

#### Synthesis, Transfer, and Boundaries

`synthesis` identifies an interaction, shared constraint, trade-off, or
recommendation reversal that cannot be obtained from one section alone.

`transfer_guidance` contains at least one reader question or scenario. It
states which parts of the model are reusable and which variables or facts must
be re-evaluated.

Each `boundary_note` is classified as one of:

- `knowledge_gap`
- `evidence_limit`
- `project_input`
- `professional_judgment`
- `frontier_dispute`

The note must link to the claims it constrains and may link to open or deferred
gaps. Renderer placement is adjacent to the constrained section when that
relationship is known; otherwise it appears in the final boundary section.

`further_learning` organizes unresolved understanding by direction rather than
emitting a task ledger. It must not contain investigation cycles, agent
instructions, or publication bookkeeping.

## 7. Validation and Review

### 7.1 Deterministic Validation

`reader_document.py` remains the only validation owner. For reader-document v2
it must additionally reject:

1. unknown, duplicate, or ungrounded concept and relation references;
2. unsupported relationship types;
3. a keystone concept that has no explanatory section;
4. a relation or mechanism chain that has no supporting claim;
5. a cyclic prerequisite graph;
6. explanatory sections whose order violates prerequisite edges;
7. unknown concept references from sections, variables, or transfer guidance;
8. missing `transfer_guidance`, map, synthesis, or typed boundary notes;
9. evidence not linked to a claim cited by the same block; and
10. internal workflow identifiers or audit-state terms in reader-facing prose.

Existing active-claim disposition and coverage-dimension checks remain. A
peripheral active claim may be grounded in the map rather than given its own
reader paragraph.

### 7.2 Skeptic Review

No new runtime stage is added. `skeptic_review` continues to decide factual
reliability and gains document defect categories:

- `cognitive_map`
- `mechanism_depth`
- `dependency_order`
- `synthesis`
- `transfer`
- `boundary_expression`
- `audit_leakage`

The reviewer rejects a document that is a list of terms without explanatory
relations, presents an unsupported causal relation, treats a heuristic as a
requirement, buries a material limitation, or offers a transfer scenario the
document cannot support.

The existing reader approval field can evolve into a structured result, but
the publisher must preserve the current invariant: any cognitive-document
defect prevents publication.

### 7.3 Lifecycle

The sequence remains:

```text
integrate_learning
  -> skeptic_review
  -> KnowledgePublisher.publish_or_reject
  -> KnowledgeStore.commit_lifecycle
  -> convergence decision
  -> deterministic render and KnowledgeStore.write_markdown_report
  -> durable host completion transition
```

`reader_document_ready()` includes the v2 validation result. `evaluate_convergence`
therefore still requires both factual convergence and a ready document, but
there is no separate `DocumentReady` lifecycle, writer, report revision, or
post-convergence model call. The host marks a run complete and advances its
completion cursor only after `write_markdown_report()` succeeds. A write
failure keeps the run active with the same pending completion cursor and
retries the same deterministic report bytes; it must not re-run learning or
publish another topic version.

## 8. Reading Experience Rules

The renderer receives an already ordered document. It must make three reading
paths usable without adding knowledge:

1. **Fast orientation:** title, central question, scope, keystone concepts,
   material conclusion, and key uncertainty appear early.
2. **Systematic learning:** the domain map precedes explanatory sections;
   sections follow prerequisite order; mechanism chains are rendered as compact
   causal sequences; synthesis follows the necessary component explanations.
3. **Targeted lookup:** heading names are reader questions or concepts rather
   than coverage-dimension labels; source notes remain compact; limits are
   discoverable near the affected conclusion.

Rendering rules:

- Use a small table or concise list for a domain map and variables, never an
  oversized table that replaces explanatory prose.
- Render a relationship or mechanism chain as a readable sequence, not raw
  internal IDs.
- Keep one primary cognitive task per section.
- Do not repeat the orientation conclusion verbatim in synthesis or the final
  boundary section.
- Use emphasis sparingly and never expose claim IDs, gap IDs, review terms,
  cycles, cursors, pending states, or host tools.
- The English canonical protocol and Chinese mirror must prescribe equivalent
  reader obligations and terminology.

## 9. Compatibility and Retirement

### Compatibility Boundary

- Schema-v1 audit rendering remains a compatibility exception for old topics.
- A schema-v2 topic carrying reader-document v1 remains readable and renders
  through the existing reader-document v1 compatibility path.
- No historical topic, report, snapshot, or lifecycle record is rewritten.
- Query remains stateless and independent of report presence.
- Report immutability, retry behavior, path containment, and `report_path`
  behavior remain unchanged.

### Anti-Entropy Declaration

- Deletion Class: `contract-carrying code`
- Old Path/Object: schema-v2 reader-document shape as the canonical contract
  for newly published topics.
- New Canonical Owner: `TopicKnowledge.reader_document` schema-v2, validated
  by `reader_document.py`.
- Expected Preserved Behavior: existing documents, old reports, single writer,
  immutable report paths, and eight-stage runtime.
- Expected Retired Behavior: new schema-v3 reports treating coverage dimensions
  and unstructured sections as sufficient cognitive organization.
- External Boundary Touched: yes, the host response contract and installed
  package documentation.
- Source-of-Truth Data Risk: possible for historical topic snapshots.
- User Confirmation Required: no, because no historical persistent state is
  deleted or rewritten.

### Retirement Decision

- Path: `compat-exception` for schema-v1 and schema-v2 reads; `delete-first`
  for schema-v3 use of the old unstructured reader-document contract.
- Why: old persistent data remains an active compatibility boundary, while new
  publications must have one clear reader-document shape.
- Non-edits: no report deletion, snapshot rewrite, mutable alias, or fallback
  renderer inference.

## 10. Verification

### Focused Contract Tests

- reader-document v2 accepts a grounded minimal cognitive map;
- rejects unsupported or ungrounded relations;
- rejects dependency cycles and invalid section order;
- rejects missing mechanisms for keystone concepts;
- rejects missing transfer guidance and untyped boundaries;
- preserves schema-v1 and schema-v2 read compatibility.

### Runtime and Lifecycle Tests

- a skeptic cognitive-document defect rejects the candidate before canonical
  version advance;
- a valid v3 candidate publishes through `KnowledgePublisher` only;
- convergence blocks an unready v3 document;
- renderer output is byte-identical for the same v3 topic;
- renderer neither computes relationships nor emits audit identifiers.
- report-write failure preserves the active host run and pending completion
  cursor; a retry writes the same bytes before completion can become durable.

### Reader Experience Fixtures

Use at least three distinct topics:

1. an engineering feasibility proposition with system variables and a
   mechanism chain;
2. a comparison or trade-off proposition with a recommendation reversal
   condition;
3. a conceptual or disputed proposition where no project-management structure
   is appropriate.

For each fixture, retain the existing reader acceptance criteria:

1. a mechanism is explained rather than merely named;
2. conditions or applicability limits are clear;
3. the report supports an action, decision, or use of the knowledge;
4. synthesis adds a cross-section insight; and
5. no internal workflow or audit information appears.

Add the cognitive-report criteria:

6. the reviewer identifies the central question, scope, and early conclusion;
7. the reviewer reconstructs the domain map and its keystone concepts;
8. the reviewer explains one mechanism chain and one key-variable change;
9. the reviewer classifies one boundary and answers one transfer prompt.

The reader check is blind: a fresh reviewer receives only the rendered
Markdown, not the topic JSON, claims, evidence registry, session history, or
fixture expectations. The evidence bundle records each fixture, the questions,
the reviewer answers, and a pass/fail result for every criterion. Deterministic
tests verify structural prerequisites; the blind review is the release
acceptance check for reader comprehension.

### Release Checks

Run focused tests, full test discovery, package checks, `compileall`, `git diff
--check`, protocol mirror checks, a lingering audit-heading scan, and package
hash verification before installation synchronization.

## 11. Implementation Scope

Likely modified files:

- `skill/deep-inquiry/scripts/reader_document.py`
- `skill/deep-inquiry/scripts/knowledge_schema.py`
- `skill/deep-inquiry/scripts/learner.py`
- `skill/deep-inquiry/scripts/judgments.py`
- `skill/deep-inquiry/scripts/knowledge_publisher.py`
- `skill/deep-inquiry/scripts/convergence.py`
- `skill/deep-inquiry/scripts/renderer.py`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- focused schema, runtime, renderer, protocol, and fixture tests

Do not modify `KnowledgeStore` unless a focused regression proves that
serialization alone needs extension. Do not modify v1 import modules, existing
report roots, or user-level installed copies in this phase.

## 12. Deferred Decisions

The following are intentionally deferred until use evidence justifies them:

- document-only revision after knowledge convergence;
- independent document version and report version axes;
- persistent report profiles or project-management module libraries;
- richer evidence authority, jurisdiction, currency, and locator metadata;
- visual maps, HTML/PDF output, or cross-topic concept merging.
