"""概念型命题用例：什么是学习方法的形成。

eval 要点：
- 纯概念命题，两阶段维度（构成要素 / 形成过程），规则为逻辑判定式；
- 预埋一个内行必问缺口（形成之后如何抗遗忘/防退转），首轮简审由
  第四问（领域完备性）击中并回流，第二轮补齐——完备性命中率的确定性基线；
- 二级节点 q3 在学习轮中始终未回补 stable，靠压缩定稿的
  stabilize_question_ids 随版本闭合——验证 stale-open 处置端到端路径。
"""

from __future__ import annotations

from scripts.judgments import BRIEF_QUESTIONS
from scripts.schema import GapType, TriggerSource

from tests.behavior.eval.base import CasePack, ExpectProfile, TeachingUser, gap_judgment

PROP = "什么是学习方法的形成"


class ConceptCase(CasePack):
    def __init__(self) -> None:
        super().__init__(
            id="concept",
            label="概念型",
            proposition=PROP,
            expect=ExpectProfile(
                brief_hits=1,
                completeness_hits=1,
                deep_pierces=0,
                gate_rejections=0,
                boundaries_min=2,
            ),
            users=[
                TeachingUser("术语薄弱型", "我不懂，学习方法到底是什么意思？", "先定义"),
                TeachingUser("结构混乱型", "要素和过程这些说法我都见过，但串不起来，分不清先后。", "先搭框架"),
                TeachingUser("理解但不会迁移型", "核心我懂了，想换个场景练迁移，怎么用到背单词上？", "先做迁移"),
            ],
            teach_replies={
                "先定义": (
                    "先稳住定义：学习方法不是一条技巧，而是「可重复的做法」——"
                    "它由动作、触发条件和反馈修正三部分构成；「形成」指的是这套做法"
                    "经过反复使用和修正，从刻意提醒变成稳定习惯的过程。"
                ),
                "先搭框架": (
                    "给你一条主线：先有三要素（动作/触发/修正），再走三步形成过程"
                    "（识别情境→刻意重复→反馈修正），最后还要过抗退转这一关。"
                    "你现在卡住的是把「要素」当成了「过程」——要素是零件，过程是装配线。"
                ),
                "先做迁移": (
                    "做个迁移：把「形成过程」套到背单词上——触发情境是什么、"
                    "重复环节怎么设计、依据什么反馈修正？写三句，我只看结构对不对。"
                ),
            },
            migration_structure="应用了「触发情境→刻意重复→反馈修正」的形成过程结构",
        )

    def anchor(self, ctx: dict) -> dict:
        text = ctx.get("raw_proposition", PROP).strip()
        return {
            "proposition_text": text,
            "proposition_scope": "只讨论学习方法本身的构成与形成过程，不讨论具体学科提分技巧",
            "adjacent_topics": [
                "天赋、性格等个体差异对学习的影响（与方法形成相关但不等同）",
                "具体学科的学习资料与工具评测",
            ],
            "scope_qualifiers": ["学习方法", "形成"],
            "coverage_dimensions": ["构成要素", "形成过程"],
            "dimension_sources": [
                {"dimension": "构成要素", "kind": "phase",
                 "source_qualifier": "学习方法", "reason": "", "related_phases": []},
                {"dimension": "形成过程", "kind": "phase",
                 "source_qualifier": "形成", "reason": "", "related_phases": []},
            ],
        }

    def tree(self, state: dict, ctx: dict) -> dict:
        return {
            "root_question": "「学习方法的形成」如何成立？",
            "sub_questions": [
                {"id": "q1", "text": "学习方法由哪些构成要素？",
                 "dimension": "构成要素", "depends_on": [], "parent_id": ""},
                {"id": "q2", "text": "这些要素经过什么过程才形成稳定方法？",
                 "dimension": "形成过程", "depends_on": ["q1"], "parent_id": ""},
                {"id": "q3", "text": "形成之后靠什么抵抗遗忘与半途而废？",
                 "dimension": "形成过程", "depends_on": ["q2"], "parent_id": "q2"},
            ],
            "priority_id": "q1",
        }

    def gap(self, state: dict, ctx: dict) -> dict:
        if state.get("round_count", 0) == 0 and not state.get("gap", {}).get("gap_statement"):
            return gap_judgment(
                GapType.CONCEPT.value,
                "构成要素尚未稳定定义，「形成」无从谈起",
                "要素不清就描述过程，只会得到坚持、自律这类口号",
            )
        return gap_judgment(
            GapType.STRUCTURE.value,
            "解释只覆盖「学会」而未覆盖「不退转」，形成过程缺少巩固环节",
            "内行必问：形成之后如何对抗遗忘与半途而废；缺这一环，方法会被误描述成一次性动作",
            source=TriggerSource.SKEPTIC.value,
        )

    def learn(self, state: dict, ctx: dict) -> dict:
        prop = state["proposition"]["proposition_text"]
        attempt = int(ctx.get("attempt", 0))
        if attempt == 0:
            return {
                "stage_explanation": (
                    f"关于「{prop}」的阶段性解释 v0.1：学习方法是一套可重复的做法，"
                    "由动作序列、触发条件、反馈修正三个要素构成；三要素齐备后，"
                    "经过反复使用就「形成」了。"
                ),
                "understanding_change": "从「方法=技巧清单」推进到「方法=三要素齐备的可重复做法」",
                "driver": "概念缺口推动：先稳住构成要素定义",
                "proposition_link": f"使「{prop}」从模糊印象变成可拆解的对象",
                "resolved_gap": False,
                "stable_question_ids": ["q1"],
                "new_sub_questions": [],
                "next_priority_id": "q2",
                "competing_explanations": False,
                "dimension_rules": [
                    {
                        "dimension": "构成要素",
                        "rule": "方法构成判定式：可重复动作序列＋明确触发条件＋反馈修正方式三者齐备才构成学习方法；只有心愿或资料堆积不构成方法",
                    }
                ],
            }
        return {
            "stage_explanation": (
                f"关于「{prop}」的阶段性解释 v0.2：形成不是一次性学会，而是一条"
                "「识别触发情境→刻意重复→依据反馈修正」的闭环，且必须跨情境复现；"
                "闭环之后还要接入巩固环节（间隔复练、环境绑定、复发预案）抵抗遗忘与半途而废，"
                "缺少巩固的方法只是短期技巧。"
            ),
            "understanding_change": (
                "补上了 v0.1 缺失的后半程：形成包含「沉淀」与「不退转」两件事，"
                "巩固是形成过程的必要环节而非形成之后的附加维护"
            ),
            "driver": "简审第四问（领域完备性）推动：内行必问「形成之后如何不退转」",
            "proposition_link": (
                f"「{prop}」的答案从「三要素+重复」修正为「三要素经闭环沉淀并接入巩固」，"
                "形成的成立条件完整"
            ),
            "resolved_gap": True,
            # q3 故意不在学习轮回补 stable：其答案已由巩固规则覆盖，
            # 应由压缩定稿经 stabilize_question_ids 显式闭合（eval stale-open 路径）
            "stable_question_ids": ["q2"],
            "new_sub_questions": [],
            "next_priority_id": "q3",
            "competing_explanations": False,
            "dimension_rules": [
                {
                    "dimension": "形成过程",
                    "rule": "形成过程判定式：新做法须经「触发情境识别→刻意重复→依据反馈修正」闭环并跨情境复现，才从临时技巧沉淀为方法",
                },
                {
                    "dimension": "形成过程",
                    "rule": "巩固环节判定式：闭环之后必须接入间隔复练、环境绑定与复发预案三者中至少两项，否则方法在中断后不可自行恢复，不算形成完成",
                },
                {
                    "dimension": "形成过程",
                    "rule": "经验量级：新做法连续执行约2～3周后才进入不假思索的自动化前期，个体差异大，不得当作固定疗程",
                    "heuristic": True,
                },
            ],
        }

    def brief(self, state: dict, ctx: dict) -> dict:
        attempt = int(ctx.get("attempt", 0))
        q1, q2, q3, q4 = BRIEF_QUESTIONS
        if attempt == 0:
            return {"findings": [
                {"question": q1, "answer": "三要素定义暂时可用，没有发现关键结构错误",
                 "structural_hit": False, "loop_gap": None},
                {"question": q2, "answer": "天赋决定论是另一层面解释，暂不替代本命题",
                 "structural_hit": False, "loop_gap": None},
                {"question": q3, "answer": "教初学者时三要素能讲清，教学暴露点暂无断裂",
                 "structural_hit": False, "loop_gap": None},
                {"question": q4,
                 "answer": "存在必答项：任何内行都会追问「形成之后如何不退转」，当前解释把形成当成一次性动作，完全没有巩固/抗遗忘环节",
                 "structural_hit": True,
                 "loop_gap": {
                     "gap_type": GapType.STRUCTURE.value,
                     "gap_statement": "形成过程缺少巩固环节，未覆盖「形成之后如何抵抗遗忘与半途而废」",
                     "why_priority": "没有巩固环节，方法会被误描述为一次性学会，迁移到任何真实场景都会在中断后失效",
                     "trigger_source": TriggerSource.SKEPTIC.value,
                     "secondary_gaps": [],
                 }},
            ]}
        return {"findings": [
            {"question": q1, "answer": "巩固环节接入后，未发现新的关键结构脆弱点",
             "structural_hit": False, "loop_gap": None},
            {"question": q2, "answer": "「他律监督替代自我修正」是补充路径，不构成替代解释",
             "structural_hit": False, "loop_gap": None},
            {"question": q3, "answer": "可用「中断后能否自行恢复」作为教学检验点直接讲解",
             "structural_hit": False, "loop_gap": None},
            {"question": q4,
             "answer": "对照完备性提示，巩固/抗退转必答项已补齐，无新的内行必问遗漏",
             "structural_hit": False, "loop_gap": None},
        ]}

    def deep(self, state: dict, ctx: dict) -> dict:
        return {
            "premises": [
                "方法的形成以三要素齐备为前提，缺一不构成方法",
                "形成必须经过跨情境复现的修正闭环，而非一次性学会",
                "巩固是形成的必要环节，缺巩固的短期技巧不记为形成完成",
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
                "间隔复练的最优周期是否存在跨人群稳定参数，尚未结论",
                "儿童与成人形成同一方法所需重复次数的差异，未展开",
            ],
            "reason": (
                f"「{prop}」的构成与形成过程已概念清楚、判定式可教，"
                "且保留两个未决边界，符合「稳、清、能教、开放」"
            ),
        }
