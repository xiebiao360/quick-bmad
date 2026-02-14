# Manifest

This bundle is intentionally split into:

- **Generic engine**: workflows/templates/skills
- **Project-bound knobs**: validation guide, coding guardrails, profiles
- **Examples**: a concrete project snapshot (LiangX) for reference

## Included

- `.bmad/workflows/workflow.yml`
- `.bmad/workflows/bugfix.yml`
- `.bmad/templates/*`
- `.bmad/project/*.template.yml`
- `.bmad/scripts/spec_baseline.py`
- `.bmad/scripts/audit_workflow.py`
- `.bmad/baseline/spec/README.md`
- `.claude/skills/*` (BMAD-related skills)
- `.claude/skills/baseline-spec/SKILL.md`
- `docs/development/ai-dev-launch-guide.md` (template)
- `docs/development/ai-dev-coding-guardrails.md` (template)
- `scripts/install.sh`, `scripts/verify.sh`

## Not Included (by design)

- Any real secrets, credentials, or environment-specific endpoints
- Your production configs
- Your database contents
