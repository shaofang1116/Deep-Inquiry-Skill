# Deep Inquiry Skill

Deep Inquiry is an agent skill for turning a central proposition into durable, skeptic-reviewed knowledge. Instead of producing a one-shot answer, the agent follows a file-based protocol to identify high-value gaps, investigate them, test explanations, and decide whether to continue, checkpoint, or converge.

The deterministic Python kernel owns protocol validation, state transitions, persistence, and report rendering. The host agent remains responsible for research and epistemic judgment.

## What It Produces

- Versioned topic knowledge under `<knowledge-root>/topics/<topic-id>/`
- An auditable history of learning deltas and unresolved boundaries
- A stateless `query` interface over the current durable topic
- An immutable, reader-oriented knowledge document at
  `topics/<topic-id>/reports/v<version>.md` when a topic genuinely converges

Queries do not modify stored knowledge or infer a user profile.

The converged report is not an audit export. It deterministically formats the
skeptic-reviewed reader document stored with canonical topic knowledge: an
overview, explanatory sections, cross-dimension synthesis, application
guidance, boundaries, and compact source notes. Audit history remains durable
for inspection but is not presented as the report's primary narrative.

## Requirements

- Python 3.10 or later
- A host agent that can execute shell commands and read/write its working directory
- No API keys, network access, third-party packages, or model-specific dependencies

The skill stores runtime state in the caller's working directory, not in its installation directory. A read-only installation is therefore supported.

## Install

The distributable skill is [`skill/deep-inquiry`](skill/deep-inquiry). Copy that complete directory into the Agent Skills directory used by your host:

```bash
git clone https://github.com/shaofang1116/Deep-Inquiry-Skill.git
cp -R Deep-Inquiry-Skill/skill/deep-inquiry <your-agent-skills-directory>/
```

The installed directory must retain this structure:

```text
deep-inquiry/
├── SKILL.md
├── SKILL.zh-CN.md
├── LICENSE
└── scripts/
```

[`SKILL.md`](skill/deep-inquiry/SKILL.md) is the canonical English protocol. [`SKILL.zh-CN.md`](skill/deep-inquiry/SKILL.zh-CN.md) is its complete Chinese mirror.

## Run a Learning Session

Set `SKILL_DIR` to the installed `deep-inquiry` directory. Choose an isolated session path, a durable knowledge root, and a stable topic ID for each proposition.

```bash
export SKILL_DIR="/absolute/path/to/deep-inquiry"
export STATE=".mentor-state/sessions/battery-safety/session.json"
export KNOWLEDGE_ROOT="/absolute/path/to/knowledge"
export TOPIC_ID="battery-safety"

python3 "$SKILL_DIR/scripts/cli.py" \
  --state "$STATE" \
  --json \
  --knowledge-root "$KNOWLEDGE_ROOT" \
  --topic-id "$TOPIC_ID" \
  init "A battery-management system can make lithium-ion storage acceptably safe for a home lab."

python3 "$SKILL_DIR/scripts/cli.py" \
  --state "$STATE" \
  --json \
  --knowledge-root "$KNOWLEDGE_ROOT" \
  --topic-id "$TOPIC_ID" \
  learn
```

`init` and `learn` normally return `status: "pending"` with a `request_path`. The host agent reads the request, writes the required UTF-8 judgment envelope to `request_paths.judgment`, and submits it:

```bash
python3 "$SKILL_DIR/scripts/cli.py" --state "$STATE" --json step
```

Repeat the request, judgment, and `step` cycle until `status: "done"`. A process exit code of `0` with `status: "pending"` is expected control flow, not completion. The full host contract, required judgment shape, and execution gates are defined in [`SKILL.md`](skill/deep-inquiry/SKILL.md).

## Query Stored Knowledge

After a durable topic exists, query it without changing its knowledge or creating a learning session:

```bash
python3 "$SKILL_DIR/scripts/cli.py" \
  --json \
  --knowledge-root "$KNOWLEDGE_ROOT" \
  --topic-id "$TOPIC_ID" \
  query "Which failure modes remain unresolved?"
```

`ask` is currently a compatibility alias for `query`.

## Protocol at a Glance

Each vNext learning round progresses through:

```text
anchor -> map_knowledge -> select_gap -> plan_investigation
       -> integrate_learning -> skeptic_review
       -> assess_convergence -> checkpoint_or_complete
```

The convergence policy is owned solely by the kernel. A completed checkpoint is not a convergence result and does not create a Markdown report.

## License

This project is licensed under the [MIT License](skill/deep-inquiry/LICENSE).
