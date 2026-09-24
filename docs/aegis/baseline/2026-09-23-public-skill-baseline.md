# Deep Inquiry Public Skill Baseline

Date: `2026-09-23`
Status: `verified reader-report baseline`

## 1. Purpose

Record the product and architecture truths that constrain correction of the
converged Markdown report.

## 2. Workspace Structure

- `skill/deep-inquiry/`: distributable Skill package
- `skill/deep-inquiry/scripts/`: deterministic Python kernel
- `tests/`: repository-level regression checks
- `docs/aegis/`: design and implementation evidence

## 3. Current Authority Surfaces

- `README.md`: public behavior and installation surface
- `skill/deep-inquiry/SKILL.md`: canonical English host protocol
- `skill/deep-inquiry/SKILL.zh-CN.md`: Chinese protocol mirror
- Runtime schema, lifecycle, store, host, and renderer modules
- Historical report design records in commit `2231e76`

## 4. Product / Requirement Baseline

### 4.1 Current Truth

Deep Inquiry turns a central proposition into reusable, skeptic-reviewed
knowledge. On genuine convergence it returns a Markdown knowledge document.

The document is for a reader who wants to understand and apply the learned
knowledge. An audit dump of claims, gates, plans, or cycle history does not
satisfy that purpose.

### 4.2 Non-negotiables

1. Reader-facing content must be grounded in durable reviewed knowledge.
2. Knowledge depth must include explanation, conditions, boundaries, and
   practical synthesis rather than isolated claim summaries.
3. Internal workflow history must remain available for audit without dominating
   the reader document.
4. English and Chinese protocols must express the same behavioral contract.

### 4.3 Product Non-goals

- Personalized teaching or learner profiling
- Automatic publication of unsupported prose
- A complete chronological audit in the reader report

## 5. Architecture / Runtime Boundary Baseline

### 5.1 Current Truth

- `KnowledgePublisher` owns publication lifecycle decisions.
- `KnowledgeStore` is the sole durable writer.
- `TopicKnowledge` is the canonical published knowledge source.
- `renderer.py` owns deterministic presentation.
- The eight-stage vNext graph and convergence owner remain stable.

### 5.2 Architecture Non-negotiables

1. No model call occurs during deterministic rendering.
2. Reader prose must pass the existing skeptic review before publication.
3. A second knowledge owner or mutable report alias is forbidden.
4. Existing topics remain readable after schema evolution.
5. A report write failure must not falsely complete a run.

### 5.3 Architecture Non-goals

- A ninth autonomous-learning stage
- A separate report database
- Reconstructing historical reader prose for old topic versions

## 6. Ownership / Contract Snapshot

- Epistemic judgment: host agent through judgment requests
- Candidate validation and integration: `Learner`
- Lifecycle decision: `KnowledgePublisher`
- Durable I/O: `KnowledgeStore`
- Reader report formatting: `renderer.py`
- Completion orchestration: `VNextHost`

## 7. Verified State and Risks

Schema-v2 `TopicKnowledge` now carries a skeptic-reviewed `reader_document`.
The deterministic renderer formats that canonical document as reader-facing
Markdown and emits no audit registry, internal IDs, or convergence history.
Schema-v1 audit rendering remains a strictly isolated compatibility exception;
historical reports and snapshots are not rewritten.

The English canonical protocol and Chinese mirror both prescribe mechanism
chains, conditions, cross-dimension synthesis, application, and boundaries.
The remaining risk is host-quality variance in authored prose, mitigated by
reference validation, skeptic approval, and two-domain reader acceptance.

## 8. Alignment Use

Read both baseline sections before changing the topic schema, integration
contract, skeptic review, renderer, or completion behavior. Changes to reader
quality and changes to persistence ownership are `scope: both`.

## 9. Compatibility Boundary

Existing topic JSON, immutable history, audit records, query behavior, report
paths, checkpoint behavior, and v1 import remain readable and stable unless an
approved migration requirement explicitly says otherwise.

## 10. Verification Snapshot

- Focused schema, runtime, renderer, host, protocol, and full regression tests
  passed on 2026-09-23.
- Lodging-construction and climbing-camera-robot fixtures passed all five
  reader-review criteria.
- Report writes remain immutable and retry-safe; failed writes retain the
  active host run and completion cursor.
- See ADR 0005 for the accepted report-shape decision and retirement evidence.
