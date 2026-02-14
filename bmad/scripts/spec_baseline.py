#!/usr/bin/env python3
"""Sync long-lived spec baseline for BMAD workflows.

Commands:
  status   - show baseline config and file presence
  seed     - copy baseline specs into artifacts workspace (for new runs)
  snapshot - copy frozen specs from artifacts workspace into baseline (before archive)
  import-archive - bootstrap baseline from an existing archive directory
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

DEFAULT_BASELINE_KEYS = ["prd", "scope", "adr", "impact", "ui_ux_spec", "api_design"]


def load_workflow(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    if not isinstance(workflow, dict):
        raise ValueError(f"invalid workflow YAML: {path}")
    return workflow


def resolve_config(
    workflow: Dict[str, Any], repo_root: Path
) -> Tuple[Path, Path, Dict[str, str], List[str]]:
    artifacts_dir = workflow.get("artifacts_dir", ".bmad/artifacts")
    artifacts_map = workflow.get("artifacts", {})
    baseline = workflow.get("baseline", {})

    if not isinstance(artifacts_map, dict):
        raise ValueError("workflow.artifacts must be a mapping")
    if not isinstance(baseline, dict):
        raise ValueError("workflow.baseline must be a mapping")

    baseline_dir = baseline.get("dir", ".bmad/baseline/spec")
    keys = baseline.get("keys")
    if keys is None:
        keys = DEFAULT_BASELINE_KEYS
    elif not isinstance(keys, list):
        keys = DEFAULT_BASELINE_KEYS

    return (
        repo_root / artifacts_dir,
        repo_root / baseline_dir,
        artifacts_map,
        [str(k) for k in keys],
    )


def write_report(path: Path, title: str, rows: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat()
    body = [f"# {title}", "", f"- Timestamp: {now}", ""] + rows + [""]
    path.write_text("\n".join(body), encoding="utf-8")


def find_latest_archive_dir(repo_root: Path) -> Path | None:
    archive_root = repo_root / ".bmad/archive"
    if not archive_root.exists():
        return None
    candidates = [p for p in archive_root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    workflow = load_workflow(repo_root / args.workflow)
    artifacts_dir, baseline_dir, artifacts_map, keys = resolve_config(
        workflow, repo_root
    )

    print(f"workflow: {args.workflow}")
    print(f"artifacts_dir: {artifacts_dir}")
    print(f"baseline_dir: {baseline_dir}")
    print(f"keys: {', '.join(keys)}")
    print("")

    missing = 0
    for key in keys:
        filename = artifacts_map.get(key)
        if not filename:
            print(f"[MISSING MAP] {key} -> <not mapped in workflow.artifacts>")
            missing += 1
            continue
        baseline_file = baseline_dir / filename
        status = (
            "OK"
            if baseline_file.exists() and baseline_file.stat().st_size > 0
            else "MISSING"
        )
        print(f"[{status}] {key} -> {baseline_file}")
        if status == "MISSING":
            missing += 1

    return 1 if missing and args.strict else 0


def cmd_seed(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    workflow = load_workflow(repo_root / args.workflow)
    artifacts_dir, baseline_dir, artifacts_map, keys = resolve_config(
        workflow, repo_root
    )
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    copied: List[str] = []
    skipped: List[str] = []
    missing_source: List[str] = []
    missing_map: List[str] = []

    for key in keys:
        filename = artifacts_map.get(key)
        if not filename:
            missing_map.append(key)
            continue
        src = baseline_dir / filename
        dst = artifacts_dir / filename
        if not src.exists() or src.stat().st_size == 0:
            missing_source.append(f"{key}:{src}")
            continue
        if dst.exists() and not args.force:
            skipped.append(str(dst))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst))

    report_rows = [
        "## Summary",
        f"- Copied: {len(copied)}",
        f"- Skipped (already exists): {len(skipped)}",
        f"- Missing baseline source: {len(missing_source)}",
        f"- Missing workflow mapping: {len(missing_map)}",
        "",
        "## Copied",
    ] + [f"- {p}" for p in copied]

    report_rows += ["", "## Skipped"] + [f"- {p}" for p in skipped]
    report_rows += ["", "## Missing Baseline Source"] + [
        f"- {p}" for p in missing_source
    ]
    report_rows += ["", "## Missing Mapping"] + [f"- {k}" for k in missing_map]

    report_path = repo_root / args.report
    write_report(report_path, "Baseline Seed Report", report_rows)

    print(
        f"copied={len(copied)} skipped={len(skipped)} missing_source={len(missing_source)} missing_map={len(missing_map)}"
    )
    print(f"report={report_path}")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    workflow = load_workflow(repo_root / args.workflow)
    artifacts_dir, baseline_dir, artifacts_map, keys = resolve_config(
        workflow, repo_root
    )
    baseline_dir.mkdir(parents=True, exist_ok=True)

    copied: List[str] = []
    missing_source: List[str] = []
    missing_map: List[str] = []

    for key in keys:
        filename = artifacts_map.get(key)
        if not filename:
            missing_map.append(key)
            continue
        src = artifacts_dir / filename
        dst = baseline_dir / filename
        if not src.exists() or src.stat().st_size == 0:
            missing_source.append(f"{key}:{src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst))

    report_rows = [
        "## Summary",
        f"- Snapshot Written: {len(copied)}",
        f"- Missing artifact source: {len(missing_source)}",
        f"- Missing workflow mapping: {len(missing_map)}",
        "",
        "## Snapshot Files",
    ] + [f"- {p}" for p in copied]

    report_rows += ["", "## Missing Artifact Source"] + [
        f"- {p}" for p in missing_source
    ]
    report_rows += ["", "## Missing Mapping"] + [f"- {k}" for k in missing_map]

    report_path = repo_root / args.report
    write_report(report_path, "Baseline Snapshot Report", report_rows)

    print(
        f"snapshot={len(copied)} missing_source={len(missing_source)} missing_map={len(missing_map)}"
    )
    print(f"report={report_path}")
    return 0


def cmd_import_archive(args: argparse.Namespace) -> int:
    repo_root = Path.cwd()
    workflow = load_workflow(repo_root / args.workflow)
    _, baseline_dir, artifacts_map, keys = resolve_config(workflow, repo_root)
    baseline_dir.mkdir(parents=True, exist_ok=True)

    if args.archive_dir:
        archive_dir = repo_root / args.archive_dir
    else:
        latest = find_latest_archive_dir(repo_root)
        if latest is None:
            print("no archive directory found under .bmad/archive/")
            return 1
        archive_dir = latest

    if not archive_dir.exists() or not archive_dir.is_dir():
        print(f"archive dir not found: {archive_dir}")
        return 1

    copied: List[str] = []
    missing_source: List[str] = []
    missing_map: List[str] = []

    for key in keys:
        filename = artifacts_map.get(key)
        if not filename:
            missing_map.append(key)
            continue
        src = archive_dir / filename
        dst = baseline_dir / filename
        if not src.exists() or src.stat().st_size == 0:
            missing_source.append(f"{key}:{src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst))

    report_rows = [
        "## Summary",
        f"- Archive Source: {archive_dir}",
        f"- Imported: {len(copied)}",
        f"- Missing in archive: {len(missing_source)}",
        f"- Missing workflow mapping: {len(missing_map)}",
        "",
        "## Imported Files",
    ] + [f"- {p}" for p in copied]

    report_rows += ["", "## Missing In Archive"] + [f"- {p}" for p in missing_source]
    report_rows += ["", "## Missing Mapping"] + [f"- {k}" for k in missing_map]

    report_path = repo_root / args.report
    write_report(report_path, "Baseline Import Report", report_rows)

    print(
        f"archive={archive_dir} imported={len(copied)} missing_source={len(missing_source)} missing_map={len(missing_map)}"
    )
    print(f"report={report_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage BMAD long-lived baseline specs.")
    p.add_argument(
        "--workflow", default=".bmad/workflows/workflow.yml", help="workflow YAML path"
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="show baseline status")
    p_status.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any baseline file is missing",
    )
    p_status.set_defaults(func=cmd_status)

    p_seed = sub.add_parser("seed", help="copy baseline files into artifacts")
    p_seed.add_argument(
        "--force", action="store_true", help="overwrite existing artifacts files"
    )
    p_seed.add_argument(
        "--report",
        default=".bmad/artifacts/baseline-seed-report.md",
        help="seed report path",
    )
    p_seed.set_defaults(func=cmd_seed)

    p_snapshot = sub.add_parser(
        "snapshot", help="copy frozen specs from artifacts into baseline"
    )
    p_snapshot.add_argument(
        "--report",
        default=".bmad/artifacts/baseline-spec-snapshot-report.md",
        help="snapshot report path",
    )
    p_snapshot.set_defaults(func=cmd_snapshot)

    p_import = sub.add_parser(
        "import-archive", help="bootstrap baseline files from an archive directory"
    )
    p_import.add_argument(
        "--archive-dir",
        help="archive directory path (relative to repo root). Defaults to latest .bmad/archive/*",
    )
    p_import.add_argument(
        "--report",
        default=".bmad/artifacts/baseline-import-report.md",
        help="import report path",
    )
    p_import.set_defaults(func=cmd_import_archive)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
