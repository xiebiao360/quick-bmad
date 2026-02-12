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

预期：输出项目根目录绝对路径。

## 2. 复制 quick-bmad 核心文件

在 `quick-bmad` 仓库根目录执行：

```bash
cd <quick-bmad-root>

# 1) 复制 bmad 引擎文件
mkdir -p <your-project-root>/.bmad
cp -R bmad/workflows <your-project-root>/.bmad/
cp -R bmad/templates <your-project-root>/.bmad/
mkdir -p <your-project-root>/.bmad/project
cp bmad/project/validation-profile.template.yml <your-project-root>/.bmad/project/validation-profile.yml
cp bmad/project/coding-profile.template.yml <your-project-root>/.bmad/project/coding-profile.yml

# 2) 复制 skills
mkdir -p <your-project-root>/.claude/skills
cp -R claude/skills/* <your-project-root>/.claude/skills/

# 3) 复制项目绑定文档模板
mkdir -p <your-project-root>/docs/development
cp docs/development/ai-dev-launch-guide.md <your-project-root>/docs/development/ai-dev-launch-guide.md
cp docs/development/ai-dev-coding-guardrails.md <your-project-root>/docs/development/ai-dev-coding-guardrails.md
```

可验证检查：

```bash
cd <your-project-root>
ls .bmad/workflows
ls .bmad/templates
ls .bmad/project
ls .claude/skills
ls docs/development
```

预期至少包含：
- `.bmad/workflows/workflow.yml`
- `.bmad/workflows/bugfix.yml`
- `.bmad/project/validation-profile.yml`
- `.bmad/project/coding-profile.yml`
- `.claude/skills/coordinator/SKILL.md`
- `.claude/skills/qa-executor/SKILL.md`
- `docs/development/ai-dev-launch-guide.md`
- `docs/development/ai-dev-coding-guardrails.md`

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

可验证检查：

```bash
cd <your-project-root>
grep -n "guide_path" .bmad/project/validation-profile.yml
grep -n "coding_guide_path" .bmad/project/coding-profile.yml
```

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

可验证检查：

```bash
cd <your-project-root>
grep -n "gateway\|migrations\|DDD\|RUN_MODE" docs/development/ai-dev-coding-guardrails.md
```

## 5. 校验 workflow 绑定关系

检查以下路径是否指向真实文件：

- `.bmad/workflows/workflow.yml`
  - `validation.guide_path`
  - `validation.profile_path`
  - `governance.coding_guide_path`
  - `governance.coding_profile_path`

- `.bmad/workflows/bugfix.yml`
  - 同上四项

可验证检查：

```bash
cd <your-project-root>
grep -n "guide_path\|profile_path\|coding_guide_path\|coding_profile_path" .bmad/workflows/workflow.yml .bmad/workflows/bugfix.yml
```

## 6. 完整性校验

在 `quick-bmad` 仓库执行：

```bash
cd <quick-bmad-root>
./scripts/verify.sh <your-project-root>
```

预期输出：
- `OK: BMAD installation looks complete at <your-project-root>`

## 7. 使用流程

### 7.1 主流程

```text
/coordinator verification_policy=default
```

### 7.2 Bugfix 流程

```text
/coordinator .bmad/workflows/bugfix.yml verification_policy=ask
```

### 7.3 验证策略选择

- `default`：默认允许 `NOT EXECUTED`
- `ask`：在验证前询问 `execute/skip`
- `strict`：必须有执行证据

## 8. 验收标准（建议）

满足以下条件视为安装完成：

- `verify.sh` 通过。
- coordinator 启动时不再报 guide/profile 缺失。
- 至少完成一次 bugfix 到 validate 的完整演练。
- 在 `ask=execute` 或 `strict` 下，能产出执行证据报告（如 `bugfix-test-report.md` + `qa-execution-evidence.md`）。
