# quick-bmad

可迁移的 BMAD 流程包（Claude/Codex 工作流）。

本仓库提供：
- Stage-gated workflows（主流程 + bugfix）
- Coordinator / PM / Architect / QA skills
- QA 执行者（qa-executor）
- 项目级“验证指南 + 编码护栏”模板
- Milestone Lock（版本化规格冻结）
- 完整性校验脚本（`scripts/verify.sh`）

## 包结构

```text
quick-bmad/
├── bmad/
│   ├── workflows/
│   │   ├── workflow.yml
│   │   └── bugfix.yml
│   ├── templates/
│   ├── scripts/
│   │   ├── milestone_lock.py
│   │   └── audit_workflow.py
│   ├── milestones/
│   │   └── README.md
│   └── project/
│       ├── validation-profile.template.yml
│       └── coding-profile.template.yml
├── claude/
│   └── skills/
│       ├── coordinator/
│       ├── milestone-lock/
│       ├── pm-prep/
│       ├── pm-discovery/
│       ├── architect-design/
│       ├── qa-matrix/
│       ├── qa-lead/
│       ├── qa-executor/
│       ├── api-design-principles/
│       └── architecture-review/
├── docs/
│   ├── INSTALL_AND_USAGE.md
│   └── development/
│       ├── ai-dev-launch-guide.md
│       └── ai-dev-coding-guardrails.md
└── scripts/
    ├── install.sh
    └── verify.sh
```

## 安装与使用

请按完整手册执行（手工安装，可验证）：

- `docs/INSTALL_AND_USAGE.md`

## 最小运行指令

主流程：

```text
/coordinator verification_policy=default milestone_use=auto
```

Bugfix 流程：

```text
/coordinator .bmad/workflows/bugfix.yml verification_policy=ask
```

策略说明：
- `default`：允许 `NOT EXECUTED`
- `ask`：验证前询问 `execute/skip`
- `strict`：必须执行验证并提供证据

## 常见问题

1. `missing project validation guide configuration`
- 检查 `validation.guide_path` 是否存在且可读。

2. `missing project coding governance guide configuration`
- 检查 `governance.coding_guide_path` 是否存在且可读。

3. `Skill ... cannot be used with Skill tool due to disable-model-invocation`
- 检查目标 skill frontmatter 中的 `disable-model-invocation`。

## Milestone 版本化（推荐）

为保证“每一期开发固定依赖一版 PRD/Arch/UIUX/API”，推荐使用 milestone lock：

- 锁目录：`.bmad/milestones/<milestone-id>/`
- 锁文件：`.bmad/milestones/<milestone-id>/milestone-lock.yml`
- 活动指针：`.bmad/milestones/ACTIVE`

推荐斜杠命令：

```text
/coordinator milestone_use=auto
/coordinator milestone_use=require milestone_id=<id>
/coordinator milestone_import_archive=latest milestone_create_id=<id> milestone_use=require
```

单独操作 milestone：

```text
/milestone-lock action=status workflow=.bmad/workflows/workflow.yml strict=true
/milestone-lock action=create workflow=.bmad/workflows/workflow.yml milestone_id=<id>
/milestone-lock action=use workflow=.bmad/workflows/workflow.yml milestone_id=<id>
/milestone-lock action=verify workflow=.bmad/workflows/workflow.yml milestone_id=<id>
/milestone-lock action=import-archive workflow=.bmad/workflows/workflow.yml milestone_id=<id> archive_dir=.bmad/archive/<dir>
```
