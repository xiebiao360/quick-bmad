# BMAD Milestones

Milestones are immutable spec snapshots for a single delivery period.

- One milestone locks one approved spec set:
  - `discovery-prd.md`
  - `discovery-scope-definition.md`
  - `architecture_design-adr.md`
  - `architecture_design-impact-analysis.md`
  - `ui-ux-design-spec.md`
  - `api-design.md`
- Lock file path:
  - `.bmad/milestones/<milestone-id>/milestone-lock.yml`
- Active milestone pointer:
  - `.bmad/milestones/ACTIVE`

Typical flow:

1) Freeze specs and create lock:

```bash
python3 .bmad/scripts/milestone_lock.py --workflow .bmad/workflows/workflow.yml create --milestone-id M1
```

2) Start next run from a locked milestone:

```bash
python3 .bmad/scripts/milestone_lock.py --workflow .bmad/workflows/workflow.yml use --milestone-id M1
```

3) Verify no drift during implementation:

```bash
python3 .bmad/scripts/milestone_lock.py --workflow .bmad/workflows/workflow.yml verify --milestone-id M1
```
