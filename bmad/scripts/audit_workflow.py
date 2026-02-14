#!/usr/bin/env python3
"""Audit BMAD workflow definitions and runtime state/evidence consistency.

Usage:
  python3 .bmad/scripts/audit_workflow.py
  python3 .bmad/scripts/audit_workflow.py --workflow .bmad/workflows/workflow.yml
  python3 .bmad/scripts/audit_workflow.py --state .bmad/artifacts/workflow-state.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


DEFAULT_MILESTONE_KEYS = ["prd", "scope", "adr", "impact", "ui_ux_spec", "api_design"]


@dataclass
class Finding:
    severity: str  # ERROR | WARN | INFO
    code: str
    message: str
    ref: Optional[str] = None


def iso_to_datetime(value: str) -> Optional[dt.datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be object: {path}")
    return data


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def check_workflow_definition(path: Path) -> Tuple[List[Finding], Dict[str, Any]]:
    findings: List[Finding] = []
    wf = load_yaml(path)

    artifacts = wf.get("artifacts")
    stages = wf.get("stages")
    milestone = wf.get("milestone", {})

    if not isinstance(artifacts, dict):
        findings.append(
            Finding(
                "ERROR",
                "WF_ARTIFACTS_MISSING",
                "workflow.artifacts must be a mapping",
                str(path),
            )
        )
        artifacts = {}

    if not isinstance(stages, list) or not stages:
        findings.append(
            Finding(
                "ERROR",
                "WF_STAGES_MISSING",
                "workflow.stages must be a non-empty list",
                str(path),
            )
        )
        stages = []

    if not isinstance(milestone, dict):
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_INVALID",
                "workflow.milestone must be a mapping",
                str(path),
            )
        )
        milestone = {}

    milestone_enabled = milestone.get("enabled", True)
    milestone_dir = milestone.get("dir", ".bmad/milestones")
    milestone_pointer = milestone.get("active_pointer", ".bmad/milestones/ACTIVE")
    milestone_lock_filename = milestone.get("lock_filename", "milestone-lock.yml")
    milestone_keys = milestone.get("keys", DEFAULT_MILESTONE_KEYS)
    milestone_enforce_stage = milestone.get("enforce_from_stage", "parallel_dev")

    if not isinstance(milestone_enabled, bool):
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_ENABLED_INVALID",
                "workflow.milestone.enabled must be bool",
                str(path),
            )
        )
        milestone_enabled = True

    if not isinstance(milestone_dir, str) or not milestone_dir.strip():
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_DIR_INVALID",
                "workflow.milestone.dir must be a non-empty string",
                str(path),
            )
        )

    if not isinstance(milestone_pointer, str) or not milestone_pointer.strip():
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_POINTER_INVALID",
                "workflow.milestone.active_pointer must be a non-empty string",
                str(path),
            )
        )

    if not isinstance(milestone_lock_filename, str) or not milestone_lock_filename.strip():
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_LOCK_FILENAME_INVALID",
                "workflow.milestone.lock_filename must be a non-empty string",
                str(path),
            )
        )

    if not isinstance(milestone_keys, list):
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_KEYS_INVALID",
                "workflow.milestone.keys must be a list",
                str(path),
            )
        )
        milestone_keys = []

    if not isinstance(milestone_enforce_stage, str):
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_ENFORCE_INVALID",
                "workflow.milestone.enforce_from_stage must be string",
                str(path),
            )
        )
        milestone_enforce_stage = ""

    if milestone_enabled:
        for key in milestone_keys:
            if key not in artifacts:
                findings.append(
                    Finding(
                        "ERROR",
                        "WF_MILESTONE_KEY_UNMAPPED",
                        f"milestone key '{key}' is not mapped in workflow.artifacts",
                        str(path),
                    )
                )

    stage_ids: List[str] = []
    for idx, stage in enumerate(stages):
        if not isinstance(stage, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "WF_STAGE_INVALID",
                    f"stage[{idx}] must be an object",
                    str(path),
                )
            )
            continue

        sid = stage.get("id")
        if not isinstance(sid, str) or not sid.strip():
            findings.append(
                Finding(
                    "ERROR",
                    "WF_STAGE_ID_MISSING",
                    f"stage[{idx}] has no valid id",
                    str(path),
                )
            )
            continue

        stage_ids.append(sid)

        owner = stage.get("owner")
        owners = stage.get("owners")
        if not owner and not owners:
            findings.append(
                Finding(
                    "ERROR",
                    "WF_STAGE_OWNER_MISSING",
                    f"stage '{sid}' must define owner or owners",
                    str(path),
                )
            )

        outputs = stage.get("outputs_required")
        if not isinstance(outputs, list) or not outputs:
            findings.append(
                Finding(
                    "ERROR",
                    "WF_STAGE_OUTPUTS_MISSING",
                    f"stage '{sid}' must define non-empty outputs_required",
                    str(path),
                )
            )
        else:
            for key in outputs:
                if key not in artifacts:
                    findings.append(
                        Finding(
                            "ERROR",
                            "WF_OUTPUT_KEY_UNMAPPED",
                            f"stage '{sid}' outputs_required key '{key}' is not mapped in workflow.artifacts",
                            str(path),
                        )
                    )

        exit_gate = stage.get("exit_gate")
        criteria = exit_gate.get("criteria") if isinstance(exit_gate, dict) else None
        if not isinstance(criteria, list) or not criteria:
            findings.append(
                Finding(
                    "ERROR",
                    "WF_STAGE_EXIT_GATE_MISSING",
                    f"stage '{sid}' must define exit_gate.criteria with at least one item",
                    str(path),
                )
            )

    if len(stage_ids) != len(set(stage_ids)):
        findings.append(
            Finding(
                "ERROR",
                "WF_STAGE_DUPLICATE",
                "workflow has duplicate stage ids",
                str(path),
            )
        )

    if (
        milestone_enabled
        and milestone_enforce_stage
        and milestone_enforce_stage not in stage_ids
    ):
        findings.append(
            Finding(
                "ERROR",
                "WF_MILESTONE_ENFORCE_STAGE_UNKNOWN",
                f"workflow.milestone.enforce_from_stage '{milestone_enforce_stage}' is not a valid stage id",
                str(path),
            )
        )

    metadata = {
        "path": path,
        "artifacts_dir": wf.get("artifacts_dir", ".bmad/artifacts"),
        "artifacts": artifacts,
        "stages": stages,
        "stage_ids": stage_ids,
        "workflow": wf.get("workflow", {}),
        "milestone": {
            "enabled": milestone_enabled,
            "dir": milestone_dir,
            "active_pointer": milestone_pointer,
            "lock_filename": milestone_lock_filename,
            "keys": [str(k) for k in milestone_keys],
            "enforce_from_stage": milestone_enforce_stage,
        },
    }
    return findings, metadata


def resolve_artifact_path(repo_root: Path, artifacts_dir: str, filename: str) -> Path:
    return repo_root / artifacts_dir / filename


def required_tokens_for_artifact(artifact_key: str, filename: str) -> List[str]:
    tokens: List[str] = []
    if artifact_key.endswith("_gate_report") or filename.endswith("-gate-report.md"):
        tokens.extend(["Gate Status", "Blockers"])
    if artifact_key == "qa_test_plan":
        tokens.extend(["Summary", "Smoke Set", "Regression", "Coverage by Task"])
    if artifact_key == "qa_test_report":
        tokens.extend(["Verification Method", "Overall Status"])
    if artifact_key == "architecture_review_gate_report":
        tokens.extend(["Review Scope", "Gate Status"])
    if artifact_key == "milestone_lock_report":
        tokens.extend(["Milestone ID", "Locked Keys", "Lock File"])
    return tokens


def check_artifact_minimum_content(
    artifact_path: Path,
    artifact_key: str,
    filename: str,
) -> List[Finding]:
    findings: List[Finding] = []
    required = required_tokens_for_artifact(artifact_key, filename)
    if not required:
        return findings

    try:
        content = artifact_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        findings.append(
            Finding(
                "ERROR",
                "ARTIFACT_READ_FAILED",
                f"failed to read artifact content: {exc}",
                str(artifact_path),
            )
        )
        return findings

    missing = [token for token in required if token not in content]
    if missing:
        findings.append(
            Finding(
                "ERROR",
                "ARTIFACT_CONTENT_INCOMPLETE",
                f"artifact '{filename}' missing required markers: {', '.join(missing)}",
                str(artifact_path),
            )
        )
    return findings


def resolve_lock_path(repo_root: Path, state_value: str) -> Path:
    p = Path(state_value)
    if p.is_absolute():
        return p
    return repo_root / p


def check_milestone_consistency(
    *,
    repo_root: Path,
    state_path: Path,
    state: Dict[str, Any],
    workflow_meta: Dict[str, Any],
    stage_index: Dict[str, int],
    current_stage: Any,
    completed: List[str],
) -> List[Finding]:
    findings: List[Finding] = []
    milestone: Dict[str, Any] = workflow_meta.get("milestone", {})
    if not milestone.get("enabled", True):
        return findings

    milestone_id = state.get("milestone_id")
    milestone_lock_path_value = state.get("milestone_lock_path")

    require_milestone = False
    scope_freeze_idx = stage_index.get("scope_freeze")
    enforce_stage = milestone.get("enforce_from_stage")
    enforce_idx = stage_index.get(enforce_stage) if isinstance(enforce_stage, str) else None

    if scope_freeze_idx is not None and len(completed) > scope_freeze_idx:
        require_milestone = True

    if enforce_idx is not None:
        if len(completed) >= enforce_idx:
            require_milestone = True
        if isinstance(current_stage, str) and current_stage in stage_index:
            if stage_index[current_stage] >= enforce_idx:
                require_milestone = True

    if not require_milestone:
        return findings

    if not isinstance(milestone_id, str) or not milestone_id.strip():
        findings.append(
            Finding(
                "ERROR",
                "STATE_MILESTONE_ID_MISSING",
                "milestone is required at current stage but state.milestone_id is missing",
                str(state_path),
            )
        )
        return findings

    if not isinstance(milestone_lock_path_value, str) or not milestone_lock_path_value.strip():
        findings.append(
            Finding(
                "ERROR",
                "STATE_MILESTONE_LOCK_PATH_MISSING",
                "milestone is required at current stage but state.milestone_lock_path is missing",
                str(state_path),
            )
        )
        return findings

    lock_path = resolve_lock_path(repo_root, milestone_lock_path_value)
    expected_lock = (
        repo_root
        / str(milestone.get("dir", ".bmad/milestones"))
        / milestone_id
        / str(milestone.get("lock_filename", "milestone-lock.yml"))
    )
    if lock_path.resolve() != expected_lock.resolve():
        findings.append(
            Finding(
                "WARN",
                "STATE_MILESTONE_LOCK_PATH_UNEXPECTED",
                f"state.milestone_lock_path differs from expected convention: {expected_lock}",
                str(state_path),
            )
        )

    if not lock_path.exists():
        findings.append(
            Finding(
                "ERROR",
                "MILESTONE_LOCK_MISSING",
                f"milestone lock file does not exist: {lock_path}",
                str(lock_path),
            )
        )
        return findings

    try:
        lock_data = load_yaml(lock_path)
    except Exception as exc:
        findings.append(
            Finding(
                "ERROR",
                "MILESTONE_LOCK_INVALID",
                f"failed to parse milestone lock: {exc}",
                str(lock_path),
            )
        )
        return findings

    files = lock_data.get("files")
    if not isinstance(files, dict):
        findings.append(
            Finding(
                "ERROR",
                "MILESTONE_LOCK_FILES_INVALID",
                "milestone lock must include files mapping",
                str(lock_path),
            )
        )
        return findings

    lock_id = lock_data.get("milestone_id")
    if isinstance(lock_id, str) and lock_id.strip() and lock_id != milestone_id:
        findings.append(
            Finding(
                "ERROR",
                "MILESTONE_ID_MISMATCH",
                f"state milestone_id '{milestone_id}' does not match lock milestone_id '{lock_id}'",
                str(lock_path),
            )
        )

    artifacts: Dict[str, str] = workflow_meta["artifacts"]
    artifacts_dir: str = workflow_meta["artifacts_dir"]
    milestone_keys = milestone.get("keys", [])
    if not isinstance(milestone_keys, list):
        milestone_keys = []

    for key in milestone_keys:
        filename = artifacts.get(key)
        if not filename:
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_ARTIFACT_UNMAPPED",
                    f"milestone key '{key}' is not mapped in workflow artifacts",
                    str(state_path),
                )
            )
            continue

        entry = files.get(key)
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_LOCK_ENTRY_MISSING",
                    f"milestone lock missing entry for key '{key}'",
                    str(lock_path),
                )
            )
            continue

        locked_path_value = entry.get("locked_path")
        expected_hash = entry.get("sha256")
        lock_artifact_name = entry.get("artifact")

        if not isinstance(locked_path_value, str) or not locked_path_value.strip():
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_LOCKED_PATH_INVALID",
                    f"milestone entry '{key}' has invalid locked_path",
                    str(lock_path),
                )
            )
            continue

        if not isinstance(expected_hash, str) or not expected_hash.strip():
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_LOCK_HASH_INVALID",
                    f"milestone entry '{key}' has invalid sha256",
                    str(lock_path),
                )
            )
            continue

        if isinstance(lock_artifact_name, str) and lock_artifact_name != filename:
            findings.append(
                Finding(
                    "WARN",
                    "MILESTONE_LOCK_ARTIFACT_NAME_DRIFT",
                    f"milestone entry '{key}' artifact name '{lock_artifact_name}' differs from workflow mapping '{filename}'",
                    str(lock_path),
                )
            )

        locked_path = resolve_lock_path(repo_root, locked_path_value)
        if not locked_path.exists() or locked_path.stat().st_size == 0:
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_LOCKED_FILE_MISSING",
                    f"milestone locked file missing/empty for key '{key}': {locked_path}",
                    str(locked_path),
                )
            )
            continue

        locked_hash = sha256_file(locked_path)
        if locked_hash != expected_hash:
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_LOCK_HASH_MISMATCH",
                    f"milestone locked file hash mismatch for key '{key}'",
                    str(locked_path),
                )
            )
            continue

        artifact_path = resolve_artifact_path(repo_root, artifacts_dir, filename)
        if not artifact_path.exists() or artifact_path.stat().st_size == 0:
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_ARTIFACT_MISSING",
                    f"artifact missing/empty for milestone key '{key}': {artifact_path}",
                    str(artifact_path),
                )
            )
            continue

        artifact_hash = sha256_file(artifact_path)
        if artifact_hash != expected_hash:
            findings.append(
                Finding(
                    "ERROR",
                    "MILESTONE_ARTIFACT_DRIFT",
                    f"artifact drift detected for milestone key '{key}'",
                    str(artifact_path),
                )
            )

    return findings


def check_state_against_workflow(
    repo_root: Path,
    state_path: Path,
    template_path: Path,
    workflow_meta: Dict[str, Any],
) -> List[Finding]:
    findings: List[Finding] = []

    if not state_path.exists():
        findings.append(
            Finding(
                "ERROR",
                "STATE_MISSING",
                "workflow-state.json does not exist",
                str(state_path),
            )
        )
        return findings

    state = load_json(state_path)
    template = load_json(template_path) if template_path.exists() else {}

    expected_fields = set(template.keys())
    state_fields = set(state.keys())
    missing_fields = sorted(expected_fields - state_fields)
    unknown_fields = sorted(state_fields - expected_fields)

    for field in missing_fields:
        findings.append(
            Finding(
                "ERROR",
                "STATE_FIELD_MISSING",
                f"workflow-state missing required field '{field}'",
                str(state_path),
            )
        )

    for field in unknown_fields:
        findings.append(
            Finding(
                "WARN",
                "STATE_FIELD_UNKNOWN",
                f"workflow-state has unknown field '{field}'",
                str(state_path),
            )
        )

    stage_ids: List[str] = workflow_meta["stage_ids"]
    stages: List[Dict[str, Any]] = workflow_meta["stages"]
    artifacts: Dict[str, str] = workflow_meta["artifacts"]
    artifacts_dir: str = workflow_meta["artifacts_dir"]
    stage_index = {sid: i for i, sid in enumerate(stage_ids)}

    current_stage = state.get("current_stage")
    completed = state.get("completed_stages")
    if not isinstance(completed, list):
        findings.append(
            Finding(
                "ERROR",
                "STATE_COMPLETED_INVALID",
                "completed_stages must be a list",
                str(state_path),
            )
        )
        completed = []

    if not isinstance(current_stage, str) or current_stage not in stage_index:
        findings.append(
            Finding(
                "ERROR",
                "STATE_CURRENT_STAGE_INVALID",
                "current_stage is missing or not in workflow stages",
                str(state_path),
            )
        )
    else:
        expected_prefix = stage_ids[: stage_index[current_stage]]
        if completed != expected_prefix:
            findings.append(
                Finding(
                    "ERROR",
                    "STATE_STAGE_SEQUENCE_INVALID",
                    "completed_stages must exactly match stages before current_stage",
                    str(state_path),
                )
            )

    if len(completed) != len(set(completed)):
        findings.append(
            Finding(
                "ERROR",
                "STATE_COMPLETED_DUPLICATE",
                "completed_stages contains duplicates",
                str(state_path),
            )
        )

    for sid in completed:
        if sid not in stage_index:
            findings.append(
                Finding(
                    "ERROR",
                    "STATE_COMPLETED_UNKNOWN",
                    f"completed stage '{sid}' is unknown",
                    str(state_path),
                )
            )

    artifacts_created = state.get("artifacts_created", [])
    if not isinstance(artifacts_created, list):
        findings.append(
            Finding(
                "ERROR",
                "STATE_ARTIFACTS_CREATED_INVALID",
                "artifacts_created must be a list",
                str(state_path),
            )
        )
        artifacts_created = []

    for sid in completed:
        stage = stages[stage_index[sid]]
        outputs = stage.get("outputs_required", [])
        for key in outputs:
            filename = artifacts.get(key)
            if not filename:
                findings.append(
                    Finding(
                        "ERROR",
                        "STATE_OUTPUT_UNMAPPED",
                        f"stage '{sid}' output key '{key}' has no artifact mapping",
                    )
                )
                continue

            artifact_path = resolve_artifact_path(repo_root, artifacts_dir, filename)
            if not artifact_path.exists():
                findings.append(
                    Finding(
                        "ERROR",
                        "STATE_OUTPUT_MISSING_FILE",
                        f"stage '{sid}' expected artifact missing: {artifact_path}",
                        str(artifact_path),
                    )
                )
                continue

            if artifact_path.stat().st_size == 0:
                findings.append(
                    Finding(
                        "ERROR",
                        "STATE_OUTPUT_EMPTY_FILE",
                        f"stage '{sid}' expected artifact is empty: {artifact_path}",
                        str(artifact_path),
                    )
                )
            else:
                findings.extend(
                    check_artifact_minimum_content(artifact_path, key, filename)
                )

            if filename not in artifacts_created:
                findings.append(
                    Finding(
                        "WARN",
                        "STATE_OUTPUT_NOT_TRACKED",
                        f"artifact '{filename}' exists for completed stage '{sid}' but is missing from state.artifacts_created",
                        str(state_path),
                    )
                )

    last_updated = iso_to_datetime(str(state.get("last_updated_at", "")))
    if last_updated is None:
        findings.append(
            Finding(
                "ERROR",
                "STATE_LAST_UPDATED_INVALID",
                "last_updated_at is missing or not valid ISO8601",
                str(state_path),
            )
        )
    elif isinstance(current_stage, str) and current_stage in stage_index:
        stage = stages[stage_index[current_stage]]
        outputs = stage.get("outputs_required", [])
        stale_outputs: List[str] = []
        for key in outputs:
            filename = artifacts.get(key)
            if not filename:
                continue
            artifact_path = resolve_artifact_path(repo_root, artifacts_dir, filename)
            if artifact_path.exists():
                mtime = dt.datetime.fromtimestamp(
                    artifact_path.stat().st_mtime, tz=last_updated.tzinfo
                )
                if mtime < last_updated:
                    stale_outputs.append(filename)
        if stale_outputs:
            findings.append(
                Finding(
                    "WARN",
                    "STATE_CURRENT_STAGE_STALE_OUTPUTS",
                    (
                        "current_stage already has older output artifacts before last_updated_at; "
                        "possible stale evidence reuse: "
                        + ", ".join(sorted(stale_outputs))
                    ),
                    str(state_path),
                )
            )

    verification_policy = state.get("verification_policy")
    if verification_policy not in {"default", "ask", "strict"}:
        findings.append(
            Finding(
                "ERROR",
                "STATE_VERIFICATION_POLICY_INVALID",
                "verification_policy must be one of: default|ask|strict",
                str(state_path),
            )
        )

    verification_decision = state.get("verification_decision")
    if verification_decision not in {"unknown", "execute", "skip"}:
        findings.append(
            Finding(
                "ERROR",
                "STATE_VERIFICATION_DECISION_INVALID",
                "verification_decision must be one of: unknown|execute|skip",
                str(state_path),
            )
        )

    task_ids = state.get("task_ids", [])
    if not isinstance(task_ids, list):
        findings.append(
            Finding(
                "ERROR",
                "STATE_TASK_IDS_INVALID",
                "task_ids must be a list",
                str(state_path),
            )
        )
    elif "parallel_dev" in completed and not task_ids:
        findings.append(
            Finding(
                "ERROR",
                "STATE_TASK_IDS_EMPTY",
                "parallel_dev is completed but task_ids is empty",
                str(state_path),
            )
        )

    findings.extend(
        check_milestone_consistency(
            repo_root=repo_root,
            state_path=state_path,
            state=state,
            workflow_meta=workflow_meta,
            stage_index=stage_index,
            current_stage=current_stage,
            completed=completed,
        )
    )

    return findings


def print_findings(findings: Iterable[Finding]) -> int:
    errors = 0
    warnings = 0
    infos = 0
    for item in findings:
        if item.severity == "ERROR":
            errors += 1
        elif item.severity == "WARN":
            warnings += 1
        else:
            infos += 1
        suffix = f" [{item.ref}]" if item.ref else ""
        print(f"{item.severity} {item.code}: {item.message}{suffix}")

    print(f"\nSummary: {errors} error(s), {warnings} warning(s), {infos} info")
    return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit BMAD workflow and state consistency."
    )
    parser.add_argument(
        "--workflow",
        action="append",
        help="Workflow YAML path to audit. Can be passed multiple times.",
    )
    parser.add_argument(
        "--state",
        default=".bmad/artifacts/workflow-state.json",
        help="workflow-state.json path",
    )
    parser.add_argument(
        "--template",
        default=".bmad/templates/workflow-state.template.json",
        help="workflow-state template path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()

    workflow_paths = args.workflow or [
        ".bmad/workflows/workflow.yml",
        ".bmad/workflows/bugfix.yml",
    ]
    workflow_paths_resolved = [repo_root / p for p in workflow_paths]

    findings: List[Finding] = []
    workflow_meta_by_path: Dict[str, Dict[str, Any]] = {}

    for wf_path in workflow_paths_resolved:
        if not wf_path.exists():
            findings.append(
                Finding(
                    "ERROR",
                    "WF_FILE_MISSING",
                    "workflow file does not exist",
                    str(wf_path),
                )
            )
            continue

        try:
            wf_findings, meta = check_workflow_definition(wf_path)
            findings.extend(wf_findings)
            workflow_meta_by_path[str(wf_path.resolve())] = meta
        except Exception as exc:
            findings.append(
                Finding(
                    "ERROR",
                    "WF_LOAD_FAILED",
                    f"failed to parse workflow: {exc}",
                    str(wf_path),
                )
            )

    state_path = repo_root / args.state
    template_path = repo_root / args.template

    if state_path.exists():
        try:
            state = load_json(state_path)
            state_workflow_path = state.get("workflow_path")
            if isinstance(state_workflow_path, str) and state_workflow_path.strip():
                resolved = (repo_root / state_workflow_path).resolve()
                meta = workflow_meta_by_path.get(str(resolved))
                if meta is None and resolved.exists():
                    wf_findings, meta = check_workflow_definition(resolved)
                    findings.extend(wf_findings)
                    workflow_meta_by_path[str(resolved)] = meta

                if meta:
                    findings.extend(
                        check_state_against_workflow(
                            repo_root=repo_root,
                            state_path=state_path,
                            template_path=template_path,
                            workflow_meta=meta,
                        )
                    )
                else:
                    findings.append(
                        Finding(
                            "ERROR",
                            "STATE_WORKFLOW_UNRESOLVED",
                            "state.workflow_path cannot be resolved for state validation",
                            str(state_path),
                        )
                    )
            else:
                findings.append(
                    Finding(
                        "ERROR",
                        "STATE_WORKFLOW_PATH_MISSING",
                        "state.workflow_path is missing",
                        str(state_path),
                    )
                )
        except Exception as exc:
            findings.append(
                Finding(
                    "ERROR",
                    "STATE_LOAD_FAILED",
                    f"failed to parse state: {exc}",
                    str(state_path),
                )
            )
    else:
        findings.append(
            Finding(
                "WARN",
                "STATE_NOT_FOUND",
                "workflow-state file not found; runtime checks skipped",
                str(state_path),
            )
        )

    return print_findings(findings)


if __name__ == "__main__":
    sys.exit(main())
