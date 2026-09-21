# Evidence Bundle Draft

## Task 1 RED

Command:

```bash
python3 examples/knowledge_first_acceptance_checks.py
```

Observed:

- Process exit code: `1`
- Failure type: `AssertionError`
- Failure reason:
  `vNext RED: canonical owners are not implemented yet: knowledge contracts, convergence policy`
- No `__pycache__` directory was produced.

Interpretation:

The acceptance entry point and fixtures load successfully. The check fails for
the intended missing production behavior before any vNext implementation is
added.

## Task 1 Sandbox Reproduction

The disposable sandbox produced the same `AssertionError` and message as the
development source. No bytecode cache was created.

Development and sandbox copies passed byte-for-byte `cmp`. Matching SHA-256
digests:

- `knowledge_first_acceptance_checks.py`:
  `a188d5a63627357f520f7f775086f43259e3f18cd1f371943a66fb1d061f836e`
- `knowledge_first_cases.py`:
  `5c1cf069df9b2b75f3670d5e89b2437de4f0cb5a693fea1be00ad159e3484c24`
- `convergence_cases.py`:
  `6b6d8690d0a7e6c0315a76bd87b5ed8db1c13507537d9ede30cc844a2f7ae7ac`

## Task 2 Schema TDD

RED:

- Initial failure: `scripts/knowledge_schema.py` did not exist.
- Intermediate failure after adding the durable owner:
  `SessionState.__init__()` rejected `topic_id`.

GREEN:

- `python3 examples/knowledge_schema_checks.py`: 6/6 passed.
- `python3 examples/tree_quality_checks.py`: 8/8 passed.
- All ten legacy regression entry points passed in the development source.
- Sandbox schema checks and tree-quality regression passed.
- Parent acceptance remains intentionally RED only for the missing convergence
  owner.
- No `__pycache__` directory was produced.

Task 2 SHA-256:

- `scripts/knowledge_schema.py`:
  `05ee7251f2013f5c869d82cffe0b7156741b3604598ae1407905337ca9cb4ca3`
- `scripts/schema.py`:
  `76b3a428a5e8dfd1debe9952ba595018a5372b21a1847c8782171fe5bdc4da7a`
- `examples/knowledge_schema_checks.py`:
  `4138a5830dc3bfd8f45be6d4fa5187a9123f9cd3042701c6c31892cac588a20f`

Frozen v1 workspace and user-level `scripts/schema.py` both retain SHA-256
`aab7b2cba366c849b46aeb6f2b9f6d05366fb8bf941fd33bf876fb8316b8bfd8`.

## Task 3 Atomic Knowledge Store TDD

RED:

- `python3 examples/knowledge_store_checks.py` exited `1`.
- The intended failure was:
  `Task 3 RED: durable knowledge store does not exist: scripts/knowledge_store.py`.
- No `__pycache__` directory was produced.

GREEN:

- `python3 examples/knowledge_store_checks.py`: 9/9 passed.
- Covered explicit-root create/load, automatic version increment, immutable
  snapshots, partial-current recovery, stale-base rejection, SHA-256 mismatch
  detection, active-writer rejection, stale-lock diagnostics, permission
  failure, and no project-local fallback.
- `knowledge_schema_checks.py` and nine related legacy regression entry points
  passed in the development source.
- The sandbox store and schema checks passed.
- Development and sandbox Task 3 files passed byte-for-byte `cmp`.
- Parent acceptance remains intentionally RED only for the missing convergence
  owner.
- No development or sandbox `__pycache__` directory was produced.

Task 3 SHA-256:

- `scripts/knowledge_store.py`:
  `6c87a4cb467235dce2903fc6e5220d91216860ca88d861562fdb17557860f57c`
- `examples/knowledge_store_checks.py`:
  `b918db0d79fa79b8713d6679a164e6750d627d61684c3c87ff9ac3ee634bc508`

Frozen v1 workspace `scripts/schema.py` remains
`aab7b2cba366c849b46aeb6f2b9f6d05366fb8bf941fd33bf876fb8316b8bfd8`.

## Task 4 Rebuildable Projection TDD

RED:

- First RED: `related_claim_refs` was dropped by durable-schema round-trip.
- After the minimal schema correction, the second RED was:
  `Task 4 RED: projection owners do not exist: scripts/indexer.py and scripts/renderer.py`.

GREEN:

- `python3 examples/index_rebuild_checks.py`: 6/6 passed.
- Covered deterministic two-topic scanning, cross-topic claim links, canonical
  source hashes, Markdown rendering, byte-for-byte deletion rebuild, corrupt
  projection repair, and canonical-state immutability.
- Development `knowledge_schema_checks.py` and
  `knowledge_store_checks.py` remained GREEN.
- Sandbox projection, store, and schema checks passed.
- Development and sandbox Task 4 files passed byte-for-byte `cmp`.
- Parent acceptance remains intentionally RED only for the missing convergence
  owner.
- No development or sandbox `__pycache__` directory was produced.

Plan correction:

- Task 4 now explicitly includes `knowledge_schema.py` and its fixture because
  cross-topic links must live in canonical topic JSON rather than being
  inferred by a derived index.
- References use `topic_id#claim_id`; per-topic schema owns shape validation,
  and full-library index rebuild owns target existence validation.

Task 4 SHA-256:

- `scripts/knowledge_schema.py`:
  `edbfff4485357790df0060a81737404d0757082bee5b0f5bbb02729e4f491085`
- `scripts/indexer.py`:
  `7818301a838069c3c5b380f2d7bb91bbe22d0054e73bc569b74558c74347ee08`
- `scripts/renderer.py`:
  `2eb77d8bbf0bc0728940b204877307f10203e5faa0ff2617637416a788dbafbc`
- `examples/index_rebuild_checks.py`:
  `afd1d78de6217a1b0cd18667a95df15aa14bea820619ac6cc07f72eee0ee9bf9`
- `examples/fixtures/knowledge_first_cases.py`:
  `26ebb822e491d04f71062fe381c767649d3b933a9001953906f3689dddbd4323`

## Task 5 Durable Learning Delta TDD

RED:

- Initial RED:
  `Task 5 RED: Learner.apply_knowledge_delta does not exist`.
- Follow-up invariant RED demonstrated that a disputed claim without a linked
  counterexample was incorrectly accepted before the schema constraint.

GREEN:

- `python3 examples/learning_delta_checks.py`: 7/7 passed.
- Covered new and revised claims, evidence, disputed claims with mandatory
  counterexamples, explicit retirement, rejected unsupported gap resolution,
  rejected unsupported high-confidence claims, and one immutable version per
  accepted delta.
- Rejected deltas left the current durable version unchanged.
- Development schema, store, index, and five directly affected legacy learner
  regression entry points passed.
- Sandbox delta, schema, and tree-quality checks passed.
- Development and sandbox Task 5 files passed byte-for-byte `cmp`.
- No sandbox `__pycache__` directory was produced.

Task 5 SHA-256:

- `scripts/learner.py`:
  `1a2eb7fb42be5771699dbe9a377ddc3e3b704e37db42cf913f416e8db957947e`
- `scripts/knowledge_schema.py`:
  `6b4fa74d5868927e50a7f1e4dd796a2f782feda9287a96a0cb23b9d5e4252d4b`
- `examples/learning_delta_checks.py`:
  `a2d70cd65ce0a2fc56b687ef219a5ad923bac3c49eb2b6435698aa4e1ecf296f`

## Task 6 Convergence Policy TDD

RED:

- `python3 examples/convergence_checks.py` exited `1` because
  `scripts/convergence.py` did not exist.

GREEN:

- `python3 examples/convergence_checks.py`: 10/10 passed.
- Covered required facets, high-value gaps, skeptic structural hits,
  insufficient marginal trend, non-low gain, evidence deficits, specific stop
  reasons, dishonest low-gain rejection, full convergence, and safety
  checkpointing without false convergence.
- Parent acceptance passes all three convergence scenarios, then reaches the
  expected Task 7 RED because `loop.build_learning_result` is absent.
- Development delta and affected legacy regressions passed.
- Sandbox convergence checks passed and reproduced the same Task 7 parent RED.
- Development and sandbox Task 6 files passed byte-for-byte `cmp`.
- No development or sandbox `__pycache__` directory was produced.

Task 6 SHA-256:

- `scripts/convergence.py`:
  `efb6e295e7c4416271b243b3de1f03b987b4976f2b188459ba7091da783a77cc`
- `scripts/failures.py`:
  `a0f29ac7c366176cf8e19c44dc6ded909813d9ed12accc2784baf29d03e76003`
- `examples/convergence_checks.py`:
  `45446d58c11f7c2e8ceaa5839135f083e47ba5c650d88f710fd0f7f5c8c350a9`
- `examples/knowledge_first_acceptance_checks.py`:
  `81e664de94eea0592d0f8c6ac71a21eefd560f689ec8bc6036093ea97ba160b7`

## Task 7 Autonomous Loop TDD

RED:

- `python3 examples/autonomous_loop_checks.py` failed with:
  `ImportError: cannot import name 'AutonomousLearningLoop' from 'scripts.loop'`.
- The failure occurred at the intended missing production API.

GREEN:

- `python3 examples/autonomous_loop_checks.py`: 5/5 passed.
- The three-cycle path selected gaps deterministically in descending value
  order, exposed each investigation plan before integration, and committed
  exactly one durable delta/version per cycle.
- The skeptic reviewed each uncommitted integration proposal before
  `Learner.apply_knowledge_delta` persisted it.
- The complete eight-stage trace ended only after the canonical convergence
  owner returned `converged`.
- The durable result contains `topic_id`, `knowledge_version`, `delta_history`,
  `unresolved_deferred_gaps`, and `convergence_reason`, with no teaching action.
- Parent knowledge-first acceptance passed 4/4.
- All development and sandbox `examples/*_checks.py` entry points passed.
- Development and sandbox `smoke_run.py` passed 6/6.
- Development and sandbox `eval_suite.py` passed 3/3.
- Development and sandbox Task 7 files passed byte-for-byte `cmp`.
- No development or sandbox `__pycache__` directory was produced.
- Frozen v1 `scripts/schema.py` remains
  `aab7b2cba366c849b46aeb6f2b9f6d05366fb8bf941fd33bf876fb8316b8bfd8`.

Architecture alignment:

- `loop.py` owns orchestration only.
- `convergence.py` remains the sole stopping-policy owner.
- `knowledge_store.py` remains the persistence and optimistic-version owner.
- `compressor.py` owns the default durable result projection.
- The v1 `MentorLoop` path remains unchanged and no fallback was added.

Complexity:

- `loop.py` increased from 1210 to 1395 lines without newly crossing the
  800-line threshold. The independent class preserves the planned owner but
  the file should be monitored; Task 8 must not add query behavior here.
- `judgments.py` is 765 lines, `compressor.py` is 198 lines, and the new
  end-to-end check is 256 lines.

Task 7 SHA-256:

- `scripts/loop.py`:
  `03652187eaba69481b2b2082f302c89aabc6761a50a7fb2b6b87aefb2bf29bbb`
- `scripts/judgments.py`:
  `07a069e939188efe036e50b83741120d9cc8ee8f3f79e85e28abfffa66cea1cd`
- `scripts/compressor.py`:
  `dc81ab043e3041fa12c403ce208e959e3cabbb0b64aafbcc718d88a3197b8cc5`
- `examples/autonomous_loop_checks.py`:
  `1fbf13f4a6caedf46f7d7f081aa743615eaf454dab915e89aea6507fa5351166`

## Task 8 Stateless Query and Teaching-Path Retirement

RED:

- `python3 examples/query_checks.py` failed because `scripts.query` did not
  exist.
- A follow-up RED showed that importing `scripts.cli` still loaded
  `scripts.mentor` through package-level aggregation.

GREEN:

- `python3 examples/query_checks.py`: 5/5 passed.
- Query reads the current topic version and leaves canonical bytes unchanged.
- Query creates no `.mentor-state`, learner profile, teaching action, or
  feedback state.
- CLI `ask` returns byte-equivalent JSON to `query`; `feedback` is not a
  default CLI command.
- Pure query import and execution do not load `scripts.mentor`.
- Default `smoke_run.py`, `eval_suite.py`, and `cli.py demo` passed without
  stateful teaching stages.
- All development and sandbox `examples/*_checks.py` entry points passed.
- Development and sandbox Task 8 files passed byte-for-byte `cmp`.
- No development or sandbox `__pycache__` directory was produced.

Retirement closure:

- Old main path: CLI `ask -> MentorLoop.begin_teaching` and `feedback`.
- Deleted from main path: stateful teaching/feedback CLI routing, default
  smoke/eval teaching assertions, and package-level imports that loaded
  `mentor.py`.
- Retained: `mentor.py`, teaching schema fields, and teaching CasePacks for the
  planned Task 10 one-way v1 importer only.
- Compatibility exception: `ask` remains for one vNext release as an exact
  alias of `query`, with no separate implementation or state mutation.
- Retirement trigger: remove `ask` before the first subsequent major version
  if no active external dependency is observed.

Architecture alignment:

- `query.py` is the sole stateless query owner.
- `knowledge_store.py` remains the canonical read owner.
- `ask` and `query` invoke the same function; no duplicate owner or fallback
  exists.
- Query behavior is outside autonomous convergence and cannot mutate it.

Task 8 SHA-256:

- `scripts/query.py`:
  `be66b38274464a86d20d4d6428d4f4177f83e71156dc0b2b1af09ce375c596f3`
- `scripts/cli.py`:
  `b16e60099f42d839f9cf57aedf1ed68c1d4b5dc7d846d1db16db56c86eef8727`
- `scripts/__init__.py`:
  `c710ed7fde7e2ae2e067e0ddad80f3dac2cf9b7a9f8235d77faa2b52489f794c`
- `examples/query_checks.py`:
  `8a5164e4833ecf5c86c1ddcc1b2e992b14e0d49373b73bccd2e8021c60ef33b4`
- `examples/smoke_run.py`:
  `56979868f69fe7803d9e13f05f1b6a3e47f82b777644a2d5e6645d219f1c62e0`
- `examples/eval_suite.py`:
  `2c249688eeae2052328b5bc38e776b9c4f179eccef3ff03c6eb3ce4ec680555d`
- `SKILL.md`:
  `57b6a4dcd7f7989b4f939bdf42bfef0db35ea43412b1beb67a8962831e196ebb`

## Task 9 Work-Host Contract TDD

RED:

- Initial `work_host_vnext_checks.py` failed because `--knowledge-root` and
  `--topic-id` were not global CLI arguments and JSON pending still used exit
  code 10.
- A second RED showed `state --json` lacked the common host envelope and the
  runtime session had not received its durable topic reference.

GREEN:

- `python3 examples/work_host_vnext_checks.py`: 5/5 passed.
- JSON pending, done, state, cancel, query, and error responses use one host
  metadata projection.
- Pending is process exit code 0 with `status: pending`; validation, state, and
  usage errors remain non-zero.
- Every host envelope includes `next_action`, resolved `knowledge_root`,
  `topic_id`, `request_path`, and named state/pending/request/judgment paths.
- `init` binds `topic_id`, resolved `knowledge_root`, and optimistic
  `base_version=1` before the first judgment is persisted.
- `sys.dont_write_bytecode = True` executes before local package imports; a
  copied Skill run without host bytecode environment variables produced no
  `__pycache__`.
- Skill instructions require protocol startup as the first business action and
  permit research tools only after `plan_investigation`.
- All development and sandbox focused checks, smoke, and eval passed.
- Development and sandbox Task 9 files passed byte-for-byte `cmp`.
- Frozen v1 source and global installation remained unchanged.

Compatibility:

- Global `--knowledge-root` and `--topic-id` placement is canonical.
- Query/ask still accept Task 8's documented post-subcommand option placement;
  both positions populate the same argparse fields and behavior.
- No fallback knowledge root exists.

Complexity:

- `cli.py` increased from 237 to 364 lines and remains below the 800-line
  review threshold. Host-envelope logic has one projection helper and one
  runtime-reference binding helper; monitor further growth during later CLI
  tasks.

Task 9 SHA-256:

- `scripts/cli.py`:
  `dfb6207bac5a67368206b2e01c21acdc00c9adc818045d0e56bc0513cba604b1`
- `SKILL.md`:
  `4c8422fb9fdfc28f95e200dbe6f36d33bd9293af3afe75bc624b7d4cd109eed3`
- `examples/work_host_vnext_checks.py`:
  `711171b8bfe2d786d06eed0e2b43c49d9f75f0b30c2912d9914708b830937984`
- `examples/work_host_contract_checks.py`:
  `f32f096ebc05433bb51f15d58d0d091dc0114cec9f4cc36f97cb10f7b585fad8`

## Task 10 One-Way v1 Import TDD

RED:

- Initial migration check failed because `scripts/migrate_v1.py` did not exist.
- Review-strengthened checks failed on unsupported `high/high` gap defaults.
- Deep corrupt-input checks failed on invalid timestamps and nested v1 field
  types.
- Enum checks failed because invalid evidence and teaching action values were
  still accepted.

GREEN:

- `python3 examples/migration_v1_checks.py`: 8/8 passed.
- Valid and partial v1 sessions create canonical vNext topics only through
  `KnowledgeStore`.
- Exact schema version, complete dataclass shape, nested types, enums, and
  non-empty evidence are validated before durable writes.
- Proposition, explanation, rules, evidence, counterexamples, open boundaries,
  and active gaps map deterministically.
- Unsupported teaching state and non-representable provenance remain inert
  canonical `migration_metadata`; convergence does not consume them.
- Imported gaps use low priority and low expected gain because v1 did not
  supply those judgments.
- Repeat import is rejected by default. Explicit re-import is allowed only
  while the current version equals the last importer-owned version.
- Source mutation before commit is rejected without creating a topic. A source
  change after a successful Store commit does not reverse the success result.
- Store errors propagate without wrapping or reclassification.
- All 20 frozen v1 `session.json` samples imported successfully in disposable
  temporary libraries, and every source remained byte-for-byte unchanged.

Regression and isolation:

- All 18 `examples/*_checks.py` entry points plus `smoke_run.py` and
  `eval_suite.py` passed in the development source.
- The same 20 entry points passed from the disposable sandbox installation.
- Development and sandbox Task 10 files passed byte-for-byte `cmp`.
- No `__pycache__` directory was produced.
- Frozen v1 hashes remained unchanged:
  - `scripts/schema.py`:
    `aab7b2cba366c849b46aeb6f2b9f6d05366fb8bf941fd33bf876fb8316b8bfd8`
  - `SKILL.md`:
    `1b16eb76ffbb4c93f6ffa2ba39961e73637f856bddf20ae77a73bc94ca34c5cf`

Architecture review:

- First review identified unsafe overwrite, broad input acceptance, provenance
  loss, invented gap priority, post-commit ambiguity, and error masking.
- ADR 0001 and the parent plan were updated before the repair.
- Two follow-up reviews verified the repairs. The final independent review
  reported no Critical or Warning findings.

Complexity:

- New owner `migrate_v1.py` is 733 lines after full legacy-shape validation,
  below the 800-line review threshold.
- Largest cohesive functions remain below the 80-line block threshold.
- No fallback or second durable writer was introduced.
- The v1 compatibility reader has an explicit retirement boundary; monitor
  importer growth and split validation only if another legacy schema appears.

Task 10 SHA-256:

- `scripts/migrate_v1.py`:
  `e528e373eea43b934f4bfaadd59feb8f8b822319b9125401335a8f045f59f35f`
- `scripts/knowledge_schema.py`:
  `aa772f1a552844f2e32936cca13f30e59e422ba956a2855026d349c5fb244010`
- `examples/migration_v1_checks.py`:
  `201008208a8038925138383d45032dfbe15ab2a1d00be8750dfc850b2587713d`
- `examples/fixtures/knowledge_first_cases.py`:
  `ef66c272b1451327bb81f39947d855568eb6142401cc523f3f336f08a9201e9a`
- `docs/aegis/adr/0001-one-way-v1-import-boundary.md`:
  `24ee8686dc3904fe6b70657fde10d988b956f8902f57968bd16dcd99265bd6cb`

## Task 11 Partial Validation

Strict TDD evidence:

- Initial RED: `/tmp/autonomous-mentor-vnext-task11-red.log` failed because
  the new `eval_vnext` owner did not exist.
- Semantic-fixture RED:
  `/tmp/autonomous-mentor-vnext-task11-specfix-red.log` rejected four renamed
  rainbow fixtures and implicit receipt generation.
- Gap-semantics RED:
  `/tmp/autonomous-mentor-vnext-task11-gap-semantics-red.log` rejected a
  condition gap resolved through a mechanism claim.

Implemented eval-only owners:

- `examples/eval_vnext_suite.py`
- `examples/realhost_vnext_profile.py`
- `examples/eval_vnext/{cases,artifacts,invariants,suite}.py`

Focused GREEN:

- Four semantic topic classes and two prose profiles each completed three
  durable cycles.
- The first two assessments were blocked by open high-value gaps.
- Every cycle committed a non-empty same-topic delta and one version.
- The final two post-baseline cycles were low gain; structural, evidence, and
  coverage gates passed before convergence.
- Gap resolution claims match mechanism, condition, and boundary facets.
- Recorded responses replayed through the canonical `KnowledgeStore`, with
  exact result and stable final-topic comparison.
- Invalid receipt hashes, missing or mismatched receipts, non-URL unfamiliar
  evidence, teaching stages, and extra or missing events were rejected.
- No bytecode cache was produced.

External-source evidence:

- Fetched `https://doi.org/10.1038/nature23288` after an investigation plan.
- The returned Nature abstract reports that nocturnal plant visits were
  reduced by 62% in artificially illuminated communities compared with dark
  areas.
- The fixture stores that exact excerpt, citation, retrieval time, and SHA-256
  receipt. The validator explicitly limits this to artifact-internal
  consistency and does not claim remote-source attestation.

Independent review:

- The first specification review found false domain fixtures and fabricated
  receipt text; both were fixed under RED.
- The second review found incorrect gap-to-claim semantics; it was fixed under
  RED.
- The final specification review confirmed the scripted and replay checks but
  correctly rejected them as proof of two independent model runs.

Blocked release evidence:

- No `claude`, `codex`, or `gemini` CLI is available in the current
  environment.
- All generated artifacts declare `artifact_origin: scripted_profile` and
  `external_model_call_verified: false`.
- Task 11 remains incomplete until two independent model hosts produce
  artifacts that pass `examples/realhost_vnext_profile.py`.
- All 21 development entry points, including `eval_vnext_suite.py`, passed
  after the semantic repairs.
- Frozen Skill aggregate tree hashes remained unchanged:
  - workspace Skill:
    `0cddcd3f580b30eeec332c34482fac200e0e214e2435b766b102531fe546c2df`
  - user-level Skill:
    `42d4f1f48ca8e8b67e64cc649b7c5759f2ae4fafc5709499ee800bf7c5136b7a`

Task 11 partial SHA-256:

- `examples/eval_vnext_suite.py`:
  `d378b844b29a4959bb4273a6de63534ae8febdc3b1c56f72049002a2c4ed9826`
- `examples/realhost_vnext_profile.py`:
  `00b8641ffa85bdc3d39cf209a2c2375bbcde6b273ab7783c9dc9992a6624f81a`
- `examples/eval_vnext/artifacts.py`:
  `89498cea6b62d335c0caca100abfe43fa893ffa0ad4e6dd689baabdf21ef21d3`
- `examples/eval_vnext/cases.py`:
  `2a764ae4501ea1eb13f0ba5bf6e6432b1a555663d7a722b675c1572044841f25`
- `examples/eval_vnext/invariants.py`:
  `475a2044b802cab83f7b9dcac91efd6e276baa962345454b883d6f62cc173e39`
- `examples/eval_vnext/suite.py`:
  `7301a43516ed27263f7f8e4311c5a8caa92979cf6dd10afb88d26636a7a82daf`

## Task 11 Supplied-Artifact Audit

The user supplied eight artifacts:

- Model A: `Gemini-3.1-Pro-Preview`
- Model B: `DeepSeek-V4-Pro`
- Cases per model: mechanism, concept, controversy, unfamiliar empirical

Replay result:

- `python3 examples/realhost_vnext_profile.py <8 artifacts>`: PASS.
- Every artifact consumed 14 events over three learning cycles.
- Every replay produced `open_high_value_gap`,
  `open_high_value_gap`, then `converged`, with gain sequence
  `medium`, `low`, `low`.
- The two models differ only in generated evidence identifiers; normalized
  behavioral profiles match on all four cases.

Acceptance result:

- `python3 examples/realhost_vnext_profile.py --compare-models <8 artifacts>`:
  FAIL as intended.
- Failure: `cross-model artifacts must use external_response_capture`.
- All supplied artifacts declare `artifact_origin: trae_code_session` and
  include model-authored `result` and `final_topic` values. The existing
  artifact format therefore proves deterministic replay but does not prevent a
  model from using a deterministic driver or copying a known profile.

Corrective validation owner:

- `examples/finalize_vnext_capture.py` accepts only provenance, initial topic,
  raw stage events, and source receipts. It generates `result` and
  `final_topic` locally through canonical replay.
- The formal comparator accepts only eight such
  `external_response_capture` / `raw_events_v1` artifacts, exactly two models,
  distinct session labels, all four cases per model, and identical normalized
  invariant profiles.
- Focused RED: missing comparator
  (`/tmp/autonomous-mentor-vnext-task11-cross-model-gate-red.log`) and missing
  raw-event finalizer (`/tmp/autonomous-mentor-vnext-task11-finisher-red.log`).
- Focused GREEN:
  `/tmp/autonomous-mentor-vnext-task11-cross-model-gate-green.log` and
  `/tmp/autonomous-mentor-vnext-task11-finisher-green.log`.

Task 11 is not accepted. Re-collection is required; the supplied artifacts
must not be relabeled or edited to satisfy the new origin contract.

Regression after the corrective validation work:

- 14/14 vNext checks passed, including schema, store, index rebuild, delta,
  convergence, autonomous loop, query, host, migration, smoke, eval, and
  `eval_vnext_suite.py`.
- No `__pycache__` or `.pyc` files exist under the vNext Skill.
- Current aggregate tree hashes:
  - frozen Skill:
    `270d7bed060882a89c4cd66a22fffb3942a72be03f5dd58ea3058ff751b3b218`
  - vNext Skill:
    `7ca5f0c339be74cc84c0175da267348d1d456372e5c2742ffb36ba64eef3287d`

## Task 11 Final Cross-Model Acceptance

Fresh raw captures were collected in distinct Trae Code sessions:

- Gemini-3.1-Pro-Preview: `gemini-task11-fresh`
- DeepSeek-V4-Pro: `deepseek-task11-fresh`
- Four cases per model: mechanism, concept, controversy, unfamiliar empirical
- Each raw capture contains exactly 14 stage events and no model-authored
  `result` or `final_topic`.

Local finalization:

```bash
python3 examples/finalize_vnext_capture.py \
  ../../validation/task11/raw-model-*/<case>.json \
  ../../validation/task11/final-model-*/<case>.json
```

All eight finalizations passed. Each final artifact declares
`artifact_origin: external_response_capture` and
`collection_protocol: raw_events_v1`.

Formal acceptance:

```bash
python3 examples/realhost_vnext_profile.py --compare-models \
  $(find ../../validation/task11/final-model-a \
    ../../validation/task11/final-model-b -type f -name '*.json' | sort)
```

Result: PASS. The gate replayed 8 artifacts, confirmed both declared models,
their distinct session labels, all four required cases per model, and equal
normalized invariant profiles. Every artifact passed the three-cycle shape:
`open_high_value_gap`, `open_high_value_gap`, `converged`; gain sequence:
`medium`, `low`, `low`.

Fresh full regression: 14/14 vNext checks passed after acceptance. No
`__pycache__` or `.pyc` files were created. Frozen Skill aggregate hash remains
`270d7bed060882a89c4cd66a22fffb3942a72be03f5dd58ea3058ff751b3b218`.

Limit: the protocol proves raw-event shape, local replay, provenance
declarations, and cross-model behavioral agreement. It does not cryptographically
attest that Trae invoked either remote provider.

## Task 12 Sandbox Recovery and Release Gate

Strict TDD:

- RED: `examples/package_vnext_checks.py` initially failed with
  `Task 12 RED: sandbox recovery and validation manifest are not implemented`.
- GREEN:
  `python3 examples/package_vnext_checks.py` passed all five release-gate
  assertions.

Covered by the GREEN command:

- Rebuilt the disposable sandbox only from the vNext development source.
- Ran all 14 vNext checks from the installed sandbox copy.
- Ran a three-cycle mechanism learning case from the sandbox `workspace/`
  with explicit sandbox `knowledge/`; it converged at durable version 4.
- Deleted `index.json` and topic `summary.md`, then rebuilt byte-equivalent
  projections from canonical `knowledge.json`.
- Excluded `.mentor-state`, bytecode caches, and absolute user paths from the
  sandbox package.
- Verified development and sandbox eligible package trees share SHA-256
  `7338788c6daeec83f8e2d6a03bd3c1346a6bea6310ea0884ad718dda32e28b39`.
- Verified frozen workspace and user-level installation hashes remained:
  `741c36607cffc03972897aa676604678412a005ece59f039a6ab148d2130bb6f`
  and
  `908eff7b8fc5350e322673687645df6bfa4b095715c522ee3e67e18305b4dfa6`.

The canonical validation manifest is
`skill/autonomous-mentor/sessions/knowledge-first-vnext/validation_manifest.json`
with SHA-256
`159a869528fa0058a61d3954dd4434f7f56b601f90fb348e3ba3c42048c0868d`.

No ZIP was generated and no user-level installation was changed. Per the
approved plan, ZIP generation requires explicit user approval after review of
this evidence.

## Task 12 Approved Archive

After explicit approval to generate only the archive, the ZIP was created from
the verified sandbox package:

- Archive:
  `dist/autonomous-mentor-vnext-2026-09-17.zip`
- SHA-256:
  `6bd00076db3b096b01d8fb391d2f4dfdc6595c31105b9e3dc29845982aadaf09`
- Archive entries: 71

Archive-level verification passed:

- No `__MACOSX`, `.mentor-state`, `__pycache__`, or `.pyc` entries.
- The archived manifest records `zip_generated: true` and the approved
  archive name.
- A fresh extraction has the same eligible content-tree hash as the validated
  sandbox package.
- `python3 examples/smoke_run.py` passed from the extracted package without
  bytecode output.

No installation, replacement, or modification of the frozen workspace Skill
or user-level Skill occurred.

## M0 Entry Truth Baseline

Scope: baseline-only architecture governance. No public CLI implementation,
schema, storage, package, frozen Skill, or user-level installation was changed.

Artifacts:

- `docs/aegis/specs/2026-09-18-m0-entry-truth-brief.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `skill/autonomous-mentor/examples/cli_route_baseline_checks.py`

Strict TDD:

- RED: the new checker loaded the golden fixture and failed intentionally with
  `M0 RED: CLI route fixture loads, but route and command checks are not
  implemented`.
- GREEN:

```bash
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
```

Result: exit 0, four assertions passed:

1. AST source routing matches the fixture: `init`, `learn`, `step`, `cancel`,
   and `state` resolve through `_run_legacy()` / `MentorLoop` or `StateStore`;
   `query` and `ask` call `query_knowledge()` with `KnowledgeStore`; `demo`
   reaches `smoke_run.main()`.
2. `cli.py --help` exposes exactly the eight fixture command names.
3. `cli.py demo` exits 0 and emits `vNext smoke passed`.
4. Isolated missing-topic `query` and `ask` both exit 1, emit identical JSON,
   and create no `.mentor-state`.

Related regression commands:

```bash
python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
```

Both passed 5/5 before the baseline checker was added. Final fresh replay is
recorded after the documentation update:

```bash
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Result: all three Python commands exited 0 (`4/4`, `5/5`, and `5/5`
respectively); the bytecode scan had no output.

Baseline alignment:

- Product / Requirement Baseline: aligned. Durable knowledge remains the vNext
  core and no teaching behavior was added to the query path.
- Architecture / Runtime Boundary Baseline: drift recorded, not repaired:
  public learning commands still instantiate `MentorLoop`; vNext durable
  learning is the approved future default in ADR 0002.

Retirement track:

- No code retired in M0.
- M0.5 must remove `MentorLoop` from public learning default paths without a
  silent fallback, subject to separately approved host recovery and durable
  initialization acceptance.

## M0.5 Task 1 RED: Durable Origin and Runtime Cursor

Strict TDD contract:

- Input: a complete durable topic fixture and an M0.5 runtime coordinator.
- Expected behavior: optional `origin_metadata` round-trips in
  `TopicKnowledge`; `HostRun` and `PendingCursor.initialize_topic()` form the
  initial validated host cursor.
- Compatibility boundary: legacy topic fixtures remain valid without
  `origin_metadata`; no production CLI path changes in this RED step.

Command:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
```

Result: exit 1, expected failure:

```text
AssertionError: M0.5 RED: missing scripts.autonomous_runtime host runtime contract
```

The failure was caused by `ModuleNotFoundError:
scripts.autonomous_runtime`, which proves the test reaches the intended missing
owner rather than failing because of fixture setup or an unrelated import.
No production source was changed.

## M0.5 Task 1 GREEN: Durable Origin and Runtime Cursor

Implemented:

- Optional `TopicKnowledge.origin_metadata`; omitted on serialization when an
  existing topic did not declare it, so legacy fixture shape is unchanged.
- `scripts/autonomous_runtime.py` with validated `HostRun` and
  `PendingCursor` value objects. They require canonical absolute knowledge
  roots, canonical UUID run IDs, supported runtime kinds/stages, JSON-safe
  stage-local payloads, and reject a copied durable topic graph.

Focused GREEN:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
```

Result: exit 0, five checks passed: optional provenance round-trip, UUID and
canonical-root validation, initialization cursor shape, full-topic rejection,
and malformed identity/stage rejection.

Related regression:

```bash
python3 skill/autonomous-mentor/examples/knowledge_schema_checks.py
python3 skill/autonomous-mentor/examples/knowledge_store_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Result: all Python commands exited 0 (`7/7`, `9/9`, and `8/8`); the bytecode
scan had no output.

Repair note: the expanded focused test initially raised `NameError` in its own
module-level error helper because `RuntimeContractError` was imported locally
inside `main()`. The production runtime had correctly rejected the copied
topic. The helper now receives the expected error type explicitly; no runtime
contract logic changed for that repair.

Scope held:

- No `KnowledgeStore.create()` call, topic initialization, pending-file write,
  public CLI dispatch, or `MentorLoop` route changed.
- `origin_metadata` is distinct from importer-owned `migration_metadata` and
  is not consumed by convergence.

## M0.5 Task 2 RED: Durable Topic Initialization

Command:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
```

Result: exit 1, expected failure:

```text
ImportError: cannot import name 'HostRuntimeCoordinator'
```

The focused check reached the missing initialization coordinator API. It did
not fail because of its temporary knowledge root, fixture, or store setup.

## M0.5 Task 2 GREEN: Idempotent Durable Topic Initialization

Implemented:

- A public-host-only `initialize_topic` judgment request and validator. Its
  response requires normalized title/proposition, two or more unique coverage
  dimensions, and complete claims/evidence/gaps/counterexamples collections.
- `HostRuntimeCoordinator`, which verifies a cursor against its explicit
  `KnowledgeStore` root, validates the seed before any write, and creates only
  a version-1 `TopicKnowledge` with `origin_metadata.host_run_id`.
- Same-run version-1 retry recognition. An unrelated existing topic cannot be
  overwritten, and an invalid seed cannot create a partial topic.

Focused GREEN:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
```

Result: exit 0, 9/9 checks passed. Coverage includes initialization request
shape, invalid cross-reference rollback, normalized version-1 creation,
same-run idempotency, and unrelated-topic rejection.

Related regression:

```bash
python3 skill/autonomous-mentor/examples/knowledge_schema_checks.py
python3 skill/autonomous-mentor/examples/knowledge_store_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Result: all Python commands exited 0 (`7/7`, `9/9`, and `8/8`); the bytecode
scan had no output.

Task 2 SHA-256:

- `scripts/judgments.py`:
  `f538243a605955ec16ab2ea03c76dc7ad55bdea990b79da5fb9196fc45cb4a12`
- `scripts/autonomous_runtime.py`:
  `8bafba99209482128fc31e3a94f8e25be5f5f1c8312a8937b0a512da72dd2f98`
- `examples/vnext_host_recovery_checks.py`:
  `c168c69add12618fdb1c6a9dbb1ace4a95850bdd2f0602e1184cbd3d450ee735`

Scope held:

- No public CLI dispatch, legacy `MentorLoop` path, archive, frozen Skill, or
  user-level installation changed.
- Direct `AutonomousLearningLoop` `anchor` behavior remains untouched.

## M0.5 Task 3 RED/GREEN: Resumable Stage Progression

RED:

- The focused recovery check was extended with a wished-for
  `HostRuntimeCoordinator.begin_learning()` API and failed because that API
  did not exist. This isolated the missing runtime transition owner rather than
  a fixture or storage setup failure.

GREEN:

- `HostRuntimeCoordinator` owns `map_knowledge`, deterministic gap selection,
  planning, integration, skeptic review, durable commit, convergence
  assessment, and checkpoint/continue projection.
- Every agent-owned stage validates its response before projecting the next
  cursor. Cursor payloads carry only stage-local context; the canonical topic
  is always reloaded from `KnowledgeStore`.
- `commit_learning` derives a stable SHA-256 marker from the uncommitted
  payload. It either applies one optimistic versioned delta or recognizes the
  matching latest durable convergence record after a post-save interruption.
- `AutonomousLearningLoop.run(topic_id)` remains compatible as a thin scripted
  adapter over the coordinator. Its legacy-compatible `anchor` request and
  trace are retained, while stage ownership and durable commit ordering move to
  `autonomous_runtime.py`.

Fresh verification:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
python3 skill/autonomous-mentor/examples/autonomous_loop_checks.py
python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
python3 skill/autonomous-mentor/examples/knowledge_schema_checks.py
python3 skill/autonomous-mentor/examples/knowledge_store_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Result: all eight Python commands exited `0`. The recovery check passed 12/12,
the autonomous loop check passed 5/5, host and query checks passed 5/5 each,
the route baseline passed 4/4, schema/store/migration passed 7/7, 9/9, and
8/8, respectively. The bytecode scan had no output.

Task 3 SHA-256:

- `scripts/autonomous_runtime.py`:
  `2a41baf5cfa7f1513436c525cb2dde1ef5c2b6da99ac8c3ec2c93615ab7911fa`
- `scripts/loop.py`:
  `5f926bac12975ffd0134f76ee53af9f6fcb8afbd5e96a066ce4fb10d9184e2e7`
- `examples/vnext_host_recovery_checks.py`:
  `0a7b5adb4a46057810c6cdacb8e026fab8b930520e338053630a343ef77d51ce`

Scope held:

- No public CLI dispatch, legacy `MentorLoop` route, archive, frozen Skill, or
  user-level installation changed.
- The pending cursor is currently represented as a validated value object;
  Task 4 is responsible for binding it to public host runtime files.

## M0.5 Task 4 RED/GREEN: Public vNext Host Route

RED:

- The public Work-host check was extended to require an
  `initialize_topic` request from `init`. It failed because the legacy public
  dispatcher emitted its former anchor request.
- The route-baseline checker was then updated to require `VNextHost` owners and
  no `MentorLoop` reference. It failed against the intentionally stale legacy
  golden fixture.
- A final public invalid-seed case failed because an
  `RuntimeContractError` escaped the CLI instead of producing the JSON error
  envelope.

GREEN:

- New `scripts/vnext_host.py` is the sole file-host adapter. It writes only
  runtime JSON through `StateStore` primitives; all durable topic writes remain
  inside `HostRuntimeCoordinator` and `KnowledgeStore`.
- `session.json` now contains a validated `HostRun`; `pending.json` contains a
  validated `PendingCursor`; `request.json` is regenerated from the cursor.
- Public `init`, `learn`, `step`, `cancel`, and `state` dispatch through
  `VNextHost`. Initialization produces the public-only durable seed request,
  a valid response creates topic version 1, and learning advances one pending
  judgment at a time.
- Invalid coordinator responses are translated to `VNextHostError`, preserving
  the JSON error exit class and the still-correctable pending cursor.
- `cli.py` no longer imports or instantiates `MentorLoop`, and no longer
  contains `_run_legacy` or `_bind_runtime_reference`. `demo` remains the
  explicit fixture-owned smoke command only.
- The M0 route golden fixture now names the vNext owners after public source
  and command behavior passed.

Fresh verification:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
python3 skill/autonomous-mentor/examples/autonomous_loop_checks.py
python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
grep -R -n -E 'MentorLoop|_bind_runtime_reference|_run_legacy' \
  skill/autonomous-mentor/scripts/cli.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Result: all six Python commands exited `0`; recovery passed 12/12, autonomous
loop 5/5, Work-host 5/5, query 5/5, migration 8/8, and route baseline 4/4.
The legacy-reference scan and bytecode scan had no output.

Task 4 SHA-256:

- `scripts/vnext_host.py`:
  `8a0723c28641d0fa366c1f499b234596760dd93d478d0f07bc49d15d9852878b`
- `scripts/cli.py`:
  `c2ccc8602be08bc43177bfc2b6f0c08923c279ba3818ddb359c14cbbbfd8dbf1`
- `examples/work_host_vnext_checks.py`:
  `39ae52c929a399e089864e6ad01571c0c76d92d91ce3bae54abc80e0fdea5b4b`
- `examples/cli_route_baseline_checks.py`:
  `c552783c53ea725b6cc4db59525a4dd65e8a329ed551085cee3ef2b1eece1a88`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`:
  `330c023db735ced3eb0c0eaa216b58b58549046b0e2de6a6660430cece157abf`

Retirement boundary:

- Retired from the public path: legacy `MentorLoop` dispatch, its legacy
  pending/session body, and `_bind_runtime_reference`.
- Retained: legacy source and `demo` fixture smoke only; no legacy session is
  read, migrated, or deleted by vNext public commands.
- Trigger: Task 5 verifies isolation and documents the later read-only
  compatibility-window retirement decision. No persistent user data was
  deleted.

## M0.5 Task 5: Isolated Regression, ADR, and Retirement Verification

Development isolation:

```bash
python3 /Users/bytedance/主动学习skill/workspaces/autonomous-mentor-vnext/skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
python3 /Users/bytedance/主动学习skill/workspaces/autonomous-mentor-vnext/skill/autonomous-mentor/examples/autonomous_loop_checks.py
python3 /Users/bytedance/主动学习skill/workspaces/autonomous-mentor-vnext/skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 /Users/bytedance/主动学习skill/workspaces/autonomous-mentor-vnext/skill/autonomous-mentor/examples/query_checks.py
python3 /Users/bytedance/主动学习skill/workspaces/autonomous-mentor-vnext/skill/autonomous-mentor/examples/migration_v1_checks.py
python3 /Users/bytedance/主动学习skill/workspaces/autonomous-mentor-vnext/skill/autonomous-mentor/examples/cli_route_baseline_checks.py
```

The commands were launched from an empty `/tmp` caller directory. All six
exited `0`: recovery 12/12, autonomous loop 5/5, Work-host 5/5, query 5/5,
migration 8/8, and route baseline 4/4.

Sandbox isolation:

- Fresh root: `/tmp/autonomous-mentor-m05-task5.7EDYTM`.
- Copied only the development `skill/autonomous-mentor` and the required
  `docs` authority tree into that root.
- From the sandbox copy, `vnext_host_recovery_checks.py`,
  `work_host_vnext_checks.py`, and `cli_route_baseline_checks.py` each exited
  `0` (12/12, 5/5, and 4/4).
- The sandbox Work-host flow used its own temporary caller and explicit
  sandbox knowledge root. No `__pycache__` or `.pyc` appeared under the
  sandbox Skill.

ADR and baseline sync:

- ADR 0002 action: amend. The accepted decision is now implemented: public
  learning commands route through `VNextHost`, which delegates to
  `HostRuntimeCoordinator`; `AutonomousLearningLoop` remains the direct
  scripted adapter over the same semantics.
- Baseline sync: updated ADR status/current-owner description and retained
  `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json` as the current public
  route matrix.
- Retirement trigger remains unchanged: remove legacy learning-path references
  and adapter-only tests only after a defined read-only compatibility window.

Retirement verification:

```bash
grep -R -n -E 'MentorLoop|_bind_runtime_reference|_run_legacy' \
  skill/autonomous-mentor/scripts/cli.py
find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc'
```

Both scans had no output. `cli.py` references only `VNextHost` for public
learning commands and `_run_demo` for the fixture-owned smoke command.
`migrate_v1.py` retains only `SessionState` parsing for one-way legacy input;
it does not instantiate `MentorLoop`.

Frozen boundary verification:

- Frozen workspace Skill tree SHA-256:
  `0cddcd3f580b30eeec332c34482fac200e0e214e2435b766b102531fe546c2df`.
- User-level Skill tree SHA-256:
  `4a6048c67d92a1ed7f49e539c84ed1c44fc6d6209e1d501b3c280529b11d6997`.
- No archive, frozen Skill, user-level Skill, legacy source, or persistent
  user knowledge was modified by M0.5 Task 5.

Baseline alignment:

- Product / requirement: aligned. Public initialization is durable and
  resumable, learning advances a single judgment per exchange, and query/ask
  remain stateless.
- Architecture / runtime boundary: aligned. `VNextHost` is the public
  file-host adapter, `HostRuntimeCoordinator` owns transitions and durable
  commit ordering, and `KnowledgeStore` remains the only durable topic writer.
- Residual risk: external consumers that depended on the legacy inner
  `state.state` shape must migrate to the documented vNext host-run reference;
  the outer host envelope and exit classes are preserved.

### Git Integration Baseline Revalidation

Git baseline `b433904` was independently revalidated after canonical source
and Aegis records were committed:

```bash
# Launched from a fresh /tmp caller
python3 /Users/bytedance/主动学习skill/skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
python3 /Users/bytedance/主动学习skill/skill/autonomous-mentor/examples/autonomous_loop_checks.py
python3 /Users/bytedance/主动学习skill/skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 /Users/bytedance/主动学习skill/skill/autonomous-mentor/examples/query_checks.py
python3 /Users/bytedance/主动学习skill/skill/autonomous-mentor/examples/migration_v1_checks.py
python3 /Users/bytedance/主动学习skill/skill/autonomous-mentor/examples/cli_route_baseline_checks.py
```

All commands exited `0`: recovery 12/12, autonomous loop 5/5, Work-host 5/5,
query 5/5, migration 8/8, and route baseline 4/4.

Fresh sandbox root `/tmp/autonomous-mentor-m05-task5-git.pzjTTc` copied the
committed Skill and `docs/aegis` authority tree. Its recovery, Work-host, and
route checks exited `0` (12/12, 5/5, and 4/4). The sandbox bytecode scan had no
matches. A first chained sandbox command reported non-zero only because an
empty `find` result exits `1`; individual command exit checks confirmed the
actual product checks were green. The final negative checks found neither
bytecode nor `MentorLoop`, `_run_legacy`, or `_bind_runtime_reference` in the
public CLI.

Retirement decision is unchanged: public legacy dispatch is retired
delete-first; legacy source and one-way v1 parsing remain a read-only
compatibility retention until the ADR 0002 trigger is explicitly planned.
