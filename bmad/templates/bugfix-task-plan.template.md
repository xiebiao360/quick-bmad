# Bugfix Task Plan

## Task ID
(TASK-XXX 由 Coordinator 自动生成)

## Title
(一句话)

## Related Artifacts
- Bug brief: .bmad/artifacts/bugfix-bug-brief.md
- Repro: .bmad/artifacts/bugfix-repro-steps.md

---

## 1) 分析（Analysis）
### Goal
- 要解决什么

### Current Behavior Evidence
- Key modules/files/entry points (with paths):
  - 
- Key call flow (high level):
  -

### Constraints / Dependencies
- Depends on (APIs/services/config):
- Affected components:
- Must keep backward compatibility? (Y/N)

### Unknowns / Questions
- 

---

## 2) 探索（Explore）
### Option A
- Approach:
- Pros:
- Cons/Risks:

### Option B
- Approach:
- Pros:
- Cons/Risks:

### Decision
- Chosen option:
- Why:
- Risk mitigations:

---

## 3) 实施（Implement）
### Allowed Scope (explicit)
- Modules/files:
- APIs/DB:
- Configuration:

### Forbidden Scope (explicit)
- Modules/files:
- APIs:
- DB schema:

### Change Steps
1.
2.
3.

### Rollback Plan
- How to revert quickly:
- Safe fallback / feature flag:

---

## 4) 质量审查（Quality Review）
### Regression Risks (>=5)
1.
2.
3.
4.
5.

### Must-test Cases (>=5)
1.
2.
3.
4.
5.

### Observability (optional)
- Logs/metrics to add or verify:
- Alerts (if P0):

### Docs/Notes (optional)
- README / comments changes:
