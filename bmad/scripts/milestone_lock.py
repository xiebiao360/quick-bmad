#!/usr/bin/env python3
"""Manage BMAD milestone locks.

Commands:
  status         - show milestone configuration and active lock status
  create         - create lock from current artifacts
  import-archive - create lock from an archive directory
  use            - seed artifacts from a lock
  verify         - verify artifacts match lock hashes
  set-active     - update active milestone pointer only
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

DEFAULT_KEYS = ["prd", "scope", "adr", "impact", "ui_ux_spec", "api_design"]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"invalid YAML object: {path}")
    return data


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return data


def dump_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=False, sort_keys=False)


def write_report(path: Path, title: str, rows: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {title}", "", f"- Timestamp: {now_iso()}", ""] + rows + [""]
    path.write_text("\n".join(body), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def find_latest_archive_dir(repo_root: Path) -> Path | None:
    root = repo_root / ".bmad/archive"
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_config(
    workflow: Dict[str, Any], repo_root: Path
) -> Tuple[bool, Path, Path, str, Path, Dict[str, str], List[str]]:
    artifacts_dir = workflow.get("artifacts_dir", ".bmad/artifacts")
    artifacts = workflow.get("artifacts", {})
    milestone = workflow.get("milestone", {})

    if not isinstance(artifacts, dict):
        raise ValueError("workflow.artifacts must be a mapping")
    if not isinstance(milestone, dict):
        raise ValueError("workflow.milestone must be a mapping")

    enabled = milestone.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("workflow.milestone.enabled must be bool")

    mdir = milestone.get("dir", ".bmad/milestones")
    pointer = milestone.get("active_pointer", ".bmad/milestones/ACTIVE")
    lock_filename = milestone.get("lock_filename", "milestone-lock.yml")
    keys = milestone.get("keys", DEFAULT_KEYS)

    if not isinstance(mdir, str) or not mdir.strip():
        raise ValueError("workflow.milestone.dir must be non-empty string")
    if not isinstance(pointer, str) or not pointer.strip():
        raise ValueError("workflow.milestone.active_pointer must be non-empty string")
    if not isinstance(lock_filename, str) or not lock_filename.strip():
        raise ValueError("workflow.milestone.lock_filename must be non-empty string")
    if not isinstance(keys, list):
        raise ValueError("workflow.milestone.keys must be a list")

    return (
        enabled,
        repo_root / artifacts_dir,
        repo_root / mdir,
        lock_filename,
        repo_root / pointer,
        artifacts,
        [str(k) for k in keys],
    )


def read_active_milestone(pointer_path: Path) -> str | None:
    if not pointer_path.exists():
        return None
    value = pointer_path.read_text(encoding="utf-8").strip()
    return value or None


def write_active_milestone(pointer_path: Path, milestone_id: str) -> None:
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(f"{milestone_id}\n", encoding="utf-8")


def load_lock(lock_path: Path) -> Dict[str, Any]:
    data = load_yaml(lock_path)
    if not isinstance(data.get("files"), dict):
        raise ValueError(f"lock missing files mapping: {lock_path}")
    return data


def resolve_lock_path(
    milestone_dir: Path, milestone_id: str, lock_filename: str
) -> Path:
    return milestone_dir / milestone_id / lock_filename


def update_state_milestone(repo_root: Path, milestone_id: str, lock_path: Path) -> None:
    state_path = repo_root / ".bmad/artifacts/workflow-state.json"
    if not state_path.exists():
        return
    try:
        state = load_json(state_path)
    except Exception:
        return

    state["milestone_id"] = milestone_id
    state["milestone_lock_path"] = relpath(lock_path, repo_root)
    state["milestone_locked_at"] = now_iso()

    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def create_lock(
    *,
    repo_root: Path,
    workflow_path: str,
    source_dir: Path,
    source_label: str,
    milestone_id: str,
    force: bool,
    allow_partial: bool,
    set_active: bool,
    report_path: Path,
) -> int:
    workflow = load_yaml(repo_root / workflow_path)
    (
        enabled,
        artifacts_dir,
        milestone_dir,
        lock_filename,
        pointer_path,
        artifacts,
        keys,
    ) = resolve_config(workflow, repo_root)

    if not enabled:
        write_report(
            report_path,
            "Milestone Create Report",
            ["## Summary", "- Milestone is disabled in workflow", "- No changes made"],
        )
        print("milestone is disabled in workflow")
        return 1

    lock_path = resolve_lock_path(milestone_dir, milestone_id, lock_filename)
    spec_dir = lock_path.parent / "spec"
    if lock_path.exists() and not force:
        print(f"lock already exists: {lock_path} (use --force to overwrite)")
        return 1

    missing_map: List[str] = []
    missing_source: List[str] = []
    available: List[Tuple[str, str, Path]] = []

    for key in keys:
        filename = artifacts.get(key)
        if not filename:
            missing_map.append(key)
            continue
        src = source_dir / filename
        if not src.exists() or src.stat().st_size == 0:
            missing_source.append(f"{key}:{src}")
            continue
        available.append((key, filename, src))

    if (missing_map or missing_source) and not allow_partial:
        rows = [
            "## Summary",
            f"- Source: {source_dir}",
            f"- Milestone ID: {milestone_id}",
            f"- Missing source: {len(missing_source)}",
            f"- Missing mapping: {len(missing_map)}",
            "- Result: FAILED (partial lock is not allowed)",
            "",
            "## Missing Source",
        ] + [f"- {item}" for item in missing_source]
        rows += ["", "## Missing Mapping"] + [f"- {item}" for item in missing_map]
        write_report(report_path, "Milestone Create Report", rows)
        print("failed: missing sources or mapping (use --allow-partial to bypass)")
        print(f"report={report_path}")
        return 1

    copied: List[str] = []
    files: Dict[str, Dict[str, str]] = {}
    spec_dir.mkdir(parents=True, exist_ok=True)

    for key, filename, src in available:
        dst = spec_dir / filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        digest = sha256_file(dst)
        files[key] = {
            "artifact": filename,
            "locked_path": relpath(dst, repo_root),
            "sha256": digest,
        }
        copied.append(relpath(dst, repo_root))

    lock_data = {
        "schema_version": 1,
        "workflow_path": workflow_path,
        "milestone_id": milestone_id,
        "created_at": now_iso(),
        "source": {
            "type": source_label,
            "path": relpath(source_dir, repo_root),
        },
        "artifacts_dir": relpath(artifacts_dir, repo_root),
        "keys": keys,
        "files": files,
    }
    dump_yaml(lock_path, lock_data)

    if set_active:
        write_active_milestone(pointer_path, milestone_id)

    update_state_milestone(repo_root, milestone_id, lock_path)

    rows = [
        "## Summary",
        f"- Source: {source_dir}",
        f"- Milestone ID: {milestone_id}",
        f"- Lock File: {relpath(lock_path, repo_root)}",
        f"- Locked Keys: {', '.join(sorted(files.keys()))}",
        f"- Copied: {len(copied)}",
        f"- Missing source: {len(missing_source)}",
        f"- Missing mapping: {len(missing_map)}",
        f"- Set Active: {'yes' if set_active else 'no'}",
        "",
        "## Copied Files",
    ] + [f"- {item}" for item in copied]
    rows += ["", "## Missing Source"] + [f"- {item}" for item in missing_source]
    rows += ["", "## Missing Mapping"] + [f"- {item}" for item in missing_map]

    write_report(report_path, "Milestone Create Report", rows)

    print(
        f"milestone={milestone_id} copied={len(copied)} missing_source={len(missing_source)} missing_map={len(missing_map)}"
    )
    print(f"lock={lock_path}")
    print(f"report={report_path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    workflow = load_yaml(repo_root / args.workflow)
    (
        enabled,
        artifacts_dir,
        milestone_dir,
        lock_filename,
        pointer_path,
        artifacts,
        keys,
    ) = resolve_config(workflow, repo_root)

    print(f"workflow: {args.workflow}")
    print(f"enabled: {enabled}")
    print(f"artifacts_dir: {artifacts_dir}")
    print(f"milestone_dir: {milestone_dir}")
    print(f"active_pointer: {pointer_path}")
    print(f"keys: {', '.join(keys)}")

    if not enabled:
        return 0

    active = read_active_milestone(pointer_path)
    print(f"active_milestone: {active if active else '<none>'}")
    if not active:
        return 1 if args.strict else 0

    lock_path = resolve_lock_path(milestone_dir, active, lock_filename)
    if not lock_path.exists():
        print(f"lock: MISSING ({lock_path})")
        return 1 if args.strict else 0

    lock = load_lock(lock_path)
    files = lock.get("files", {})

    missing = 0
    for key in keys:
        filename = artifacts.get(key)
        if not filename:
            print(f"[MISSING MAP] {key} -> <not mapped in workflow.artifacts>")
            missing += 1
            continue
        entry = files.get(key)
        if not isinstance(entry, dict):
            print(f"[MISSING LOCK] {key} -> <entry missing in lock>")
            missing += 1
            continue

        locked_path = repo_root / str(entry.get("locked_path", ""))
        artifact_path = artifacts_dir / filename

        if not locked_path.exists() or locked_path.stat().st_size == 0:
            print(f"[MISSING LOCK FILE] {key} -> {locked_path}")
            missing += 1
            continue

        digest = str(entry.get("sha256", ""))
        lock_ok = digest == sha256_file(locked_path)
        if not lock_ok:
            print(f"[LOCK HASH MISMATCH] {key} -> {locked_path}")
            missing += 1
            continue

        if not artifact_path.exists() or artifact_path.stat().st_size == 0:
            print(f"[ARTIFACT MISSING] {key} -> {artifact_path}")
            missing += 1
            continue

        artifact_ok = sha256_file(artifact_path) == digest
        label = "OK" if artifact_ok else "DRIFT"
        print(f"[{label}] {key} -> {artifact_path}")
        if not artifact_ok:
            missing += 1

    return 1 if missing and args.strict else 0


def cmd_create(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    return create_lock(
        repo_root=repo_root,
        workflow_path=args.workflow,
        source_dir=repo_root / ".bmad/artifacts",
        source_label="artifacts",
        milestone_id=args.milestone_id,
        force=args.force,
        allow_partial=args.allow_partial,
        set_active=args.set_active,
        report_path=repo_root / args.report,
    )


def cmd_import_archive(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    if args.archive_dir:
        source_dir = repo_root / args.archive_dir
    else:
        latest = find_latest_archive_dir(repo_root)
        if latest is None:
            print("no archive directory found under .bmad/archive/")
            return 1
        source_dir = latest

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"archive dir not found: {source_dir}")
        return 1

    return create_lock(
        repo_root=repo_root,
        workflow_path=args.workflow,
        source_dir=source_dir,
        source_label="archive",
        milestone_id=args.milestone_id,
        force=args.force,
        allow_partial=args.allow_partial,
        set_active=args.set_active,
        report_path=repo_root / args.report,
    )


def resolve_target_lock(
    *,
    repo_root: Path,
    workflow_path: str,
    milestone_id: str | None,
) -> Tuple[Path, Dict[str, Any], Dict[str, str], Path, str, str, List[str]]:
    workflow = load_yaml(repo_root / workflow_path)
    (
        enabled,
        artifacts_dir,
        milestone_dir,
        lock_filename,
        pointer_path,
        artifacts,
        keys,
    ) = resolve_config(workflow, repo_root)

    if not enabled:
        raise ValueError("milestone is disabled in workflow")

    resolved_id = milestone_id or read_active_milestone(pointer_path)
    if not resolved_id:
        raise ValueError("milestone_id is required (or set an active milestone first)")

    lock_path = resolve_lock_path(milestone_dir, resolved_id, lock_filename)
    if not lock_path.exists():
        raise ValueError(f"lock file not found: {lock_path}")

    lock = load_lock(lock_path)
    return lock_path, lock, artifacts, artifacts_dir, resolved_id, lock_filename, keys


def cmd_use(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()

    try:
        (
            lock_path,
            lock,
            artifacts,
            artifacts_dir,
            milestone_id,
            _,
            _keys,
        ) = resolve_target_lock(
            repo_root=repo_root,
            workflow_path=args.workflow,
            milestone_id=args.milestone_id,
        )
    except Exception as exc:
        print(exc)
        return 1

    files = lock.get("files", {})
    copied: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    for key, entry in files.items():
        if not isinstance(entry, dict):
            failed.append(f"{key}:invalid lock entry")
            continue

        filename = artifacts.get(key)
        if not filename:
            failed.append(f"{key}:not mapped in workflow.artifacts")
            continue

        src = repo_root / str(entry.get("locked_path", ""))
        expected_hash = str(entry.get("sha256", ""))
        if not src.exists() or src.stat().st_size == 0:
            failed.append(f"{key}:locked file missing {src}")
            continue
        if sha256_file(src) != expected_hash:
            failed.append(f"{key}:locked file hash mismatch {src}")
            continue

        dst = artifacts_dir / filename
        if dst.exists() and not args.force:
            skipped.append(relpath(dst, repo_root))
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(relpath(dst, repo_root))

    if not failed:
        update_state_milestone(repo_root, milestone_id, lock_path)

    report_path = repo_root / args.report
    rows = [
        "## Summary",
        f"- Milestone ID: {milestone_id}",
        f"- Lock File: {relpath(lock_path, repo_root)}",
        f"- Copied: {len(copied)}",
        f"- Skipped: {len(skipped)}",
        f"- Failed: {len(failed)}",
        "",
        "## Copied",
    ] + [f"- {item}" for item in copied]
    rows += ["", "## Skipped"] + [f"- {item}" for item in skipped]
    rows += ["", "## Failed"] + [f"- {item}" for item in failed]
    write_report(report_path, "Milestone Seed Report", rows)

    print(
        f"milestone={milestone_id} copied={len(copied)} skipped={len(skipped)} failed={len(failed)}"
    )
    print(f"report={report_path}")
    return 1 if failed else 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()

    try:
        (
            lock_path,
            lock,
            artifacts,
            artifacts_dir,
            milestone_id,
            _,
            keys,
        ) = resolve_target_lock(
            repo_root=repo_root,
            workflow_path=args.workflow,
            milestone_id=args.milestone_id,
        )
    except Exception as exc:
        print(exc)
        return 1

    files = lock.get("files", {})
    if not isinstance(files, dict):
        print(f"invalid lock format, missing files mapping: {lock_path}")
        return 1

    ok: List[str] = []
    drift: List[str] = []
    missing: List[str] = []
    extra: List[str] = []

    for key in keys:
        filename = artifacts.get(key)
        if not filename:
            missing.append(f"{key}:not mapped in workflow.artifacts")
            continue

        entry = files.get(key)
        if not isinstance(entry, dict):
            missing.append(f"{key}:missing lock entry")
            continue

        locked_path_value = entry.get("locked_path")
        expected_hash = str(entry.get("sha256", ""))
        if not isinstance(locked_path_value, str) or not locked_path_value.strip():
            missing.append(f"{key}:invalid locked_path in lock")
            continue

        locked_path = resolve_lock_path(repo_root, locked_path_value)
        if not locked_path.exists() or locked_path.stat().st_size == 0:
            missing.append(f"{key}:locked file missing {locked_path}")
            continue

        locked_hash = sha256_file(locked_path)
        if locked_hash != expected_hash:
            drift.append(
                f"{key}:locked file hash mismatch {relpath(locked_path, repo_root)}"
            )
            continue

        artifact_path = artifacts_dir / filename
        if not artifact_path.exists() or artifact_path.stat().st_size == 0:
            missing.append(f"{key}:{artifact_path}")
            continue

        digest = sha256_file(artifact_path)
        if digest == expected_hash:
            ok.append(f"{key}:{relpath(artifact_path, repo_root)}")
        else:
            drift.append(f"{key}:{relpath(artifact_path, repo_root)}")

    for key in files.keys():
        if key not in keys:
            extra.append(str(key))

    report_path = repo_root / args.report
    rows = [
        "## Summary",
        f"- Milestone ID: {milestone_id}",
        f"- Lock File: {relpath(lock_path, repo_root)}",
        f"- OK: {len(ok)}",
        f"- Drift: {len(drift)}",
        f"- Missing: {len(missing)}",
        f"- Extra lock keys: {len(extra)}",
        "",
        "## OK",
    ] + [f"- {item}" for item in ok]
    rows += ["", "## Drift"] + [f"- {item}" for item in drift]
    rows += ["", "## Missing"] + [f"- {item}" for item in missing]
    rows += ["", "## Extra Lock Keys"] + [f"- {item}" for item in extra]
    write_report(report_path, "Milestone Verify Report", rows)

    print(
        f"milestone={milestone_id} ok={len(ok)} drift={len(drift)} missing={len(missing)} extra={len(extra)}"
    )
    print(f"report={report_path}")
    return 1 if drift or missing else 0


def cmd_set_active(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    workflow = load_yaml(repo_root / args.workflow)
    (
        enabled,
        _,
        milestone_dir,
        lock_filename,
        pointer_path,
        _,
        _,
    ) = resolve_config(workflow, repo_root)

    if not enabled:
        print("milestone is disabled in workflow")
        return 1

    lock_path = resolve_lock_path(milestone_dir, args.milestone_id, lock_filename)
    if not lock_path.exists():
        print(f"lock not found: {lock_path}")
        return 1

    write_active_milestone(pointer_path, args.milestone_id)
    print(f"active milestone set: {args.milestone_id}")
    print(f"pointer={pointer_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage BMAD milestone lock lifecycle")
    p.add_argument(
        "--workflow", default=".bmad/workflows/workflow.yml", help="workflow YAML path"
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="show milestone status")
    p_status.add_argument("--strict", action="store_true", help="fail on missing data")
    p_status.set_defaults(func=cmd_status)

    p_create = sub.add_parser("create", help="create lock from artifacts")
    p_create.add_argument("--milestone-id", required=True, help="milestone id")
    p_create.add_argument(
        "--force", action="store_true", help="overwrite existing lock"
    )
    p_create.add_argument(
        "--allow-partial",
        action="store_true",
        help="allow creating lock when some configured keys are missing",
    )
    p_create.add_argument(
        "--set-active",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="set ACTIVE pointer after create (default: true)",
    )
    p_create.add_argument(
        "--report",
        default=".bmad/artifacts/milestone-lock-report.md",
        help="create report path",
    )
    p_create.set_defaults(func=cmd_create)

    p_import = sub.add_parser(
        "import-archive", help="create lock from archive directory"
    )
    p_import.add_argument("--milestone-id", required=True, help="milestone id")
    p_import.add_argument("--archive-dir", help="archive path relative to repo root")
    p_import.add_argument(
        "--force", action="store_true", help="overwrite existing lock"
    )
    p_import.add_argument(
        "--allow-partial",
        action="store_true",
        help="allow creating lock when some configured keys are missing",
    )
    p_import.add_argument(
        "--set-active",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="set ACTIVE pointer after import (default: true)",
    )
    p_import.add_argument(
        "--report",
        default=".bmad/artifacts/milestone-lock-report.md",
        help="import report path",
    )
    p_import.set_defaults(func=cmd_import_archive)

    p_use = sub.add_parser("use", help="seed artifacts from lock")
    p_use.add_argument("--milestone-id", help="milestone id (default: ACTIVE pointer)")
    p_use.add_argument(
        "--force", action="store_true", help="overwrite existing artifacts"
    )
    p_use.add_argument(
        "--report",
        default=".bmad/artifacts/milestone-seed-report.md",
        help="seed report path",
    )
    p_use.set_defaults(func=cmd_use)

    p_verify = sub.add_parser("verify", help="verify artifacts match lock")
    p_verify.add_argument(
        "--milestone-id", help="milestone id (default: ACTIVE pointer)"
    )
    p_verify.add_argument(
        "--report",
        default=".bmad/artifacts/milestone-verify-report.md",
        help="verify report path",
    )
    p_verify.set_defaults(func=cmd_verify)

    p_set = sub.add_parser("set-active", help="set ACTIVE pointer")
    p_set.add_argument("--milestone-id", required=True, help="milestone id")
    p_set.set_defaults(func=cmd_set_active)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
