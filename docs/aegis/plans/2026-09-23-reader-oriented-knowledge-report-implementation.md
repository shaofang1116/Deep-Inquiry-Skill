# Reader-Oriented Knowledge Report Implementation Plan

## Goal

Replace the audit-style converged Markdown output with an immutable,
reader-oriented knowledge document backed by skeptic-reviewed canonical topic
data. Preserve the eight-stage graph, one-writer persistence boundary,
immutable topic versions and report paths, and schema-v1 readability.

## Architecture

- `reader_document.py` becomes the single owner of reader-document structure,
  reference validation, reader readiness, and deterministic text normalization
  helpers needed by validation.
- `TopicKnowledge` remains the only canonical knowledge projection and stores
  the optional reader document.
- `Learner` merges a complete reader-document candidate only while constructing
  a validated next topic version.
- `KnowledgePublisher` remains the lifecycle-policy owner; its existing
  immutable audit integration payload retains the submitted document and review.
- `HostRuntimeCoordinator` carries the existing integration and skeptic
  decisions through the same publication transaction; no ninth stage is added.
- `renderer.py` formats schema-v2 reader documents deterministically and never
  creates claims or prose.
- `KnowledgeStore` remains the sole durable file writer and does not acquire
  document-policy logic.

## Tech Stack

Python 3.10+ standard library, `unittest`, existing file-protocol test
fixtures, UTF-8 Markdown, and existing atomic `KnowledgeStore` writes.

## Baseline / Authority Refs

- `docs/aegis/specs/2026-09-23-reader-oriented-knowledge-report-design.md`
- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- `README.md`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- Historical report decision in commit `2231e76`

## Compatibility Boundary

- Read schema-v1 topics, immutable snapshots, audit records, v1 imports, and
  existing report files unchanged.
- Do not rewrite or delete historical reports or topic snapshots.
- Schema-v2 topic writes require a valid reader document; schema-v1 topics are
  upgraded only by an accepted learning publication.
- A checkpoint creates no report.
- A true convergence report remains
  `topics/<topic-id>/reports/v<six-digit-version>.md`.
- `report_path` stays additive and report-write retry behavior stays unchanged.
- `query` remains stateless and does not create reader-document content.

## Verification

Run every focused test module introduced by this plan, then the existing
regression test, bytecode compilation, `git diff --check`, package-local import
checks, a two-domain end-to-end fixture run, and an explicit lingering-reference
scan for audit-style report headings.

## Plan Basis

Facts:

- The current renderer is a deterministic audit export and cannot create
  connected explanatory content from atomic claims.
- `HostRuntimeCoordinator.commit_learning()` already commits one integration
  candidate and one skeptic decision through `KnowledgePublisher`.
- `TopicKnowledge` validates all canonical references and serializes immutable
  snapshots.
- `KnowledgeStore.write_markdown_report()` already provides version containment,
  atomic write, immutable-byte comparison, and retry safety.

Assumptions:

- Complete-document replacement is acceptable because the current document is
  returned in every integration state snapshot.
- The host can keep a complete reader document coherent within the integration
  response size boundary.

Unknowns to resolve during execution:

- Whether existing public package checks outside this slim repository still
  assert the old report headings; discover them before protocol replacement.
- Whether the installed user Skill needs a manual post-verification sync. Do
  not sync until package verification passes and the user explicitly requests
  it.

## Ripple Signal Triage

- Schema ripple: `TopicKnowledge`, snapshots, store reads, publisher audit
  records, runtime state snapshots, renderer, and convergence policy.
- Host-contract ripple: integration and skeptic response shapes, Skill protocol,
  package behavior, and fixture agents.
- Public-output ripple: report narrative and any downstream Markdown consumer.
- Result: expanded verification is required across core, behavior, migration,
  adapter, package, and sandbox surfaces.

## Architecture Integrity Lens

- Invariant: every reader-facing assertion in a report already exists in the
  skeptic-approved canonical topic version.
- Canonical owner / contract: `TopicKnowledge.reader_document`; not
  `renderer.py`, not a report file, and not a post-convergence model call.
- Responsibility overlap: `KnowledgeStore` persists bytes only; renderer
  formats only; the host does not revise content.
- Higher-level simplification: place validation in `reader_document.py` and
  compose it into `TopicKnowledge` / `Learner`, rather than add ad hoc renderer
  guards or host fallbacks.
- Retirement / falsifier: any schema-v2 report that renders raw convergence
  history, or any published document without a successful skeptic decision,
  falsifies the architecture.
- Verdict: proceed.

## Plan Pressure Test

- Owner / contract / retirement: one new narrow schema-validation owner;
  historical audit report rendering retires only for schema-v2 completion.
- Architecture integrity / higher-level path: no duplicate writer, report
  store, or model post-processing path.
- Verification scope: high; contract, persistence, rendering, and host runtime
  all change.
- Task executability: each slice has a focused `unittest` module and a
  deterministic command.
- Pressure result: proceed.

## Plan-Time Complexity Check

- Target files: `knowledge_schema.py` (897 lines), `learner.py` (709 lines),
  `judgments.py`, `autonomous_runtime.py`, `convergence.py`, `renderer.py`,
  both Skill protocols, and new focused tests.
- Existing size signals: schema and learner are already large core owners.
- Owner fit: document-specific validation does not belong in the generic schema
  or learner modules.
- Add-in-place risk: adding all nested document validation to
  `knowledge_schema.py` would increase mixed responsibilities.
- Better boundary: create `scripts/reader_document.py`, imported only by
  schema, learner, convergence, and renderer.
- Recommendation: add owner file, then make narrow integration edits.

## Anti-Entropy Declaration

- Deletion Class: `code-retirement` plus `persistent-state` compatibility
  boundary.
- Old Path/Object: schema-v2 use of audit-style primary report sections in
  `render_knowledge_report`.
- New Canonical Owner: `TopicKnowledge.reader_document` with deterministic
  `renderer.py` presentation.
- Expected Preserved Behavior: immutable report paths, report-write retry,
  schema-v1 readability, audit records, and old report files.
- Expected Retired Behavior: new schema-v2 reports presenting claim registries,
  gap ledgers, and convergence history as their primary narrative.
- External Boundary Touched: yes, installed package and existing report
  consumers may read old artifacts.
- Source-of-Truth Data Risk: confirmed for historical topic snapshots and
  reports.
- User Confirmation Required: yes for deletion or rewrite of historical state;
  no for code-path retirement.

## Retirement Decision

- Path: `compat-exception` for schema-v1 rendering and existing immutable
  report files; `delete-first` for the schema-v2 audit-style primary renderer
  branch.
- Why: historical data is persistent source-of-truth and must not be rewritten;
  the internal report behavior can retire once the new schema-v2 contract is
  proven.
- Non-edits: no data deletion, no snapshot rewrite, no `latest.md`, no
  alternate writer, and no post-processing compatibility fallback.

## File Map

Create:

- `skill/deep-inquiry/scripts/reader_document.py`
- `tests/test_reader_document_schema.py`
- `tests/test_reader_document_runtime.py`
- `tests/test_reader_report_renderer.py`
- `tests/test_reader_report_protocol.py`
- `tests/test_reader_report_e2e.py`

Modify:

- `skill/deep-inquiry/scripts/knowledge_schema.py`
- `skill/deep-inquiry/scripts/learner.py`
- `skill/deep-inquiry/scripts/judgments.py`
- `skill/deep-inquiry/scripts/autonomous_runtime.py`
- `skill/deep-inquiry/scripts/convergence.py`
- `skill/deep-inquiry/scripts/renderer.py`
- `skill/deep-inquiry/SKILL.md`
- `skill/deep-inquiry/SKILL.zh-CN.md`
- `README.md`
- `docs/aegis/INDEX.md`
- `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`

Do not modify:

- `knowledge_store.py` unless a focused immutability regression proves a
  serialization-only change is necessary.
- Legacy v1 importer and session schema modules.
- Existing persistent knowledge roots or reports.

## Task 1: Add the Canonical Reader-Document Contract

**Files**

- Create `skill/deep-inquiry/scripts/reader_document.py`
- Modify `skill/deep-inquiry/scripts/knowledge_schema.py`
- Create `tests/test_reader_document_schema.py`

**Why**

Give canonical knowledge a reviewed representation capable of supporting a
reader document without creating a second source of truth.

**Repair Track**

- Root cause: `TopicKnowledge` stores only atomic claims, so a deterministic
  renderer cannot supply connected explanatory prose.
- Canonical owner: `TopicKnowledge.reader_document`.
- Minimal stable repair: structured, reference-bearing reader blocks validated
  against the same topic graph.
- Compatibility: schema-v1 input stays loadable with `reader_document=None`.

**Verification**

```bash
python3 tests/test_reader_document_schema.py
```

Expected final output: all schema and compatibility cases pass.

1. [ ] Write `tests/test_reader_document_schema.py` with a schema-v1 fixture
   based on `tests/test_low_gain_major_delta.py::_topic`, and a schema-v2
   fixture containing:

   ```python
   "reader_document": {
       "schema_version": 1,
       "overview": {
           "paragraphs": ["The proposition depends on linked controls."],
           "claim_ids": ["claim-1"],
           "evidence_ids": [],
       },
       "sections": [
           {
               "id": "scope-and-risk",
               "heading": "Scope and risk",
               "paragraphs": ["Scope choices determine the risk envelope."],
               "key_points": ["Treat the two dimensions as one decision."],
               "dimension_refs": ["scope", "risk"],
               "claim_ids": ["claim-1"],
               "evidence_ids": [],
           }
       ],
       "synthesis": {
           "paragraphs": ["The dimensions must be evaluated together."],
           "claim_ids": ["claim-1"],
           "evidence_ids": [],
       },
       "application_guidance": [
           {
               "text": "Check the operating scope before accepting risk.",
               "claim_ids": ["claim-1"],
               "evidence_ids": [],
           }
       ],
       "boundary_notes": [
           {
               "text": "Evidence is still limited for unusual conditions.",
               "claim_ids": ["claim-1"],
               "gap_ids": [],
           }
       ],
   }
   ```

   Assert schema-v1 round-trips with `reader_document is None`, schema-v2
   round-trips byte-for-byte through `TopicKnowledge.to_dict()`, every coverage
   dimension is represented, and duplicate section IDs, unknown claims, retired
   claims, mismatched evidence, uncovered dimensions, and unknown gaps raise
   `KnowledgeSchemaError`.
2. [ ] Run the test before implementation:

   ```bash
   python3 tests/test_reader_document_schema.py
   ```

   Expected: `ModuleNotFoundError` for `scripts.reader_document` or assertions
   fail because `TopicKnowledge` has no `reader_document`.
3. [ ] Implement `reader_document.py` with:

   ```python
   def reader_document_from_dict(
       data: object,
       *,
       topic: TopicKnowledge,
       require_complete: bool,
   ) -> dict[str, object] | None: ...

   def reader_document_to_dict(
       document: dict[str, object] | None,
   ) -> dict[str, object] | None: ...

   def reader_document_ready(topic: TopicKnowledge) -> bool: ...
   ```

   Validate JSON shape, text fields, unique section IDs, active/disputed claim
   references, evidence-to-claim linkage, coverage dimension disposition,
   reference-bearing overview/synthesis/application blocks, and boundary
   references. `require_complete=False` accepts `None` for schema-v1 reads;
   `require_complete=True` rejects it.

   Modify `TopicKnowledge` to add `reader_document: dict[str, Any] | None`,
   serialize it when present, deserialize it, and validate it through the new
   module after validating claims, evidence, gaps, and counterexamples. Keep
   schema version 1 readable; require version 2 for a non-null document.
4. [ ] Re-run:

   ```bash
   python3 tests/test_reader_document_schema.py
   python3 tests/test_low_gain_major_delta.py
   ```

   Expected: both test modules pass.
5. [ ] Do not commit. Record the focused test result in the active work
   checkpoint if execution spans sessions.

## Task 2: Publish the Document Only With an Approved Learning Delta

**Files**

- Modify `skill/deep-inquiry/scripts/learner.py`
- Modify `skill/deep-inquiry/scripts/judgments.py`
- Modify `skill/deep-inquiry/scripts/autonomous_runtime.py`
- Create `tests/test_reader_document_runtime.py`

**Why**

Make reader prose a full integration candidate that passes the same skeptic
review and lifecycle transaction as factual knowledge.

**Repair Track**

- Root cause: current integration and skeptic contracts have no field that
  carries or reviews reader-oriented prose.
- Canonical owner: `Learner.build_knowledge_candidate()` builds the next
  canonical projection; `HostRuntimeCoordinator.commit_learning()` enforces the
  approved transition.
- Compatibility: the vNext graph retains eight stages and legacy v1 judgments
  remain untouched.

**Verification**

```bash
python3 tests/test_reader_document_runtime.py
```

Expected final output: accepted documents publish atomically; invalid or
unapproved documents do not advance the canonical version.

1. [ ] Write `tests/test_reader_document_runtime.py` with a scripted
   `HostRuntimeCoordinator` flow. Assert:
   - `build_autonomous_request("integrate_learning", ...)` requires
     `reader_document` and includes the current document in the topic snapshot;
   - `build_autonomous_request("skeptic_review", ..., context)` exposes the
     complete integration proposal;
   - an invalid reader document produces a rejected lifecycle outcome with
     unchanged topic version;
   - `reader_document_approved=False` produces a rejected outcome with
     unchanged topic version;
   - an approved valid response publishes claims and reader document together,
     advancing exactly one version;
   - retiring a claim without replacing the reader document produces an
     invalid/unready schema-v2 candidate rather than a convergable report
     source.
2. [ ] Run:

   ```bash
   python3 tests/test_reader_document_runtime.py
   ```

   Expected: fail because autonomous request templates and runtime review
   decisions lack reader-document fields.
3. [ ] Modify `judgments.py`:
   - add `reader_document` to `INTEGRATE_LEARNING` required fields and provide
     the complete nested response template;
   - expand the English instruction with mechanisms, conditions, application,
     uncertainty, cross-dimension synthesis, and the prohibition on workflow
     narration;
   - add `reader_document_approved` and `reader_document_defects` to
     `SKEPTIC_REVIEW`, validate boolean/list types, and require the defect list
     to be empty on approval.

   Modify `learner.py` so `build_knowledge_candidate()` receives the complete
   document, constructs the updated factual graph first, validates the document
   against that graph with `require_complete=True`, sets
   `schema_version=2`, and rejects a candidate whose retired/revised references
   leave stale reader prose.

   Modify `autonomous_runtime.py` so the skeptic response is retained in the
   pending payload; `commit_learning()` requires both no structural hit and
   `reader_document_approved`, passes the actual skeptic reason/defects to the
   publication review record, and returns to `integrate_learning` on rejection.
4. [ ] Re-run:

   ```bash
   python3 tests/test_reader_document_runtime.py
   python3 tests/test_reader_document_schema.py
   python3 tests/test_low_gain_major_delta.py
   ```

   Expected: all modules pass, and accepted publication increments the topic
   once while rejection leaves it unchanged.
5. [ ] Do not commit. Confirm with `git diff --check`.

## Task 3: Gate Convergence on Reader Readiness

**Files**

- Modify `skill/deep-inquiry/scripts/convergence.py`
- Create or extend `tests/test_reader_document_runtime.py`

**Why**

Prevent a schema-v1 topic or incomplete schema-v2 document from reaching the
completion path and emitting a reader report.

**Repair Track**

- Root cause: convergence currently checks facets, gaps, evidence, and marginal
  gain but has no reader-document readiness invariant.
- Canonical owner: deterministic `evaluate_convergence()`.
- Compatibility: checkpoints remain possible; convergence instead returns a
  blocking reason and resumes learning.

**Verification**

```bash
python3 tests/test_reader_document_runtime.py
```

Expected final output: unready documents block convergence with a stable reason
code, while an otherwise equivalent valid document reaches normal policy
evaluation.

1. [ ] Add test cases that build a topic satisfying existing facet and evidence
   requirements but with:
   - schema version 1 and no reader document;
   - schema version 2 with an invalid/unready document;
   - schema version 2 with a complete valid document.

   Assert the first two return `reader_document_not_ready` before normal
   convergence success, and the valid case preserves the existing convergence
   result.
2. [ ] Run:

   ```bash
   python3 tests/test_reader_document_runtime.py
   ```

   Expected: fail because no reader-document readiness check exists.
3. [ ] Import `reader_document_ready` into `convergence.py` and add:

   ```python
   if not reader_document_ready(topic):
       return _blocked(
           "reader_document_not_ready",
           "A complete skeptic-reviewed reader document is required.",
       )
   ```

   Place this after deterministic topic validation and before a result can
   return `converged=True`. Do not change safety checkpoint behavior.
4. [ ] Re-run:

   ```bash
   python3 tests/test_reader_document_runtime.py
   python3 tests/test_low_gain_major_delta.py
   ```

   Expected: both pass.
5. [ ] Do not commit. Record the reason-code compatibility decision in the
   implementation evidence.

## Task 4: Replace the Schema-v2 Report Projection

**Files**

- Modify `skill/deep-inquiry/scripts/renderer.py`
- Create `tests/test_reader_report_renderer.py`

**Why**

Deliver the reader document without reintroducing model calls, audit narration,
or another knowledge owner.

**Retirement Track**

- Old owner/path: the schema-v2 branch of
  `render_knowledge_report()` that emits claims, evidence, gaps, and
  convergence history as the main report.
- New owner: `TopicKnowledge.reader_document` content, formatted by
  `renderer.py`.
- Keep reason: a schema-v1 fallback remains only to read compatible historical
  topics and must be clearly isolated.
- Retirement trigger: delete the schema-v2 audit projection once the new
  renderer fixture and end-to-end tests pass.

**Verification**

```bash
python3 tests/test_reader_report_renderer.py
```

Expected final output: repeated schema-v2 rendering returns identical bytes with
reader headings and source notes, without audit headings or internal IDs.

1. [ ] Write `tests/test_reader_report_renderer.py` using a schema-v2 fixture
   with two dimensions, active claims, evidence, an open gap, counterexample,
   and a valid reader document. Assert:
   - byte-identical output from two render calls;
   - headings `Overview`, section headings, `Synthesis`, `Applying the
     Knowledge`, `Boundaries and Uncertainty`, and `Sources`;
   - prose and source text appear in expected order;
   - no `Convergence History`, `Knowledge by Dimension`, `Topic ID`, `Kind:`,
     `Confidence:`, `Status:`, raw claim ID heading, or raw evidence ID heading;
   - Markdown-sensitive content remains escaped;
   - a schema-v1 fixture renders through a clearly named compatibility path
     without claiming it is a reader report.
2. [ ] Run:

   ```bash
   python3 tests/test_reader_report_renderer.py
   ```

   Expected: fail because the current renderer produces audit sections.
3. [ ] Refactor `renderer.py`:
   - retain `_inline()` and add small pure helpers for paragraphs, numbered
     source-note allocation, and reference collection;
   - branch explicitly on `topic.schema_version`;
   - for schema version 2, validate `reader_document_ready(topic)`, render the
     stored block order, derive compact numbered source notes only from
     referenced evidence, and emit no claim/gap/history registry;
   - isolate the old output as `_render_schema_v1_audit_compatibility()` so it
     cannot become the schema-v2 default;
   - make missing schema-v2 readiness a `ValueError` rather than a silent audit
     fallback.
4. [ ] Re-run:

   ```bash
   python3 tests/test_reader_report_renderer.py
   python3 tests/test_reader_document_schema.py
   python3 tests/test_low_gain_major_delta.py
   ```

   Expected: all tests pass.
5. [ ] Run:

   ```bash
   grep -nE "Convergence History|Knowledge by Dimension|Topic ID" \
     skill/deep-inquiry/scripts/renderer.py
   ```

   Expected: any remaining matches are confined to
   `_render_schema_v1_audit_compatibility`; add that assertion to the renderer
   test rather than relying on the grep result alone.

## Task 5: Preserve Host Completion and Immutable Report Semantics

**Files**

- Modify `skill/deep-inquiry/scripts/vnext_host.py` only if focused tests show
  the existing call site needs an explicit schema-v2 readiness error mapping.
- Create `tests/test_reader_report_e2e.py`

**Why**

Prove the public file-host contract produces an immutable reader report only
after an approved, converged schema-v2 topic.

**Verification**

```bash
python3 tests/test_reader_report_e2e.py
```

Expected final output: true convergence returns an immutable `report_path`;
checkpoint, unready state, and failed report writes do not mark the run
complete.

1. [ ] Write `tests/test_reader_report_e2e.py` using temporary roots and
   scripted `VNextHost` / `HostRuntimeCoordinator` responses. Cover:
   - complete schema-v2 convergence returns `status: "done"` and an absolute
     report path;
   - the file contains reader headings and excludes audit headings;
   - repeated completion uses identical bytes;
   - a checkpoint returns no `report_path`;
   - a schema-v1 or unready schema-v2 convergence decision cannot produce a
     report;
   - monkeypatching `write_markdown_report()` to raise `KnowledgeStoreError`
     preserves the pending completion cursor and active run status.
2. [ ] Run:

   ```bash
   python3 tests/test_reader_report_e2e.py
   ```

   Expected: fail until reader readiness and new renderer behavior are wired
   through completion.
3. [ ] Apply the minimum host change only if the focused failure proves it:
   preserve the existing order `render -> write immutable report -> mark run
   complete`; surface readiness failures as `VNextHostError`; keep the pending
   cursor intact on all report-write failures. Do not move rendering into
   `KnowledgePublisher` or `KnowledgeStore`.
4. [ ] Re-run:

   ```bash
   python3 tests/test_reader_report_e2e.py
   python3 tests/test_reader_report_renderer.py
   python3 tests/test_reader_document_runtime.py
   ```

   Expected: all pass.
5. [ ] Do not commit. Verify no write path other than `KnowledgeStore` was
   introduced:

   ```bash
   grep -RIn "open(.*reports\|write_text\|write_bytes" \
     skill/deep-inquiry/scripts
   ```

   Expected: report durable write remains confined to `KnowledgeStore`.

## Task 6: Restore Protocol Depth and English/Chinese Parity

**Files**

- Modify `skill/deep-inquiry/SKILL.md`
- Modify `skill/deep-inquiry/SKILL.zh-CN.md`
- Modify `README.md`
- Create `tests/test_reader_report_protocol.py`

**Why**

Prevent canonical-English protocol compression from degrading agent behavior
and document the reader-report contract for public users.

**Verification**

```bash
python3 tests/test_reader_report_protocol.py
```

Expected final output: both protocols contain stable markers for the same
eight-stage, reviewer, reader-depth, deterministic-rendering, and exclusion
contract.

1. [ ] Write `tests/test_reader_report_protocol.py` that reads both protocol
   files and asserts each contains stable field/stage markers:

   ```python
   required_markers = (
       "integrate_learning",
       "skeptic_review",
       "reader_document",
       "mechanism",
       "conditions",
       "cross-dimension",
       "application",
       "boundaries",
       "deterministic",
       "eight",
   )
   ```

   Use language-specific expected phrases for prose obligations, but keep
   JSON-field and stage names byte-identical. Assert the old promise that a
   report is merely a full claim/evidence/gap/history projection is absent.
2. [ ] Run:

   ```bash
   python3 tests/test_reader_report_protocol.py
   ```

   Expected: fail because current protocol files lack reader-document markers
   and preserve the old audit-projection claim.
3. [ ] Update both Skill files so that:
   - `SKILL.md` is the complete English canonical contract;
   - `SKILL.zh-CN.md` is a full semantic mirror;
   - integration and skeptic instructions specify the reader document,
     explanatory depth, cross-dimension synthesis, application, and boundaries;
   - external-output sections state that schema-v2 reports exclude internal
     history and renderer calls no model;
   - all protocol fields, enum names, stage count, and errors remain
     language-independent.

   Update `README.md` to describe the reader-oriented report and the retained
   audit availability without presenting audit records as the report itself.
4. [ ] Re-run:

   ```bash
   python3 tests/test_reader_report_protocol.py
   python3 -m compileall -q skill/deep-inquiry/scripts
   ```

   Expected: both pass.
5. [ ] Do not commit. Inspect both diffs together to ensure no English-only or
   Chinese-only behavioral condition remains.

## Task 7: Full Regression, Two-Domain Acceptance, and Documentation Closeout

**Files**

- Modify `docs/aegis/INDEX.md`
- Modify `docs/aegis/baseline/2026-09-23-public-skill-baseline.md`
- Create `docs/aegis/adr/0005-reader-oriented-report.md` only after
  implementation evidence passes.

**Why**

Verify behavior across all touched layers, prove retirement behavior, and
record the accepted architecture without inventing an unverified ADR.

**Verification**

```bash
python3 tests/test_low_gain_major_delta.py
python3 tests/test_reader_document_schema.py
python3 tests/test_reader_document_runtime.py
python3 tests/test_reader_report_renderer.py
python3 tests/test_reader_report_e2e.py
python3 tests/test_reader_report_protocol.py
python3 -m compileall -q skill/deep-inquiry/scripts
git diff --check
```

Expected final output: every command exits 0.

1. [ ] Run all commands in the verification block. Fix only the confirmed
   owner responsible for each failure; do not add a renderer fallback, a second
   writer, or unreviewed post-processing to make a fixture pass.
2. [ ] Add two end-to-end fixtures to `tests/test_reader_report_e2e.py`:
   - a construction or lodging proposition with stages, constraints, and
     regulatory boundaries;
   - a small climbing-camera-robot proposition with mechanics, power,
     communication, and field limitations.

   Assert structural report requirements for both, then perform the five
   reader-review questions from the approved Design Spec and record `PASS` or
   `FAIL` in a short test fixture comment or execution evidence. Do not copy
   prior reports as generated text.
3. [ ] Perform retirement verification:

   ```bash
   grep -RInE "Convergence History|Knowledge by Dimension|Topic ID" \
     skill/deep-inquiry/scripts tests
   ```

   Expected: schema-v2 renderer tests assert absence; any source match is
   limited to schema-v1 compatibility code or negative-test expectations.

   Then run a schema-v1 fixture and a schema-v2 fixture to prove old persistent
   data remains readable while new output uses the reader contract.
4. [ ] After all verification passes, create ADR 0005 documenting:
   - supersession of ADR 0004's report shape only;
   - continued immutable storage and retry guarantees;
   - reader document canonical ownership;
   - schema-v1 compatibility exception and no historical rewrite;
   - retirement evidence for the schema-v2 audit projection.

   Update `docs/aegis/INDEX.md` and baseline status from proposed to verified.
5. [ ] Do not commit or push unless the user explicitly requests it. Report the
   exact fresh verification outputs and the user-level installation-sync status.

## Risks and Rollback

- Reader payload size or host quality regresses:
  reject candidate through skeptic review; no partial topic write occurs.
- New validation is too strict:
  adjust `reader_document.py` rules with an explicit fixture and spec update;
  do not relax the single-source or reviewer invariants.
- Renderer regression:
  schema-v1 compatibility branch continues to read historical topics; current
  schema-v2 report writes fail closed rather than emitting audit fallback.
- Installed Skill mismatch:
  keep the user-level copy unchanged until package verification passes and a
  deliberate sync is requested.

## Completion Evidence

The implementation is not complete until:

1. all seven test commands in Task 7 pass freshly;
2. both domain fixtures pass the five reader-quality questions;
3. schema-v1 compatibility and schema-v2 retirement scans pass;
4. immutable report retry behavior is observed;
5. `git diff --check` passes;
6. ADR 0005 and baseline/index updates record actual, not planned, evidence.
