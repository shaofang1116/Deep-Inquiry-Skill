"""争议型命题用例：高主动学习是否天然优于目标导向学习。

eval 要点：
- 两阶段维度（两方适用条件）+ 一横切维度（优劣判定的条件边界），
  横切一级节点必须 depends_on 两个阶段节点——验证维度推导链与依赖边；
- 简审不击中，由深审反例（零基础学生探究式学习反例）首次击穿→带反例冲突
  回流重学，第二轮深审通过——深审存在意义的确定性基线；
- 重学轮显式 competing_explanations=True，两种解释条件化共存而非选边；
- 二级节点 q4（新手期反转的定量阈值）确属未决，压缩定稿走
  retain_open_questions 带理由保留 open，并自动并入开放边界。
"""

from __future__ import annotations

from scripts.judgments import BRIEF_QUESTIONS
from scripts.schema import GapType, TriggerSource

from examples.eval.base import CasePack, ExpectProfile, TeachingUser, gap_judgment

PROP = "高主动学习是否天然优于目标导向学习"

RETAIN_REASON_Q4 = "新手期效果反转的定量阈值（先备知识/认知负荷切点）需实证研究，本版只给条件变量，不编造数值"


class ControversyCase(CasePack):
    def __init__(self) -> None:
        super().__init__(
            id="controversy",
            label="争议型",
            proposition=PROP,
            expect=ExpectProfile(
                brief_hits=0,
                completeness_hits=0,
                deep_pierces=1,
                gate_rejections=0,
                boundaries_min=3,  # 两条常规边界 + q4 retain 自动并入一条
                retain_open={"q4": RETAIN_REASON_Q4},
                competing=True,
            ),
            users=[
                TeachingUser("术语薄弱型", "这里说的主动学习是什么意思？我不懂这些术语。", "先定义"),
                TeachingUser("结构混乱型", "两种学习我都听过，但它们的适用条件分不清，一团混乱。", "先搭框架"),
                TeachingUser("理解但不会迁移型", "条件变量我理解了，想练迁移：怎么用到给新员工设计培训上？", "先做迁移"),
            ],
            teach_replies={
                "先定义": (
                    "先稳住两个词。高主动学习：学习者自己决定学什么、按什么顺序、用什么材料；"
                    "目标导向学习：目标和验收标准先定好，学习围绕达标组织。"
                    "注意这题问的是「是否天然优于」——答案不是二选一，而是看条件。"
                ),
                "先搭框架": (
                    "给你一条主线：① 各自的生效条件；② 条件切换时效果反转；"
                    "③ 不存在无条件排序。你卡住的地方是把「哪种更好」当成了固定属性，"
                    "它其实是先备知识、认知负荷、反馈质量、任务结构四个变量的函数。"
                ),
                "先做迁移": (
                    "做个迁移：给新员工设计培训时，这四个变量分别取什么值？"
                    "什么时候该给高自主（选修/项目制），什么时候该强目标（清单/考核）？"
                    "写三句条件式结论，我只看结构对不对。"
                ),
            },
            migration_structure="应用了四变量条件化判定，未做无条件选边",
        )

    def anchor(self, ctx: dict) -> dict:
        text = ctx.get("raw_proposition", PROP).strip()
        return {
            "proposition_text": text,
            "proposition_scope": "只比较两类学习方式在不同条件下的相对效果，不评价具体课程产品",
            "adjacent_topics": [
                "学习风格（视觉型/听觉型）等人格化分类理论",
                "具体学校与课程体系的排名比较",
            ],
            "scope_qualifiers": ["高主动学习", "目标导向学习"],
            "coverage_dimensions": ["高主动学习的适用条件", "目标导向学习的适用条件", "优劣判定的条件边界"],
            "dimension_sources": [
                {"dimension": "高主动学习的适用条件", "kind": "phase",
                 "source_qualifier": "高主动学习", "reason": "", "related_phases": []},
                {"dimension": "目标导向学习的适用条件", "kind": "phase",
                 "source_qualifier": "目标导向学习", "reason": "", "related_phases": []},
                {"dimension": "优劣判定的条件边界", "kind": "cross_cutting",
                 "source_qualifier": "",
                 "reason": "争议命题需要横切两方证据的判定维度：优劣不属任一方，是条件变量的函数",
                 "related_phases": ["高主动学习的适用条件", "目标导向学习的适用条件"]},
            ],
        }

    def tree(self, state: dict, ctx: dict) -> dict:
        return {
            "root_question": "「高主动学习是否天然优于目标导向学习」在什么条件下成立？",
            "sub_questions": [
                {"id": "q1", "text": "高主动学习在什么条件下更有效？",
                 "dimension": "高主动学习的适用条件", "depends_on": [], "parent_id": ""},
                {"id": "q2", "text": "目标导向学习在什么条件下更有效？",
                 "dimension": "目标导向学习的适用条件", "depends_on": ["q1"], "parent_id": ""},
                {"id": "q3", "text": "两者的优劣按哪些条件变量判定？",
                 "dimension": "优劣判定的条件边界", "depends_on": ["q1", "q2"], "parent_id": ""},
                {"id": "q4", "text": "新手期两方效果为什么会发生反转？",
                 "dimension": "优劣判定的条件边界", "depends_on": ["q3"], "parent_id": "q3"},
            ],
            "priority_id": "q1",
        }

    def gap(self, state: dict, ctx: dict) -> dict:
        if state.get("round_count", 0) == 0 and not state.get("gap", {}).get("gap_statement"):
            return gap_judgment(
                GapType.CONCEPT.value,
                "两种学习方式的作用机制未分开，比较缺少共同刻度",
                "不先界定各自生效条件就回答优劣，只会得到立场表态",
            )
        return gap_judgment(
            GapType.COUNTEREXAMPLE.value,
            "深审反例击穿：零基础学生在完全探究式环境中效果低于直接指导，"
            "「高主动天然更优」的无条件结论不成立",
            "反例直接否定命题的无条件形式，必须把结论改写为条件式",
            source=TriggerSource.SKEPTIC.value,
        )

    def learn(self, state: dict, ctx: dict) -> dict:
        prop = state["proposition"]["proposition_text"]
        attempt = int(ctx.get("attempt", 0))
        if attempt == 0:
            return {
                "stage_explanation": (
                    f"关于「{prop}」的阶段性解释 v0.1：高主动学习让学习者自主选择内容与节奏，"
                    "投入度与远迁移更好，因此总体上优于被外部目标驱动的目标导向学习；"
                    "目标导向只适合应试等窄场景。"
                ),
                "understanding_change": "从「两种学习谁好」的站队问题，转为先描述高主动学习的作用机制",
                "driver": "概念缺口推动：先界定高主动学习的生效机制",
                "proposition_link": f"给出「{prop}」的初步肯定回答，但结论形态偏无条件",
                "resolved_gap": False,
                "stable_question_ids": ["q1"],
                "new_sub_questions": [],
                "next_priority_id": "q2",
                "competing_explanations": False,
                "dimension_rules": [
                    {
                        "dimension": "高主动学习的适用条件",
                        "rule": "高主动学习生效判定式：先备知识达门槛且认知负荷有余量时，自主选择提升投入度与远迁移；零基础时自由选择导致负荷过载，表现反降",
                    },
                    {
                        "dimension": "高主动学习的适用条件",
                        "rule": "经验量级：任务同时占用约4～5个陌生组块时，继续增加自主选择开始降效；切点因人差异大，属经验启发式",
                        "heuristic": True,
                    },
                ],
            }
        return {
            "stage_explanation": (
                f"关于「{prop}」的阶段性解释 v0.2（条件化结论）：不存在无条件优劣。"
                "高主动学习在先备知识足、认知负荷有余量、反馈质量高、任务结构开放时更优；"
                "目标导向学习在先备知识弱、任务边界清晰、需要快速达标的场景更优。"
                "两种解释不互相消灭而条件化共存：争议的正确出口是给出切换变量，"
                "而不是替一方背书。新手期反转是同一组变量的端点表现，"
                "但反转的定量切点仍需实证，本版不编造。"
            ),
            "understanding_change": (
                "反例迫使结论从「天然优于」改为「条件化优劣」；"
                "目标导向不再是窄场景例外，而是另一组条件下的更优解"
            ),
            "driver": "深审反例推动：零基础探究式学习反例击穿无条件结论",
            "proposition_link": f"「{prop}」的答案被改写为判定条件，命题的无条件形式被否定",
            "resolved_gap": True,
            "stable_question_ids": ["q2", "q3"],
            "new_sub_questions": [],
            "next_priority_id": "q4",
            "competing_explanations": True,
            "dimension_rules": [
                {
                    "dimension": "目标导向学习的适用条件",
                    "rule": "目标导向学习生效判定式：目标具体可测、反馈即时、任务边界清晰时收敛更快；目标僵化或反馈失真时退化为表面应付",
                },
                {
                    "dimension": "优劣判定的条件边界",
                    "rule": "统一排序判定式：不存在无条件优劣；结果随先备知识、认知负荷余量、反馈质量、任务结构四变量切换，输出必须是条件式结论而非选边",
                },
            ],
        }

    def brief(self, state: dict, ctx: dict) -> dict:
        # 争议型的冲突留给深审反例承担；两轮简审四问均不结构击中
        q1, q2, q3, q4 = BRIEF_QUESTIONS
        return {"findings": [
            {"question": q1, "answer": "当前层级的结构脆弱点留待深审用反例检验，简审不重复判击中",
             "structural_hit": False, "loop_gap": None},
            {"question": q2,
             "answer": "另一方解释已作为竞争解释保留，未被隐藏，是否构成替代由深审反例裁决",
             "structural_hit": False, "loop_gap": None},
            {"question": q3, "answer": "教学时会直接呈现两种条件分支，暂未发现必然露馅点",
             "structural_hit": False, "loop_gap": None},
            {"question": q4,
             "answer": "对照完备性提示，两方适用条件与判定边界均已在问题树中，无内行必问遗漏",
             "structural_hit": False, "loop_gap": None},
        ]}

    def deep(self, state: dict, ctx: dict) -> dict:
        # 压缩前 state.current_explanation 仍为空，被审文本在 ctx.stage_explanation：
        # 首轮 v0.1（无条件结论）击穿，重学后 v0.2（条件化结论）放行
        current = ctx.get("stage_explanation") or state["proposition"].get("current_explanation", "")
        pierce = "条件化结论" not in current
        if pierce:
            return {
                "premises": [
                    "待检验前提：高主动学习总体优于目标导向学习",
                    "待检验前提：目标导向只适合应试等窄场景",
                ],
                "boundary_clear": False,
                "counterexample_pierces": True,
                "only_high_cognition": False,
                "passed": False,
                "critical_issue": "无条件结论被零基础探究式学习反例击穿，必须改写为条件式",
                "counterexample": (
                    "完全探究式课堂对零基础学生的效果低于带直接指导的目标导向教学："
                    "先备知识不足时自主选择造成认知负荷过载"
                ),
                "loop_gap": {
                    "gap_type": GapType.COUNTEREXAMPLE.value,
                    "gap_statement": "零基础学生在完全探究式环境中效果低于直接指导，「高主动天然更优」的无条件结论不成立",
                    "why_priority": "反例否定命题的无条件形式，结论必须条件化",
                    "trigger_source": TriggerSource.SKEPTIC.value,
                    "secondary_gaps": [],
                },
            }
        return {
            "premises": [
                "优劣是先备知识、认知负荷、反馈质量、任务结构四变量的函数",
                "两种解释条件化共存，争议出口是切换变量而非选边",
                "新手期反转的定量切点未闭合，已作为开放边界保留",
            ],
            "boundary_clear": True,
            "counterexample_pierces": False,
            "only_high_cognition": False,
            "passed": True,
            "critical_issue": "",
            "loop_gap": None,
        }

    def compress_payload(self, state: dict, ctx: dict) -> dict:
        prop = state["proposition"]["proposition_text"]
        return {
            "open_boundaries": [
                "四变量之间是否存在交互效应（如反馈质量能否补偿先备知识不足），尚未展开",
                "组织层面（选拔制度、考核周期）如何改变两类学习的相对优势，未结论",
            ],
            "reason": (
                f"「{prop}」已收敛为条件化结论，竞争解释共存且边界清楚、可教学；"
                "未决切点显式保留，符合「稳、清、能教、开放」"
            ),
        }
