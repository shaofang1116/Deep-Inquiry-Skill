# Deep Inquiry Rename Implementation Plan

## Goal

Replace the active Autonomous Mentor identity with Deep Inquiry across the
canonical Skill package, discovery entry, CLI, tests, and release sandbox.

## Architecture

- `skill/deep-inquiry` becomes the only active package owner.
- `.trae/skills/deep-inquiry` becomes the only active workspace discovery link.
- Existing vNext runtime, persistence, and importer owners remain unchanged.

## Tech Stack

Agent Skills Markdown, Python 3.10+ standard library, Git worktrees, executable
four-layer checks.

## Baseline / Authority Refs

- `docs/aegis/specs/2026-09-23-deep-inquiry-rename-brief.md`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `skill/autonomous-mentor/SKILL.md`

## Compatibility Boundary

The old Skill name is an internal entry being retired, not an external
compatibility contract. Historical records and v1 provenance remain immutable.
No old-name alias, forwarding directory, or duplicate discovery link is added.

## Verification

Run the focused rename contract through RED and GREEN, all four layer runners,
package sandbox checks, symlink-resolution checks, `git diff --check`, and
bounded old-name scans.

## Architecture Integrity Lens

- Invariant: one active Skill identity and one canonical package.
- Canonical owner: `skill/deep-inquiry`.
- Responsibility overlap: no old-name forwarding package or discovery alias.
- Higher-level simplification: rename distribution surfaces only; do not alter
  runtime state or persistence contracts.
- Falsifier: an active old package/link remains, or historical provenance is
  rewritten.
- Verdict: proceed.

## TDD Route

- Mode: auto
- Decision: strict
- Reason: package discovery and distribution contracts cross multiple files.
- Verification: focused rename contract plus complete layered and sandbox runs.

## Task 1: Pin the Rename Contract

**Files**

- Create:
  `skill/autonomous-mentor/examples/tests/adapter/skill_identity_checks.py`
- Modify: `skill/autonomous-mentor/examples/tests/layer_manifest.json`

1. Assert the new canonical directory, frontmatter, title, CLI identity,
   package paths, and absence of active old entries.
2. Assert v1 provenance and legacy importer symbols remain unchanged.
3. Run the focused check and observe failure against the old identity.

## Task 2: Move the Canonical Package

**Files**

- Rename: `skill/autonomous-mentor` to `skill/deep-inquiry`
- Modify active package branding, install examples, test runner wording, CLI
  identity, sandbox paths, and license attribution.

1. Perform the directory rename without retaining a forwarding directory.
2. Apply only public identity and active-path changes.
3. Keep `.mentor-state`, `autonomous-mentor-v1`, `mentor.py`, and `MentorLoop`.
4. Run the focused contract and adapter layer until green.

## Task 3: Update Discovery and Governance

**Files**

- Replace the active `.trae/skills/autonomous-mentor` link with
  `.trae/skills/deep-inquiry`.
- Create `docs/aegis/adr/0005-deep-inquiry-skill-identity.md`.
- Modify `docs/aegis/INDEX.md`.

1. Record the canonical identity and preservation boundary.
2. Verify the discovery link resolves to the renamed package.
3. Do not rewrite historical Aegis records.

## Task 4: Release Verification

1. Run `python3 examples/tests/run_layer.py --all` from `skill/deep-inquiry`.
2. Run package sandbox verification with renamed frozen/user install fixtures.
3. Audit active old-name references and classify every allowed remainder.
4. Run `git diff --check` and review the complete diff.
5. Apply the verified tracked changes and active discovery link to `main`
   without committing.

## Risks and Retirement

- Risk: package tests accidentally validate the old installed copy. Mitigation:
  renamed path assertions and tree hashes.
- Risk: provenance becomes unreadable. Mitigation: preserve
  `autonomous-mentor-v1` exactly.
- Retirement decision: `delete-first` for the old package and active discovery
  entry; no persistent data deletion and no compatibility exception.
