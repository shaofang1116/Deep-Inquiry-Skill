"""导师逻辑：对外生成有效成长。

不调用模型：用户假设、动作选择、教学回应、反馈判读均来自 agent 判断响应，
本模块负责枚举护栏、一轮一个主动作、有效/无效动作记账与教学缺口回流登记。

用户理解假设只在当前命题下有效，可被单轮对话修正，不是长期画像。
"""

from __future__ import annotations

from typing import Any

from .schema import (
    DialogGoal,
    GapState,
    GapType,
    LearnerHypothesis,
    SchemaError,
    TeachingAction,
    TeachingAsset,
    TriggerSource,
)


class Mentor:
    def assess(
        self, state: Any, user_message: str, judgment: dict[str, Any]
    ) -> LearnerHypothesis:
        hypothesis = LearnerHypothesis(
            level=judgment.get("level", ""),
            block_type=judgment.get("block_type", ""),
            preferred_style=judgment.get("preferred_style", ""),
            note=judgment.get("note", ""),
        )
        state.teaching.learner_hypothesis = hypothesis
        return hypothesis

    def plan(self, state: Any, user_message: str, judgment: dict[str, Any]) -> dict[str, Any]:
        action = judgment.get("teaching_action", "")
        goal = judgment.get("dialog_goal", "")
        # 规则护栏：目标与动作必须来自收束集合，且一轮只有一个主动作
        valid_actions = {a.value for a in TeachingAction}
        valid_goals = {g.value for g in DialogGoal}
        if action not in valid_actions:
            raise SchemaError(f"主导师动作非法: {action!r}")
        if goal not in valid_goals:
            raise SchemaError(f"本轮教学目标非法: {goal!r}")
        aux = list(judgment.get("auxiliary_actions", []))
        state.teaching.dialog_goal = goal
        state.teaching.teaching_action = action
        return {
            "dialog_goal": goal,
            "teaching_action": action,
            "auxiliary_actions": aux,
            "reason": judgment.get("reason", ""),
        }

    def build_reply(self, state: Any, judgment: dict[str, Any]) -> dict[str, Any]:
        reply = judgment.get("reply", "")
        if not reply:
            raise SchemaError("教学回应失败：reply 为空")
        return {"reply": reply, "path_note": judgment.get("path_note", "")}

    def reset_for_new_user(self, state: Any) -> None:
        """样例验证用：同一命题面对不同用户状态时，重置当前命题下的教学假设。"""
        state.teaching = type(state.teaching)()

    def receive_feedback(
        self, state: Any, user_message: str, feedback_text: str,
        judgment: dict[str, Any],
    ) -> dict[str, Any]:
        """应用反馈判断；是否回流学习循环由 loop 按规则裁决。"""
        action = state.teaching.teaching_action
        understood = bool(judgment["understood"])
        kind = judgment.get("failure_kind", "")

        if understood:
            if action and action not in state.teaching.effective_actions:
                state.teaching.effective_actions.append(action)
            state.teaching.misconception_signal = ""
        else:
            if action and action not in state.teaching.failed_actions:
                state.teaching.failed_actions.append(action)
            state.teaching.misconception_signal = judgment.get("misconception_signal", "")

            # v3.1 决策五：用户没听懂时依次检查
            # 动作选错 / 解释跳步 / 用户假设错误 / 理解不成熟
            loop_back = kind in {"解释跳步", "理解不成熟"}
            if loop_back:
                state.gap = GapState(
                    gap_type=GapType.TEACHING.value,
                    gap_statement=f"教学暴露的缺口（{kind}）：{judgment.get('note', '')}",
                    why_priority="教学是学习成熟度的检验器，一教就露馅必须优先回到学习循环",
                    trigger_source=TriggerSource.TEACHING.value,
                )

        # 教学资产库：记录本轮动作对当前用户状态的效果（无论理解与否）
        hypothesis = state.teaching.learner_hypothesis
        state.teaching.asset_library.append(
            TeachingAsset(
                block_type=hypothesis.block_type,
                teaching_action=action,
                dialog_goal=state.teaching.dialog_goal,
                effective=understood,
                failure_kind="" if understood else kind,
                note=judgment.get("note", ""),
            )
        )
        return {**judgment, "loop_back": (not understood) and kind in {"解释跳步", "理解不成熟"}}
