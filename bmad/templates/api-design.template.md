# API Design (Frozen Contract)

**Version**: 1.0  
**Date**: YYYY-MM-DD  
**Owner**: Backend  
**References**:
- PRD: `.bmad/artifacts/discovery-prd.md`
- Scope: `.bmad/artifacts/discovery-scope-definition.md`
- ADR: `.bmad/artifacts/architecture_design-adr.md`
- Impact: `.bmad/artifacts/architecture_design-impact-analysis.md`
- UI/UX: `.bmad/artifacts/ui-ux-design-spec.md`

## 1. Summary
- In-scope API surfaces
- Out-of-scope / Non-goals
- Compatibility / versioning strategy (if any)

## 2. Conventions
- Base URL(s) / environment notes
- AuthN/AuthZ (JWT/session, roles, scopes)
- Request headers (trace id, idempotency key)
- Response envelope (if used)
- Time format / timezone
- Pagination, sorting, filtering conventions
- Error model (error code taxonomy + recoverability)

## 3. Data Models
Define core DTOs (request/response) with field-level notes:
- required/optional
- validation rules
- example values

## 4. Endpoint Catalog
For each endpoint:
- Method + Path
- Purpose (link to PRD item / UX flow)
- Auth requirement
- Request body/query params
- Response body
- Error cases
- Idempotency (Y/N) and key rules
- Side effects/events

## 5. Third-Party Integrations
- IM (group create/member manage) - success/failure paths
- Map / geo - expected inputs/outputs and fallbacks
- Pay - order creation, callback, retry, reconciliation
- AI parse - request schema, timeout/retry, fallbacks

## 6. Open Questions
- Q1:
- Q2:

## 7. Change Log
- YYYY-MM-DD: Initial freeze
