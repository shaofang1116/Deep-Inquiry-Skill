# Post-M0.5 Compatibility Window and Legacy Retirement Plan

## Status

Draft plan. It archives the remaining work after M0.5 and requires an explicit
execution approval before any runtime, public command, or legacy source change.
It does not authorize source deletion, package installation, or persistent-data
mutation.

## Goal

Close the M0.5 compatibility window with evidence, then reduce retained legacy
code without reintroducing a second learning owner or breaking the explicit v1
import boundary.

## Historical Analysis

The shared proposal identified five themes: establish a route baseline, add a
host adapter, protect knowledge quality, separate compatibility responsibilities,
and layer evaluation assets. Their current disposition is:

| Historical theme | Current disposition | Evidence |
| --- | --- | --- |
| Route baseline and unique default path | Complete | M0 route fixture and ADR 0002 |
| Host adapter and resumable public execution | Complete | `VNextHost`, `HostRuntimeCoordinator`, M0.5 checks |
| Durable knowledge / source-of-truth boundary | Complete for this scope | `KnowledgeStore`, `TopicKnowledge`, one-way v1 importer |
| Compatibility and legacy retirement | Remaining | ADR 0002 read-only compatibility-window trigger |
| Evaluation asset layering | Deferred | historical evaluator evidence remains, but is not public-path behavior |

The historical proposal's immediate M0 work is already complete. Its remaining
valid concern is not a new facade or schema merge: it is proving that retained
compatibility has no active dependency before removing it.

## Architecture

- `VNextHost` remains the only public file-host adapter.
- `HostRuntimeCoordinator` remains the only public learning-stage and durable
  commit-order owner.
- `KnowledgeStore` remains the only durable topic writer.
- `query_knowledge` remains the stateless read owner.
- `SessionState` remains read-only importer input until a dedicated v1 parsing
  boundary replaces it.
- `MentorLoop`, `mentor.py`, teaching judgments, and historical evaluator cases
  are not public learning owners. They are retirement candidates, not fallback
  implementations.

## Tech Stack

Python 3.10+ standard library, canonical JSON files, existing focused example
checks, Git integration baseline, and no model SDK or telemetry service.

## Baseline / Authority Refs

- `docs/aegis/adr/0001-one-way-v1-import-boundary.md`
- `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- `docs/aegis/specs/2026-09-18-m0-cli-route-golden.json`
- `docs/aegis/specs/2026-09-18-m05-host-recovery-design.md`
- `docs/aegis/plans/2026-09-18-m05-host-recovery-implementation.md`
- Git baseline `b433904` and revalidation `06e9ff7`

## Facts, Assumptions, and Unknowns

### Facts

- Public `init`, `learn`, `step`, `cancel`, and `state` use `VNextHost`.
- Public `query` and `ask` are currently byte-equivalent stateless reads.
- Public `demo` is a fixture-owned smoke command.
- The public CLI contains no `MentorLoop`, `_run_legacy`, or
  `_bind_runtime_reference`.
- `migrate_v1.py` validates `SessionState` as read-only input; it does not
  instantiate `MentorLoop`.
- `MentorLoop` and historical teaching evaluators remain in `loop.py`,
  `mentor.py`, `judgments.py`, `schema.py`, and legacy example checks.

### Assumptions

- The compatibility window needs a documented duration and observation record
  before public alias or legacy-support retirement.
- No active external dependency has yet been demonstrated.

### Unknowns That Block Deletion

- Which release/version constitutes the promised one-release window for `ask`.
- Whether any external CLI consumer reads the former inner `state.state` shape.
- Whether historical evaluators are required as long-term compatibility
  evidence, or can be archived after their v1 importer coverage is retained.
- Whether v1 import can be preserved with a narrow parser that no longer
  imports the full teaching-era runtime schema.

Unknown dependency is not active dependency evidence. It does not justify
retaining a second public owner, but it does require an explicit observation
window before changing a documented public alias.

## Compatibility Boundary

- No public fallback to `MentorLoop`, legacy pending files, or project-local
  knowledge may be added.
- Existing legacy sessions are never migrated, read, or deleted implicitly.
- The v1 importer remains explicit, one-way, and source-read-only.
- `query` semantics remain unchanged while `ask` exists.
- No frozen Skill, user-level Skill, ZIP, archive, or persistent user knowledge
  is modified by observation or retirement planning.

## Architecture Integrity Lens

- Invariant: one public learning owner, one durable topic writer, and no legacy
  runtime state as a public source of truth.
- Canonical owner / contract: `VNextHost -> HostRuntimeCoordinator ->
  KnowledgeStore`.
- Responsibility overlap: `SessionState` currently serves both historical
  teaching runtime and v1 importer parsing; this must be separated before
  deleting the runtime schema.
- Higher-level simplification: extract a narrow immutable v1 import record if
  evidence supports it, instead of retaining the full legacy state machine.
- Retirement / falsifier: any public CLI reference to `MentorLoop`, or any
  importer behavior regression after narrowing its input parser, blocks
  retirement.
- Verdict: observe first; do not delete code in the compatibility-window setup.

## Plan Pressure Test

- Owner / contract / retirement: M0.5 public ownership is complete; remaining
  work touches compatibility and retirement only.
- Architecture integrity / higher-level path: parser extraction is preferable
  to preserving the full teaching runtime, but only after importer fixture
  coverage proves the required field set.
- Verification scope: command-level route checks, importer fixtures, isolated
  sandbox checks, and an explicit compatibility observation receipt.
- Task executability: observation setup can proceed independently; source
  retirement is gated by measured/recorded evidence.
- Pressure result: proceed with the observation plan; pause before deletion.

## Plan-Time Complexity Check

- Target files: potential future changes to `migrate_v1.py`, `schema.py`,
  `loop.py`, `judgments.py`, `mentor.py`, `cli.py`, and historical examples.
- Existing size / shape signals: `loop.py` is 1,364 lines, `judgments.py` is
  853 lines, and `schema.py` is 846 lines.
- Owner fit: compatibility observation belongs in documentation and route tests;
  future v1 parsing belongs in a dedicated importer DTO/parser, not in
  `VNextHost` or `cli.py`.
- Add-in-place risk: deleting teaching branches from the large legacy files
  before extracting importer input would conflate import compatibility with
  runtime removal.
- Better file boundary: add a narrow v1 import record/parser only if Task 2
  evidence proves the schema split; otherwise retain the existing parser.
- Recommendation: document and observe first; later add an owner file, then
  delete legacy runtime code in a separate approved slice.

## Tasks

### 1. Establish the Read-Only Compatibility Window

**Files**

- Create: `docs/aegis/work/2026-09-21-compatibility-window/10-intent.md`
- Create: `docs/aegis/work/2026-09-21-compatibility-window/20-checkpoint.md`
- Create: `docs/aegis/work/2026-09-21-compatibility-window/90-evidence.md`
- Modify: `docs/aegis/adr/0002-vnext-default-entry-retirement.md`

**Why**

The existing ADR has a retirement trigger but no window duration, observation
method, or completion receipt. Those are required before deciding whether public
compatibility remains needed.

**Impact / Compatibility**

Documentation-only. No command, source, package, or persistent state changes.

**Steps**

1. Record the window start from the approved execution date, its release/version
   boundary, and the named compatibility surfaces: `ask`, former
   `state.state`, v1 importer input, and historical evaluator assets.
2. Define a read-only observation receipt: caller/source identifier when
   available, command name, public envelope version, whether deprecated
   surfaces were requested, and a redaction rule that excludes proposition and
   knowledge content.
3. State that absence of evidence is sufficient only after the declared window
   closes; an observed dependency creates a separately documented
   `compat-exception` with migration target and retirement date.
4. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
   python3 skill/autonomous-mentor/examples/query_checks.py
   ```

   Expected: public owners and `ask` alias behavior remain unchanged.
5. Commit only the work records and ADR clarification.

### 2. Prove the Minimum v1 Import Input Surface

**Files**

- Create: `skill/autonomous-mentor/examples/v1_import_surface_checks.py`
- Modify: `skill/autonomous-mentor/examples/migration_v1_checks.py`
- Potentially create: `skill/autonomous-mentor/scripts/v1_import_record.py`
- Potentially modify: `skill/autonomous-mentor/scripts/migrate_v1.py`

**Why**

`SessionState` is currently imported by the v1 importer. A retirement decision
cannot distinguish parser-required fields from teaching-runtime-only fields
until that dependency is measured by executable fixtures.

**Impact / Compatibility**

The importer must preserve all current valid/partial/corrupt v1 outcomes,
immutable source-hash protection, and evolved-topic overwrite rejection.
`SessionState` remains untouched until the new checks prove parity.

**Steps**

1. Write a RED fixture matrix containing every v1 field consumed by
   `migrate_v1.py`, plus teaching-only fields that must be ignored as inert
   provenance.
2. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/v1_import_surface_checks.py
   ```

   Expected: fail because the explicit importer surface contract does not yet
   exist.
3. Implement only a pure input-surface report/check; do not replace
   `SessionState` parsing in this task.
4. Run:

   ```bash
   python3 skill/autonomous-mentor/examples/v1_import_surface_checks.py
   python3 skill/autonomous-mentor/examples/migration_v1_checks.py
   ```

   Expected: both exit 0 and preserve all existing importer cases.
5. Commit the checks and report separately from any code deletion.

### 3. Decision Gate: Retain, Extract, or Retire

**Files**

- Modify: `docs/aegis/adr/0002-vnext-default-entry-retirement.md`
- Modify: `docs/aegis/work/2026-09-21-compatibility-window/20-checkpoint.md`
- Modify: `docs/aegis/work/2026-09-21-compatibility-window/90-evidence.md`
- Potentially create: `docs/aegis/adr/0003-v1-import-parser-extraction.md`

**Why**

Retirement must be based on observed dependency evidence, not a calendar-only
assumption or an unbounded compatibility exception.

**Impact / Compatibility**

This is a decision-only gate. It does not delete source, archives, user
sessions, or durable knowledge.

**Steps**

1. At window close, inspect the observation receipt and importer surface report.
2. Classify each retained surface:
   - `ask`: retire only when the declared release window closes without active
     external dependency evidence.
   - `SessionState`: extract a narrow v1 importer record if it carries
     non-runtime import data; otherwise retain the parser with a new trigger.
   - `MentorLoop` and teaching evaluators: retire only after the importer has no
     runtime dependency and historical evidence has an archive disposition.
3. Record exactly one outcome per surface: `delete-first`, `compat-exception`,
   or `defer with evidence gap`.
4. Amend ADR 0002 or create ADR 0003 only if the outcome changes canonical
   ownership or introduces the parser boundary.
5. Do not execute source deletion in this decision task.

### 4. Execute Approved Retirement Slices

**Files**

- Determined by Task 3 only; expected candidates include `cli.py`, `SKILL.md`,
  `migrate_v1.py`, `schema.py`, `loop.py`, `mentor.py`, `judgments.py`, and
  legacy example files.

**Why**

Each retirement class has a different proof obligation. A single broad delete
would risk breaking v1 import or historical auditability.

**Impact / Compatibility**

This task may touch public commands and contract-carrying code. It requires a
new approved strict-TDD implementation plan for each selected deletion slice.
Persistent user state is out of scope and may not be deleted.

**Steps**

1. Create a dedicated plan for the selected decision outcome before source
   edits.
2. For `ask`, write a route RED case that expects the command to be absent
   while `query` remains stateless.
3. For parser extraction, write importer parity RED cases before changing
   `migrate_v1.py` or `schema.py`.
4. For legacy runtime removal, write source and behavior negative checks proving
   no remaining public/default reference and no importer dependency.
5. Re-run the full M0.5 suite, importer surface suite, and a fresh sandbox
   acceptance before committing the retirement slice.

## Verification

Before declaring any retirement slice complete:

```bash
python3 skill/autonomous-mentor/examples/vnext_host_recovery_checks.py
python3 skill/autonomous-mentor/examples/autonomous_loop_checks.py
python3 skill/autonomous-mentor/examples/work_host_vnext_checks.py
python3 skill/autonomous-mentor/examples/query_checks.py
python3 skill/autonomous-mentor/examples/migration_v1_checks.py
python3 skill/autonomous-mentor/examples/cli_route_baseline_checks.py
```

Run the relevant new compatibility-window and v1-import-surface checks, then
repeat the selected checks from a fresh sandbox with an explicit knowledge root.
The bytecode scan must be empty:

```bash
if find skill/autonomous-mentor -type d -name __pycache__ -o -type f -name '*.pyc' | grep -q .; then
  exit 1
fi
```

## Risks and Rollback

- Risk: an external client depends on `ask` or old state shape. Mitigation:
  retain only through a documented `compat-exception` with a migration target;
  do not silently reintroduce legacy dispatch.
- Risk: parser extraction loses a v1 edge case. Mitigation: freeze the importer
  surface matrix and keep `migration_v1_checks.py` as the parity authority.
- Risk: deleting tests hides historical behavior without preserving audit
  evidence. Mitigation: record an archive disposition before deleting
  evaluator-only fixtures.
- Risk: large legacy files encourage broad edits. Mitigation: split parser
  extraction from runtime removal and require dedicated plans.
- Rollback: restore only the immediately preceding source commit if a focused
  or sandbox acceptance fails. Do not alter frozen Skills, user installations,
  or durable user knowledge.

## Retirement

Anti-Entropy Declaration:

- Deletion Class: `code-retirement` and `contract-carrying code`.
- Old Path/Object: `ask` alias, teaching-era `MentorLoop` runtime, and
  evaluator-only teaching assets, each evaluated independently.
- New Canonical Owner: `VNextHost`, `HostRuntimeCoordinator`,
  `KnowledgeStore`, `query_knowledge`, and a future narrow v1 parser if needed.
- Expected Preserved Behavior: vNext public learning, stateless `query`,
  explicit one-way v1 import, and durable topic history.
- Expected Retired Behavior: legacy public state/session learning and
  teaching-era default execution.
- External Boundary Touched: yes.
- Source-of-Truth Data Risk: none for source retirement; persistent user data
  is explicitly out of scope.
- User Confirmation Required: no for source-only retirement after a separately
  approved plan; yes for any future persistent-state deletion.

## Completion Boundary

This planning artifact is complete when it has been reviewed and committed. It
does not complete the compatibility window or authorize any retirement slice.
