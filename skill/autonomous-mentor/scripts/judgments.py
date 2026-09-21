"""判断点契约：内核与「执行 Skill 的 agent」之间的唯一交换面。

设计原则（模型无关）：
- 内核不调用任何大模型 API，不内置厂商、密钥、SDK。
- 凡是认识论判断（缺口选择、解释生成、怀疑审查、用户假设、导师动作、成熟度），
  内核都只生成一个**判断请求**（JudgmentRequest），由当前执行 Skill 的 agent
  （任意模型）按 response_template 填成 JSON，再通过 step 喂回内核。
- 内核对响应做**形状校验 + 规则校验**：必填字段、枚举取值、简审四问完整性等。
  判断内容由模型负责，结构合法性由内核负责。

离线冒烟时由 examples/scripted_judge.py 这个确定性夹具代替 agent 填表，
它不是生产路径，只是让循环无需模型也能被验证。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schema import DIM_SOURCE_ANCHOR_KINDS, DialogGoal, GapType, TeachingAction

# 判断点名称
ANCHOR = "anchor_proposition"
EXPAND_TREE = "expand_question_tree"
IDENTIFY_GAP = "identify_gap"
LEARN = "learn_round"
BRIEF_REVIEW = "brief_review"
REWRITE_FOCUS = "rewrite_review_focus"
DEEP_REVIEW = "deep_review"
COMPRESS = "compress_explanation"
ASSESS_USER = "assess_user"
PLAN_TEACHING = "plan_teaching"
TEACH = "teach_reply"
ASSESS_MIGRATION_OUTPUT = "assess_migration_output"
READ_FEEDBACK = "read_feedback"

ALL_NAMES = (
    ANCHOR,
    EXPAND_TREE,
    IDENTIFY_GAP,
    LEARN,
    BRIEF_REVIEW,
    REWRITE_FOCUS,
    DEEP_REVIEW,
    COMPRESS,
    ASSESS_USER,
    PLAN_TEACHING,
    TEACH,
    ASSESS_MIGRATION_OUTPUT,
    READ_FEEDBACK,
)

# vNext durable autonomous-learning stages. These remain separate from the v1
# judgment registry so the existing file-protocol state machine is unchanged.
AUTONOMOUS_ANCHOR = "anchor"
MAP_KNOWLEDGE = "map_knowledge"
SELECT_GAP = "select_gap"
PLAN_INVESTIGATION = "plan_investigation"
INTEGRATE_LEARNING = "integrate_learning"
SKEPTIC_REVIEW = "skeptic_review"
ASSESS_CONVERGENCE = "assess_convergence"
CHECKPOINT_OR_COMPLETE = "checkpoint_or_complete"
INITIALIZE_TOPIC = "initialize_topic"

AUTONOMOUS_STAGES = (
    AUTONOMOUS_ANCHOR,
    MAP_KNOWLEDGE,
    SELECT_GAP,
    PLAN_INVESTIGATION,
    INTEGRATE_LEARNING,
    SKEPTIC_REVIEW,
    ASSESS_CONVERGENCE,
    CHECKPOINT_OR_COMPLETE,
)

_AUTONOMOUS_AGENT_SPECS = {
    AUTONOMOUS_ANCHOR: (
        "Confirm the durable topic proposition and learning boundary.",
        ["accepted"],
    ),
    MAP_KNOWLEDGE: (
        "Inspect the current durable knowledge map before selecting work.",
        ["accepted"],
    ),
    PLAN_INVESTIGATION: (
        "Expose a concrete investigation plan for the selected gap.",
        ["plan"],
    ),
    INTEGRATE_LEARNING: (
        "Propose one validated knowledge delta without persisting it.",
        [
            "delta",
            "claims",
            "evidence",
            "gaps",
            "counterexamples",
            "phase",
            "gain_level",
        ],
    ),
    SKEPTIC_REVIEW: (
        "Review the proposed integration for unresolved structural defects.",
        ["structural_hit"],
    ),
    ASSESS_CONVERGENCE: (
        "Assess marginal gain and remaining work against durable topic state.",
        [
            "gain_level",
            "open_high_value_gap_ids",
            "evidence_deficit_claim_ids",
            "structural_hit",
            "continue_learning",
            "reason",
        ],
    ),
}

_INITIALIZE_TOPIC_FIELDS = (
    "title",
    "proposition",
    "coverage_dimensions",
    "claims",
    "evidence",
    "gaps",
    "counterexamples",
)

GAP_TYPES = [g.value for g in GapType]
DIALOG_GOALS = [g.value for g in DialogGoal]
TEACHING_ACTIONS = [a.value for a in TeachingAction]

BRIEF_QUESTIONS = [
    "这里最可能错在哪？",
    "有没有更强的替代解释？",
    "如果现在拿去教初学者，会在哪暴露漏洞？",
    "在该领域的标准实践中，是否存在本解释完全没提到、但换任何内行都会追问的必答项"
    "（对照 context.completeness_hint 中尚无规则的维度与相邻标准工况，如遗漏的荷载工况/"
    "失效模式/强制验算/构造要求）？有则逐条列出并记为击中，确无则明确回答无。",
]


class JudgmentError(ValueError):
    """判断响应不满足契约。修复后重新 step 即可，pending 不会丢失。"""


@dataclass
class FieldSpec:
    name: str
    type_desc: str
    required: bool = True
    note: str = ""


@dataclass
class JudgmentRequest:
    """内核发给执行 agent 的判断请求（序列化为 request.json）。"""

    name: str
    instruction: str
    state_snapshot: dict[str, Any]
    context: dict[str, Any]
    response_template: dict[str, Any]
    required_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "judgment": self.name,
            "instruction": self.instruction,
            "state_snapshot": self.state_snapshot,
            "context": self.context,
            "response_template": self.response_template,
            "required_fields": self.required_fields,
        }


# ---- 每个判断点：指令 + 响应模板 + 必填字段 -------------------------------


def _spec(
    name: str,
    instruction: str,
    template: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "instruction": instruction,
        "template": template,
        "required": required,
    }


REGISTRY: dict[str, dict[str, Any]] = {
    ANCHOR: _spec(
        ANCHOR,
        "把用户给出的原始命题锚定为一句话中心命题，并显式划出命题边界与"
        "至少两个「不属于本命题」的邻接议题（v3.1 阶段1 退出判据）。"
        "同时必须拆解命题里的限定词（scope_qualifiers，如「商用楼」「全过程」"
        "「海边」等会改变知识范围的修饰），并据此给出至少两个互不重叠的"
        "主干覆盖维度（coverage_dimensions）——它们是该领域回答命题必须覆盖的"
        "一级方面（如流程类命题的前期/设计/施工/验收运营）。后续问题树必须"
        "覆盖每一个维度，先宽后深，防止只沿最显眼的一条线深挖。"
        "每个维度必须在 dimension_sources 中给出可审计的推导链，逐条对应、不许多缺："
        "kind=phase 表示由某个限定词直接推出，source_qualifier 必须原样回指 "
        "scope_qualifiers 中的一条；kind=cross_cutting 表示横切多个阶段的属性"
        "（如经济性/合规性），必须给 reason，并用 related_phases 列出它横切哪些"
        "阶段维度（省略=全部阶段）；kind=standalone 表示非限定词推出的其他维度，"
        "必须给 reason。至少一个 phase 维度；不允许只给维度名不给来源。",
        {
            "proposition_text": "一句话中心命题",
            "proposition_scope": "命题边界说明",
            "adjacent_topics": ["邻接议题1（不属于命题本身）", "邻接议题2"],
            "scope_qualifiers": ["改变知识范围的命题限定词1", "限定词2"],
            "coverage_dimensions": ["主干覆盖维度1", "主干覆盖维度2"],
            "dimension_sources": [
                {
                    "dimension": "主干覆盖维度1",
                    "kind": "phase",
                    "source_qualifier": "必须原样取自 scope_qualifiers",
                    "reason": "",
                    "related_phases": [],
                },
                {
                    "dimension": "经济性",
                    "kind": "cross_cutting",
                    "source_qualifier": "",
                    "reason": "成本横切各阶段，不是由某个限定词推出的阶段",
                    "related_phases": [],
                },
            ],
        },
        ["proposition_text", "proposition_scope", "adjacent_topics",
         "coverage_dimensions", "dimension_sources"],
    ),
    EXPAND_TREE: _spec(
        EXPAND_TREE,
        "围绕命题建立「先宽后深」的覆盖骨架，而不是最小问题树："
        "先为锚定声明的每一个 coverage_dimensions 各放至少一个一级子问题占位"
        "（parent_id 留空，保证一级方面全覆盖、维度之间 MECE）；深挖表现为"
        "给一级节点挂二级子问题（parent_id 填该一级节点 id），而不是往同一节点"
        "文本里堆内容——树深最多两级，禁止三级。二级节点必须与父节点同一 dimension。"
        "每个子问题必须带 dimension 标签（取自 coverage_dimensions）并用 depends_on "
        "表达依赖；kind=cross_cutting 的横切维度（如经济性），其一级节点必须 "
        "depends_on 它横切的全部阶段维度节点（related_phases 省略即全部阶段）。"
        "一个节点只问一件可独立回答的事：出现两个疑问词或两个问号即复合问法，"
        "会被内核拒绝（反例：「桩长如何取值，以及冲刷线下埋深怎么定？」必须拆开；"
        "正例：「桩长如何取值？」+ 二级节点「冲刷线下稳定埋深如何确定？」）。"
        "根问题必须中性（如何成立/如何起作用/什么条件下失效），禁止预写答案形态"
        "（不得含「全过程/完整决策框架/体系」等答案目录词）。"
        "容量：一级 ≤7、单个一级节点下二级 ≤3、总数 ≤15。"
        "若 context.coverage_hint 指出缺枝或有维度尚未学透，必须补齐对应维度，"
        "且保留已有问题的 id 与内容，不要重建已学部分。问题树承担结构作用，不是目录。",
        {
            "root_question": "中性主问题（如何成立/如何起作用，不预写答案形态）",
            "sub_questions": [
                {"id": "q1", "text": "维度A的一个单一问题", "dimension": "主干覆盖维度1", "depends_on": [], "parent_id": ""},
                {"id": "q2", "text": "维度B的一个单一问题", "dimension": "主干覆盖维度2", "depends_on": ["q1"], "parent_id": ""},
                {"id": "q3", "text": "对q2深挖的一个单一问题", "dimension": "主干覆盖维度2", "depends_on": ["q2"], "parent_id": "q2"},
            ],
            "priority_id": "q1",
        },
        ["root_question", "sub_questions", "priority_id"],
    ),
    IDENTIFY_GAP: _spec(
        IDENTIFY_GAP,
        "识别当前唯一一个主认知缺口并说明为何它优先。缺口类型只能取给定枚举。"
        "若当前确实没有可识别缺口，返回 gap_statement 为空串（循环将待命）。"
        "若 context.coverage_hint 指出有主干维度尚未学透，主缺口必须指向这些维度"
        "中最该先补的一个，而不是继续深挖已稳定的维度。"
        "若 context.depth_hint 指出某些已稳定维度零规则零裁决（维度占位符），"
        "主缺口必须指向其中一个，目标是补出该维度的可执行规则；不要重复学同一内容。",
        {
            "gap_type": " | ".join(GAP_TYPES),
            "gap_statement": "主缺口描述；无缺口时为空串",
            "why_priority": "为什么它是当前优先缺口",
            "secondary_gaps": [],
        },
        ["gap_type", "gap_statement", "why_priority"],
    ),
    LEARN: _spec(
        LEARN,
        "围绕主缺口/主问题推进一轮学习，产出可被怀疑者审查的阶段性解释。"
        "必须说明本轮理解变化、变化由什么推动、以及如何回连中心命题；"
        "回连牵强即低价值扩张，内核会拒绝。"
        "可选提供 evidence 列出支撑本轮解释的证据，压缩后会挂到证据簿。"
        "可选提供 dimension_rules：为本轮学到的主干维度沉淀可执行规则/取值/判定式，"
        "dimension 必须取自锚定的 coverage_dimensions，rule 必须具体可执行"
        "（含阈值、分支条件或判定方法，如「软土厚 >10m 选桩基」）；"
        "「应注意」「视情况而定」类空话会被拒绝。"
        "压缩前每个主干维度必须至少有 1 条规则，或经怀疑者无增量裁决。"
        "若 context.depth_hint 存在，本轮学习必须为其 shallow_dimensions 中的维度补规则。"
        "深挖一个维度时用 new_sub_questions 挂二级节点（parent_id 指向一级节点、同维度），"
        "不要把多个追问塞进同一节点文本；一个节点只问一件事，树深最多两级。",
        {
            "stage_explanation": "阶段性解释全文",
            "understanding_change": "本轮理解发生了什么变化",
            "driver": "该变化由哪个缺口/依据/反例/教学暴露推动",
            "proposition_link": "本轮新增学习如何改变了对中心命题的理解",
            "resolved_gap": False,
            "stable_question_ids": ["被本轮稳定下来的子问题 id"],
            "new_sub_questions": [
                {
                    "id": "q2-1",
                    "text": "对某一级节点深挖的一个单一问题（禁止复合问法）",
                    "dimension": "必须与 parent 同维度",
                    "depends_on": ["q2"],
                    "parent_id": "挂二级节点时填一级节点 id；新增一级节点留空",
                }
            ],
            "next_priority_id": "下一个优先子问题 id 或空串",
            "competing_explanations": False,
            "dimension_rules": [
                {
                    "dimension": "必须来自锚定的 coverage_dimensions",
                    "rule": "可执行规则/取值/判定式（带阈值或分支条件），空话不计",
                    "basis": "数值规则填规范编号/条文出处；非数值规则留空",
                    "heuristic": False,
                }
            ],
            "evidence": [
                {
                    "evidence_type": "来源观察 | 反例击穿 | 教学断链 | 逻辑推导",
                    "content": "证据内容",
                    "source": "证据来源（如「简审第四问」「用户反馈」）",
                    "citation": "规范编号级出处（如 JTS 145-2015 第5.2条）；无统一出处填说明",
                }
            ],
        },
        ["stage_explanation", "understanding_change", "driver", "proposition_link"],
    ),
    BRIEF_REVIEW: _spec(
        BRIEF_REVIEW,
        "对阶段性解释执行简审。必须逐项回答固定四问，问题文本不可更改；"
        "structural_hit=true 表示该问击中了关键结构问题（不是措辞问题），"
        "击中时必须给出 loop_gap（新的主缺口）。第三问必须检查教学暴露点。"
        "第四问是领域完备性检查：以「换任何内行都会追问的必答项」为标尺，"
        "结合 context.completeness_hint 中尚无规则沉淀的维度，主动对照相邻标准工况"
        "（遗漏的荷载工况、失效模式、规范强制验算、构造要求等）；发现遗漏必须逐条列出"
        "具体条目并记 structural_hit=true + loop_gap，确无遗漏才回答无。"
        "可选提供 no_increment_verdicts：仅当你确认某主干维度在本命题下"
        "与通用做法完全相同、确实不存在任何专项规则/取值/判定式时才裁决，"
        "每项必须给出 reason（为什么无增量），且不能给已有规则的维度下裁决。",
        {
            "findings": [
                {
                    "question": BRIEF_QUESTIONS[0],
                    "answer": "……",
                    "structural_hit": False,
                    "loop_gap": None,
                    "counterexample": "击中时填反例描述；未击中为空串",
                },
                {
                    "question": BRIEF_QUESTIONS[1],
                    "answer": "……",
                    "structural_hit": False,
                    "loop_gap": None,
                    "counterexample": "",
                },
                {
                    "question": BRIEF_QUESTIONS[2],
                    "answer": "……",
                    "structural_hit": False,
                    "loop_gap": None,
                    "counterexample": "",
                },
                {
                    "question": BRIEF_QUESTIONS[3],
                    "answer": "无；或逐条列出遗漏的必答项（如：未考虑负摩阻力）",
                    "structural_hit": False,
                    "loop_gap": None,
                    "counterexample": "",
                },
            ],
            "no_increment_verdicts": [
                {
                    "dimension": "来自 coverage_dimensions 的维度名",
                    "reason": "为何本命题下该维度与通用做法完全相同、无专项增量",
                }
            ],
        },
        ["findings"],
    ),
    REWRITE_FOCUS: _spec(
        REWRITE_FOCUS,
        "已命中「怀疑者空转」失败模式：最近三次审查无一击中结构问题。"
        "请重写异议焦点，使下一次简审指向真正的结构/教学脆弱点。",
        {"new_focus": "新的异议焦点与提问方向"},
        ["new_focus"],
    ),
    DEEP_REVIEW: _spec(
        DEEP_REVIEW,
        "执行深审（四项全成立才 passed=true）：\n"
        "1. 显式化关键前提：列出解释成立所依赖的、但未在解释中明说的前提假设。\n"
        "2. 检查概念边界：解释的适用范围是否清晰？边界外的场景是否被明确排除？\n"
        "3. 主动构造反例并判断是否击穿核心解释（counterexample_pierces）：\n"
        "   ——你必须主动构造至少一个具体、可操作的场景作为反例来压测当前解释。\n"
        "   ——好的反例：极端但现实的参数组合（如零基础学习者面对纯探究式任务）、\n"
        "    边界条件外推（如极端工期下规范条款的适用性）、已知反例库中的标准反例。\n"
        "   ——坏的回避：说「当前解释足够稳健、无明显反例」而不给出具体场景。\n"
        "   ——若构造的反例确实击穿了核心解释，counterexample_pierces=true，\n"
        "    必须在 counterexample 字段中写下该反例的完整描述，并在 passed=false 的\n"
        "    同时通过 loop_gap 指定回流学习循环的缺口方向。\n"
        "   ——若你构造了反例但经分析后确认它不击穿，counterexample_pierces=false，\n"
        "    但仍需在 counterexample 字段中列出你尝试过的反例场景及其不击穿的原因，\n"
        "    以证明你确实主动执行了压测而非跳过。\n"
        "4. 判断当前结构是否只对高认知用户成立（only_high_cognition）：\n"
        "   解释是否需要大量领域背景知识才能理解？初学者能否跟上逻辑链？\n\n"
        "可选提供 no_increment_verdicts：仅当确认某主干维度在本命题下"
        "与通用做法完全相同、不存在任何专项规则/取值/判定式时才裁决，"
        "每项必须给出 reason；不能给已有规则的维度下裁决（语义由内核拒绝）。",
        {
            "premises": ["显式化的关键前提1", "关键前提2"],
            "boundary_clear": True,
            "counterexample_pierces": False,
            "only_high_cognition": False,
            "passed": True,
            "critical_issue": "未通过时的关键问题；通过时为空串",
            "loop_gap": None,
            "counterexample": "击穿时填反例完整描述；未击穿时列出尝试过的反例场景及不击穿原因（不得为空串）",
            "no_increment_verdicts": [
                {
                    "dimension": "来自 coverage_dimensions 的维度名",
                    "reason": "为何本命题下该维度与通用做法完全相同、无专项增量",
                }
            ],
        },
        ["premises", "boundary_clear", "counterexample_pierces",
         "only_high_cognition", "passed"],
    ),
    COMPRESS: _spec(
        COMPRESS,
        "把通过审查的解释压缩为当前版本最稳解释。必须同时给出最稳解释、"
        "至少一个开放边界、以及为什么现在可以阶段收敛（稳/清/能教/开放）。"
        "给不出开放边界就不许收敛，应让 gap_statement 型判断把循环打回。"
        "若 context.stale_open_nodes 非空（规则已沉淀但节点状态仍 open 的"
        "悬置子问题），定稿前必须逐个显式处置：规则确已答出的列入 "
        "stabilize_question_ids（随定稿回补 stable）；确属未决、允许带入"
        "新版本的列入 retain_open_questions，每项附非空 reason（自动并入"
        "开放边界）。两字段并集必须恰好覆盖 stale_open_nodes 全部 id，"
        "不得漏处置、不得引用不存在/已 stable 的 id、同一节点不得同时进两字段。",
        {
            "explanation": "当前版本最稳解释",
            "open_boundaries": ["至少一个尚未解决的边界/未决点"],
            "reason": "为什么现在可以阶段收敛",
            "stabilize_question_ids": [
                "可选；context.stale_open_nodes 中规则已答、随定稿回补 stable 的节点 id"
            ],
            "retain_open_questions": [
                {
                    "id": "可选；确属未决、允许保留 open 的节点 id",
                    "reason": "为何保留 open（非空，自动并入开放边界）",
                }
            ],
        },
        ["explanation", "open_boundaries", "reason"],
    ),
    ASSESS_USER: _spec(
        ASSESS_USER,
        "基于用户本轮消息，形成当前命题下的用户理解假设。它是可被下一轮修正的"
        "假设，不是长期画像；只用于约束对外表达，不用于限制内部学习深度。",
        {
            "level": "用户在本命题上的大致理解层级",
            "block_type": "当前最明显卡点（如 概念缺口/结构缺口/缺乏直观/"
                          "关键误解/迁移缺口/状态不清）",
            "preferred_style": "当前更适合的讲解方式",
            "note": "假设依据",
        },
        ["level", "block_type", "preferred_style"],
    ),
    PLAN_TEACHING: _spec(
        PLAN_TEACHING,
        "依据用户假设选择本轮教学路径。dialog_goal 与 teaching_action 只能取"
        "给定枚举；一轮只有一个主动作（auxiliary_actions 仅作辅助）。"
        "换路径必须体现理解顺序的重建，而不是语气或篇幅变化。",
        {
            "dialog_goal": " | ".join(DIALOG_GOALS),
            "teaching_action": " | ".join(TEACHING_ACTIONS),
            "auxiliary_actions": [],
            "reason": "为什么是这个目标与主动作",
        },
        ["dialog_goal", "teaching_action", "reason"],
    ),
    TEACH: _spec(
        TEACH,
        "按已选定的唯一主动作产出本轮教学回应。要给用户一条可吸收的理解路径，"
        "适度超前形成牵引，并在合适处把用户从接受知识推向自己生成问题。",
        {"reply": "给用户的教学回应", "path_note": "本回应如何体现主动作"},
        ["reply"],
    ),
    ASSESS_MIGRATION_OUTPUT: _spec(
        ASSESS_MIGRATION_OUTPUT,
        "怀疑者判分：检查用户在迁移练习中的产出是否真正应用了命题的核心结构，"
        "而非表面套用。通过则教学成功；未通过则暴露结构缺口并回流学习循环。",
        {
            "passed": True,
            "structure_applied": "产出中应用了命题的哪个核心结构（通过时必填）",
            "gap_if_failed": "未通过时暴露的结构缺口描述（未通过时必填，通过时为空串）",
            "note": "判分依据",
        },
        ["passed", "note"],
    ),
    READ_FEEDBACK: _spec(
        READ_FEEDBACK,
        "解读用户对上一条教学回应的反馈。understood=false 时，failure_kind "
        "只能取：动作选错 / 解释跳步 / 用户假设错误 / 理解不成熟。"
        "不默认归因于用户水平；解释跳步与理解不成熟会触发回流学习循环。",
        {
            "understood": False,
            "failure_kind": "动作选错 | 解释跳步 | 用户假设错误 | 理解不成熟",
            "misconception_signal": "新识别到的误解信号，没有则为空串",
            "note": "判断依据",
        },
        ["understood", "note"],
    ),
}


def build_request(
    name: str,
    state_snapshot: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> JudgmentRequest:
    if name not in REGISTRY:
        raise JudgmentError(f"未知判断点: {name}")
    spec = REGISTRY[name]
    return JudgmentRequest(
        name=name,
        instruction=spec["instruction"],
        state_snapshot=state_snapshot,
        context=context or {},
        response_template=spec["template"],
        required_fields=list(spec["required"]),
    )


def validate(name: str, response: Any) -> dict[str, Any]:
    """形状校验。语义级校验（如命题回连、三问文本）由角色模块/内核补充。"""
    if name not in REGISTRY:
        raise JudgmentError(f"未知判断点: {name}")
    if not isinstance(response, dict):
        raise JudgmentError("判断响应必须是 JSON 对象")
    spec = REGISTRY[name]
    for field_name in spec["required"]:
        if field_name not in response:
            raise JudgmentError(f"判断响应缺少必填字段: {field_name}")
        value = response[field_name]
        if value is None or (isinstance(value, str) and not value.strip()):
            # gap_statement 允许为空串（表示无缺口），但它不在 required 语义内被禁
            if not (name == IDENTIFY_GAP and field_name == "gap_statement"):
                raise JudgmentError(f"判断响应字段不能为空: {field_name}")

    if name == ANCHOR:
        dims = response.get("coverage_dimensions")
        if not isinstance(dims, list):
            raise JudgmentError("coverage_dimensions 必须是列表")
        sources = response.get("dimension_sources")
        if not isinstance(sources, list) or not sources:
            raise JudgmentError(
                "锚定必须提供非空 dimension_sources（每维度一条推导链）"
            )
        for i, item in enumerate(sources):
            if not isinstance(item, dict):
                raise JudgmentError(f"dimension_sources[{i}] 必须是对象")
            if not str(item.get("dimension", "")).strip():
                raise JudgmentError(f"dimension_sources[{i}] 缺少非空 dimension")
            kind = str(item.get("kind", "")).strip()
            if kind not in DIM_SOURCE_ANCHOR_KINDS:
                raise JudgmentError(
                    f"dimension_sources[{i}] kind 非法: {kind!r}，"
                    f"合法值 {sorted(DIM_SOURCE_ANCHOR_KINDS)}"
                )
            if not isinstance(item.get("source_qualifier", ""), str):
                raise JudgmentError(f"dimension_sources[{i}] source_qualifier 必须是字符串")
            if not isinstance(item.get("reason", ""), str):
                raise JudgmentError(f"dimension_sources[{i}] reason 必须是字符串")
            related = item.get("related_phases", [])
            if not isinstance(related, list) or not all(
                isinstance(p, str) and p.strip() for p in related
            ):
                raise JudgmentError(
                    f"dimension_sources[{i}] related_phases 必须是字符串列表"
                )
        # 语义校验（限定词回指、横切理由、related_phases 指向阶段）由 learner.anchor 负责
    if name == IDENTIFY_GAP:
        gt = response.get("gap_type", "")
        if gt and gt not in GAP_TYPES:
            raise JudgmentError(f"gap_type 非法: {gt}；合法值: {GAP_TYPES}")
    if name == BRIEF_REVIEW:
        findings = response.get("findings")
        if not isinstance(findings, list) or len(findings) != 4:
            raise JudgmentError("简审必须恰好包含四问 findings（含领域完备性第四问）")
        for i, item in enumerate(findings):
            if not isinstance(item, dict):
                raise JudgmentError(f"第 {i + 1} 问格式非法")
            if item.get("question") != BRIEF_QUESTIONS[i]:
                raise JudgmentError(
                    f"第 {i + 1} 问必须固定为：{BRIEF_QUESTIONS[i]}"
                )
            if "answer" not in item or "structural_hit" not in item:
                raise JudgmentError(f"第 {i + 1} 问缺少 answer/structural_hit")
    if name == DEEP_REVIEW:
        for bool_field in (
            "boundary_clear",
            "counterexample_pierces",
            "only_high_cognition",
            "passed",
        ):
            if not isinstance(response.get(bool_field), bool):
                raise JudgmentError(f"深审字段 {bool_field} 必须为布尔值")
        if not isinstance(response.get("premises"), list) or not response["premises"]:
            raise JudgmentError("深审必须显式化至少一个关键前提")
    if name == LEARN:
        rules = response.get("dimension_rules")
        if rules is not None:
            if not isinstance(rules, list):
                raise JudgmentError("dimension_rules 必须是列表")
            for i, item in enumerate(rules):
                if not isinstance(item, dict):
                    raise JudgmentError(f"dimension_rules[{i}] 必须是对象")
                if not str(item.get("dimension", "")).strip():
                    raise JudgmentError(f"dimension_rules[{i}] 缺少非空 dimension")
                if not str(item.get("rule", "")).strip():
                    raise JudgmentError(f"dimension_rules[{i}] 缺少非空 rule")
                if "basis" in item and not isinstance(item["basis"], str):
                    raise JudgmentError(f"dimension_rules[{i}] basis 必须是字符串")
                if "heuristic" in item and not isinstance(item["heuristic"], bool):
                    raise JudgmentError(f"dimension_rules[{i}] heuristic 必须是布尔值")
        evidence = response.get("evidence")
        if evidence is not None:
            if not isinstance(evidence, list):
                raise JudgmentError("evidence 必须是列表")
            for i, item in enumerate(evidence):
                if not isinstance(item, dict):
                    raise JudgmentError(f"evidence[{i}] 必须是对象")
                if "citation" in item and not isinstance(item["citation"], str):
                    raise JudgmentError(f"evidence[{i}] citation 必须是字符串（规范编号级出处）")
        new_subs = response.get("new_sub_questions")
        if new_subs is not None:
            if not isinstance(new_subs, list):
                raise JudgmentError("new_sub_questions 必须是列表")
            for i, item in enumerate(new_subs):
                if not isinstance(item, dict):
                    raise JudgmentError(f"new_sub_questions[{i}] 必须是对象")
                if not str(item.get("id", "")).strip() or not str(item.get("text", "")).strip():
                    raise JudgmentError(f"new_sub_questions[{i}] 缺少 id/text")
                if "parent_id" in item and not isinstance(item["parent_id"], str):
                    raise JudgmentError(f"new_sub_questions[{i}] parent_id 必须是字符串")
    if name in (BRIEF_REVIEW, DEEP_REVIEW):
        verdicts = response.get("no_increment_verdicts")
        if verdicts is not None:
            if not isinstance(verdicts, list):
                raise JudgmentError("no_increment_verdicts 必须是列表")
            for i, item in enumerate(verdicts):
                if not isinstance(item, dict):
                    raise JudgmentError(f"no_increment_verdicts[{i}] 必须是对象")
                if not str(item.get("dimension", "")).strip():
                    raise JudgmentError(f"no_increment_verdicts[{i}] 缺少非空 dimension")
                if not str(item.get("reason", "")).strip():
                    raise JudgmentError(f"no_increment_verdicts[{i}] 缺少非空 reason（无增量裁决必须说明理由）")
    if name == COMPRESS:
        bounds = response.get("open_boundaries")
        if not isinstance(bounds, list) or not bounds:
            raise JudgmentError("阶段压缩必须给出至少一个开放边界")
        stabilize_ids = response.get("stabilize_question_ids")
        if stabilize_ids is not None:
            if not isinstance(stabilize_ids, list):
                raise JudgmentError("stabilize_question_ids 必须是列表")
            for qid in stabilize_ids:
                if not str(qid).strip():
                    raise JudgmentError("stabilize_question_ids 中存在空 id")
        retain = response.get("retain_open_questions")
        if retain is not None:
            if not isinstance(retain, list):
                raise JudgmentError("retain_open_questions 必须是列表")
            for i, item in enumerate(retain):
                if not isinstance(item, dict):
                    raise JudgmentError(f"retain_open_questions[{i}] 必须是对象")
                if not str(item.get("id", "")).strip():
                    raise JudgmentError(f"retain_open_questions[{i}] 缺少非空 id")
                if not str(item.get("reason", "")).strip():
                    raise JudgmentError(
                        f"retain_open_questions[{i}] 缺少非空 reason"
                        "（保留 open 必须给出理由）"
                    )
    if name == PLAN_TEACHING:
        if response["dialog_goal"] not in DIALOG_GOALS:
            raise JudgmentError(f"dialog_goal 非法: {response['dialog_goal']}")
        if response["teaching_action"] not in TEACHING_ACTIONS:
            raise JudgmentError(
                f"teaching_action 非法: {response['teaching_action']}"
            )
    if name == READ_FEEDBACK:
        if not isinstance(response.get("understood"), bool):
            raise JudgmentError("understood 必须为布尔值")
        if not response["understood"]:
            valid_kinds = {"动作选错", "解释跳步", "用户假设错误", "理解不成熟"}
            if response.get("failure_kind") not in valid_kinds:
                raise JudgmentError(
                    f"failure_kind 非法: {response.get('failure_kind')}"
                )
    if name == ASSESS_MIGRATION_OUTPUT:
        if not isinstance(response.get("passed"), bool):
            raise JudgmentError("passed 必须为布尔值")
        if response["passed"]:
            if not str(response.get("structure_applied", "")).strip():
                raise JudgmentError("通过时必须说明应用了命题的哪个核心结构")
        else:
            if not str(response.get("gap_if_failed", "")).strip():
                raise JudgmentError("未通过时必须描述暴露的结构缺口")
    if name == EXPAND_TREE:
        subs = response.get("sub_questions")
        if not isinstance(subs, list) or len(subs) < 2:
            raise JudgmentError("问题树至少需要两个关键子问题")
        dims = set()
        for item in subs:
            if not isinstance(item, dict) or not item.get("id") or not item.get("text"):
                raise JudgmentError("每个子问题需要 id 与 text")
            if "parent_id" in item and not isinstance(item["parent_id"], str):
                raise JudgmentError(
                    f"子问题 {item.get('id')} 的 parent_id 必须是字符串"
                )
            dim = str(item.get("dimension", "")).strip()
            if not dim:
                raise JudgmentError(
                    f"子问题 {item.get('id')} 缺少 dimension 主干维度标签"
                )
            dims.add(dim)
        if len(dims) < 2:
            raise JudgmentError(
                "问题树至少要覆盖两个不同的主干维度（先宽后深），"
                f"当前只有：{sorted(dims)}"
            )
    return response


def build_autonomous_request(
    stage: str,
    topic: Any,
    context: dict[str, Any] | None = None,
) -> JudgmentRequest:
    """Build a model-neutral request for one vNext agent-owned stage."""
    if stage not in _AUTONOMOUS_AGENT_SPECS:
        raise JudgmentError(f"unknown autonomous agent stage: {stage}")
    instruction, required = _AUTONOMOUS_AGENT_SPECS[stage]
    snapshot = topic.to_dict() if hasattr(topic, "to_dict") else dict(topic)
    return JudgmentRequest(
        name=stage,
        instruction=instruction,
        state_snapshot=snapshot,
        context=dict(context or {}),
        response_template={field_name: None for field_name in required},
        required_fields=list(required),
    )


def validate_autonomous_response(
    stage: str,
    response: Any,
) -> dict[str, Any]:
    """Validate the response envelope without judging its semantic truth."""
    if stage not in _AUTONOMOUS_AGENT_SPECS:
        raise JudgmentError(f"unknown autonomous agent stage: {stage}")
    if not isinstance(response, dict):
        raise JudgmentError("autonomous stage response must be a JSON object")
    _, required = _AUTONOMOUS_AGENT_SPECS[stage]
    for field_name in required:
        if field_name not in response:
            raise JudgmentError(
                f"autonomous stage response missing field: {field_name}"
            )
        value = response[field_name]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise JudgmentError(
                f"autonomous stage response field cannot be empty: {field_name}"
            )
    return response


def build_initialize_topic_request(
    *,
    topic_id: str,
    proposition: str,
) -> JudgmentRequest:
    """Build the public-host-only durable topic initialization request."""
    return JudgmentRequest(
        name=INITIALIZE_TOPIC,
        instruction=(
            "Create a normalized durable topic seed from the proposition. "
            "Provide a concise title, the normalized proposition, at least "
            "two coverage dimensions, and complete initial entity collections."
        ),
        state_snapshot={},
        context={"topic_id": topic_id, "proposition": proposition},
        response_template={
            "title": "normalized title",
            "proposition": "normalized proposition",
            "coverage_dimensions": [
                "coverage dimension one",
                "coverage dimension two",
            ],
            "claims": [],
            "evidence": [],
            "gaps": [],
            "counterexamples": [],
        },
        required_fields=list(_INITIALIZE_TOPIC_FIELDS),
    )


def validate_initialize_topic_response(response: Any) -> dict[str, Any]:
    """Validate and normalize the public-host durable topic seed response."""
    if not isinstance(response, dict):
        raise JudgmentError("initialize_topic response must be a JSON object")
    missing = [field for field in _INITIALIZE_TOPIC_FIELDS if field not in response]
    if missing:
        raise JudgmentError(
            "initialize_topic response missing fields: "
            f"{', '.join(missing)}"
        )
    title = response["title"]
    proposition = response["proposition"]
    if not isinstance(title, str) or not title.strip():
        raise JudgmentError("initialize_topic title must be non-empty")
    if not isinstance(proposition, str) or not proposition.strip():
        raise JudgmentError("initialize_topic proposition must be non-empty")
    dimensions = response["coverage_dimensions"]
    if not isinstance(dimensions, list) or len(dimensions) < 2:
        raise JudgmentError(
            "initialize_topic requires at least two coverage_dimensions"
        )
    normalized_dimensions = []
    for index, dimension in enumerate(dimensions):
        if not isinstance(dimension, str) or not dimension.strip():
            raise JudgmentError(
                "initialize_topic coverage_dimensions["
                f"{index}] must be non-empty"
            )
        normalized_dimensions.append(dimension.strip())
    if len(set(normalized_dimensions)) != len(normalized_dimensions):
        raise JudgmentError(
            "initialize_topic coverage_dimensions must be unique"
        )
    normalized = {
        "title": title.strip(),
        "proposition": proposition.strip(),
        "coverage_dimensions": normalized_dimensions,
    }
    for field in ("claims", "evidence", "gaps", "counterexamples"):
        value = response[field]
        if not isinstance(value, list):
            raise JudgmentError(f"initialize_topic {field} must be a list")
        normalized[field] = value
    return normalized
