#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-""}"
if [[ -z "$TARGET" ]]; then
  TARGET="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$TARGET" || ! -d "$TARGET" ]]; then
  echo "Target repo root not found." >&2
  exit 1
fi

need() {
  local p="$1"
  if [[ ! -s "$TARGET/$p" ]]; then
    echo "MISSING: $p" >&2
    return 1
  fi
}

# Detect mode: bundle repo vs installed target
if [[ -d "$TARGET/bmad/workflows" ]]; then
  # bundle repo mode
  need bmad/workflows/workflow.yml
  need bmad/workflows/bugfix.yml
  need bmad/templates/qa-test-report.template.md
  need bmad/templates/bugfix-test-report.template.md
  need bmad/project/validation-profile.template.yml
  need bmad/project/coding-profile.template.yml
  need docs/development/ai-dev-launch-guide.md
  need docs/development/ai-dev-coding-guardrails.md
  need claude/skills/coordinator/SKILL.md
  need claude/skills/qa-executor/SKILL.md
  need scripts/install.sh
  echo "OK: quick-bmad bundle looks complete at $TARGET"
else
  # installed target mode
  need .bmad/workflows/workflow.yml
  need .bmad/workflows/bugfix.yml
  need .bmad/templates/qa-test-report.template.md
  need .bmad/templates/bugfix-test-report.template.md
  need .bmad/project/validation-profile.yml
  need .bmad/project/coding-profile.yml
  need docs/development/ai-dev-launch-guide.md
  need docs/development/ai-dev-coding-guardrails.md
  need .claude/skills/coordinator/SKILL.md
  need .claude/skills/qa-executor/SKILL.md
  echo "OK: BMAD installation looks complete at $TARGET"
fi
