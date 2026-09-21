# Read-Only Compatibility Window Intent

## Requested Outcome

Establish the first read-only compatibility window required by ADR 0002 without
changing public commands, runtime code, packages, archives, frozen Skills, or
durable user knowledge.

## Parent Plan and Scope

- Parent plan:
  `docs/aegis/plans/2026-09-21-post-m05-compatibility-window-retirement.md`
- Active slice: Task 1, "Establish the Read-Only Compatibility Window".
- Working baseline: commit `3accc78` on 2026-09-21; the M0.5 runtime baseline
  is `b433904`.
- Scope: documentation, observation receipt format, ADR clarification, and
  focused public-route verification only.

## Non-Goals

- Do not remove `ask`, legacy source, sessions, evaluator assets, or tests.
- Do not instrument the CLI or collect caller data.
- Do not inspect, migrate, modify, or delete persistent user knowledge.
- Do not treat missing telemetry as proof that no dependency exists.

## Compatibility Window

- Start: 2026-09-21.
- Release/version boundary: no Git tag, remote release, or declared public
  version exists at the start of this window. This is an explicit release
  evidence gap, not a default approval to retain compatibility indefinitely.
- Review trigger: execute Task 3 from the recorded evidence now; a calendar
  delay cannot create evidence because no telemetry or consumer inventory
  exists.
- Close condition: make one per-surface decision in Task 3. `ask` cannot be
  retired until a concrete release/version identifier exists; internal surfaces
  may be classified immediately. No source retirement is authorized by this
  record.

The existing instruction that `ask` must be removed before the first subsequent
major version remains in force. If a major-version boundary is declared before
the window review, `ask` must be decided before that release; the absence of a
declared version cannot be used to bypass the decision.

## Named Surfaces

| Surface | Current contract | Observation signal | Retirement precondition |
| --- | --- | --- | --- |
| `ask` | Exact stateless alias of `query` | Explicit caller report or review receipt naming `ask` | Window close, release identifier, and no active dependency or a documented exception |
| Former `state.state` | Superseded inner legacy state shape; vNext exposes host-run references | Explicit external consumer report or migration review | Proven consumers migrated or a time-bounded exception |
| v1 importer input | Explicit, one-way, source-read-only `SessionState` input | Importer fixture/surface evidence and reported consumer use | Task 2 surface proof and importer parity |
| Historical evaluator assets | Non-public evidence, not a runtime fallback | Archive/consumer inventory | Evidence disposition and no active required consumer |

## Read-Only Observation Receipt

No telemetry service exists and this task adds none. A receipt is a manually
recorded, non-content-bearing observation supplied by a caller, release review,
or repository audit. Each receipt must record:

```text
receipt_id: stable local identifier
observed_at: ISO-8601 timestamp
observer_kind: caller-report | release-review | repository-audit
caller_or_source_id: opaque identifier when available, otherwise unavailable
surface: ask | state.state | v1-importer-input | evaluator-assets
command: public command name or not-applicable
public_envelope_version: declared value or not-declared
deprecated_surface_requested: yes | no | unknown
dependency_evidence: concise non-content description
disposition: observation-only | compat-exception-proposed
```

Redaction rule: never record a user question, proposition, claim, evidence
body, knowledge JSON, session body, filesystem path, credential, or raw caller
identifier. Use an opaque source label or hash where identification is needed.
`public_envelope_version: not-declared` is valid at this baseline because the
current CLI has no exposed envelope version field; the receipt must also cite
the reviewed commit.

An observed active dependency requires a separately documented
`compat-exception` with its migration target, observation metric, owner, and
retirement date. No receipt is only "no observation recorded"; it is not
absence-of-dependency evidence. It does not block classification of internal
code, because unknown dependency is not active dependency evidence.

## Baseline Read Set

- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `skill/autonomous-mentor/SKILL.md`
- `skill/autonomous-mentor/scripts/cli.py`
- `skill/autonomous-mentor/scripts/migrate_v1.py`

## Risk Hints

- Preserve one public learning owner and one durable topic writer.
- Keep v1 import explicit and source-read-only.
- Do not turn an observation record into an unbounded compatibility exception.
