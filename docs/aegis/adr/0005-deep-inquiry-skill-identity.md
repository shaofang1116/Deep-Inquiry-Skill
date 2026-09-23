# ADR 0005: Deep Inquiry Skill Identity

## Status

Accepted on 2026-09-23.

## Context

The active Skill no longer has teaching or learner mentoring as its default
product contract. It performs autonomous investigation, skeptic review,
convergence, durable knowledge accumulation, and optional stateless queries.
The Autonomous Mentor name therefore advertises a retired responsibility.

## Decision

1. The public name is **Deep Inquiry** and the Skill ID is `deep-inquiry`.
2. `skill/deep-inquiry` is the only canonical package directory.
3. `.trae/skills/deep-inquiry` is the active workspace discovery entry.
4. The old Skill package and discovery name are deleted without a compatibility
   alias because there is no proven external dependency boundary.
5. Historical Aegis records, existing knowledge/session assets, and Git history
   are not rewritten.
6. The provenance value `autonomous-mentor-v1`, `mentor.py`, `Mentor`, and
   `MentorLoop` remain legacy importer evidence. Their later retirement is
   governed separately.
7. `.mentor-state` remains the runtime protocol directory. Renaming it would be
   an unrelated state migration and is outside this decision.

## Consequences

- New installations, CLI help, package checks, and discovery use Deep Inquiry.
- There is one active identity and no forwarding package.
- Existing v1 imports remain attributable to their original source format.
- Historical documents can still be interpreted against the names used when
  their evidence was recorded.

## Retirement Governance

- Deletion class: `code-retirement` and `contract-carrying code`.
- Retirement decision: `delete-first`.
- New canonical owner: `skill/deep-inquiry`.
- External boundary touched: no proven active dependency.
- Source-of-truth data risk: none.
- Persistent data deletion: none.

## Verification

- Focused identity checks cover frontmatter, title, CLI, package paths, and
  negative old-name scans inside the distributable package.
- Filesystem checks prove the old package and discovery entry are absent.
- Four-layer and package-sandbox checks prove behavior is unchanged.
- Migration checks prove preserved v1 provenance remains readable.
