# Cognitive Reader Report Optimization Implementation Plan

## Goal

Implement the approved schema-v3 cognitive reader-document upgrade so that new
Deep Inquiry publications produce grounded reports with a compact domain map,
dependency-ordered explanation, mechanism chains, variables, transfer prompts,
and typed boundaries. Preserve the existing eight-stage graph, one-writer
boundary, immutable report path, and schema-v1/schema-v2 readability.

## Architecture

- `TopicKnowledge` remains the sole published canonical topic. Durable facts
  remain claims, evidence, gaps, and counterexamples.
- `TopicKnowledge.reader_document` remains the only reader-facing knowledge
  projection. Its schema advances from v1 to v2; it contains the minimal
  cognitive map rather than a sibling `knowledge_model`.
- `reader_document.py` remains the sole owner of reader-document structure,
  reference validation, prerequisite ordering, and reader readiness.
- The host authors the complete reader document only in `integrate_learning`.
- `skeptic_review` remains stage six and gains structured
  cognitive-document findings; it does not become a new lifecycle stage.
- `KnowledgePublisher` remains the lifecycle owner; `KnowledgeStore` remains
  the sole durable writer.
- `renderer.py` formats an already approved, ordered document. It does not
  infer concepts, relations, mechanisms, or conclusions.
- `VNextHost` writes the deterministic report before it persists `complete`;
  report-write failure leaves the run and cursor retryable.

## Tech Stack

Python 3.10+ standard library, `unittest`, existing atomic file-protocol
fixtures, UTF-8 Markdown, and the current immutable `KnowledgeStore` report
writer.

## Baseline / Authority Refs

- `docs/aegis/specs/2026-09-24-cognitive-reader-report-optimization-design.md`
- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- `docs/aegis/adr/0005-reader-oriented-report.md`
- `docs/aegis/specs/2026-09-23-reader-oriented-knowledge-report-design.md`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- `README.md`

## Plan Basis

Facts:

- The current schema-v2 reader document validates grounding and coverage but
  has no canonical representation for concepts, typed relations, explanation
  order, variables, or reader transfer.
- `VNextHost._result()` already renders and writes the report before saving the
  host run as complete; its retry semantics must remain explicit and tested.
- `KnowledgePublisher.publish_or_reject()` already atomically preserves the
  integration candidate and skeptic decision through `KnowledgeStore`.
- Existing tests cover schema-v1 compatibility, schema-v2 reports, eight-stage
  stability, report-write retry, and two-domain reader acceptance.

Assumptions:

- A complete v2 reader document fits the existing integration response size
  boundary.
- A blind reader review can be executed as a release Gate using rendered
  Markdown only and recorded as evidence, without adding a model call to the
  deterministic kernel.

Unknowns resolved during execution:

- Whether the public package checker asserts v1 reader-document field names
  outside current test modules.
- Whether Chinese terminology for cognitive map and transfer prompts needs a
  localized term list beyond the existing protocol mirror.

## Ripple Signal Triage

- Schema ripple: `TopicKnowledge`, immutable snapshots, learner candidate
  construction, reader readiness, lifecycle records, and persistence reads.
- Host-contract ripple: `integrate_learning` and `skeptic_review` templates,
  runtime payloads, audit reviews, and package protocols.
- Presentation ripple: Markdown heading sequence, source collection, domain-map
  table/list formatting, and internal-term leakage checks.
- Completion ripple: convergence readiness and the report-write-before-complete
  invariant.
- Result: expanded core, behavior, protocol, renderer, end-to-end, package,
  and blind-reader verification is required.

## Compatibility Boundary

- Read schema-v1 audit topics, schema-v2 reader-document-v1 topics, immutable
  snapshots, lifecycle records, imports, and existing report files unchanged.
- Do not rewrite or delete historical topics, reports, or snapshots.
- New accepted learning publications write schema-v3 topics with a complete
  reader-document v2. Existing schema-v2 topics upgrade only through such a
  publication.
- Keep report filenames `topics/<topic-id>/reports/vNNNNNN.md`, `report_path`,
  atomic byte comparison, containment checks, and retry behavior unchanged.
- Keep `query` stateless and independent of report presence.
- Do not introduce document-only publication, a mutable report alias, a second
  version axis, or a durable writer other than `KnowledgeStore`.

## Architecture Integrity Lens

- Invariant: all visible cognitive relationships and reader assertions are in
  the skeptic-approved published reader document and trace to durable facts.
- Canonical owner / contract: `TopicKnowledge.reader_document` v2 and
  `reader_document.py`; claims/evidence/gaps remain the fact source.
- Responsibility overlap: renderer inference and a separate `knowledge_model`
  are prohibited because they duplicate host judgment or reader-document
  organization.
- Higher-level simplification: evolve the existing schema validator and
  publisher transaction rather than add a post-convergence composition service.
- Retirement / falsifier: any v3 report that obtains a relation or mechanism
  from renderer inference, or any document-only direct store write, falsifies
  this architecture.
- Verdict: proceed.

## Plan Pressure Test

- Owner / contract / retirement: one nested document contract replaces the
  unstructured contract for new v3 publications; old v1/v2 reads are bounded
  compatibility carriers.
- Architecture integrity / higher-level path: no new writer, stage, or fact
  projection is needed.
- Verification scope: high because the contract crosses schema, lifecycle,
  host, renderer, protocol, and release acceptance.
- Task executability: each task has focused unittest commands and explicit
  negative cases.
- Pressure result: proceed.

## Plan-Time Complexity Check

- Target files: `knowledge_schema.py` (962 lines), `judgments.py` (940),
  `autonomous_runtime.py` (734), `learner.py` (726), `renderer.py` (369), and
  `reader_document.py` (299).
- Existing size / shape signals: schema, judgments, learner, and runtime are
  already large core owners.
- Owner fit: nested document validation belongs in `reader_document.py`;
  runtime should only carry validated contract fields; renderer should only
  format.
- Add-in-place risk: embedding topology validation into `knowledge_schema.py`
  or renderer would create duplicate ownership.
- Better file boundary: extend `reader_document.py`; create focused new test
  modules rather than growing existing mixed suites further.
- Recommendation: add owner-specific tests; edit core owners only at their
  existing integration seams.

## Anti-Entropy Declaration

- Deletion Class: `contract-carrying code`
- Old Path/Object: schema-v3 use of reader-document v1 as the canonical
  document contract.
- New Canonical Owner: reader-document v2 inside `TopicKnowledge`.
- Expected Preserved Behavior: v1/v2 reads, old reports, single writer,
  immutable report versions, and eight-stage graph.
- Expected Retired Behavior: publishing a new schema-v3 topic with an
  unstructured reader document that lacks cognitive organization.
- External Boundary Touched: yes, host protocol and installed package.
- Source-of-Truth Data Risk: possible for historical snapshots.
- User Confirmation Required: no, because no stored data is deleted or
  rewritten.

## Retirement Decision

- Path: `compat-exception` for schema-v1 and schema-v2 reads; `delete-first`
  for new schema-v3 use of the v1 document contract.
- Why: old artifacts are immutable sources of record, but a new publication
  needs exactly one complete v2 document contract.
- Non-edits: no old-report rewrite, snapshot migration, report alias, renderer
  fallback inference, or document-only store write.

## File Map

Create:

- `tests/test_cognitive_reader_document_schema.py`
- `tests/test_cognitive_reader_document_runtime.py`
- `tests/test_cognitive_reader_report_renderer.py`
- `tests/test_cognitive_reader_report_e2e.py`
- `docs/aegis/adr/0006-cognitive-reader-document.md`
- `docs/aegis/work/2026-09-24-cognitive-reader-report-optimization/`
  evidence and Gate records during execution

Modify:

- `skill/deep-inquiry/scripts/reader_document.py`
- `skill/deep-inquiry/scripts/knowledge_schema.py`
- `skill/deep-inquiry/scripts/learner.py`
- `skill/deep-inquiry/scripts/judgments.py`
- `skill/deep-inquiry/scripts/knowledge_publisher.py`
- `skill/deep-inquiry/scripts/autonomous_runtime.py`
- `skill/deep-inquiry/scripts/convergence.py`
- `skill/deep-inquiry/scripts/renderer.py`
- `skill/deep-inquiry/scripts/vnext_host.py`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- `README.md`
- `docs/aegis/INDEX.md`
- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`

Do not modify:

- `knowledge_store.py` unless a focused retry regression proves a
  serialization-only adjustment is necessary.
- v1 importers, persistent knowledge roots, historical report files, or
  user-level installed package copies.

## Task 1: Define Schema-v3 Reader Document v2

**Files**

- Create `tests/test_cognitive_reader_document_schema.py`
- Modify `skill/deep-inquiry/scripts/reader_document.py`
- Modify `skill/deep-inquiry/scripts/knowledge_schema.py`
- Modify `skill/deep-inquiry/scripts/learner.py`

**Why**

Give the existing canonical reader document enough structure to express a
grounded domain map without creating a second knowledge source.

**Repair Track**

- Root cause: reader-document v1 validates prose references but cannot capture
  concepts, relations, prerequisites, variables, or transfer.
- Canonical owner: `reader_document.py`.
- Minimal stable repair: add reader-document v2 dispatch and topology
  validation inside the existing owner.
- Compatibility: schema-v1 and schema-v2 topic reads retain their existing
  validators; only a new accepted publication upgrades to topic schema-v3.

**Verification**

```bash
python3 -m unittest tests.test_cognitive_reader_document_schema -v
python3 -m unittest tests.test_reader_document_schema -v
```

Expected: v2 accepts a complete grounded map; all invalid-map and legacy
compatibility cases pass.

1. [ ] Write `tests/test_cognitive_reader_document_schema.py` using the
   existing valid v1 reader-document fixture as a base. Add a valid v2 fixture
   with `orientation.current_conclusion`, three concepts, two typed relations,
   a topologically ordered prerequisite edge, a keystone mechanism chain, one
   key variable, typed boundary note, and one transfer prompt. Add negative
   tests for an unknown concept, unsupported relation type, ungrounded
   relation, prerequisite cycle, section order violation, missing keystone
   mechanism, missing transfer prompt, and invalid boundary type.
2. [ ] Run the new module before implementation and confirm it fails because
   reader-document schema version 2 is unsupported:
   `python3 -m unittest tests.test_cognitive_reader_document_schema -v`.
3. [ ] In `reader_document.py`, retain the current schema-v1 validator as a
   named compatibility path. Add a v2 validator that normalizes JSON,
   validates local IDs and claim/evidence references, validates the five
   relation enums, checks the prerequisite graph with a deterministic
   topological-order helper, verifies section ordering, and enforces the
   required reader blocks. Keep all validation errors as
   `ReaderDocumentError`.
4. [ ] In `knowledge_schema.py`, allow `TopicKnowledge.schema_version >= 3`
   only when a reader-document v2 validates; preserve existing v1/v2 load
   behavior. In `learner.py`, make an accepted complete v2 document upgrade
   its candidate topic to schema version 3 while preserving the existing
   retirement exception behavior.
5. [ ] Run both focused modules until green and run
   `python3 -m compileall -q skill/deep-inquiry/scripts tests`.

## Task 2: Carry Cognitive Review Through the Existing Publication Transaction

**Files**

- Create `tests/test_cognitive_reader_document_runtime.py`
- Modify `skill/deep-inquiry/scripts/judgments.py`
- Modify `skill/deep-inquiry/scripts/knowledge_schema.py`
- Modify `skill/deep-inquiry/scripts/autonomous_runtime.py`
- Modify `skill/deep-inquiry/scripts/knowledge_publisher.py`

**Why**

Ensure a valid topology is not merely structurally present: it must be
reviewed by the existing skeptic stage and atomically audited with the factual
candidate.

**Impact / Compatibility**

- Preserve exactly eight `AUTONOMOUS_STAGES`.
- Evolve review data as one structured reader-document decision, retaining
  legacy review-record readability.
- Never let host payload handling or `KnowledgePublisher` accept a cognitive
  defect as an approved document.

**Verification**

```bash
python3 -m unittest tests.test_cognitive_reader_document_runtime -v
python3 -m unittest tests.test_reader_document_runtime -v
```

Expected: approval publishes one schema-v3 topic; any cognitive defect rejects
before canonical version advance and records the rejection.

1. [ ] Write failing runtime tests that build an integrate candidate with
   reader-document v2 and a skeptic response containing an approved/rejected
   document decision plus defect categories. Cover rejection for each of
   `cognitive_map`, `mechanism_depth`, `dependency_order`, `synthesis`,
   `transfer`, `boundary_expression`, and `audit_leakage`; assert topic version
   does not advance and terminal audit records retain the decision.
2. [ ] Run the module and confirm failure because current judgment templates
   neither request nor validate the structured cognitive findings.
3. [ ] Update `judgments.py` templates and response validation to request the
   v2 document from `integrate_learning` and structured reader-document review
   from `skeptic_review`. Update `autonomous_runtime.py` to carry that result
   unchanged into the publication review payload.
4. [ ] Update `PublicationRecord` validation and
   `KnowledgePublisher._review_decision()` to accept the structured review
   shape, reject every non-empty defect list, and preserve legacy audit-record
   readability. Do not add a new publisher entry point or stage.
5. [ ] Run both focused runtime modules until green, then run
   `python3 -m unittest tests.test_low_gain_major_delta -v`.

## Task 3: Render the Cognitive Map Without Inference

**Files**

- Create `tests/test_cognitive_reader_report_renderer.py`
- Modify `skill/deep-inquiry/scripts/renderer.py`
- Modify `skill/deep-inquiry/scripts/reader_document.py` only if a
  renderer-needed ordering helper is already owned there

**Why**

Make the approved cognitive organization readable in Markdown while preserving
deterministic output and the renderer's presentation-only boundary.

**Impact / Compatibility**

- Keep `_render_schema_v1_audit_compatibility()` unchanged.
- Keep the schema-v2-topic / reader-document-v1 renderer path explicit.
- Add a schema-v3 / reader-document-v2 branch without converting old reports.
- Use reader-provided order; do not sort concepts, invent headings, or derive
  relations from claims.

**Verification**

```bash
python3 -m unittest tests.test_cognitive_reader_report_renderer -v
python3 -m unittest tests.test_reader_report_renderer -v
```

Expected: v3 output has stable source numbers, no internal IDs, and three
usable reading paths.

1. [ ] Write a v3 renderer fixture and failing tests for: early central
   question/scope/current conclusion; compact domain-map presentation;
   prerequisite-ordered explanatory headings; a readable mechanism sequence;
   near-section typed boundary placement; transfer prompt; stable byte output;
   and absence of claim/gap IDs, review terms, cycle/cursor/pending text, or
   audit headings.
2. [ ] Run the module and confirm it fails because the renderer only
   understands reader-document v1.
3. [ ] Add a dedicated v3 renderer function. Render orientation first, then
   the map, ordered explanatory sections, synthesis, transfer guidance,
   further learning, and sources. Render the map as a compact table/list and
   mechanism chains as a readable sequence. Collect evidence IDs strictly from
   displayed document blocks in first-display order.
4. [ ] Preserve v1/v2 branches and make `render_knowledge_report()` dispatch
   explicitly by topic schema and reader-document schema. Raise `ValueError`
   for an unready v3 topic rather than falling back to v1 output.
5. [ ] Run both renderer modules until green. Have the v3 renderer test write
   its deterministic output to a temporary fixture path and scan that output
   only for `Convergence History`, `Knowledge Gaps`, `Topic ID`, and
   `Cycle <number>`; assert no matches. Do not scan `renderer.py` globally
   because the schema-v1 compatibility function intentionally contains those
   headings.

## Task 4: Preserve Convergence and Completion Retry Semantics

**Files**

- Create `tests/test_cognitive_reader_report_e2e.py`
- Modify `skill/deep-inquiry/scripts/convergence.py`
- Modify `skill/deep-inquiry/scripts/vnext_host.py`
- Modify `skill/deep-inquiry/scripts/autonomous_runtime.py` only where v3
  readiness payload handling requires it

**Why**

Keep report quality as a completion prerequisite without allowing a render or
write failure to falsely finish a run.

**Impact / Compatibility**

- Convergence remains owned by `evaluate_convergence()`.
- `reader_document_ready()` is the only document readiness predicate.
- `VNextHost._result()` must write immutable report bytes before durable run
  completion and retain the same pending cursor on failure.
- Checkpoints continue to have no report path.

**Verification**

```bash
python3 -m unittest tests.test_cognitive_reader_report_e2e -v
python3 -m unittest tests.test_reader_report_e2e -v
```

Expected: valid v3 converges and writes a report; unready v3 blocks; a report
write failure keeps the run active and retry writes identical bytes before the
run becomes complete.

1. [ ] Write failing end-to-end tests with a v3 candidate for successful
   completion, non-convergence when document validation fails, checkpoint
   behavior, stale completion-cursor refusal, and a store writer that fails
   once before succeeding. Assert that the failed run is still `active`, the
   same cursor remains pending, topic version does not advance again, and the
   retry result contains the immutable report path.
2. [ ] Run the module and confirm failure because existing fixtures only model
   reader-document v1.
3. [ ] Update convergence and host-facing readiness code only as necessary to
   recognize schema-v3 document readiness; retain the existing
   report-write-before-`_save_run(status="complete")` ordering and make the
   retry assertion explicit in code comments or tests.
4. [ ] Update e2e fixture builders so schema-v2 compatibility reports still
   exercise their old path and schema-v3 exercises the new path.
5. [ ] Run both e2e modules until green and run the full test suite:
   `python3 -m unittest discover -s tests -v`.

## Task 5: Publish Equivalent Host Contracts and Record the Decision

**Files**

- Modify `skill/deep-inquiry/SKILL.md`
- Modify `skill/deep-inquiry/SKILL.zh-CN.md`
- Modify `README.md`
- Create `docs/aegis/adr/0006-cognitive-reader-document.md`
- Modify `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- Modify `docs/aegis/INDEX.md`
- Modify `tests/test_reader_report_protocol.py` or create
  `tests/test_cognitive_reader_report_protocol.py`

**Why**

Expose the new complete host contract in the English canonical protocol and
Chinese mirror, and preserve the source-of-truth decision for future changes.

**Impact / Compatibility**

- English remains the canonical protocol; Chinese is a complete mirror.
- Protocol examples show only plain-text reader prose and never internal IDs.
- Documentation states that cognitive organization is part of the existing
  reader document, not an independent knowledge graph.
- ADR 0005 remains valid for ownership, deterministic rendering, and v1
  compatibility; ADR 0006 records the schema-v3 refinement and deferrals.

**Verification**

```bash
python3 -m unittest tests.test_cognitive_reader_report_protocol -v
python3 -m unittest tests.test_reader_report_protocol -v
```

Expected: both protocols require equivalent map, mechanism, transfer, boundary,
and review behavior; README describes reader capability without promising
document-only editing.

1. [ ] Write failing protocol tests that require both language files to mention
   the same reader-document v2 fields, keystone-concept target, supported
   relation types, mechanism chain, transfer guidance, typed boundaries,
   skeptic defect categories, and no ninth stage. Assert README does not claim
   graph visualization, mutable revisions, or a separate knowledge model.
2. [ ] Run the module and confirm it fails against the v1 protocol shape.
3. [ ] Update both protocols and README. Create ADR 0006 with decision,
   alternatives, owners, compatibility exception, retirement trigger,
   non-goals, and evidence required before a future document-only revision.
   Update the baseline's verified-state and risk sections only after code and
   tests are green.
4. [ ] Append ADR, spec, and plan references to `docs/aegis/INDEX.md`.
5. [ ] Run both protocol modules until green and run
   `git diff --check`.

## Task 6: Execute Cross-Topic and Blind Reader Acceptance Gates

**Files**

- Extend `tests/test_cognitive_reader_report_e2e.py`
- Create or update
  `docs/aegis/work/2026-09-24-cognitive-reader-report-optimization/20-checkpoint.md`
- Create or update
  `docs/aegis/work/2026-09-24-cognitive-reader-report-optimization/90-evidence.md`

**Why**

Prove that the new document shape survives different domains and that its
reader value is not reduced to structural validation.

**Impact / Compatibility**

- Deterministic tests never call a model.
- Blind review is a release acceptance Gate, not a runtime feature.
- The reviewer sees only generated Markdown and no topic JSON, claims,
  evidence registry, session, or expected-answer fixture.

**Verification**

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skill/deep-inquiry/scripts tests
git diff --check
```

Expected: all automated tests pass; evidence records the blind reviewer
questions, answers, and criterion-level pass/fail results for each domain.

1. [ ] Add three deterministic v3 fixtures: engineering feasibility with
   variables and a mechanism chain; comparison/trade-off with a recommendation
   reversal condition; and conceptual/disputed knowledge without fabricated
   project-management content. Assert the generated reports structurally
   contain orientation, map, keystones, mechanism, variable, transfer, typed
   boundary, and no audit leakage.
2. [ ] Run the full suite and confirm all old schema-v1/v2 compatibility tests
   plus new v3 fixtures pass.
3. [ ] Dispatch a fresh independent reader reviewer for each rendered Markdown
   file. Require documented answers for mechanism, conditions, use/action,
   synthesis, absence of internals, central question/scope/conclusion, domain
   map/keystones, variable effect, boundary classification, and transfer
   question. Record exact PASS/FAIL evidence in `90-evidence.md`.
4. [ ] If any blind criterion fails, return only the relevant document contract
   or renderer slice to review; do not weaken the checklist or add a renderer
   inference fallback.
5. [ ] Record final drift check, package gate, and remaining residual risk in
   `20-checkpoint.md` and `90-evidence.md`. Do not commit, push, or synchronize
   the user installation unless the user explicitly asks.

## Final Verification and Release Gate

Before any completion, commit, merge, push, or package synchronization claim:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q skill/deep-inquiry/scripts tests
git diff --check
git status -sb
```

Also run package-local import and protocol checks, inspect the schema-v3
renderer output for audit headings, complete the three blind-reader reviews,
and verify a schema-v1 report still renders only its compatibility projection.

## Risks and Rollback

- Host payload growth: reject at contract validation; do not truncate a
  document silently.
- Cognitive-map hallucination: skeptic rejects unsupported relations; renderer
  cannot repair or infer them.
- Schema migration regression: retain v1/v2 read branches and fixture tests;
  rollback by not publishing an unaccepted v3 candidate.
- Reader overload: blind review catches excessive tables, repeated conclusions,
  and absent transfer; do not add more block types in this phase.
- Completed-report editing demand: defer to a separate reviewed lifecycle
  design; do not introduce a direct writer bypass.

## Execution Boundary

This plan creates no automatic commit. Commit, push, merge, and user-level
Skill synchronization require explicit user instructions after the relevant
verification and independent-review Gates pass.
