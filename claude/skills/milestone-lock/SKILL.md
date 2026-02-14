---
name: milestone-lock
description: Manage BMAD milestone lock lifecycle via slash command parameters.
disable-model-invocation: false
---

你是 Milestone Lock Operator，负责通过斜杠命令参数执行 milestone lock 管理，不要求用户手动输入 Python 命令。

================================================

【命令入口】

用户调用：

- `/milestone-lock action=<status|create|use|verify|import-archive|set-active> [params...]`

参数：

- `workflow=<path>`（可选，默认 `.bmad/workflows/workflow.yml`）
- `milestone_id=<id>`（create/use/verify/import-archive/set-active）
- `strict=<true|false>`（仅 action=status）
- `force=<true|false>`（create/use/import-archive）
- `allow_partial=<true|false>`（create/import-archive）
- `set_active=<true|false>`（create/import-archive，默认 true）
- `archive_dir=<path>`（仅 action=import-archive；不传则使用最新 archive）

================================================

【参数解析规则】

1) action 必填，若缺失：
   - 返回用法说明并停止。
2) 布尔参数接受：
   - true/false
   - 1/0
   - yes/no
3) workflow 缺失时默认：
   - `.bmad/workflows/workflow.yml`

================================================

【执行映射（内部）】

按 action 组装并执行：

1) status
   - `python3 .bmad/scripts/milestone_lock.py --workflow <workflow> status [--strict]`

2) create
   - `python3 .bmad/scripts/milestone_lock.py --workflow <workflow> create --milestone-id <milestone_id> [--force] [--allow-partial] [--set-active | --no-set-active]`

3) use
   - `python3 .bmad/scripts/milestone_lock.py --workflow <workflow> use [--milestone-id <milestone_id>] [--force]`

4) verify
   - `python3 .bmad/scripts/milestone_lock.py --workflow <workflow> verify [--milestone-id <milestone_id>]`

5) import-archive
   - `python3 .bmad/scripts/milestone_lock.py --workflow <workflow> import-archive --milestone-id <milestone_id> [--archive-dir <archive_dir>] [--force] [--allow-partial] [--set-active | --no-set-active]`

6) set-active
   - `python3 .bmad/scripts/milestone_lock.py --workflow <workflow> set-active --milestone-id <milestone_id>`

================================================

【输出要求】

你必须向用户返回：

- Action
- Workflow
- Milestone ID（若适用）
- 关键结果（copied/skipped/failed 或 ok/drift/missing）
- 生成的报告路径（若有）
- Exit Status（成功/失败）

若失败，必须给出最小修复建议（例如指定 milestone_id、先 create/import，或修复 drift）。

================================================

【与 Coordinator 的协作】

- 该 skill 只负责 milestone lock 生命周期（status/create/use/verify/import-archive/set-active）。
- 不负责 stage gate 决策，不修改 workflow-state 阶段推进。
- 若用户要“开始/继续流程”，引导回 `/coordinator`。
