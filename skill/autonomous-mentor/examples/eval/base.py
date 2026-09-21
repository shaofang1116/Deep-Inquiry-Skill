"""CasePack 用例协议与确定性脚本宿主。

CasePack 声明一个命题用例的全部输入与期望画像；ScriptedHost 像「执行 Skill
的理想 agent」一样读 request.json 填 judgment.json，但内容全部来自用例脚本，
无模型、无随机。真实模型验证时替换 build_judgment 的来源即可，断言画像不变。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.judgments import (
    ANCHOR,
    ASSESS_MIGRATION_OUTPUT,
    ASSESS_USER,
    BRIEF_REVIEW,
    COMPRESS,
    DEEP_REVIEW,
    EXPAND_TREE,
    IDENTIFY_GAP,
    LEARN,
    PLAN_TEACHING,
    READ_FEEDBACK,
    REWRITE_FOCUS,
    TEACH,
)
from scripts.schema import GapType


@dataclass
class TeachingUser:
    name: str
    message: str
    expected_action: str


@dataclass
class ExpectProfile:
    """单用例的确定性断言画像（eval 固化的「尺子」）。"""

    brief_hits: int = 1                 # 简审四问累计击中次数（含第四问）
    completeness_hits: int = 0          # 其中第四问（领域完备性）击中次数
    deep_pierces: int = 0               # 深审反例击穿次数
    gate_rejections: int = 0            # 双条件闸门/覆盖闸门拦截次数（理想路径=0）
    boundaries_min: int = 2             # 定稿开放边界下限
    retain_open: dict[str, str] = field(default_factory=dict)  # 定稿保留 open 的节点→理由片段
    competing: bool = False             # 是否要求竞争解释共存（争议型）


@dataclass
class CasePack:
    id: str
    label: str                          # 机制型 / 概念型 / 争议型
    proposition: str
    expect: ExpectProfile
    users: list[TeachingUser]

    # ---- 学习循环：由子类/构造时给出的内容函数 ----
    def anchor(self, ctx: dict) -> dict:
        raise NotImplementedError

    def tree(self, state: dict, ctx: dict) -> dict:
        raise NotImplementedError

    def gap(self, state: dict, ctx: dict) -> dict:
        raise NotImplementedError

    def learn(self, state: dict, ctx: dict) -> dict:
        raise NotImplementedError

    def brief(self, state: dict, ctx: dict) -> dict:
        raise NotImplementedError

    def deep(self, state: dict, ctx: dict) -> dict:
        raise NotImplementedError

    def rewrite_focus(self, state: dict, ctx: dict) -> dict:
        return {
            "new_focus": "放弃重复「是否相关/证据够不够」类问法，"
                         "改问「这个解释教出去会在哪里立刻露馅」"
        }

    def compress_payload(self, state: dict, ctx: dict) -> dict:
        """返回 explanation/open_boundaries/reason；悬置处置由宿主统一补齐。"""
        raise NotImplementedError

    # ---- 教学循环 ----
    teach_replies: dict[str, str] = field(default_factory=dict)
    migration_structure: str = "应用了命题的核心结构"
    migration_note: str = "脚本判分：迁移产出结构正确"


class ScriptedHost:
    """按 CasePack 对 request.json 确定性产出 judgment 的宿主。"""

    def __init__(self, case: CasePack):
        self.case = case

    def build_judgment(self, request: dict[str, Any]) -> dict[str, Any]:
        name = request["judgment"]
        state = request.get("state_snapshot", {})
        ctx = request.get("context", {})
        handler = {
            ANCHOR: lambda: self.case.anchor(ctx),
            EXPAND_TREE: lambda: self.case.tree(state, ctx),
            IDENTIFY_GAP: lambda: self.case.gap(state, ctx),
            LEARN: lambda: self.case.learn(state, ctx),
            BRIEF_REVIEW: lambda: self.case.brief(state, ctx),
            REWRITE_FOCUS: lambda: self.case.rewrite_focus(state, ctx),
            DEEP_REVIEW: lambda: self.case.deep(state, ctx),
            COMPRESS: lambda: self._compress(state, ctx),
            ASSESS_USER: lambda: self._assess(state, ctx),
            PLAN_TEACHING: lambda: self._plan(state, ctx),
            TEACH: lambda: self._teach(state, ctx),
            ASSESS_MIGRATION_OUTPUT: lambda: self._migration(state, ctx),
            READ_FEEDBACK: lambda: self._feedback(state, ctx),
        }[name]
        return handler()

    # ---- 压缩：内容来自用例，悬置处置统一自动完成 ----
    def _compress(self, state: dict, ctx: dict) -> dict:
        payload = self.case.compress_payload(state, ctx)
        judgment = {
            "explanation": ctx.get("stage_explanation")
            or state["proposition"].get("current_explanation", "")
            or payload.get("explanation", ""),
            "open_boundaries": list(payload["open_boundaries"]),
            "reason": payload["reason"],
        }
        stale = ctx.get("stale_open_nodes")
        if stale is None:
            stale = [
                {"id": q.get("id", ""), "text": q.get("text", "")}
                for q in state.get("question_tree", {}).get("sub_questions", [])
                if q.get("status") == "open"
            ]
        stale_ids = [n["id"] for n in stale if n.get("id")]
        retain = self.case.expect.retain_open
        retain_here = [qid for qid in stale_ids if qid in retain]
        stabilize_here = [qid for qid in stale_ids if qid not in retain]
        if stabilize_here:
            judgment["stabilize_question_ids"] = stabilize_here
        if retain_here:
            judgment["retain_open_questions"] = [
                {"id": qid, "reason": retain[qid]} for qid in retain_here
            ]
        return judgment

    # ---- 教学：用户假设/规划/反馈为命题无关的通用规则 ----
    def _assess(self, state: dict, ctx: dict) -> dict:
        msg = ctx.get("user_message", "")
        if any(k in msg for k in ("我一直以为", "我认为就是", "肯定是", "不就是")):
            return {
                "level": "入门但持有稳定误解",
                "block_type": "关键误解",
                "preferred_style": "先用反例松动误解，再给结构",
                "note": "用户语气确定，疑似把顺滑解释当成结论",
            }
        if any(k in msg for k in ("太抽象", "举个例子", "听不懂说的啥")):
            return {
                "level": "感性直觉为主",
                "block_type": "缺乏直观",
                "preferred_style": "先举例建立直观",
                "note": "抽象表述无法进入",
            }
        if any(k in msg for k in ("关系", "混乱", "分不清", "串不起来")):
            return {
                "level": "知道零散术语",
                "block_type": "结构缺口",
                "preferred_style": "先搭框架，再填概念",
                "note": "有术语但没有关系图",
            }
        if any(k in msg for k in ("怎么用到", "迁移", "别的场景", "换个问题", "换个场景")):
            return {
                "level": "核心结构基本理解",
                "block_type": "迁移缺口",
                "preferred_style": "推动自我生成，给迁移任务而非解释",
                "note": "理解已到位，缺的是生成练习",
            }
        if any(k in msg for k in ("什么意思", "不懂", "是什么", "指什么")):
            return {
                "level": "首次接触",
                "block_type": "概念缺口",
                "preferred_style": "先定义关键术语，避免机制全貌一次压上",
                "note": "术语基础薄弱",
            }
        return {
            "level": "状态不明",
            "block_type": "状态不清",
            "preferred_style": "先提问判断卡点",
            "note": "信息不足以判断卡点类型",
        }

    def _plan(self, state: dict, ctx: dict) -> dict:
        block = state["teaching"]["learner_hypothesis"]["block_type"]
        mapping = {
            "关键误解": ("纠偏", "先给反例"),
            "缺乏直观": ("解惑", "先举例"),
            "结构缺口": ("搭框架", "先搭框架"),
            "迁移缺口": ("促进迁移", "先做迁移"),
            "概念缺口": ("扫盲", "先定义"),
        }
        goal, action = mapping.get(block, ("扫盲", "先提问"))
        return {
            "dialog_goal": goal,
            "teaching_action": action,
            "auxiliary_actions": [],
            "reason": f"用户当前卡点为「{block}」，需要的是路径切换而非语气调整",
        }

    def _teach(self, state: dict, ctx: dict) -> dict:
        action = state["teaching"]["teaching_action"]
        reply = self.case.teach_replies.get(
            action,
            state["proposition"].get("current_explanation", "")
            or f"我们来谈谈「{self.case.proposition}」。",
        )
        return {
            "reply": reply,
            "path_note": f"主动作={action}；只使用一个主动作，其余动作本轮不并行",
        }

    def _feedback(self, state: dict, ctx: dict) -> dict:
        msg = ctx.get("feedback_text", "")
        if any(k in msg for k in ("懂了", "明白", "清楚了", "会用了", "能串起来")):
            return {
                "understood": True,
                "failure_kind": "",
                "misconception_signal": "",
                "note": "用户确认进入点被接住，本轮教学目标完成",
            }
        if "跳步" in msg:
            kind = "解释跳步"
        elif "假设" in msg or "我早就知道" in msg:
            kind = "用户假设错误"
        elif "动作" in msg or "没回答" in msg or "不是我问的" in msg:
            kind = "动作选错"
        else:
            kind = "理解不成熟"
        return {
            "understood": False,
            "failure_kind": kind,
            "misconception_signal": "教学反馈显示进入点未被接住" if kind != "动作选错" else "",
            "note": f"按「{kind}」回流检查，不默认归因于用户水平",
        }

    def _migration(self, state: dict, ctx: dict) -> dict:
        return {
            "passed": True,
            "structure_applied": self.case.migration_structure,
            "gap_if_failed": "",
            "note": self.case.migration_note,
        }


def gap_judgment(
    gap_type: str, statement: str, why: str, source: str = "学习"
) -> dict:
    """缺口判断小工具：三字段必填，来源默认学习侧。"""
    return {
        "gap_type": gap_type,
        "gap_statement": statement,
        "why_priority": why,
        "secondary_gaps": [],
        "trigger_source": source,
    }


# 供用例内容引用，避免到处 import GapType 字符串拼写漂移
GAP_CONCEPT = GapType.CONCEPT.value
GAP_STRUCTURE = GapType.STRUCTURE.value
GAP_COUNTEREXAMPLE = GapType.COUNTEREXAMPLE.value
