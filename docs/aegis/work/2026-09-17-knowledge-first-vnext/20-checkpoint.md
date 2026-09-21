# Todo Checkpoint

## Current Todo

M0.5 Task 3: implement resumable stage progression and at-most-once commits.

## Completed

- Task 0 isolated baseline.
- Task 1 fixtures for complete knowledge, a high-value gap, one-cycle stopping,
  and two post-baseline low-gain deltas.
- Task 1 acceptance runner covering convergence decisions and the absence of
  teaching actions from the default learning result.
- Task 2 durable knowledge dataclasses and cross-reference validation.
- Task 2 runtime session references: `topic_id`, `knowledge_root`, and
  `base_version`.
- Task 2 development and sandbox verification.
- Task 3 atomic global file library with versioned immutable snapshots,
  optimistic conflict rejection, SHA-256 verification, locked recovery, and
  explicit no-fallback failures.
- Task 3 development and sandbox verification.
- Task 4 durable `related_claim_refs` for cross-topic claim links.
- Task 4 deterministic `index.json` and human-readable `summary.md`
  projections, including delete/corruption rebuild checks.
- Task 4 development and sandbox verification.
- Task 5 validated durable delta application for new, revised, disputed, and
  retired claims, evidence, counterexamples, and gap resolution.
- Task 5 development and sandbox verification.
- Task 6 deterministic convergence owner covering all seven stop conditions,
  dishonest low-gain rejection, and bounded safety checkpointing.
- Task 6 development and sandbox verification.
- Task 7 independent durable autonomous-learning orchestrator with explicit
  eight-stage traces.
- Task 7 deterministic highest-value gap selection, investigation plans before
  integration, skeptic-before-commit ordering, and one delta/version per cycle.
- Task 7 durable completion result projection without teaching actions.
- Task 7 development and sandbox verification.
- Task 8 stateless durable query owner and CLI `query` command.
- Task 8 one-release `ask` compatibility alias with identical query semantics.
- Task 8 removal of `feedback` and stateful teaching from default CLI,
  smoke, eval, and Skill instructions.
- Task 8 package import cleanup so query does not load legacy `mentor.py`.
- Task 8 development and sandbox verification.
- Task 9 JSON pending/done/state/cancel/error envelopes with complete host
  metadata and process exit semantics.
- Task 9 runtime session references bound from explicit host arguments.
- Task 9 bytecode suppression before local imports and research-tool gating
  after `plan_investigation`.
- Task 9 development and sandbox verification.
- Task 10 strict one-way v1 importer with exact schema and nested type
  validation.
- Task 10 deterministic proposition, rule, evidence, counterexample, and open
  boundary mapping through `KnowledgeStore`.
- Task 10 durable inert migration provenance and unsupported teaching context.
- Task 10 default repeat rejection and explicit importer-owned version guard
  that prevents overwrite after vNext evolution.
- Task 10 valid, partial, corrupt, source-race, Store-error, and 20-real-session
  verification in development and sandbox.
- Task 10 architecture review closed with no Critical or Warning findings.
- Task 11 real-host raw-event capture and cross-model acceptance.
- Task 12 sandbox recovery, packaging, and release gate.
- M0 entry-truth baseline: current CLI route matrix, golden fixture, and
  separate target-direction ADR without changing a public runtime route.

## Active Slice

M0.5 is complete. Development checks executed from an isolated caller and a
fresh sandbox copy both passed. The sandbox replayed host recovery, public
`init`/`step` initialization, `learn`/`step` stage progression, and route
ownership against an explicit sandbox knowledge root. ADR 0002 now records the
implemented `VNextHost -> HostRuntimeCoordinator` public path, while retaining
the future read-only compatibility-window deletion trigger. Source scans show
that the public CLI contains no `MentorLoop`, `_run_legacy`, or
`_bind_runtime_reference`; legacy source, v1 session input support, frozen
Skills, user-level Skill, archive, and user durable state remain intact. The
next action, if requested, is a separate compatibility-window retirement
decision; it must not delete source or persistent data without a scoped plan
and confirmation where applicable.

## Evidence Refs

- `skill/autonomous-mentor/examples/knowledge_first_acceptance_checks.py`
- `skill/autonomous-mentor/examples/fixtures/knowledge_first_cases.py`
- `skill/autonomous-mentor/examples/fixtures/convergence_cases.py`
- `skill/autonomous-mentor/examples/eval_vnext_suite.py`
- `skill/autonomous-mentor/examples/realhost_vnext_profile.py`
- `skill/autonomous-mentor/examples/eval_vnext/`
- `skill/autonomous-mentor/examples/package_vnext_checks.py`
- `skill/autonomous-mentor/examples/cli_route_baseline_checks.py`
- `skill/autonomous-mentor/sessions/knowledge-first-vnext/validation_manifest.json`
- `docs/aegis/specs/2026-09-18-m0-entry-truth-brief.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `docs/aegis/specs/2026-09-18-m05-host-recovery-design.md`
- `docs/aegis/plans/2026-09-18-m05-host-recovery-implementation.md`
- `skill/autonomous-mentor/examples/vnext_host_recovery_checks.py`
- `/tmp/autonomous-mentor-vnext-m05-task1-red.log`
- `/tmp/autonomous-mentor-vnext-m05-task2-red.log`
- `/tmp/autonomous-mentor-vnext-m05-task2-green.log`
- `/tmp/autonomous-mentor-vnext-task12-red.log`
- `/tmp/autonomous-mentor-vnext-task12-green.log`
- `/tmp/autonomous-mentor-vnext-task11-red.log`
- `/tmp/autonomous-mentor-vnext-task11-specfix-red.log`
- `/tmp/autonomous-mentor-vnext-task11-gap-semantics-red.log`
- `/tmp/autonomous-mentor-vnext-red.log`
- `/tmp/autonomous-mentor-vnext-sandbox-red.log`
- `/tmp/autonomous-mentor-vnext-schema-red.log`
- `/tmp/autonomous-mentor-vnext-schema-mid.log`
- `/tmp/autonomous-mentor-vnext-store-red.log`
- `/tmp/autonomous-mentor-vnext-store-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-index-red.log`
- `/tmp/autonomous-mentor-vnext-index-red-owners.log`
- `/tmp/autonomous-mentor-vnext-index-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-delta-red.log`
- `/tmp/autonomous-mentor-vnext-dispute-red.log`
- `/tmp/autonomous-mentor-vnext-delta-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-convergence-red.log`
- `/tmp/autonomous-mentor-vnext-convergence-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-parent-after-convergence.log`
- `/tmp/autonomous-mentor-vnext-sandbox-parent-task7-red.log`
- `/tmp/autonomous-mentor-vnext-loop-red.log`
- `/tmp/autonomous-mentor-vnext-loop-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-task7-all-checks.log`
- `/tmp/autonomous-mentor-vnext-task7-sandbox-checks.log`
- `/tmp/autonomous-mentor-vnext-query-red.log`
- `/tmp/autonomous-mentor-vnext-query-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-query-lazy-red.log`
- `/tmp/autonomous-mentor-vnext-task8-final-checks.log`
- `/tmp/autonomous-mentor-vnext-task8-sandbox-checks.log`
- `/tmp/autonomous-mentor-vnext-work-host-red.log`
- `/tmp/autonomous-mentor-vnext-work-host-green-attempt.log`
- `/tmp/autonomous-mentor-vnext-work-host-envelope-red.log`
- `/tmp/autonomous-mentor-vnext-task9-final-checks.log`
- `/tmp/autonomous-mentor-vnext-task9-sandbox-checks.log`
- `/tmp/autonomous-mentor-vnext-migration-red.log`
- `/tmp/autonomous-mentor-vnext-migration-review-red.log`
- `/tmp/autonomous-mentor-vnext-migration-deep-red.log`
- `/tmp/autonomous-mentor-vnext-migration-shape-red.log`
- `/tmp/autonomous-mentor-vnext-migration-enum-red.log`
- `/tmp/autonomous-mentor-vnext-migration-final-green.log`
- `/tmp/autonomous-mentor-vnext-task10-final-dev.log`
- `/tmp/autonomous-mentor-vnext-task10-final-sandbox.log`
- SHA-256:
  - acceptance runner:
    `a188d5a63627357f520f7f775086f43259e3f18cd1f371943a66fb1d061f836e`
  - knowledge fixtures:
    `5c1cf069df9b2b75f3670d5e89b2437de4f0cb5a693fea1be00ad159e3484c24`
  - convergence fixtures:
    `6b6d8690d0a7e6c0315a76bd87b5ed8db1c13507537d9ede30cc844a2f7ae7ac`
  - durable knowledge schema:
    `05ee7251f2013f5c869d82cffe0b7156741b3604598ae1407905337ca9cb4ca3`
  - runtime schema:
    `76b3a428a5e8dfd1debe9952ba595018a5372b21a1847c8782171fe5bdc4da7a`
  - schema checks:
    `4138a5830dc3bfd8f45be6d4fa5187a9123f9cd3042701c6c31892cac588a20f`
  - atomic knowledge store:
    `6c87a4cb467235dce2903fc6e5220d91216860ca88d861562fdb17557860f57c`
  - knowledge-store checks:
    `b918db0d79fa79b8713d6679a164e6750d627d61684c3c87ff9ac3ee634bc508`
  - extended durable schema:
    `edbfff4485357790df0060a81737404d0757082bee5b0f5bbb02729e4f491085`
  - indexer:
    `7818301a838069c3c5b380f2d7bb91bbe22d0054e73bc569b74558c74347ee08`
  - renderer:
    `2eb77d8bbf0bc0728940b204877307f10203e5faa0ff2617637416a788dbafbc`
  - index rebuild checks:
    `afd1d78de6217a1b0cd18667a95df15aa14bea820619ac6cc07f72eee0ee9bf9`
  - updated knowledge fixtures:
    `26ebb822e491d04f71062fe381c767649d3b933a9001953906f3689dddbd4323`
  - learner with durable delta application:
    `1a2eb7fb42be5771699dbe9a377ddc3e3b704e37db42cf913f416e8db957947e`
  - schema with disputed-claim invariant:
    `6b4fa74d5868927e50a7f1e4dd796a2f782feda9287a96a0cb23b9d5e4252d4b`
  - learning-delta checks:
    `a2d70cd65ce0a2fc56b687ef219a5ad923bac3c49eb2b6435698aa4e1ecf296f`
  - convergence owner:
    `efb6e295e7c4416271b243b3de1f03b987b4976f2b188459ba7091da783a77cc`
  - failures constants:
    `a0f29ac7c366176cf8e19c44dc6ded909813d9ed12accc2784baf29d03e76003`
  - convergence checks:
    `45446d58c11f7c2e8ceaa5839135f083e47ba5c650d88f710fd0f7f5c8c350a9`
  - parent acceptance:
    `81e664de94eea0592d0f8c6ac71a21eefd560f689ec8bc6036093ea97ba160b7`
  - durable autonomous loop:
    `03652187eaba69481b2b2082f302c89aabc6761a50a7fb2b6b87aefb2bf29bbb`
  - vNext autonomous judgment contracts:
    `07a069e939188efe036e50b83741120d9cc8ee8f3f79e85e28abfffa66cea1cd`
  - durable learning result projection:
    `dc81ab043e3041fa12c403ce208e959e3cabbb0b64aafbcc718d88a3197b8cc5`
  - autonomous loop checks:
    `1fbf13f4a6caedf46f7d7f081aa743615eaf454dab915e89aea6507fa5351166`
  - stateless query owner:
    `be66b38274464a86d20d4d6428d4f4177f83e71156dc0b2b1af09ce375c596f3`
  - CLI with query and ask alias:
    `b16e60099f42d839f9cf57aedf1ed68c1d4b5dc7d846d1db16db56c86eef8727`
  - side-effect-free package initializer:
    `c710ed7fde7e2ae2e067e0ddad80f3dac2cf9b7a9f8235d77faa2b52489f794c`
  - stateless query checks:
    `8a5164e4833ecf5c86c1ddcc1b2e992b14e0d49373b73bccd2e8021c60ef33b4`
  - vNext default smoke:
    `56979868f69fe7803d9e13f05f1b6a3e47f82b777644a2d5e6645d219f1c62e0`
  - vNext default eval:
    `2c249688eeae2052328b5bc38e776b9c4f179eccef3ff03c6eb3ce4ec680555d`
  - vNext Skill instructions:
    `57b6a4dcd7f7989b4f939bdf42bfef0db35ea43412b1beb67a8962831e196ebb`
  - Work-host CLI:
    `dfb6207bac5a67368206b2e01c21acdc00c9adc818045d0e56bc0513cba604b1`
  - Work-host Skill instructions:
    `4c8422fb9fdfc28f95e200dbe6f36d33bd9293af3afe75bc624b7d4cd109eed3`
  - vNext Work-host checks:
    `711171b8bfe2d786d06eed0e2b43c49d9f75f0b30c2912d9914708b830937984`
  - updated declarative host checks:
    `f32f096ebc05433bb51f15d58d0d091dc0114cec9f4cc36f97cb10f7b585fad8`
  - one-way v1 importer:
    `e528e373eea43b934f4bfaadd59feb8f8b822319b9125401335a8f045f59f35f`
  - durable schema with inert migration metadata:
    `aa772f1a552844f2e32936cca13f30e59e422ba956a2855026d349c5fb244010`
  - v1 migration checks:
    `201008208a8038925138383d45032dfbe15ab2a1d00be8750dfc850b2587713d`
  - knowledge fixture with explicit empty migration metadata:
    `ef66c272b1451327bb81f39947d855568eb6142401cc523f3f336f08a9201e9a`
  - v1 import boundary ADR:
    `24ee8686dc3904fe6b70657fde10d988b956f8902f57968bd16dcd99265bd6cb`

## Blocked On

No blocker. The vNext ZIP is generated, while installation and replacement of
either frozen Skill remain out of scope without a separate scoped approval.

## Resume State

Tasks 1 through 12 are complete. The archive is
`dist/autonomous-mentor-vnext-2026-09-17.zip`, SHA-256
`6bd00076db3b096b01d8fb391d2f4dfdc6595c31105b9e3dc29845982aadaf09`.
Do not install or replace either frozen Skill without a new scoped approval.

## Drift Check

- Intent: unchanged; package validation and ZIP generation were sandbox-only.
- Compatibility boundary: preserved; frozen v1 and global installation untouched.
- New owner/fallback: Task 12 adds an eval-only package gate; it excludes
  `.mentor-state` and caches rather than introducing a runtime fallback.
- Retirement track: v1 teaching evaluators are not imported by the vNext suite.
- Decision: Task 12 complete; user-level installation remains intentionally
  untouched.
