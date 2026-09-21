# M0 Entry Truth Baseline

## Status

Approved baseline-only slice. This document records observed routing and the
approved future direction; it does not switch any command to a new engine.

## Goal

Make the difference between the vNext product direction and the current public
CLI route observable, testable, and reviewable before any default-entry switch.

## Authority

- Knowledge-first intent and owner boundaries:
  `docs/2026-09-17-knowledge-first-skill-plan.md`
- Isolation and frozen-source boundary: `ISOLATION.md`
- Current public CLI routing: `skill/autonomous-mentor/scripts/cli.py`
- Current v1 import retirement boundary:
  `docs/aegis/adr/0001-one-way-v1-import-boundary.md`

## Baseline Alignment

- Product / Requirement Baseline: durable knowledge and autonomous convergence
  are the vNext product core; teaching is outside the default learning path.
- Architecture / Runtime Boundary Baseline: `KnowledgeStore` owns durable
  topic writes; `AutonomousLearningLoop` sequences vNext learning;
  `convergence.py` owns stopping decisions.
- Observed state: public `init`, `learn`, and `step` route through
  `_run_legacy()` to `MentorLoop`, while `query` and `ask` use vNext durable
  knowledge.
- Result: `Implementation Drift`, scope `architecture`. The durable knowledge
  contract remains intact, but the public default learning entry does not yet
  use its canonical loop.

## M0 Scope

1. Record the current command-to-owner matrix.
2. Capture normalized golden route fixtures for the public command surface.
3. Record the runtime-session and durable-knowledge schema boundary.
4. Record the approved target and compatibility retention in ADR 0002.
5. Run read-only source and isolated-temp-directory verification.

## Non-Goals

- Do not modify `scripts/cli.py`, `scripts/loop.py`, either schema, storage, or
  the generated ZIP.
- Do not migrate a user topic, delete legacy code, or install the vNext Skill.
- Do not claim that vNext is the current default learning route.

## Current CLI Route Matrix

| Command | Actual owner | Durable topic read/write | Runtime session | Status |
| --- | --- | --- | --- | --- |
| `init` | `_run_legacy()` -> `MentorLoop.begin_init()` | only binds references | creates pending/request | legacy main path |
| `learn` | `_run_legacy()` -> `MentorLoop.begin_learning()` | none | legacy pending flow | legacy main path |
| `step` | `_run_legacy()` -> `MentorLoop.step()` | none | consumes legacy judgment | legacy main path |
| `cancel` | `_run_legacy()` -> `MentorLoop.cancel()` | none | removes active legacy pending state | legacy control path |
| `state` | `_run_legacy()` -> `StateStore.load()` | none | reads legacy session state | legacy control path |
| `query` | `query_knowledge()` -> `KnowledgeStore` | reads current topic | none | vNext read path |
| `ask` | exact `query` alias | reads current topic | none | one-release compatibility alias |
| `demo` | `_run_legacy()` dispatches `smoke_run.main()` | fixture-owned | temporary fixtures only | vNext smoke via legacy dispatcher |

## Schema Boundary Matrix

| Concept | `schema.py` | `knowledge_schema.py` | M0 classification |
| --- | --- | --- | --- |
| Primary aggregate | `SessionState` | `TopicKnowledge` | separate runtime and durable owners |
| Evidence | session-oriented `Evidence` | durable `Evidence` | same label, different lifetime and reference semantics |
| Counterexample | session-oriented `Counterexample` | durable `Counterexample` | same label, different lifetime and reference semantics |
| Gap | `GapState` plus question tree | `KnowledgeGap` | same problem area, not interchangeable |
| Progress | `ProgressEntry` / pending judgment state | `ConvergenceRecord` / `LearningDelta` | runtime cursor versus canonical history |
| Teaching | `TeachingState`, `TeachingAsset`, `LearnerHypothesis` | absent | legacy/import-only context |
| Durable version | runtime `base_version` reference | topic `version` with snapshots | optimistic reference versus canonical version |

M0 records this boundary only. A later slice must decide whether any shared
value object is genuinely identical before merging names or types.

## Golden Fixture Contract

The fixture must contain only stable facts:

- command name;
- owner symbol and module;
- durable versus runtime effects;
- machine-output status/exit-code class where applicable;
- compatibility and retirement classification.

It must exclude paths, timestamps, generated request IDs, model prose, and
temporary fixture content. A future route-switch change must intentionally
update this fixture and ADR status rather than silently redirecting commands.

## Acceptance

1. The route fixture matches the current CLI source and isolated command
   behavior.
2. `query` and `ask` remain stateless durable reads; `ask` remains
   byte-equivalent to `query`.
3. Work-host `init` and `step` retain their current JSON envelope and
   exit-code behavior until M0.5.
4. The schema matrix correctly separates runtime-only and durable-only types.
5. Neither frozen Skill nor user-level installation is modified.

## Next Slice: M0.5

M0.5 may switch `init`, `learn`, and `step` to the vNext loop only after it
defines a replacement host state protocol, proves durable-topic creation and
recovery, and establishes the legacy import-only compatibility boundary.
