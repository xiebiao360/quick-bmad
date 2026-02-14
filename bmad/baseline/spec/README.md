# BMAD Spec Baseline

This directory stores long-lived frozen spec artifacts reused across workflow runs.

- Source files come from `.bmad/artifacts/` via:
  - `python3 .bmad/scripts/spec_baseline.py snapshot`
- New runs can seed missing artifacts via:
  - `python3 .bmad/scripts/spec_baseline.py seed`
- Typical baseline files:
  - `discovery-prd.md`
  - `discovery-scope-definition.md`
  - `architecture_design-adr.md`
  - `architecture_design-impact-analysis.md`
  - `ui-ux-design-spec.md`
  - `api-design.md`

Do not treat this directory as run-scoped temporary output. It is intentionally preserved across archives.
