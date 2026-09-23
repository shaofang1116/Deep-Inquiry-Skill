---
name: "deep-inquiry"
description: "Use when the user wants autonomous deep learning, skeptic-reviewed convergence, durable knowledge accumulation, or a stateless query over learned knowledge."
---

# Deep Inquiry

Deep Inquiry actively learns, challenges, and converges around one **central proposition**, then stores durable knowledge. Learning is driven by high-value knowledge gaps and marginal return. Optional queries only read stored knowledge: they do not model a user or decide whether learning is complete.

The complete specifications are in `docs/superpowers/specs/`. This file defines the behavioral entry point and non-negotiable protocol rules. `SKILL.zh-CN.md` is its Chinese companion; this English document is canonical.

## Mandatory Execution Gate After Triggering

**This section overrides convenience, one-shot-answer habits, and the host's default research flow. Loading this Skill is not executing this Skill.**

After this Skill is triggered, the host must obey all of the following:

1. **The first non-Skill tool call must start the CLI file protocol.** For a new proposition run:
   `python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<global knowledge root>" --topic-id "<topic-id>" init "<central proposition>"`.
   Do not call `WebSearch`, `WebFetch`, Read, Write, a canvas, or another research/output tool first; do not answer directly; do not use `mkdir`, `cd`, `ls`, or environment inspection as preparation. Run the CLI directly from the host-provided working directory. The kernel creates state directories.
2. Work mode, or any host that reuses one working directory, must use isolated state for each new proposition:
   `.mentor-state/sessions/<proposition-slug>/session.json`. Put
   `--state ".mentor-state/sessions/<proposition-slug>/session.json"` before `--json` and the subcommand. Reuse that path for later rounds of the same proposition.
3. Run `learn` immediately after `init`; anchoring is not learning completion:
   `python3 "$SKILL_DIR/scripts/cli.py" --json learn`. Only the convergence owner decides completion. Do not replace convergence with "ready to teach". For a specific user question, run `query` after a durable topic exists; query is an optional read, not a completion condition.
4. In JSON mode, `status: "pending"` is normal control flow and exits with code 0. Read the current `request_path`, write the templated response to `request_paths.judgment`, and run `step` using that same state path until `status: "done"`. Writing a file without `step` is not submission. A nonzero exit code means a real error.
5. Do not call `WebSearch`, `WebFetch`, or any other research tool before `plan_investigation`. After that judgment explicitly establishes an investigation plan, use research tools only according to that plan and pass findings to `integrate_learning`.
6. A learning result may only come from a completed round's durable result. A query result may only come from the current topic version in the specified knowledge root. Do not create temporary teaching state or modify durable knowledge from a user question.
7. If the host lacks a shell, Python, or permission to write in its current directory, explicitly report that the protocol cannot run and stop. **Do not silently degrade** to ordinary search, ordinary Q&A, direct report writing, or imitation of question-tree/skeptic language.

The following do not count as executing the Skill: responding after only loading it; web research alone; manually writing a "skeptic perspective" section; creating only an output document; or failing to persist a session for the proposition.

## When to Use

- The user presents a proposition or topic they want to understand deeply, rather than receive a one-shot answer.
- The user wants reusable knowledge to deepen and validate over time.
- The work needs multiple rounds around one proposition with staged versions and open questions.

Do not use for fact lookups, one-off summaries, material management, or conversation unrelated to a proposition.

## Model Independence

This Skill has no model API, reads no API key, makes no network request, and has no third-party dependency. The agent running it is the judge. The kernel only routes stages; validates judgment shapes and enums; enforces rules; migrates state; and persists knowledge. The agent must personally make all epistemic judgments from the request: whether anchoring holds, what the gap is, whether an explanation survives skepticism, and which investigation action is appropriate.

Therefore any model can run this Skill without a kernel change.

## Installation and Prerequisites

- **Form:** copy the complete `deep-inquiry/` directory into any compatible Agent Skills directory. No build, pip/venv, or executable bit is required.
- **Runtime:** Python 3.10 or later using only the standard library, shell execution, and read/write access to the current working directory. Use `python3` on macOS/Linux and possibly `python` on Windows.
- **No dependency on:** a model API, keys, network access, fixed installation locations, environment variables, or third-party packages.
- **State location:** by default the caller's current working directory under `.mentor-state/`, never the Skill installation directory. A read-only installed Skill is valid, and projects are naturally isolated.

```text
deep-inquiry/
├── SKILL.md                 # canonical protocol loaded after triggering
├── SKILL.zh-CN.md           # Chinese companion
├── LICENSE                  # MIT
├── scripts/                 # deterministic kernel; execute it, do not load source
│   ├── cli.py               # single command-line entry point
│   ├── judgments.py         # vNext stages and v1 compatibility contracts
│   ├── knowledge_schema.py / knowledge_store.py / renderer.py / query.py
│   ├── loop.py / convergence.py / learner.py / compressor.py
│   └── schema.py / store.py / mentor.py   # legacy v1 importer boundary
```

The runtime `request.json` self-describes all needed instructions, state snapshots, response templates, and required fields. Do not read `scripts/` source unless diagnosing the kernel.

## Execution Protocol

`$SKILL_DIR` is the absolute directory containing this `SKILL.md`. Replace it with the path actually loaded by the host. Do not assume `.trae/skills/`. Run these commands from any working directory; state is written to the current directory:

```bash
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<global knowledge root>" \
  --topic-id "<topic-id>" init "<central proposition>"
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<global knowledge root>" \
  --topic-id "<topic-id>" learn
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<global knowledge root>" \
  --topic-id "<topic-id>" query "<user question>"
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<global knowledge root>" \
  --topic-id "<topic-id>" ask "<user question>"
```

When CWD is the Skill directory, `python3 -m scripts.cli ...` is equivalent. On Windows replace `python3` with `python`. `--json` is required for production hosts and returns machine-readable output including `request_path`.

| Exit code | Meaning | Next action |
|---|---|---|
| 0 | Command succeeded; inspect `status` for control flow | For pending follow `next_action`; for done/query_result read the result |
| 1 | Runtime error in rules or state | Read stderr, correct it, and retain the scene |
| 2 | CLI usage error | Check arguments |

1. Start a round with one of the four commands above. The kernel writes `.mentor-state/request.json` and `pending.json`, and returns `status: "pending"`, `next_action`, the resolved `knowledge_root`, `topic_id`, and all request paths.
2. Read `request.json`: `judgment` is the current judgment point; `instruction` says what to judge; `state_snapshot` is a read-only view of the five durable state types; `context` holds round details; and `response_template` / `required_fields` define the required response shape. Think for yourself and write UTF-8 `.mentor-state/judgment.json`:

```json
{"judgment": "<exactly match request.judgment>", "response": { ... }}
```

3. Run `python3 "$SKILL_DIR/scripts/cli.py" step --json`. A mismatched judgment name, missing field, or illegal enum fails while retaining the scene. Correct `judgment.json` and retry. A next judgment returns pending; repeat step 2. `status: "done"` means the round was persisted, its result is in `trace.result`, and runtime files are cleared.

Use `cancel` to abandon only the active runtime round and `state` to inspect durable state. For parallel propositions, use `--state <path>/session.json`.

### vNext Eight Stages

`anchor → map_knowledge → select_gap → plan_investigation → integrate_learning → skeptic_review → assess_convergence → checkpoint_or_complete`

`convergence.py` is the only stop-policy owner. `loop.py` only orchestrates. Each round may commit at most one durable delta.

### v1 Importer Compatibility Judgments

- Autonomous-loop judgments: `anchor_proposition`, `expand_question_tree`, `identify_gap`, `learn_round`, `brief_review`, `deep_review`, `rewrite_review_focus`, and `compress_explanation`.
- `assess_user`, `plan_teaching`, `teach_reply`, and `read_feedback` are solely for the legacy-session importer; they are not in the default vNext graph.

## Default vNext Paths

1. **Autonomous learning:** choose the highest-value gap, publish an investigation plan, integrate evidence, conduct skeptic review, atomically commit one delta, then let the convergence owner continue or complete. On true convergence, the kernel deterministically renders published knowledge to `topics/<topic-id>/reports/v<version>.md` and returns its absolute `report_path`. A checkpoint produces no report.
2. **Optional query:** `query` reads the selected topic's current version and returns active claims, supporting evidence, and unresolved boundaries. It creates no session, writes no knowledge, and infers no user level. `ask` is an identical compatibility alias.

## Protocol Invariants

- Every round has exactly one primary advancement objective. All other actions serve it.
- Before compression, every staged explanation must pass brief review: four questions covering where it is most likely wrong, whether a stronger alternative exists, where teaching it would fail, and the domain-expert requirement it may have missed.
- Deep review occurs only when an explanation enters a stable version, becomes a teaching backbone, conflicts with a counterexample, or competes with alternatives.
- A structural brief-review finding must rewrite the explanation; wording-only repair is forbidden.
- Compression requires the strongest current explanation, at least one open boundary, and why convergence is justified.
- **No stale open node may be forgotten.** Once the dual gate passes, the kernel provides still-open learned nodes as `stale_open_nodes`. Compression must place every id in `stabilize_question_ids` or `retain_open_questions`; each retained item needs an `id` and nonempty `reason`. Their union must exactly cover the ids. Missing, nonexistent, already-stable, duplicate, or unreasoned retained nodes are rejected without consuming the judgment. When none exist these fields are optional; `forced_compress` bypasses this validation.
- **Breadth-before-depth dual gate.** `anchor` declares at least two distinct `coverage_dimensions`, derived from qualifiers. The question tree starts broad with one `dimension`-tagged question per dimension and roughly 4–7 questions. Before compression every dimension must have a stable question and either an executable `dimension_rules` rule/value/decision expression from `learn_round`, or a reasoned skeptic `no_increment_verdicts` determination. No rule and no determination is a placeholder that returns to `IDENTIFY_GAP` with `depth_hint`. The gate does not apply to `forced_compress` or legacy sessions lacking the fields.
- **Question-tree quality.** One node asks one independently answerable question. Two question marks or interrogatives are compound and rejected. Depth is at most two: children use `parent_id`, retain the parent's `dimension`, and deepen inside it. Reject third-level nodes, cross-dimension attachment, and unknown parents. Capacities: at most 7 roots, 3 children per root, and 15 total. Root questions are neutral, not prewritten answer forms. `learn_round.new_sub_questions` follows the same rules; pruning removes a parent with its children.
- **Auditable dimension derivation.** Every `coverage_dimensions` entry has exactly one `dimension_sources` record. A `phase` source must preserve a `scope_qualifiers` `source_qualifier`; a `cross_cutting` source needs `reason` and root `depends_on` all relevant phases; a `standalone` source needs a reason. At least one phase is required; new anchors cannot create `legacy`. Old sessions migrate missing provenance as `legacy` only to remain loadable.
- **Evidence provenance and no false precision.** A unit-bearing numeric value in `dimension_rules` needs either `basis` at standard/clause level or `heuristic: true`; otherwise reject it. A heuristic still counts for depth but public rendering must state it is a heuristic requiring local planning/current-standard confirmation. Logical rules without numbers need no provenance. Evidence may persist `citation`.
- Queries never write user profile, teaching action, feedback state, or durable knowledge.
- Remove the `ask` alias before the first subsequent major version; do not extend it without external-dependency evidence.
- Expansion must connect back to the central proposition and state how the round changed its understanding.
- Every judgment response is genuine reasoning over `state_snapshot` and `context`: never fake enums, skip required fields, or manually edit `pending.json` / `session.json`.

### Real Host Operation Rules

- Each `brief_review.findings[i].question` must exactly reproduce the fixed wording in `request.response_template`, including the fourth domain-expert item. Summaries, truncation, and paraphrases are rejected without consuming the judgment.
- Writing a file is not submission. Write the judgment envelope, then run `step`. A "judgment name mismatch" means the previous judgment still needs submission; submit it in order.
- Global `--state` and `--json` options precede the subcommand: `python3 scripts/cli.py --state <path> --json <subcommand> ...`. Placing them after it fails argument parsing and produces no pending state.
- `init` is anchoring, not learning completion. `query` / `ask` must explicitly provide `--knowledge-root` and `--topic-id`; neither reads nor creates `.mentor-state`.

## Failure Modes

Follow `scripts/failures.py` when these conditions occur: proposition drift reanchors; an inflated question tree prunes low-relevance branches; three skeptic reviews without a hit rewrite the review focus; obsolete teaching adaptation forces hypothesis/action reassessment; premature convergence returns to skepticism or gap identification; and repeated rounds without an explanation-version update force an output or terminate expansion.

## State Boundaries

- **Authoritative persistence:** `<knowledge-root>/topics/<topic-id>/knowledge.json` and immutable history.
- **Runtime references:** the session stores only `topic_id`, `knowledge_root`, and optimistic `base_version`.
- A v1 teaching state is readable only through its one-way importer; vNext never writes back to it.
- **Runtime-only:** `pending.json`, `request.json`, and `judgment.json`; per-round trace, attempt, review drafts, one-time branch judgments, and message-local choices. They are cleared when the round ends and must never enter `session.json`.

## External Output

Do not expose internal process theater. A completed learning run returns knowledge version, delta history, deferred gaps, and convergence reason. True convergence also returns immutable Markdown `report_path`. The report only projects canonical `TopicKnowledge`, never calls a model again, and never invents unstored content. A report-write failure must not mark the run complete; retain the completion cursor for in-place retry. A query returns the current knowledge projection and does not pretend to be personalized teaching.
