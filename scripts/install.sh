#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
BMAD Portable installer

Usage:
  ./scripts/install.sh [--target <repo-root>] [--mode copy]

Installs:
  - .bmad/ (workflows, templates, scripts, baseline)
  - .bmad/project templates (validation-profile, coding-profile)
  - .claude/skills (BMAD skills)
  - docs/development templates (validation guide, coding guardrails)

Notes:
  - Existing files are not overwritten; missing files are added.
  - If you already have your own project-bound docs/config, keep them and just wire paths in workflows.
USAGE
}

MODE="copy"
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"; shift 2 ;;
    --mode)
      MODE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  TARGET="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi
if [[ -z "$TARGET" || ! -d "$TARGET" ]]; then
  echo "Target repo root not found. Use --target <repo-root>." >&2
  exit 1
fi

if [[ "$MODE" != "copy" ]]; then
  echo "Only --mode copy is supported." >&2
  exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p \
  "$TARGET/.bmad/workflows" \
  "$TARGET/.bmad/templates" \
  "$TARGET/.bmad/scripts" \
  "$TARGET/.bmad/baseline/spec" \
  "$TARGET/.bmad/project" \
  "$TARGET/.claude/skills" \
  "$TARGET/docs/development"

# Copy missing workflows/templates/scripts (do not overwrite existing files).
for f in "$SRC_DIR/bmad/workflows"/*; do
  base="$(basename "$f")"
  if [[ ! -e "$TARGET/.bmad/workflows/$base" ]]; then
    cp "$f" "$TARGET/.bmad/workflows/$base"
  fi
done

for f in "$SRC_DIR/bmad/templates"/*; do
  base="$(basename "$f")"
  if [[ ! -e "$TARGET/.bmad/templates/$base" ]]; then
    cp "$f" "$TARGET/.bmad/templates/$base"
  fi
done

for f in "$SRC_DIR/bmad/scripts"/*; do
  base="$(basename "$f")"
  if [[ ! -e "$TARGET/.bmad/scripts/$base" ]]; then
    cp "$f" "$TARGET/.bmad/scripts/$base"
  fi
done

if [[ -d "$SRC_DIR/bmad/baseline/spec" ]]; then
  for f in "$SRC_DIR/bmad/baseline/spec"/*; do
    base="$(basename "$f")"
    if [[ ! -e "$TARGET/.bmad/baseline/spec/$base" ]]; then
      cp "$f" "$TARGET/.bmad/baseline/spec/$base"
    fi
  done
fi

# Project templates
if [[ ! -e "$TARGET/.bmad/project/validation-profile.yml" ]]; then
  cp "$SRC_DIR/bmad/project/validation-profile.template.yml" "$TARGET/.bmad/project/validation-profile.yml"
fi
if [[ ! -e "$TARGET/.bmad/project/coding-profile.yml" ]]; then
  cp "$SRC_DIR/bmad/project/coding-profile.template.yml" "$TARGET/.bmad/project/coding-profile.yml"
fi

# Docs templates
if [[ ! -e "$TARGET/docs/development/ai-dev-launch-guide.md" ]]; then
  cp "$SRC_DIR/docs/development/ai-dev-launch-guide.md" "$TARGET/docs/development/ai-dev-launch-guide.md"
fi
if [[ ! -e "$TARGET/docs/development/ai-dev-coding-guardrails.md" ]]; then
  cp "$SRC_DIR/docs/development/ai-dev-coding-guardrails.md" "$TARGET/docs/development/ai-dev-coding-guardrails.md"
fi

# Skills (copy missing skill folders)
for d in "$SRC_DIR/claude/skills"/*; do
  name="$(basename "$d")"
  if [[ ! -e "$TARGET/.claude/skills/$name" ]]; then
    cp -R "$d" "$TARGET/.claude/skills/"
  fi
done

chmod +x "$TARGET/.bmad/scripts/spec_baseline.py" 2>/dev/null || true
chmod +x "$TARGET/.bmad/scripts/audit_workflow.py" 2>/dev/null || true

cat <<EOF2
Install completed.

Next:
  1) Edit $TARGET/.bmad/workflows/workflow.yml and $TARGET/.bmad/workflows/bugfix.yml if you want different guide/profile paths.
  2) Fill in $TARGET/.bmad/project/validation-profile.yml (health URLs, client base URLs).
  3) Customize:
     - $TARGET/docs/development/ai-dev-launch-guide.md
     - $TARGET/docs/development/ai-dev-coding-guardrails.md
  4) Run coordinator:
     - /coordinator verification_policy=default|ask|strict baseline=auto|seed|skip
  5) Optional baseline ops (slash):
     - /baseline-spec action=status workflow=.bmad/workflows/workflow.yml strict=true
EOF2
