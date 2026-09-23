# Converged Markdown Report Implementation Plan

## Goal

Implement the approved deterministic Markdown report generated at genuine
vNext learning convergence.

## Architecture

- The existing pure `renderer.py` owner gains the completion-report projection.
- `KnowledgeStore` remains the sole durable writer and owns immutable,
  versioned report persistence.
- `VNextHost` invokes report persistence before marking a converged run
  complete and returns `report_path`.
- Publication and convergence owners remain unchanged.

## Tech Stack

Python 3.10+ standard library, UTF-8 Markdown, existing atomic file helper,
layered executable checks.

## Baseline / Authority Refs

- `docs/aegis/specs/2026-09-23-converged-markdown-report-brief.md`
- `docs/aegis/adr/0003-publication-audit-journal.md`
- `docs/aegis/specs/2026-09-22-publication-lifecycle-and-test-layering-design.md`

## Compatibility Boundary

- Existing public commands and result fields remain valid.
- `report_path` is additive and appears only for converged learning results.
- Checkpoint-required termination creates no report.
- Existing topic, history, and audit files are not rewritten.
- No alternate writer, report alias, model call, or export command is added.

## Verification

Run focused RED/GREEN checks, all four layer runners, and the external sandbox
acceptance command already used by package verification.

## Plan Basis

Facts:

- `VNextHost._advance_internal()` owns the final host status transition.
- `ConvergenceDecision` distinguishes convergence from checkpoint termination.
- `KnowledgeStore` already owns path validation and atomic writes.
- `loop.py` is large and is not the active vNext completion owner.

Assumption:

- A structured deterministic projection is the correct meaning of automatic
  report generation; no additional model-authored narrative is required.

Stop condition:

- If report creation requires changing publication atomicity or adding a second
  durable writer, stop and return to architecture review.

## Architecture Integrity Lens

- Invariant: only published canonical knowledge is rendered, by one durable
  writer, after true convergence.
- Canonical owner / contract: renderer owns projection, store owns bytes,
  host owns completion orchestration.
- Responsibility overlap: none; publisher does not own derived reports.
- Higher-level simplification: use the existing completion and store boundaries
  rather than extending `loop.py` or adding an export subsystem.
- Retirement / falsifier: any model call, `latest.md` alias, caller-side write,
  or checkpoint report falsifies the design.
- Verdict: proceed.

## Plan-Time Complexity Check

- Target files: existing `renderer.py`, `knowledge_store.py`, `vnext_host.py`, focused
  core/adapter checks, manifest, and `SKILL.md`.
- Existing pressure: `knowledge_store.py` and `vnext_host.py` are established
  owners; `loop.py` is overloaded and excluded.
- Owner fit: extend the existing pure renderer; add small store and host methods.
- Recommendation: edit the three existing owners in place.

## Task 1: Pin Renderer and Store Contracts

**Files**

- Create:
  `skill/autonomous-mentor/examples/tests/core_contract/markdown_report_checks.py`
- Modify: `skill/autonomous-mentor/scripts/renderer.py`
- Modify: `skill/autonomous-mentor/scripts/knowledge_store.py`
- Modify: `skill/autonomous-mentor/examples/tests/layer_manifest.json`

**Why**

Define deterministic content and preserve the one-writer invariant.

**Steps**

1. Write checks that call the wished-for renderer and store API, asserting
   report sections, UTF-8 determinism, immutable path, idempotency, and
   mismatch rejection.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/core_contract/markdown_report_checks.py
   ```

   Expected: fail because the renderer/API is missing.
3. Add `render_knowledge_markdown(topic) -> bytes` and
   `KnowledgeStore.write_markdown_report(topic, payload) -> Path`.
4. Re-run the focused check and the core-contract layer. Expected: pass.
5. Do not commit unless explicitly requested.

## Task 2: Integrate True-Convergence Completion

**Files**

- Create:
  `skill/autonomous-mentor/examples/tests/adapter/markdown_report_host_checks.py`
- Modify: `skill/autonomous-mentor/scripts/vnext_host.py`
- Modify: `skill/autonomous-mentor/examples/tests/layer_manifest.json`

**Why**

Make automatic generation observable through the public completion result and
retain retry safety on write failure.

**Steps**

1. Write host checks for converged report creation, checkpoint non-creation,
   and write-failure retry state.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/tests/adapter/markdown_report_host_checks.py
   ```

   Expected: fail because completion does not generate or return a report.
3. Render and persist before changing host status to complete. Add
   `report_path` only for `decision.converged`.
4. Re-run the focused check and adapter layer. Expected: pass.
5. Do not commit unless explicitly requested.

## Task 3: Document and Verify

**Files**

- Modify: `skill/autonomous-mentor/SKILL.md`
- Modify: `docs/aegis/INDEX.md`

**Why**

Make the automatic completion artifact part of the reusable Skill protocol.

**Steps**

1. Add the report path, trigger, and failure semantics to `SKILL.md`.
2. Run all four layer commands and package/sandbox acceptance.
3. Inspect `git diff --check`, changed-file diff, and architecture invariants.
4. Record exact verification evidence in the completion response.
5. Do not commit unless explicitly requested.

## Risks and Retirement

- Risk: report bytes diverge from canonical topic data. Mitigation: pure
  rendering from the loaded version and immutable mismatch rejection.
- Risk: checkpoint is mistaken for convergence. Mitigation: direct assertion on
  `decision.converged`.
- Risk: report failure leaves a false completed run. Mitigation: persist before
  setting run status and keep the pending cursor until success.
- Retirement: no old path exists. A future format change must use a new explicit
  report schema/version decision rather than overwrite existing reports.
