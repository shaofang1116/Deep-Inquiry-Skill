# Converged Markdown Report Evidence

## TDD Evidence

- Initial renderer/store RED: missing `render_knowledge_report`.
- Initial host RED: completed result lacked `report_path`.
- Review RED: stale convergence cursor completed a newer unassessed version.
- Review RED: Markdown list/thematic-break and embedded-backtick inputs were
  not safely rendered.
- Review RED: empty/non-UTF-8 payloads were accepted.
- Review RED: report-directory, topic-directory, and `topics/` ancestor
  symbolic links could escape the configured storage boundary.

All reproductions have focused regression assertions.

## Verification Evidence

- `python3 skill/autonomous-mentor/examples/tests/core_contract/markdown_report_checks.py`
  -> `5/5` passed.
- `python3 skill/autonomous-mentor/examples/tests/adapter/markdown_report_host_checks.py`
  -> `4/4` passed.
- `python3 skill/autonomous-mentor/examples/tests/run_layer.py --verify-manifest`
  -> manifest valid.
- `python3 skill/autonomous-mentor/examples/tests/run_layer.py --all`
  -> `core_contract 8/8`, `behavior 9/9`, `migration 2/2`,
  `adapter 9/9`.
- Sandbox package gate -> `16/16` checks passed; development and sandbox tree
  hashes match.
- `git diff --check` -> clean.

## Independent Review

- First review found stale-cursor certification, incomplete Markdown escaping,
  symlink escape, invalid payload acceptance, and incomplete package coverage.
- Second review confirmed all except an ancestor `topics/` symlink case.
- The ancestor case was reproduced, fixed in the store owner, and covered by
  the final `5/5` core report check.

## Architecture Evidence

- One renderer owner: `scripts/renderer.py`.
- One durable writer: `KnowledgeStore`.
- Publication lifecycle remains owned by `KnowledgePublisher`.
- Completion orchestration remains owned by `VNextHost`.
- No report is generated for checkpoint termination.
- No fallback, alias report, second writer, or model post-processing was added.
