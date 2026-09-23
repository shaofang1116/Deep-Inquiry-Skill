# Deep Inquiry Localization Plan

## Goal

Make `skill/deep-inquiry/SKILL.md` the English canonical public protocol and
add `skill/deep-inquiry/SKILL.zh-CN.md` as its complete Simplified Chinese
mirror, without changing the executable protocol or distribution state.

## Architecture

- `SKILL.md` remains the only discovery entry and canonical source.
- `SKILL.zh-CN.md` mirrors the same protocol for Chinese readers.
- Python runtime, CLI semantics, knowledge schema, state layout, package
  discovery, and installed copies remain outside this change.

## Baseline / Authority Refs

- `skill/deep-inquiry/SKILL.md`
- `docs/aegis/adr/0005-deep-inquiry-skill-identity.md`
- `docs/aegis/reports/2026-09-23-deep-inquiry-rename-validation.md`

## Compatibility Boundary

The active Skill identifier remains `deep-inquiry`; its English frontmatter
and loading path do not change. The Chinese file is a companion document, not
a second discoverable Skill and not a locale-selection mechanism.

## Verification

Run a localization contract that verifies:

1. the canonical file is English and retains the required host-protocol
   anchors;
2. the Chinese companion exists, identifies its relationship to the canonical
   file, and retains the same anchors;
3. both documents preserve the exact command and state-path literals;
4. existing adapter and package-sandbox checks remain green.

## Plan Pressure Test

- Owner / contract / retirement: `SKILL.md` remains the sole active owner;
  no old owner or compatibility route is created.
- Architecture integrity: documentation-only change; no higher-level runtime
  owner is implicated.
- Verification scope: public protocol text, companion parity anchors, and
  package behavior.
- Task executability: bounded to two Markdown files and one adapter contract.
- Pressure result: proceed.

## Execution Stages

1. **Contract first.** Add a focused adapter check for canonical-English,
   companion presence, and stable protocol literals; run it and observe RED.
2. **Canonical localization.** Translate the current protocol faithfully into
   English in `SKILL.md`, then preserve the current Chinese protocol in
   `SKILL.zh-CN.md` with a clear canonical-source note. Run the focused
   contract to GREEN.
3. **Release verification.** Run the adapter layer, full layered suite,
   package sandbox check, Markdown whitespace check, and diff review. Do not
   update the user-level installed copy or create a commit without a separate
   explicit request.

## Human Confirmation Gates

- **Gate A, before execution:** confirm the canonical-English and
  Chinese-mirror wording model. This plan is the approval artifact.
- **Gate B, after automated verification:** review the English protocol for
  terminology and global-reader clarity before any installation or release
  synchronization.

## Risks and Rollback

- Risk: a translation weakens an imperative protocol rule. Mitigation:
  contract anchors retain exact commands and key prohibitions; review diffs
  section by section.
- Risk: the two files drift. Mitigation: companion and structural anchors are
  asserted by the focused check; substantive parity remains a human review
  concern at Gate B.
- Rollback: restore only the two Markdown files and focused check. No
  persistent state, package, or installed copy is modified.
