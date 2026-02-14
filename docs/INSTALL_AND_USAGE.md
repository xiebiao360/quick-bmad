# quick-bmad 安装与使用说明（手工安装 + 可验证）

本文档提供一套不依赖一键脚本的安装方式。每一步都附带可验证检查。

## 1. 前置条件

- 你有目标项目仓库写权限。
- 目标项目已存在 `.claude`（若不存在可新建）。
- 使用的 agent 运行环境支持读取：
  - `.bmad/workflows/*.yml`
  - `.claude/skills/*/SKILL.md`

可验证检查：

```bash
cd <your-project-root>
git rev-parse --show-toplevel
```

## 2. 复制 quick-bmad 核心文件

在 `quick-bmad` 仓库根目录执行：

```bash
cd <quick-bmad-root>

mkdir -p <your-project-root>/.bmad
cp -R bmad/workflows <your-project-root>/.bmad/
cp -R bmad/templates <your-project-root>/.bmad/
cp -R bmad/scripts <your-project-root>/.bmad/
mkdir -p <your-project-root>/.bmad/milestones
cp bmad/milestones/README.md <your-project-root>/.bmad/milestones/README.md

mkdir -p <your-project-root>/.bmad/project
cp bmad/project/validation-profile.template.yml <your-project-root>/.bmad/project/validation-profile.yml
cp bmad/project/coding-profile.template.yml <your-project-root>/.bmad/project/coding-profile.yml

mkdir -p <your-project-root>/.claude/skills
cp -R claude/skills/* <your-project-root>/.claude/skills/

mkdir -p <your-project-root>/docs/development
cp docs/development/ai-dev-launch-guide.md <your-project-root>/docs/development/ai-dev-launch-guide.md
cp docs/development/ai-dev-coding-guardrails.md <your-project-root>/docs/development/ai-dev-coding-guardrails.md
```

可验证检查：

```bash
cd <your-project-root>
ls .bmad/workflows
ls .bmad/scripts
ls .bmad/milestones
ls .claude/skills
```

## 3. 填写项目绑定配置（必须）

### 3.1 validation-profile

编辑：`<your-project-root>/.bmad/project/validation-profile.yml`

至少填写：
- `project.name`
- `entry.guide_path`
- `services.*.health_url`
- `clients.*.base_url`
- `qa.evidence_dir`

### 3.2 coding-profile

编辑：`<your-project-root>/.bmad/project/coding-profile.yml`

至少确认：
- `entry.coding_guide_path`

## 4. 定制项目绑定文档（必须）

### 4.1 验证指南

编辑：`<your-project-root>/docs/development/ai-dev-launch-guide.md`

必须替换：
- 服务启动命令
- 健康检查地址
- 前端/客户端启动与验证步骤
- 执行报告模板

### 4.2 编码护栏

编辑：`<your-project-root>/docs/development/ai-dev-coding-guardrails.md`

必须确认：
- 配置加载规则
- DB/Redis 使用约束
- 迁移流程规范
- API 网关路由规范
- 项目结构与 DDD 分层约束

## 5. 校验 workflow 绑定关系

检查以下路径是否指向真实文件：

- `.bmad/workflows/workflow.yml`
  - `validation.guide_path`
  - `validation.profile_path`
  - `governance.coding_guide_path`
  - `governance.coding_profile_path`
  - `milestone.*`

- `.bmad/workflows/bugfix.yml`
  - 同上四项（bugfix 下可关闭 milestone）

## 6. 完整性校验

在 `quick-bmad` 仓库执行：

```bash
cd <quick-bmad-root>
./scripts/verify.sh <your-project-root>
```

预期输出：
- `OK: BMAD installation looks complete at <your-project-root>`

## 7. 使用流程

### 7.1 新一期（全新规格）

```text
/coordinator verification_policy=default milestone_use=skip
```

完成 scope freeze 后立刻创建 milestone：

```text
/milestone-lock action=create workflow=.bmad/workflows/workflow.yml milestone_id=<milestone-id>
```

### 7.2 按既有 milestone 继续迭代

```text
/coordinator verification_policy=default milestone_use=require milestone_id=<milestone-id>
```

### 7.3 从历史归档启动新一期

```text
/milestone-lock action=import-archive workflow=.bmad/workflows/workflow.yml milestone_id=<new-milestone-id> archive_dir=.bmad/archive/<dir>
/coordinator milestone_use=require milestone_id=<new-milestone-id>
```

## 8. 验收标准（建议）

满足以下条件视为安装完成：

- `verify.sh` 通过。
- coordinator 启动时不再报 guide/profile 缺失。
- 至少完成一次 scope_freeze 并产出 `milestone-lock-report.md`。
- 在 parallel_dev / architecture_review / qa_validation 阶段都能通过 milestone verify（无 drift）。

## 9. Milestone Slash 命令总览

```text
/milestone-lock action=status workflow=.bmad/workflows/workflow.yml strict=true
/milestone-lock action=create workflow=.bmad/workflows/workflow.yml milestone_id=<id>
/milestone-lock action=use workflow=.bmad/workflows/workflow.yml milestone_id=<id>
/milestone-lock action=verify workflow=.bmad/workflows/workflow.yml milestone_id=<id>
/milestone-lock action=import-archive workflow=.bmad/workflows/workflow.yml milestone_id=<id> archive_dir=.bmad/archive/<dir>
/milestone-lock action=set-active workflow=.bmad/workflows/workflow.yml milestone_id=<id>
```
