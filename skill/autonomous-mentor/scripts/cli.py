"""最小命令行入口：agent 与内核之间的文件协议。

三类最小输入（vNext 边界）：
1. 新命题输入：   init "<命题>"
2. 继续学习请求： learn [--objective "..."]
3. 知识查询：     query "<问题>" --knowledge-root <路径> --topic-id <主题>
   `ask` 暂作 query 的兼容别名；默认路径不再维护教学状态或 feedback。

协议节奏：
- legacy begin 类命令（init/learn）写出 request.json + pending.json，
  JSON body 用 status=pending 表示「等待判断」，进程退出码仍为 0；
- 执行 Skill 的 agent（任意模型）阅读 request.json，把
  {"judgment": ..., "response": {...}} 写入 judgment.json；
- 运行 step 消费判断；若仍为 status=pending，重复上一步。
- cancel 放弃当前轮次（只清运行时文件，不动 session.json）。

可从任意工作目录以脚本绝对路径直跑：python3 /<安装路径>/scripts/cli.py ...
状态默认落在当前工作目录的 .mentor-state/，不依赖 Skill 安装位置。

--json 输出机器可读结果，供自动化与冒烟使用。
状态默认写入工作目录 .mentor-state/。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.dont_write_bytecode = True

# 两种等价启动方式，安装路径无关、当前工作目录无关：
#   1) python3 -m scripts.cli ...                （CWD 在 skill 目录或包在 PYTHONPATH 中）
#   2) python3 /<安装路径>/autonomous-mentor/scripts/cli.py ...   （任意 CWD，推荐给 agent）
if __package__ in (None, ""):
    _SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _SKILL_ROOT not in sys.path:
        sys.path.insert(0, _SKILL_ROOT)
    from scripts.knowledge_store import KnowledgeStore, KnowledgeStoreError
    from scripts.query import QueryError, query_knowledge
    from scripts.store import JUDGMENT_FILE, REQUEST_FILE
    from scripts.vnext_host import VNextHost, VNextHostError
else:
    from .knowledge_store import KnowledgeStore, KnowledgeStoreError
    from .query import QueryError, query_knowledge
    from .store import JUDGMENT_FILE, REQUEST_FILE
    from .vnext_host import VNextHost, VNextHostError

DEFAULT_STATE = os.path.join(".mentor-state", "session.json")
EXIT_ERROR = 1


def _force_utf8_stdio() -> None:
    """Windows 传统控制台默认 GBK/cp936，强制 UTF-8 以保证中文与符号输出不崩。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def format_trace(trace) -> str:
    lines = [
        f"【{trace.loop}】主推进目标：{trace.primary_objective}",
        "-" * 64,
    ]
    for e in trace.events:
        tag = {"action": "·", "gate": "✓", "failure": "⚠", "result": "→"}.get(
            e.kind, "·"
        )
        lines.append(f"[{e.stage}] {tag} {e.summary}")
    if trace.effective_updates:
        lines.append("-" * 64)
        lines.append("本轮有效状态更新：")
        lines.extend(f"  · {u}" for u in trace.effective_updates)
    if trace.result:
        lines.append("-" * 64)
        lines.append("结果：")
        for k, v in trace.result.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def format_pending(outcome, state_dir: str) -> str:
    req = outcome.request
    lines = [
        "=" * 64,
        f"等待判断：{req.name}（status=pending）",
        "=" * 64,
        f"指令：{req.instruction}",
        "-" * 64,
        "操作步骤：",
        f"  1. 阅读 {os.path.join(state_dir, REQUEST_FILE)}（含状态快照与上下文）",
        f"  2. 将判断响应写入 {os.path.join(state_dir, JUDGMENT_FILE)}，格式：",
        '     {"judgment": "%s", "response": {...按 response_template 填写...}}'
        % req.name,
        "  3. 重新运行 step（可用 --json）",
        "-" * 64,
        "response_template：",
        json.dumps(req.response_template, ensure_ascii=False, indent=2),
        "必填字段：" + ", ".join(req.required_fields),
    ]
    return "\n".join(lines)


def emit(outcome, args: argparse.Namespace, state_dir: str) -> int:
    status = outcome.to_dict().get("status")
    if status == "pending":
        payload = _host_payload(
            outcome.to_dict(),
            args,
            state_dir,
            next_action="write_judgment_and_step",
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(format_pending(outcome, state_dir))
        return 0
    if status == "done":
        payload = _host_payload(
            outcome.to_dict(),
            args,
            state_dir,
            next_action="read_result",
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2))
        return 0
    raise TypeError(f"未知结果类型: {type(outcome)}")


def emit_query(
    result: dict,
    args: argparse.Namespace,
    state_dir: str,
) -> int:
    payload = _host_payload(
        result,
        args,
        state_dir,
        next_action="complete",
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"主题：{result['topic_id']}（v{result['knowledge_version']}）")
        print(f"问题：{result['question']}")
        for claim in result["claims"]:
            print(f"- [{claim['dimension']}/{claim['kind']}] {claim['statement']}")
        if result["unresolved_gaps"]:
            print("未决边界：")
            for gap in result["unresolved_gaps"]:
                print(f"- {gap['question']}")
    return 0


def _host_payload(
    payload: dict,
    args: argparse.Namespace,
    state_dir: str,
    *,
    next_action: str,
) -> dict:
    request_paths = {
        "state": os.path.abspath(args.state),
        "pending": os.path.join(state_dir, "pending.json"),
        "request": os.path.join(state_dir, REQUEST_FILE),
        "judgment": os.path.join(state_dir, JUDGMENT_FILE),
    }
    return {
        **payload,
        "next_action": next_action,
        "knowledge_root": _resolved_knowledge_root(args.knowledge_root),
        "topic_id": args.topic_id,
        "request_path": payload.get("request_path"),
        "request_paths": request_paths,
    }


def _resolved_knowledge_root(path: str) -> str:
    return os.path.realpath(os.path.abspath(os.path.expanduser(path)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autonomous-mentor",
        description="自主学习导师 Skill 最小可运行内核（模型无关文件协议）",
    )
    parser.add_argument(
        "--state", default=DEFAULT_STATE, help=f"状态文件路径（默认 {DEFAULT_STATE}）"
    )
    parser.add_argument(
        "--knowledge-root",
        help="显式全局知识库根目录（不允许回退到 session 目录）",
    )
    parser.add_argument("--topic-id", help="当前 durable topic ID")
    parser.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="接收新中心命题（begin）")
    p_init.add_argument("proposition")

    p_learn = sub.add_parser("learn", help="开始一轮自主学习循环（begin）")
    p_learn.add_argument("--objective", default=None, help="本轮唯一主推进目标")

    for command, help_text in (
        ("query", "无状态读取当前 durable knowledge"),
        ("ask", "query 的一版兼容别名（不维护教学状态）"),
    ):
        query_parser = sub.add_parser(command, help=help_text)
        query_parser.add_argument("question")
        query_parser.add_argument(
            "--knowledge-root",
            default=argparse.SUPPRESS,
            help="兼容旧调用位置；推荐放在子命令之前",
        )
        query_parser.add_argument(
            "--topic-id",
            default=argparse.SUPPRESS,
            help="兼容旧调用位置；推荐放在子命令之前",
        )

    p_step = sub.add_parser("step", help="消费 judgment.json 并推进一轮")
    p_step.add_argument(
        "--message", default="",
        help="（可选）用户产出，用于迁移练习判分等场景",
    )
    sub.add_parser("cancel", help="放弃当前进行中的轮次")
    sub.add_parser("state", help="打印当前持久化状态")
    sub.add_parser("demo", help="运行端到端冒烟（脚本化夹具，无需模型）")
    return parser


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "demo" and (
        not args.knowledge_root or not args.topic_id
    ):
        parser.error(
            "--knowledge-root and --topic-id are required for host commands"
        )
    state_dir = os.path.dirname(os.path.abspath(args.state))

    try:
        if args.command in {"query", "ask"}:
            result = query_knowledge(
                KnowledgeStore(args.knowledge_root),
                args.topic_id,
                args.question,
            )
            return emit_query(result, args, state_dir)
        if args.command == "demo":
            return _run_demo()
        return _run_vnext_host(args)
    except (KnowledgeStoreError, QueryError, VNextHostError) as exc:
        _emit_error(exc, args, state_dir)
        return 1
    return 0


def _run_vnext_host(args: argparse.Namespace) -> int:
    host = VNextHost(
        state_path=args.state,
        knowledge_root=_resolved_knowledge_root(args.knowledge_root),
    )
    state_dir = os.path.dirname(os.path.abspath(args.state))
    if args.command == "init":
        return emit(
            host.initialize(
                topic_id=args.topic_id,
                proposition=args.proposition,
            ),
            args,
            state_dir,
        )
    if args.command == "learn":
        return emit(host.learn(topic_id=args.topic_id), args, state_dir)
    if args.command == "step":
        return emit(host.step(), args, state_dir)
    if args.command == "cancel":
        payload = _host_payload(
            host.cancel(topic_id=args.topic_id).to_dict(),
            args,
            state_dir,
            next_action="complete",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "state":
        payload = _host_payload(
            {"status": "state", "state": host.state(topic_id=args.topic_id)},
            args,
            state_dir,
            next_action="complete",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    raise VNextHostError(f"unsupported vNext host command {args.command!r}")


def _run_demo() -> int:
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    examples = os.path.join(skill_root, "examples")
    sys.path.insert(0, examples)
    from tests.adapter import smoke_run

    smoke_run.main()
    return 0


def _emit_error(
    exc: Exception,
    args: argparse.Namespace,
    state_dir: str,
) -> None:
    if args.json:
        payload = _host_payload(
            {"status": "error", "error": str(exc)},
            args,
            state_dir,
            next_action="correct_error",
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[中止] {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
