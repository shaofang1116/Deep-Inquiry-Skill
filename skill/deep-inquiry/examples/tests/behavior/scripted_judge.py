"""离线冒烟夹具：代替「执行 Skill 的 agent」填写 judgment.json。

注意：这不是生产路径，也不是模型适配器。真实运行时，判断由加载本 Skill 的
任意模型阅读 request.json 后自行给出。本夹具只用确定性内容驱动同一条文件协议，
让 smoke_run 在没有任何模型的情况下验证内核结构。

阶段三起，夹具内容单一事实来源迁入 eval 用例包（机制型命题）：
examples/tests/behavior/eval/cases/mechanism.py；本文件仅保留同名入口 build_judgment，
委托给通用脚本宿主 ScriptedHost，使 smoke_run 与 eval_suite 走同一套判断逻辑。

入口：build_judgment(request: dict) -> response: dict
"""

from __future__ import annotations

import os
import sys
from typing import Any

# 允许从任意 CWD 导入（联调/自检测试用）：把 Skill 根目录加入 sys.path
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from tests.behavior.eval.base import ScriptedHost  # noqa: E402
from tests.behavior.eval.cases.mechanism import MechanismCase  # noqa: E402

# 冒烟默认命题即机制型用例（samples.PROPOSITIONS["mechanism"]）
_HOST = ScriptedHost(MechanismCase())


def build_judgment(request: dict[str, Any]) -> dict[str, Any]:
    return _HOST.build_judgment(request)


if __name__ == "__main__":
    # 自检联调：python3 scripted_judge.py <request.json> [judgment.json]
    # 不给输出路径则打印到 stdout。再次强调：这是离线夹具，不是生产判断来源。
    import json

    if len(sys.argv) < 2:
        print(
            "用法: python3 scripted_judge.py <request.json> [judgment.json]",
            file=sys.stderr,
        )
        raise SystemExit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        _request = json.load(f)
    _envelope = {
        "judgment": _request["judgment"],
        "response": build_judgment(_request),
    }
    _text = json.dumps(_envelope, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(_text + "\n")
    else:
        print(_text)
