# Evidence Bundle Draft

## Task 1: Canonical Reader-Document Contract

- `python3 tests/test_reader_document_schema.py`: 4 tests passed.
- `python3 tests/test_low_gain_major_delta.py`: 3 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts`: exit 0.
- `git diff --check`: exit 0.
- Independent spec-compliance review: approved, no findings.
- Independent code-quality review: approved, no findings.

Drift check: Task 1 stayed inside the approved schema boundary. No new writer,
runtime stage, renderer policy, model call, fallback, historical-data mutation,
or retirement action was introduced.

## Task 2: Approved Reader-Document Publication

- `python3 -m unittest discover -s tests -v`: 24 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts tests`: exit 0.
- `git diff --check`: exit 0.
- Independent spec-compliance review: approved after repair loops for direct
  retirement, review audit persistence, convergence readiness, active-claim
  disposition, and boundary-gap relevance.
- Independent code-quality review: approved after repair loops for schema-v1
  convergence, legacy direct-write bypass, review-shape validation, and strict
  schema-version typing.

Drift check: Task 2 preserved the eight-stage graph, `KnowledgePublisher`
lifecycle ownership, and `KnowledgeStore` as the sole durable writer. A reader
document can publish only through the approved lifecycle transition. Schema-v1
and legacy audit records remain readable but cannot produce a new convergence
report; direct retirement intentionally produces a non-convergent schema-v2
topic with no reader document. No renderer, host-completion, protocol, v1
importer, historical-data, or installation-copy change was made.

## Task 3: Reader-Readiness Convergence Gate

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 26 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts tests`: exit 0.
- `git diff --check`: exit 0.
- Independent spec-compliance review: approved after adding a genuinely
  convergence-eligible fixture and preserving the maximum-cycle checkpoint
  before the readiness gate.
- Independent code-quality review: approved with no findings.

Drift check: Task 3 added no stage, writer, fallback, or renderer behavior. It
keeps schema-v1 readable but non-convergent, blocks unready schema-v2 topics
with `reader_document_not_ready`, and retains the existing `MAX_AUTONOMOUS_CYCLES`
safety checkpoint as the higher-priority outcome.

## Task 4: Schema-v2 Reader Report Rendering

- `python3 tests/test_reader_report_renderer.py`: 4 tests passed.
- `python3 tests/test_reader_document_schema.py`: 9 tests passed.
- `python3 tests/test_low_gain_major_delta.py`: 5 tests passed.
- `python3 -m unittest discover -s tests -v`: 30 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts tests`: exit 0.
- `git diff --check`: exit 0.
- Independent spec-compliance review: approved, no findings.

Drift check: Task 4 preserves deterministic rendering, `KnowledgeStore` as the
only report writer, and schema-v1 readability. Schema-v2 emits only the stored
reader-document presentation in block order with first-reference source notes;
it contains no audit registry, lifecycle history, internal IDs, model call, or
new knowledge source. The old audit report shape is contained solely in the
explicit schema-v1 compatibility function.

## Task 5: Host Completion and Immutable Report Semantics

- `python3 tests/test_reader_report_e2e.py`: 4 tests passed.
- `python3 tests/test_reader_report_renderer.py`: 4 tests passed.
- `python3 tests/test_reader_document_runtime.py`: 12 tests passed.
- `python3 -m unittest discover -s tests -v`: 34 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts tests`: exit 0.
- `git diff --check`: exit 0.
- Report-write ownership scan: no alternate report write path found under
  `skill/deep-inquiry/scripts`.

Drift check: Task 5 retains `KnowledgeStore.write_markdown_report()` as the
only durable report writer and preserves the existing order of rendering,
immutable persistence, then run completion. `VNextHost` now rejects
schema-v1 or unready schema-v2 completion cursors before report generation and
maps renderer readiness errors to its public error boundary; a failed write
retains the active run and exact pending cursor for retry.

## Task 6: Protocol Depth and Bilingual Parity

- `python3 tests/test_reader_report_protocol.py`: 2 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts tests`: exit 0.
- `git diff --check`: exit 0.
- English/Chinese parity inspection: both protocol files require
  `integrate_learning` to supply `reader_document`, require
  `skeptic_review` approval, prescribe mechanism/conditions/cross-dimension
  synthesis/application/boundaries, and prohibit schema-v2 audit registries.

Drift check: Task 6 changes no runtime code or persistent state. `SKILL.md`
remains the English canonical contract and `SKILL.zh-CN.md` remains the
complete semantic mirror; the public README now distinguishes a reader-facing
knowledge document from durable audit records.

## Task 7: Final Acceptance and Documentation Closeout

- `python3 tests/test_low_gain_major_delta.py`: 5 tests passed.
- `python3 tests/test_reader_document_schema.py`: 9 tests passed.
- `python3 tests/test_reader_document_runtime.py`: 12 tests passed.
- `python3 tests/test_reader_report_renderer.py`: 4 tests passed.
- `python3 tests/test_reader_report_e2e.py`: 5 tests passed.
- `python3 tests/test_reader_report_protocol.py`: 2 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts`: exit 0.
- `git diff --check`: exit 0.
- `python3 -m unittest discover -s tests -v`: 37 tests passed.
- Audit-heading scan: matches are confined to
  `_render_schema_v1_audit_compatibility()` or explicit positive/negative test
  expectations.
- Reader review: lodging construction and climbing-camera-robot fixtures pass
  all five questions: mechanism, applicability and failure conditions,
  concrete action, cross-dimension connection, and no internal process
  narrative.
- Documentation: ADR 0005 accepted; Aegis index and public baseline updated
  with verified reader-report ownership and compatibility evidence.

Final drift check: schema-v2 report content has one canonical owner,
`TopicKnowledge.reader_document`; rendering stays deterministic and
model-free; `KnowledgeStore` remains the sole durable report writer; immutable
versioned report paths and retry semantics remain intact. No installed copy was
synchronized, no main-workspace change was made, and no commit or push
occurred.

## Independent Review Repair: Retire Direct Learner Publication

- Independent task-completeness review found that
  `Learner.apply_knowledge_delta()` still wrote new schema-v1 topic versions
  through `KnowledgeStore.save()`, bypassing `KnowledgePublisher`.
- The method now fails closed for every invocation with a
  `KnowledgePublisher` migration error and no longer imports or calls
  `KnowledgeStore` at runtime.
- `test_apply_knowledge_delta_rejects_legacy_v1_publication` verifies the
  historical schema-v1-shaped request leaves the stored version unchanged.
- `python3 tests/test_low_gain_major_delta.py`: 5 tests passed.
- `python3 -m unittest discover -s tests -v`: 37 tests passed.
- `python3 -m compileall -q skill/deep-inquiry/scripts tests`: exit 0.
- `git diff --check`: exit 0.

Repair boundary: `KnowledgePublisher` is now the sole learning-publication
lifecycle owner. The remaining `migrate_v1.py` `KnowledgeStore.save()` call is
an explicit legacy-import migration path, not a learning-delta publication
path.

## Baseline

- `python3 tests/test_low_gain_major_delta.py`: passed before execution.
- `python3 -m compileall -q skill/deep-inquiry/scripts`: passed before execution.
