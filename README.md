# BMAD Portable Bundle

可迁移的 BMAD 流程包（Claude/Codex 工作流），包含：

- Stage-gated workflows（主流程 + bugfix）
- Coordinator / PM / Architect / QA skills
- QA 执行者（qa-executor）
- 项目级“验证指南 + 编码护栏”模板
- 一键安装与完整性校验脚本

## 1. 包结构

```text
packages/bmad-portable/
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
├── docs/development/
│   ├── ai-dev-launch-guide.md
│   └── ai-dev-coding-guardrails.md
├── examples/liangx/
│   ├── docs/development/...
│   └── bmad/project/...
└── scripts/
    ├── install.sh
    └── verify.sh
```

## 2. 安装（推荐）

### 2.1 一键安装

```bash
cd <this-repo>/packages/bmad-portable
./scripts/install.sh --target <your-project-root>
```

### 2.2 安装后校验

```bash
cd <this-repo>/packages/bmad-portable
./scripts/verify.sh <your-project-root>
```

## 3. 必做配置（完整可用的关键）

安装后必须完成以下配置，否则流程不完整：

1. 填写项目验证配置
- 文件：`<your-project-root>/.bmad/project/validation-profile.yml`
- 至少补齐：服务健康检查地址、客户端地址、执行证据目录

2. 填写项目编码护栏配置
- 文件：`<your-project-root>/.bmad/project/coding-profile.yml`
- 至少确认：`coding_guide_path`

3. 定制项目绑定文档
- `<your-project-root>/docs/development/ai-dev-launch-guide.md`
- `<your-project-root>/docs/development/ai-dev-coding-guardrails.md`

4. 确认 workflow 路径绑定
- `<your-project-root>/.bmad/workflows/workflow.yml`
- `<your-project-root>/.bmad/workflows/bugfix.yml`
- 检查：
  - `validation.guide_path`
  - `validation.profile_path`
  - `governance.coding_guide_path`
  - `governance.coding_profile_path`

## 4. 运行方式

### 4.1 主流程

```text
/coordinator verification_policy=default
```

### 4.2 Bugfix 流程

```text
/coordinator .bmad/workflows/bugfix.yml verification_policy=ask
```

说明：
- `default`：允许 NOT EXECUTED（不强制实跑）
- `ask`：在验证前询问 execute/skip
- `strict`：必须执行验证并提供证据

## 5. qa-executor 说明

`qa-executor` 已设置为可调用（`disable-model-invocation: false`），可直接用于验证执行与证据输出。

## 6. 迁移到新项目的最小步骤

1. 运行安装脚本
2. 按新项目改写两份项目绑定文档（验证指南/编码护栏）
3. 更新 validation/coding profile
4. 跑 `verify.sh` 通过
5. 触发 `/coordinator` 执行

## 7. 常见问题

1. 报错 `missing project validation guide configuration`
- 检查 workflow 的 `validation.guide_path` 是否存在且可读

2. 报错 `missing project coding governance guide configuration`
- 检查 workflow 的 `governance.coding_guide_path` 是否存在且可读

3. 报错 `Skill ... cannot be used with Skill tool due to disable-model-invocation`
- 检查目标 skill 的 frontmatter `disable-model-invocation`

## 8. LiangX 示例

如果你要复用 LiangX 的现成配置/文档，可参考：

- `examples/liangx/docs/development/ai-dev-launch-guide.md`
- `examples/liangx/docs/development/ai-dev-coding-guardrails.md`
- `examples/liangx/bmad/project/validation-profile.yml`
- `examples/liangx/bmad/project/coding-profile.yml`

