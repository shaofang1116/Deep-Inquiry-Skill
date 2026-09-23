---
name: "autonomous-mentor"
description: "Use when the user wants autonomous deep learning, skeptic-reviewed convergence, durable knowledge accumulation, or a stateless query over learned knowledge."
---

# 自主学习导师（Autonomous Mentor）

围绕一个**中心命题**主动学习、主动怀疑、持续收敛并沉淀 durable knowledge 的 Skill。
学习以高价值认知缺口和边际收益驱动；可选查询只读取已沉淀知识，不模拟用户画像，也不决定学习是否完成。

完整协议见仓库 `docs/superpowers/specs/`：内核规范 v2、核心能力验证框架、主循环规范 v3.1、MVP 实现边界。
本文件只定义行为入口与不可违反的协议铁律。

## 触发后的强制执行闸门

**本节优先于便利性、一次性回答习惯和宿主的默认研究流程。加载本 Skill 不等于执行本 Skill。**

Skill 被触发后，必须遵守以下宿主契约：

1. **首个非 Skill 工具调用必须启动 CLI 文件协议**。新命题执行
   `python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<全局知识库>" --topic-id
   "<topic-id>" init "<中心命题>"`；不得先调用
   WebSearch、WebFetch、Read、Write、画布或其他研究/产出工具，不得直接回答；
   也不得先用 mkdir、cd、ls 或环境探测作为“准备动作”。应直接在宿主已经提供的当前工作目录
   启动 CLI；状态子目录由内核创建。
2. Work 模式或其他会复用同一工作目录的宿主，必须为每个新命题使用独立状态：
   `.mentor-state/sessions/<proposition-slug>/session.json`。实际命令把
   `--state ".mentor-state/sessions/<proposition-slug>/session.json"` 放在 `--json`
   和子命令之前；同一命题的后续轮次必须复用该路径。
3. `init` 结束后必须立即执行 `learn`，不能把锚定完成误当成学习完成：
   `python3 "$SKILL_DIR/scripts/cli.py" --json learn`。学习是否结束只由 convergence owner
   判定，不得以“已可教学”替代收敛。用户提出具体问题时，在 durable topic 已存在后执行
   `query`；查询是可选读取步骤，不属于学习完成条件。
4. JSON 模式下 `status: "pending"` 是正常控制流，进程退出码为 0。必须读取当前
   `request_path`、按模板写入 `request_paths.judgment`、执行同一状态路径下的 `step`，
   循环到 `status: "done"`。写文件但未 `step` 不算提交；非零退出码只表示真实错误。
5. `plan_investigation` 之前禁止调用 WebSearch、WebFetch 或其他研究工具；该判断完成并
   明确调查计划后，允许按计划使用研究工具，并把结果交给 `integrate_learning`。
6. 学习结果只能来自已完成轮次的 durable result；查询结果只能来自指定 knowledge root
   中的当前 topic version。不得根据用户问题临时创建教学状态或修改 durable knowledge。
7. 如果宿主没有 shell、Python 或当前目录写权限，必须明确报告无法执行协议并停止；
   **不得静默降级**为普通搜索、普通问答、直接写报告或仅模仿问题树/怀疑者措辞。

以下行为一律视为未执行 Skill：只调用 Skill 加载器后直接回答；只做网页检索；
手写“怀疑者视角”章节；只创建成果文档；未产生对应命题的持久化 session。

## 何时使用

- 用户给出一个想真正搞懂的命题/主题，要求持续深入学习而非一次性回答
- 用户希望持续加深、校验并积累可复用知识，而不是只得到一次性答案
- 需要在多轮中持续围绕同一命题推进，并保留阶段版本与开放问题

不适用于：事实查询、一次性摘要、资料管理、与任何命题无关的闲聊。

## 模型无关：判断由执行本 Skill 的 agent 自己完成

本 Skill **不接入、也不内置任何模型 API**：不读取 API key、不发起网络请求、零第三方依赖。
加载本 Skill 的 agent（你，无论底层是什么模型）本身就是判断者。内核只做确定性的事：
路由阶段、校验判断的形状与枚举、执行规则、迁移状态、落库。所有认识论判断
（锚定是否成立、缺口是什么、解释是否经得住怀疑、用户卡在哪、该用哪个教学动作）
都由你在阅读请求后亲自给出。

因此同一份 Skill 可以被任意模型执行，切换模型不需要改动内核任何一行代码。

## 安装与前置要求

- **形态**：标准 Agent Skills 目录包，复制整个 `autonomous-mentor/` 到任意兼容工具
  （Claude Code、各类支持 SKILL.md 的 agent 工具）的 skills 目录即安装完成：
  无需构建、无需 pip/venv、无需可执行位。
- **运行时**：Python ≥ 3.10（仅标准库；macOS/Linux 用 `python3`，Windows 上可能是 `python`）、
  shell 执行能力、当前工作目录的文件读写权限。
- **不依赖**：任何模型 API/密钥/网络、任何固定安装路径、任何环境变量、第三方包。
- **状态位置**：默认写入**调用方当前工作目录**的 `.mentor-state/`，绝不写入 Skill 安装目录
  （因此 Skill 装在只读位置也能运行；不同项目目录天然隔离为不同会话）。

目录结构（符合 Agent Skills 渐进披露约定）：

```
autonomous-mentor/
├── SKILL.md                 # 本文件：触发后加载的执行协议（Tier 2）
├── LICENSE                  # MIT
├── scripts/                 # 确定性内核：直接「执行」，不要把源码读入上下文
│   ├── cli.py               # 唯一命令行入口
│   ├── judgments.py         # vNext 自主学习阶段与 v1 兼容判断契约
│   ├── knowledge_schema.py / knowledge_store.py / renderer.py / query.py
│   ├── loop.py / convergence.py / learner.py / compressor.py
│   └── schema.py / store.py / mentor.py   # v1 importer 兼容边界
└── examples/                # Tier 3 自检资产：样例、确定性夹具、端到端冒烟
    └── tests/               # 按责任分层的可执行检查与夹具
        ├── core_contract/   # schema、store、index、lifecycle、convergence
        ├── behavior/        # learning loop、eval、real-host 与 judge
        ├── migration/       # v1 importer
        └── adapter/         # CLI、query、host、package 与 smoke
```

判断所需的全部上下文（指令、状态快照、响应模板、必填字段）都在运行时的 `request.json`
里自描述，因此**不需要阅读 `scripts/` 源码**；只有排查内核问题时才读。

## 执行协议（begin → 判断 → step，循环到 done）

约定 `$SKILL_DIR` = 本 SKILL.md 所在目录的**绝对路径**（各工具安装位置不同，
用你实际加载到的路径替换；不要假设它在 `.trae/skills/` 下）。
以下命令可从**任意工作目录**运行，状态落在当前工作目录：

```bash
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<全局知识库>" \
  --topic-id "<topic-id>" init "<中心命题>"                     # 输入 1：新命题
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<全局知识库>" \
  --topic-id "<topic-id>" learn                                 # 输入 2：继续学习
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<全局知识库>" \
  --topic-id "<topic-id>" query "<用户问题>"                    # 可选、无状态读取
python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root "<全局知识库>" \
  --topic-id "<topic-id>" ask "<用户问题>"                      # query 的一版兼容别名
```

（CWD 恰好在 Skill 目录时，`python3 -m scripts.cli ...` 等价；Windows 将 `python3` 换为 `python`。）
`--json` 是生产宿主的必需参数，用于获得机器可读输出（含 `request_path`）。

**JSON 宿主契约**：

| 退出码 | 含义 | 下一步 |
|---|---|---|
| 0 | 命令成功；具体控制流看 `status` | pending 则按 `next_action` 继续，done/query_result 则读取结果 |
| 1 | 运行错误（规则/状态） | 读 stderr 修正；现场保留 |
| 2 | 命令行用法错误 | 检查参数 |

第 1 步，发起一个轮次（begin，上表四条命令）。内核写出
`.mentor-state/request.json`（判断请求）与 `pending.json`（轮次信封），返回
`status: "pending"`、`next_action`、解析后的 `knowledge_root`、`topic_id` 和全部 request paths。

第 2 步，阅读 `request.json`，它包含：

- `judgment`：当前判断点名称（共 12 个，见下）
- `instruction`：这次要你判断什么
- `state_snapshot`：五类持久化状态的快照（只读）
- `context`：本轮运行时上下文（如 attempt、user_message、stage_explanation）
- `response_template` / `required_fields`：响应必须具备的字段形状

**用你自己的思考**完成判断，严格按模板写入 `.mentor-state/judgment.json`（UTF-8）：

```json
{"judgment": "<与 request 中的 judgment 完全一致>", "response": { ... }}
```

第 3 步，运行 `python3 "$SKILL_DIR/scripts/cli.py" step --json`：

- 内核消费 judgment：名称不匹配、字段缺失、枚举非法都会报错并**保留现场**，
  你修改 `judgment.json` 后重新 step 即可，轮次不会丢；
- 若内核需要下一个判断，会再写 `request.json` 并返回 `status: "pending"` —— 回到第 2 步；
- `status: "done"` 表示本轮完成：结果在输出的 `trace.result` 中，状态已落库，运行时文件已清空。

中途可 `cancel` 放弃当前轮次（只清运行时文件，不动 session.json）；
`state` 查看持久化状态；`demo` 运行端到端冒烟（由 `examples/tests/behavior/scripted_judge.py`
确定性夹具代填判断，仅供离线验证，**不是生产路径，真实运行时禁止照抄它的内容**）。
多命题并行时，用 `--state <路径>/session.json` 为每个命题指定独立状态文件。

**vNext 默认 eval**：`python3 examples/tests/behavior/eval_suite.py` 依次验证 convergence owner、
至少三轮的 autonomous loop，以及 stateless query/`ask` alias。默认 trace 和结果不得出现
`assess_user`、`plan_teaching`、`teach_reply` 或 `feedback`。旧教学 CasePack 仅保留为
Task 10 的 v1 importer 兼容证据，不再由默认 smoke/eval 执行。

### vNext 八阶段

`anchor → map_knowledge → select_gap → plan_investigation → integrate_learning
→ skeptic_review → assess_convergence → checkpoint_or_complete`

`convergence.py` 是唯一停止策略 owner；`loop.py` 只编排；每轮最多提交一个 durable delta。

### v1 importer 兼容判断点

- 自主学习循环：`anchor_proposition`（命题锚定）、`expand_question_tree`（问题树展开）、
  `identify_gap`（缺口识别）、`learn_round`（阶段解释）、`brief_review`（简审四问）、
  `deep_review`（条件深审）、`rewrite_review_focus`（重写异议焦点）、
  `compress_explanation`（阶段压缩提案）
- `assess_user`、`plan_teaching`、`teach_reply`、`read_feedback` 仅供旧会话 importer
  读取与验证，不属于 vNext 默认图。

## vNext 默认路径

1. **自主学习**：持续选择最高价值缺口，先公开 investigation plan，再整合证据，
   经 skeptic review 后原子提交一个 delta，最后由 convergence owner 判断继续或完成。
   真正收敛时，内核把当前已发布知识确定性渲染为
   `topics/<topic-id>/reports/v<version>.md`，并在完成结果的 `report_path`
   返回绝对路径。checkpoint 中止不生成报告。
2. **可选查询**：`query` 读取指定 topic 当前版本，返回 active claims、支撑证据与未决边界；
   不创建 session、不写 knowledge、不推断用户水平。`ask` 仅是完全相同的兼容别名。

## 协议铁律（规则，不交给模型自由决定）

- 每轮运行**有且只有一个主推进目标**，其他动作只能服务于它。
- 任何阶段性解释在压缩前**必须经过简审三问**：最可能错在哪 / 有无更强替代解释 / 现在教会在哪露馅。
- 深审只在四种条件触发：解释将进入稳定版本、将作为教学主干、出现反例冲突、多解释竞争。
- 简审击中结构问题 → 回流重写解释，不允许只做措辞修补。
- 阶段压缩必须同时给出：当前最稳解释、**至少一个开放边界**、为什么现在可以收敛；缺一不可。
- **悬置节点不得遗忘（stale open disposition）**：双条件闸门通过后，内核按状态现算仍为 open 的
  子问题（其维度已学稳、规则已沉淀，但 learn_round 从未显式回补 stable），以 `stale_open_nodes`
  注入压缩请求 context。压缩定稿必须逐个显式处置：规则确已答出的列入 `stabilize_question_ids`
  （随定稿回补 stable）；确属未决、允许带入新版本的列入 `retain_open_questions`（每项 `id` +
  非空 `reason`，自动以「未闭合子问题（id）：……——理由」并入开放边界，节点保持 open）。
  两字段并集必须恰好覆盖全部悬置 id——漏处置、引用不存在/已 stable 的 id、同一节点同时进两字段、
  retain 无理由，一律拒绝且判断不被消费，可原地修正重试。无悬置节点时新字段可省（向后兼容）；
  `forced_compress` 安全阀不启用本校验。
- **先宽后深双条件闸门**：锚定须声明 `coverage_dimensions`（≥2 个互异主干维度，由限定词拆出），问题树展开
  采用先宽后深骨架（每维度至少一个带 `dimension` 标签的子问题，总计约 4–7 个）；压缩前内核确定性校验
  两个条件——①覆盖：每个主干维度至少有一个「已稳定」子问题，缺枝回问题树补（EXPAND_TREE）、有占位未学稳
  回缺口识别补学（IDENTIFY_GAP）；②最低深度：每个维度必须沉淀 ≥1 条可执行规则/取值/判定式
  （在 learn_round 的 `dimension_rules` 给出，空话不计），或由怀疑者在简审/深审中显式裁决
  `no_increment_verdicts`「本命题下该维度无专项增量」（必须附理由，与规则互斥，已有规则的维度不再受理裁决）。
  零规则零裁决的维度即「维度占位符」，闸门打回 IDENTIFY_GAP 并带 `depth_hint`，未双条件全满足不得压缩；
  `forced_compress` 安全阀（无限扩张截断）与旧会话无该字段时闸门不启用，保持向后兼容。
- **问题树质量铁律（节点单一问题 + 两级树 + 根中性）**：一个子问题只问一件可独立回答的事——
  出现两个问号或两个疑问词（如何/什么/怎么/是否…）即复合问法，内核直接拒绝并要求拆节点；
  深挖必须以**二级子问题**（`parent_id` 指向一级节点、与父节点同 `dimension`）长在维度内部，
  而不是往同一节点文本里灌内容；树深最多两级，三级节点、跨维度挂载、未知 parent 一律拒绝。
  容量分层：一级 ≤7、单个一级节点下二级 ≤3、总数 ≤15。根问题必须中性（如何成立/如何起作用/
  什么条件下失效），禁止预写答案形态（「全过程」「完整决策框架」「体系」等目录词），否则树退化为目录。
  learn_round 的 `new_sub_questions` 受同样约束；裁剪时二级节点随父节点同进同退，不留孤儿。
- **维度推导链可审计（限定词 → 维度，阶段与横切分层）**：锚定时每个 `coverage_dimensions` 必须在
  `dimension_sources` 中恰好有一条来源——`phase`（阶段维度）的 `source_qualifier` 必须原样回指
  `scope_qualifiers` 中的一条限定词；`cross_cutting`（横切面，如经济性/合规性）必须给 `reason`，
  其一级节点必须用 `depends_on` 依赖它横切的全部阶段维度节点（`related_phases` 省略=全部阶段）；
  `standalone`（非限定词推出）必须给理由。至少一个 phase；无来源的维度不允许凭空添加。
  旧会话无来源记录时迁移为 `legacy` 占位，仅保证可加载，新锚定不得产出 legacy。
- **证据溯源与伪精确零容忍**：`dimension_rules` 中凡带计量单位的数值取值（如 65mm、200米、30%），
  必须二选一——给 `basis`（规范编号/条文级出处），或显式标 `heuristic: true`；两者皆无内核直接拒绝。
  heuristic 规则仍计入最低深度，但对外展示（压缩解释/教学）必须经 `render_rule` 附带
  「经验启发式，须以当地规划/现行规范为准」，不得写成确定规则；逻辑推导型无数值规则无需溯源。
  证据条目支持 `citation`（规范编号级出处），随证据簿持久化。
- 查询不得写入用户画像、教学动作、反馈状态或任何 durable knowledge 字段。
- `ask` 兼容别名在首个后续 major version 前删除；若无外部依赖证据，不得延长。
- 扩张必须回连中心命题，回答「这轮如何改变了我对命题的理解」；答不出即低价值扩张。
- 判断响应必须是针对 `state_snapshot` 与 `context` 的真实推理结果；不得伪造枚举值、
  不得跳过 required_fields、不得手改 `pending.json` / `session.json`。

### 真实宿主操作铁律（阶段三-B 真实形状回补，违反即拒绝或空跑）

- **简审四问问法必须逐字照抄**：`brief_review` 的每条 `findings[i].question` 必须等于
  `request.response_template` 给出的固定问法（尤其第四问「内行必答项」），概括、截断、改写一律被内核拒绝；
  拒绝时判断未被消费，把 question 改成逐字原文重提即可，轮次不丢。
- **写文件 ≠ 提交**：每个判断点必须先把信封写入 `judgment.json` 再 `step`；若 step 报
  「判断名称不匹配：当前请求需要 X，收到 Y」，说明上一判断点尚未提交，按序补提 X 即可，
  已写入的信封不会被覆盖、轮次不丢。
- **全局参数必须位于子命令之前**：`--state` / `--json` 是顶层参数，正确写法
  `python3 scripts/cli.py --state <path> --json <子命令> ...`；放在子命令之后 argparse 直接失败，
  不产生任何 pending（安全，重试即可）。
- **状态入口要分清**：锚定（`init`）不是学习完成；`query`/`ask` 必须显式指定
  `--knowledge-root` 与 `--topic-id`，且不读取或创建 `.mentor-state`。

## 六类失败模式（命中即按 scripts/failures.py 的修正动作处理）

命题漂移 → 强制重新锚定；问题树膨胀 → 裁剪低关联分支；怀疑者空转（最近三审无一击中）
→ 重写异议焦点；教学伪适配（重复使用已失效讲法）→ 强制重判假设重选动作；
过早收敛（无开放边界/未过审就压缩）→ 回流怀疑或缺口识别；
无限扩张（连续多轮无解释版本更新）→ 强制输出版本，输出不了即截断。

## 状态边界

- **权威持久化**：全局知识库 `topics/<topic-id>/knowledge.json` 及 immutable history。
- **运行时引用**：session 只保存 `topic_id`、`knowledge_root` 与 optimistic `base_version`。
- v1 教学状态只允许被 one-way importer 读取，vNext 不写回。
- **只在运行时存在**（`pending.json` / `request.json` / `judgment.json`，轮次结束即清除）：
  单轮 trace、attempt、简审/深审草稿、一次性分支判断、消息级临时选择。
  这些内容禁止写入 `session.json`。

## 输出口径

对外不展示内部流程表演。学习完成返回 knowledge version、delta history、未决 deferred gaps
和 convergence reason；真正收敛还返回不可变 Markdown 文档的 `report_path`。
文档只投影 canonical `TopicKnowledge`，不再次调用模型或补写未沉淀内容。文档写入失败时
不得把 run 标记为 complete，必须保留 completion cursor 供原地重试；查询返回当前版本的
知识投影，不伪装成个性化教学。
