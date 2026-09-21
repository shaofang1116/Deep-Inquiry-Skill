# Knowledge-First vNext Intent

## Requested Outcome

Execute the approved knowledge-first implementation plan in the isolated vNext
workspace. Durable knowledge and autonomous convergence are the product core;
teaching is optional and outside the default learning path.

## Scope

- Parent plan: `docs/2026-09-17-knowledge-first-skill-plan.md`
- Development source: `skill/autonomous-mentor/`
- Disposable runtime target:
  `/Users/bytedance/主动学习skill/.sandbox/autonomous-mentor-vnext/`

## Non-Goals

- Do not modify either frozen v1 Skill location.
- Do not install vNext globally before release acceptance and explicit approval.
- Do not add databases, embeddings, model APIs, or third-party dependencies.

## Baseline Read Set

- `ISOLATION.md`
- `docs/2026-09-17-knowledge-first-skill-plan.md`
- Existing validation scripts under `skill/autonomous-mentor/examples/`

## Risk Hints

- Persistence and convergence must each have one canonical owner.
- Runtime sessions must not become a second knowledge source of truth.
- RED tests must fail for missing behavior, not broken test infrastructure.
