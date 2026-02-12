# quick-bmad

可迁移的 BMAD 流程包（Claude/Codex 工作流）。

本仓库提供：
- Stage-gated workflows（主流程 + bugfix）
- Coordinator / PM / Architect / QA skills
- QA 执行者（qa-executor）
- 项目级“验证指南 + 编码护栏”模板
- 完整性校验脚本（`scripts/verify.sh`）

## 包结构

```text
quick-bmad/
├── bmad/
│   ├── workflows/
│   │   ├── workflow.yml
│   │   └── bugfix.yml
│   ├── templates/
│   └── project/
│       ├── validation-profile.template.yml
│       └── coding-profile.template.yml
├── claude/
│   └── skills/
│       ├── coordinator/
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
    └── verify.sh
```

## 安装与使用

请按完整手册执行（手工安装，可验证）：

- `docs/INSTALL_AND_USAGE.md`

## 最小运行指令

主流程：

```text
/coordinator verification_policy=default
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
