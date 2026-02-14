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

## Baseline 继承（新增）

为避免归档后丢失 PRD/UIUX/ADR 等冻结规格，新增 baseline 机制：

- 基线路径：`.bmad/baseline/spec/`
- 主流程可在启动时自动 seed（回填缺失规格到 `.bmad/artifacts/`）
- 归档前应做 snapshot（将最新冻结规格写回 baseline）

推荐斜杠命令：

```text
/coordinator baseline=auto
/coordinator baseline=seed
/coordinator baseline=skip
/coordinator baseline_import_archive=latest baseline=seed
```

单独操作 baseline：

```text
/baseline-spec action=status workflow=.bmad/workflows/workflow.yml strict=true
/baseline-spec action=seed workflow=.bmad/workflows/workflow.yml
/baseline-spec action=snapshot workflow=.bmad/workflows/workflow.yml
/baseline-spec action=import-archive workflow=.bmad/workflows/workflow.yml archive_dir=.bmad/archive/<dir>
```
