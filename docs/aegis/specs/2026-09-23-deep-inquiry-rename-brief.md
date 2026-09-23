# Deep Inquiry Rename Spec Brief

## Status

Approved in conversation on 2026-09-23.

## Goal

Rename the active Skill from Autonomous Mentor / `autonomous-mentor` to
Deep Inquiry / `deep-inquiry` so its public identity matches the current
knowledge-first product scope.

## Requirements

1. The canonical package directory is `skill/deep-inquiry`.
2. `SKILL.md` uses frontmatter name `deep-inquiry`, title `Deep Inquiry`, and
   installation examples rooted at `deep-inquiry/`.
3. The CLI presents `deep-inquiry` and Deep Inquiry as its public identity.
4. Active package, test-layer, sandbox, frozen-install, and user-install paths
   use `deep-inquiry`.
5. The active workspace discovery link is `.trae/skills/deep-inquiry` and
   resolves to `skill/deep-inquiry`.
6. No active `skill/autonomous-mentor` package or
   `.trae/skills/autonomous-mentor` discovery entry remains.
7. No compatibility alias is added for the retired Skill name.

## Preservation Boundary

- Historical Aegis specifications, plans, work records, reports, commits, and
  existing knowledge/session assets retain their original wording.
- The v1 migration provenance value `autonomous-mentor-v1` remains unchanged.
- `mentor.py`, `MentorLoop`, and teaching-era importer symbols remain explicitly
  legacy until their separately governed retirement.
- Runtime state remains under `.mentor-state`; this internal protocol path is
  not part of the public Skill rename.

## Acceptance

- A dedicated rename contract check fails against the old package and passes
  only when public identity, canonical paths, negative old-entry checks, and
  legacy preservation are all satisfied.
- All four executable test layers pass from `skill/deep-inquiry`.
- Package sandbox verification uses only `deep-inquiry` install paths.
- Grep and filesystem audits find no active old package/discovery entry while
  allowing only the documented provenance and historical evidence.

## Architecture Review

`ArchitectureReviewRequired: yes`

This is a distribution and discovery contract change. It must retire the old
internal entry completely without rewriting immutable history or changing
knowledge persistence semantics.
