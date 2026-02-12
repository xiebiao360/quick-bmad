#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
BMAD Portable installer

Usage:
  ./scripts/install.sh [--target <repo-root>] [--mode copy]

Installs:
  - .bmad/ (workflows, templates)
  - .bmad/project templates (validation-profile, coding-profile)
  - .claude/skills (BMAD skills)
  - docs/development templates (validation guide, coding guardrails)

Notes:
  - Existing files are not overwritten; templates are installed only if missing.
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

mkdir -p "$TARGET/.bmad" "$TARGET/.claude/skills" "$TARGET/docs/development" "$TARGET/.bmad/project"

# .bmad core
if [[ ! -e "$TARGET/.bmad/workflows" ]]; then
  cp -R "$SRC_DIR/bmad/workflows" "$TARGET/.bmad/"
fi
if [[ ! -e "$TARGET/.bmad/templates" ]]; then
  cp -R "$SRC_DIR/bmad/templates" "$TARGET/.bmad/"
fi

# project templates
if [[ ! -e "$TARGET/.bmad/project/validation-profile.yml" ]]; then
  cp "$SRC_DIR/bmad/project/validation-profile.template.yml" "$TARGET/.bmad/project/validation-profile.yml"
fi
if [[ ! -e "$TARGET/.bmad/project/coding-profile.yml" ]]; then
  cp "$SRC_DIR/bmad/project/coding-profile.template.yml" "$TARGET/.bmad/project/coding-profile.yml"
fi

# docs templates
if [[ ! -e "$TARGET/docs/development/ai-dev-launch-guide.md" ]]; then
  cp "$SRC_DIR/docs/development/ai-dev-launch-guide.md" "$TARGET/docs/development/ai-dev-launch-guide.md"
fi
if [[ ! -e "$TARGET/docs/development/ai-dev-coding-guardrails.md" ]]; then
  cp "$SRC_DIR/docs/development/ai-dev-coding-guardrails.md" "$TARGET/docs/development/ai-dev-coding-guardrails.md"
fi

# skills
for d in "$SRC_DIR/claude/skills"/*; do
  name="$(basename "$d")"
  if [[ ! -e "$TARGET/.claude/skills/$name" ]]; then
    cp -R "$d" "$TARGET/.claude/skills/"
  fi
done

cat <<EOF2
Install completed.

Next:
  1) Edit $TARGET/.bmad/workflows/workflow.yml and $TARGET/.bmad/workflows/bugfix.yml if you want different guide/profile paths.
  2) Fill in $TARGET/.bmad/project/validation-profile.yml (health URLs, client base URLs).
  3) Customize:
     - $TARGET/docs/development/ai-dev-launch-guide.md
     - $TARGET/docs/development/ai-dev-coding-guardrails.md
  4) Run coordinator:
     - /coordinator verification_policy=default|ask|strict
EOF2
