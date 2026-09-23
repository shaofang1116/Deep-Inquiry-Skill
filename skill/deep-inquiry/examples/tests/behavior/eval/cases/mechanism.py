"""机制型命题用例：怀疑机制如何避免伪理解。

内容从 examples/tests/behavior/scripted_judge.py 逐字迁入（2026-09 前的冒烟夹具），
行为必须与旧夹具等价：简审第三问首轮击中→回流重学，深审通过，
两个逻辑判定式规则分别落在两个维度，定稿保留两个开放边界。
"""

from __future__ import annotations

from scripts.judgments import BRIEF_QUESTIONS
from scripts.schema import GapType, TriggerSource

from tests.behavior.eval.base import CasePack, ExpectProfile, TeachingUser, gap_judgment

PROP = "怀疑机制如何避免伪理解"


class MechanismCase(CasePack):
    def __init__(self) -> None:
        super().__init__(
            id="mechanism",
            label="机制型",
            proposition=PROP,
            expect=ExpectProfile(
                brief_hits=1,
                completeness_hits=0,
                deep_pierces=0,
                gate_rejections=0,
                boundaries_min=2,
            ),
            users=[
                TeachingUser("术语薄弱型", "我第一次接触，伪理解到底是什么意思？完全不懂。", "先定义"),
                TeachingUser("结构混乱型", "这几个概念我都见过，但它们之间的关系我分不清，一团混乱。", "先搭框架"),
                TeachingUser("理解但不会迁移型", "核心机制我已经懂了，但怎么用到别的场景里？我想练迁移。", "先做迁移"),
            ],
            teach_replies={
                "先定义": (
                    "先用一句话稳住两个词。伪理解：解释听起来自洽、也能复述，"
                    "但一被追问前提或被拿去教别人就断。怀疑机制：不是「再想一遍」，"
                    "而是专门有人去找这个解释最可能断的地方。先记住这两个定义，"
                    "我们再看它们怎么咬合。"
                ),
                "先搭框架": (
                    f"先不补细节，给你一条主线串起「{PROP}」：① 学习产出一个解释；"
                    "② 怀疑者只找结构脆弱点，不做润色；③ 被击中的点必须改写成解释的新版本。"
                    "你现在卡住的不是某个词，而是②到③这一步——大多数系统停在②。"
                ),
                "先做迁移": (
                    f"结构你已经有了。做个迁移：不要复述「{PROP}」，"
                    "试着把这个回路套到「代码 review 为什么有时形同虚设」上——"
                    "对应②③分别是什么？写三句给我，我只看结构对不对。"
                ),
            },
            migration_structure="应用了「异议→显式缺口→解释重构」的回路结构",
        )

    def anchor(self, ctx: dict) -> dict:
        text = ctx.get("raw_proposition", PROP).strip()
        return {
            "proposition_text": text,
            "proposition_scope": f"围绕「{text}」本身如何成立、如何起作用展开，不延伸到周边主题",
            "adjacent_topics": [
                f"与「{text}」相关但不等同的资料搜集与工具评测",
                f"脱离「{text}」的一般学习理论与流派比较",
            ],
            "scope_qualifiers": ["怀疑机制", "避免伪理解"],
            "coverage_dimensions": ["概念定义", "作用机制"],
            "dimension_sources": [
                {"dimension": "概念定义", "kind": "phase",
                 "source_qualifier": "怀疑机制", "reason": "", "related_phases": []},
                {"dimension": "作用机制", "kind": "phase",
                 "source_qualifier": "避免伪理解", "reason": "", "related_phases": []},
            ],
        }

    def tree(self, state: dict, ctx: dict) -> dict:
        prop = state["proposition"]["proposition_text"]
        return {
            "root_question": f"如何理解「{prop}」？",
            "sub_questions": [
                {"id": "q1", "text": f"「{prop}」中的核心概念分别指什么？",
                 "dimension": "概念定义", "depends_on": [], "parent_id": ""},
                {"id": "q2", "text": "这些概念之间按什么关系形成机制？",
                 "dimension": "作用机制", "depends_on": ["q1"], "parent_id": ""},
                {"id": "q3", "text": "这套机制在什么条件下会失效？",
                 "dimension": "作用机制", "depends_on": ["q2"], "parent_id": "q2"},
            ],
            "priority_id": "q1",
        }

    def gap(self, state: dict, ctx: dict) -> dict:
        if state.get("round_count", 0) == 0 and not state.get("gap", {}).get("gap_statement"):
            return gap_judgment(
                GapType.CONCEPT.value,
                "核心术语尚未稳定定义，机制链条无从搭起",
                "概念不稳时直接谈机制，只会得到顺滑但空洞的叙述",
            )
        return gap_judgment(
            GapType.STRUCTURE.value,
            "概念之间的作用链条存在跳步，缺少一个关键中间环节",
            "已有概念定义，但机制解释在最关键处直接断言结论",
        )

    def learn(self, state: dict, ctx: dict) -> dict:
        prop = state["proposition"]["proposition_text"]
        attempt = int(ctx.get("attempt", 0))
        if state.get("round_count", 0) >= 1:
            return {
                "stage_explanation": (
                    f"关于「{prop}」的阶段性解释 v0.3：把反馈回路补上教学检验位——"
                    "学习者先把解释教给一个真实初学者，怀疑者只在「教学断链处」发起攻击；"
                    "断链被显式登记为教学缺口后，解释必须按初学者实际跟丢的那一步重写，"
                    "而不是换种说法重复。于是回路闭环为：学习产出解释 → 教学暴露断链 → "
                    "怀疑把断链结构化为缺口 → 解释按断链重构。"
                    "边界仍在：外部反馈与内部怀疑的分工、空转的客观检测信号尚未解决。"
                ),
                "understanding_change": (
                    "教学被纳入回路本身：它不是学习之后的输出环节，而是怀疑最可靠的触发源；"
                    "「跳步」这类教学反馈被识别为解释结构缺口，而非用户理解能力问题"
                ),
                "driver": "教学缺口推动：跳步反馈暴露了回路缺少真实检验位",
                "proposition_link": f"「{prop}」从内部怀疑回路扩展为教学驱动的闭环，成立条件更完整",
                "resolved_gap": True,
                "stable_question_ids": ["q3"],
                "new_sub_questions": [],
                "next_priority_id": None,
                "competing_explanations": False,
            }
        if attempt == 0:
            return {
                "stage_explanation": (
                    f"关于「{prop}」的阶段性解释 v0.1："
                    "系统只要在形成解释后安排一个怀疑环节，让怀疑者寻找反例和漏洞，"
                    "就能识别不可靠的自洽叙述，从而避免伪理解。"
                ),
                "understanding_change": "从「学会=搜集到正确资料」推进到「学会=经得住反驳」",
                "driver": "概念缺口推动：先补齐了「伪理解」与「怀疑」两个核心概念的定义",
                "proposition_link": f"使「{prop}」从口号变成了一个可描述的环节：学习之后接怀疑",
                "resolved_gap": False,
                "stable_question_ids": ["q1"],
                "new_sub_questions": [],
                "next_priority_id": "q2",
                "competing_explanations": False,
                "dimension_rules": [
                    {
                        "dimension": "概念定义",
                        "rule": "伪理解判定式：解释能复述，但被追问未声明前提或教给初学者即刻断链，即判定为伪理解而非学会",
                    }
                ],
            }
        return {
            "stage_explanation": (
                f"关于「{prop}」的阶段性解释 v0.2：怀疑机制避免伪理解，靠的不是「存在怀疑者」，"
                "而是一个反馈回路——怀疑者必须击中解释的结构脆弱点，学习者必须据此重构解释；"
                "前提是异议被显式化为可检验的缺口。若怀疑只产出礼节性反问而解释不变，"
                "怀疑本身就是伪理解的一部分（怀疑者空转）。"
            ),
            "understanding_change": (
                "发现 v0.1 隐含了未声明前提「怀疑必然有效」；"
                "补上中间环节「异议→显式缺口→解释重构」的反馈回路后，机制才闭合"
            ),
            "driver": "怀疑者简审第三问（教学暴露点）推动：教初学者时「怀疑者自己走过场怎么办」无法回答",
            "proposition_link": (
                f"「{prop}」的答案从「加一个怀疑环节」修正为「让怀疑能真正改写解释的回路」，"
                "命题的成立条件被明确"
            ),
            "resolved_gap": True,
            "stable_question_ids": ["q2"],
            "new_sub_questions": [],
            "next_priority_id": "q3",
            "competing_explanations": False,
            "dimension_rules": [
                {
                    "dimension": "作用机制",
                    "rule": "有效怀疑判定式：怀疑击中结构脆弱点且解释据此发生结构重构（而非措辞修补），才记为一轮有效怀疑；连续 3 轮解释无变化即判怀疑者空转",
                }
            ],
        }

    def brief(self, state: dict, ctx: dict) -> dict:
        attempt = int(ctx.get("attempt", 0))
        q1, q2, q3, q4 = BRIEF_QUESTIONS
        completeness_ok = {
            "question": q4,
            "answer": "对照完备性提示无遗漏：本命题讨论的是怀疑机制本身，"
                      "不存在该领域标准实践中被省略的内行必答项",
            "structural_hit": False,
            "loop_gap": None,
        }
        if state.get("round_count", 0) >= 1:
            return {"findings": [
                {"question": q1, "answer": "教学检验位补齐后，未发现新的关键结构脆弱点",
                 "structural_hit": False, "loop_gap": None},
                {"question": q2, "answer": "「教学只是输出而非检验」可被 v0.3 的断链登记机制直接反驳，不构成替代解释",
                 "structural_hit": False, "loop_gap": None},
                {"question": q3, "answer": "解释本身就以初学者跟丢的一步为起点展开，教学暴露点已成为机制部件",
                 "structural_hit": False, "loop_gap": None},
                dict(completeness_ok),
            ]}
        if attempt == 0:
            return {"findings": [
                {"question": q1, "answer": "「安排怀疑环节就能避免伪理解」可能只是相关而非因果，错误较轻微",
                 "structural_hit": False, "loop_gap": None},
                {"question": q2, "answer": "可能是外部检验而非内部怀疑在起作用，但证据不足，暂不构成替代",
                 "structural_hit": False, "loop_gap": None},
                {"question": q3,
                 "answer": "初学者立刻会问：怀疑者自己走过场怎么办？当前解释默认「怀疑必然有效」，这个前提没有显式化，一教就露馅",
                 "structural_hit": True,
                 "loop_gap": {
                     "gap_type": GapType.STRUCTURE.value,
                     "gap_statement": "解释隐含未声明前提「怀疑必然有效」，缺少异议驱动重构的中间环节",
                     "why_priority": "该前提不补上，整个机制建立在偶然性上，且教学时必然暴露",
                     "trigger_source": TriggerSource.SKEPTIC.value,
                     "secondary_gaps": [],
                 }},
                dict(completeness_ok),
            ]}
        return {"findings": [
            {"question": q1, "answer": "反馈回路的各环节都已显式化，未发现新的关键结构脆弱点",
             "structural_hit": False, "loop_gap": None},
            {"question": q2, "answer": "「外部检验更强」是补充而非替代：外部反馈也需经过同一回路才能改写解释",
             "structural_hit": False, "loop_gap": None},
            {"question": q3, "answer": "可用「怀疑者空转」作为边界案例直接教学，教学暴露点已变成解释的一部分",
             "structural_hit": False, "loop_gap": None},
            dict(completeness_ok),
        ]}

    def deep(self, state: dict, ctx: dict) -> dict:
        return {
            "premises": [
                "怀疑若要有效，异议必须显式化为可检验缺口",
                "解释必须因异议发生结构性重构，而非措辞修补",
                "怀疑者空转本身是伪理解的一种形态",
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
                "外部反馈（他人、实验、真实任务）与内部怀疑回路如何分工，尚未展开",
                "怀疑者空转除「重写异议焦点」外是否还有更稳的检测信号，尚未结论",
            ],
            "reason": (
                f"「{prop}」的核心机制已相对一致、概念清楚、可面向初学者转译，"
                "且仍明确保留两个未决边界，符合「稳、清、能教、开放」"
            ),
        }
