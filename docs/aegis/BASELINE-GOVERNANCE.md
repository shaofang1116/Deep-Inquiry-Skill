# Baseline Governance

## 1. Baseline Roles

- Product / Requirement Baseline: accepted problem, reader outcome, success
  evidence, non-goals, and workflow constraints.
- Architecture / Runtime Boundary Baseline: canonical owners, contracts,
  source-of-truth boundaries, dependency direction, compatibility, and
  retirement state.

## 2. Design Defect

A confirmed error, gap, contradiction, or wrong abstraction in a requirement,
design, or baseline.

- Correct the defective requirement or design first.
- Then align implementation to the corrected baseline.
- Do not patch implementation around a defective baseline.

## 3. Implementation Drift

Implementation, planning, review, or documentation has deviated from a
confirmed, correct, unchanged baseline.

- Return to the baseline through the simplest stable path.
- Do not update the baseline merely to legitimize drift.

## 4. Compatibility Aliases

- Architecture Defect means an architecture-scoped Design Defect.
- Architecture Drift means an architecture-scoped Implementation Drift.
- New findings state `scope: requirements | architecture | both`.

## 5. Baseline Check Protocol

Before a non-trivial change:

1. Read the current product or requirement baseline.
2. Read the current architecture or runtime boundary baseline.
3. Compare the proposed work with both.
4. Check for new ownership, fallback, migration, and entropy risks.
5. Report `aligned`, `Design Defect`, `Implementation Drift`,
   `missing-authority`, or `needs-clarification`.

## 6. Architecture Review

Review ownership integrity, module boundaries, contract changes, cascade
proliferation, dependency direction, retirement completeness, and net entropy.

## 7. Hard Boundaries

- This file governs this repository's Aegis records.
- Baseline snapshots are evidence, not substitutes for runtime tests.
- ADRs record accepted decisions; they do not replace baseline governance.
- Changes to this file require explicit user review.
