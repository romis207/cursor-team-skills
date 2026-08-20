#!/usr/bin/env python3
"""Bulk ETC change: prepare, submit, check, verify."""

from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import random
import shutil
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import requests

ETC_INPUT_ROOT = Path("/mobileye/DPT/Dev/etc_change_input")
ETC_OUTPUT_ROOT = Path("/mobileye/DPT/Dev/etc_change_output")
WORK_ROOT = Path.home() / "bulk_etc_change"
API_URL = "http://etc-change:5000/api/new_request"
REQUESTS_URL = "http://etc-change:5000/api/requests"
CSV_FIELDS = [
    "session_name",
    "sub_session",
    "view_name",
    "action",
    "file_name",
    "section",
    "field",
    "value",
]
DEFAULT_SUB_SESSION = "s001"
DEFAULT_VIEWS = [
    "p_Front-SV2",
    "p_Surround-SV2",
    "s_Front-1CAM-GM1",
    "s_Front-2CAM-GM1",
]
DEFAULT_FILE = "ext_calib.conf"
DEFAULT_ACTION = "replace_file"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk ETC change workflow")
    parser.add_argument(
        "--batch-name",
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Subdirectory under etc_change_input/<user>/",
    )
    parser.add_argument(
        "--requestor",
        default=os.environ.get("USER") or getpass.getuser(),
        help="ETC requestor username",
    )
    parser.add_argument(
        "--comment",
        default="Bulk ETC change",
        help="Comment for ETC requests",
    )
    parser.add_argument(
        "--sub-session",
        default=DEFAULT_SUB_SESSION,
        help="Default sub_session when not inferred",
    )
    parser.add_argument(
        "--views",
        default=",".join(DEFAULT_VIEWS),
        help="Comma-separated view names to update per session (GM default: all 4 views)",
    )
    parser.add_argument(
        "--view",
        help="Single view only (overrides --views)",
    )
    parser.add_argument(
        "--file-name",
        default=DEFAULT_FILE,
        help="ETC file to replace",
    )
    parser.add_argument(
        "--mapping-file",
        help="Optional session->sub_session/view mapping (gf_to_etc.list format)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Working directory (default: ~/bulk_etc_change/<batch-name>)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Copy files and build CSV")
    prepare.add_argument(
        "input",
        nargs="+",
        help="Source file paths, or a single .list/.txt file with one path per line",
    )

    submit = sub.add_parser("submit", help="Submit ETC requests from prepared CSV")
    submit.add_argument("--csv", type=Path, help="Prepared CSV path")

    check = sub.add_parser("check", help="Check request statuses")
    check.add_argument("--summary", type=Path, help="Submit summary JSON")

    verify = sub.add_parser("verify", help="Verify completed requests")
    verify.add_argument("--summary", type=Path, help="Submit summary JSON")

    coverage = sub.add_parser(
        "coverage",
        help="Report per-session AWS view coverage from a submit summary",
    )
    coverage.add_argument("--summary", type=Path, help="Submit summary JSON")

    run = sub.add_parser("run", help="prepare + submit")
    run.add_argument("input", nargs="+", help="Same as prepare input")
    run.add_argument("--dry-run", action="store_true", help="Prepare only, do not submit")

    return parser.parse_args()


def expand_inputs(raw_inputs: list[str]) -> list[str]:
    if len(raw_inputs) == 1 and Path(raw_inputs[0]).is_file():
        path = Path(raw_inputs[0])
        if path.suffix in {".list", ".txt", ".csv"}:
            lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
            return [line for line in lines if line and not line.startswith("#")]
    return raw_inputs


def infer_session_name(source_path: Path) -> str:
    parts = source_path.parts
    for part in reversed(parts):
        if part.endswith("_0000") or "_Sil" in part or part.count("_") >= 3:
            return part
    raise ValueError(f"Cannot infer session name from path: {source_path}")


def load_mapping(mapping_file: Path | None) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    if not mapping_file or not mapping_file.is_file():
        return mapping
    for line in mapping_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        left, right = line.split(maxsplit=1)
        session = left.split("/")[-3] if left.startswith("/") else left
        etc_root = right.rstrip("/")
        parts = etc_root.split("/")
        try:
            idx = parts.index(session)
            sub_session = parts[idx + 1]
            view_name = parts[idx + 2]
            mapping[session] = (sub_session, view_name)
        except (ValueError, IndexError):
            continue
    return mapping


def resolve_views(batch: argparse.Namespace) -> list[str]:
    if batch.view:
        return [batch.view]
    return [view.strip() for view in batch.views.split(",") if view.strip()]


def paths(batch: argparse.Namespace) -> dict[str, Path]:
    work_dir = batch.work_dir or (WORK_ROOT / batch.batch_name)
    requestor = batch.requestor
    input_root = ETC_INPUT_ROOT / requestor / batch.batch_name
    return {
        "work_dir": work_dir,
        "input_root": input_root,
        "lists_dir": input_root / "lists",
        "csv": work_dir / "bulk_etc_change.csv",
        "sessions": work_dir / "sessions.list",
        "summary": work_dir / "submit_summary.json",
        "log": work_dir / "run.log",
    }


def prepare(batch: argparse.Namespace) -> int:
    loc = paths(batch)
    loc["work_dir"].mkdir(parents=True, exist_ok=True)
    loc["input_root"].mkdir(parents=True, exist_ok=True)

    mapping = load_mapping(Path(batch.mapping_file) if batch.mapping_file else None)
    sources = [Path(p) for p in expand_inputs(batch.input)]
    views = resolve_views(batch)
    rows = []

    for src in sources:
        if not src.is_file():
            print(f"ERROR: missing source file: {src}", file=sys.stderr)
            return 1

        session_name = infer_session_name(src)
        mapped = mapping.get(session_name)
        sub_session = mapped[0] if mapped else batch.sub_session
        dst_dir = loc["input_root"] / session_name
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / batch.file_name
        shutil.copy2(src, dst)

        for view_name in views:
            rows.append(
                {
                    "session_name": session_name,
                    "sub_session": sub_session,
                    "view_name": view_name,
                    "action": DEFAULT_ACTION,
                    "file_name": batch.file_name,
                    "section": "",
                    "field": "",
                    "value": str(dst),
                }
            )

    with loc["csv"].open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    unique_sessions = sorted({row["session_name"] for row in rows})
    loc["sessions"].write_text("\n".join(unique_sessions) + "\n", encoding="utf-8")

    meta = {
        "batch_name": batch.batch_name,
        "requestor": batch.requestor,
        "comment": batch.comment,
        "csv": str(loc["csv"]),
        "input_root": str(loc["input_root"]),
        "session_count": len(unique_sessions),
        "view_count": len(views),
        "views": views,
        "csv_rows": len(rows),
    }
    (loc["work_dir"] / "prepare_meta.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )

    print(f"Prepared {len(unique_sessions)} sessions x {len(views)} views = {len(rows)} CSV rows")
    print(f"Views: {', '.join(views)}")
    print(f"CSV: {loc['csv']}")
    print(f"Input files: {loc['input_root']}")
    return 0


def session_path(session_name: str, sub_session: str, view_name: str) -> str:
    if sub_session and view_name:
        return f"{session_name}/{sub_session}/{view_name}"
    return session_name


def build_change_item(row: dict[str, str]) -> dict:
    action = row["action"]
    item = {"action": action, "file": row["file_name"], "exceptions": []}
    if action in {"replace_file", "add_file"}:
        item["path"] = row["value"]
    elif action in {"replace_field", "add_field"}:
        item.update({"section": row["section"], "field": row["field"], "value": row["value"]})
    elif action == "remove_field":
        item.update({"section": row["section"], "field": row["field"]})
    elif action == "remove_section":
        item["section"] = row["section"]
    return item


def submit(batch: argparse.Namespace) -> int:
    loc = paths(batch)
    csv_path = getattr(batch, "csv", None) or loc["csv"]
    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 1

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        rows = list(csv.DictReader(csv_file))

    loc["lists_dir"].mkdir(parents=True, exist_ok=True)
    group_id = f"{batch.requestor}_{datetime.now().strftime('%Y-%m-%d')}_{uuid.uuid4().hex[:6]}"
    grouped: dict[tuple, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            row["action"],
            row["file_name"],
            row["section"],
            row["field"],
            row["value"],
        )
        grouped[key].append(row)

    summary = {
        "group_id": group_id,
        "requestor": batch.requestor,
        "comment": batch.comment,
        "csv_path": str(csv_path),
        "requests": [],
    }

    for index, (change_key, group_rows) in enumerate(grouped.items(), start=1):
        sessions = [
            session_path(r["session_name"], r["sub_session"], r["view_name"])
            for r in group_rows
        ]
        list_path = loc["lists_dir"] / f"{group_id}_{index}.list"
        list_path.write_text("\n".join(sessions) + "\n", encoding="utf-8")

        payload = {
            "changeType": "ETC",
            "fileType": "path",
            "value": str(list_path),
            "username": batch.requestor,
            "changes": [build_change_item(group_rows[0])],
            "comment": batch.comment,
            "status": "APPROVED",
            "group_id": group_id,
            "send_mail": False,
            "jira_required": True,
        }

        response = requests.post(API_URL, json=payload, verify=False, timeout=120)
        try:
            body = response.json()
        except Exception:
            body = {"success": False, "message": response.text}

        request_info = {
            "index": index,
            "sessions": sessions,
            "list_path": str(list_path),
            "http_status": response.status_code,
            "success": body.get("success", False),
            "request_id": body.get("id") or body.get("request_id"),
            "message": body.get("message", ""),
            "jira": body.get("jira") or body.get("jiraUrl"),
        }
        summary["requests"].append(request_info)

        status = "OK" if request_info["success"] else "FAIL"
        print(
            f"[{status}] {index}/{len(grouped)} "
            f"id={request_info['request_id']} views={len(sessions)}"
        )
        if not request_info["success"]:
            print(f"  message: {request_info['message']}")

    summary["total_requests"] = len(summary["requests"])
    summary["succeeded"] = sum(1 for req in summary["requests"] if req["success"])
    summary["failed"] = summary["total_requests"] - summary["succeeded"]
    loc["summary"].write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\ngroup_id: {group_id}")
    print(f"summary: {loc['summary']}")
    print(f"opened {summary['succeeded']}/{summary['total_requests']} requests")
    return 0 if summary["failed"] == 0 else 1


def check(batch: argparse.Namespace) -> int:
    loc = paths(batch)
    summary_path = getattr(batch, "summary", None) or loc["summary"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    group_id = summary["group_id"]
    request_ids = [req["request_id"] for req in summary["requests"] if req.get("request_id")]

    print(f"group_id: {group_id}")
    print(
        f"submitted: {summary.get('succeeded', len(request_ids))}/"
        f"{summary.get('total_requests', len(request_ids))}"
    )
    if request_ids:
        print(f"request_ids: {request_ids[0]} .. {request_ids[-1]}")

    response = requests.get(REQUESTS_URL, params={"group_id": group_id}, verify=False, timeout=60)
    items = response.json().get("data") or []
    if isinstance(items, dict):
        items = list(items.values())
    if not items:
        print("No API results yet.")
        return 0

    statuses = Counter(item.get("request_status") or item.get("status", "unknown") for item in items)
    print("\nAPI statuses:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")

    errors = [item for item in items if (item.get("request_status") or item.get("status")) == "ERROR"]
    if errors:
        print("\nErrors:")
        for item in errors[:10]:
            print(
                f"  {item.get('request_id')}: "
                f"{item.get('error_message') or item.get('message', '')}"
            )
        return 1
    return 0


def aws_views_by_session(group_id: str) -> dict[str, set[str]]:
    response = requests.get(REQUESTS_URL, params={"group_id": group_id}, verify=False, timeout=120)
    items = response.json().get("data") or []
    coverage: dict[str, set[str]] = {}
    for req in items:
        if req.get("request_status") != "SUCCESS":
            continue
        for item in req.get("request_items") or []:
            if item.get("location") != "aws" or item.get("status") != "SUCCESS":
                continue
            session = item.get("session_name")
            view = item.get("view_name")
            if session and view:
                coverage.setdefault(session, set()).add(view)
    return coverage


def coverage_report(batch: argparse.Namespace) -> int:
    loc = paths(batch)
    summary_path = getattr(batch, "summary", None) or loc["summary"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    group_id = summary["group_id"]
    expected_views = set(resolve_views(batch))

    sessions = sorted(
        {
            session.split("/")[0]
            for req in summary.get("requests", [])
            for session in req.get("sessions", [])
        }
    )
    if not sessions:
        sessions_path = loc["sessions"]
        if sessions_path.is_file():
            sessions = [
                line.strip()
                for line in sessions_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    actual = aws_views_by_session(group_id)
    complete = []
    partial = []
    for session in sessions:
        have = actual.get(session, set())
        missing = sorted(expected_views - have)
        if not missing:
            complete.append(session)
        else:
            partial.append((session, sorted(have), missing))

    print(f"group_id: {group_id}")
    print(f"expected views: {sorted(expected_views)}")
    print(f"complete sessions: {len(complete)}/{len(sessions)}")
    if partial:
        print("\nPartial sessions:")
        for session, have, missing in partial:
            print(f"  {session}")
            print(f"    have: {have}")
            print(f"    missing: {missing}")
            output_dir = ETC_OUTPUT_ROOT / _request_id_for_session(summary, session)
            missing_file = output_dir / "no_clips_or_sessions"
            if missing_file.is_file():
                print("    note: no_clips_or_sessions (views not registered in cloud)")
    return 0 if not partial else 1


def _request_id_for_session(summary: dict, session_name: str) -> str:
    for req in summary.get("requests", []):
        for entry in req.get("sessions", []):
            if entry.startswith(session_name + "/"):
                return req.get("request_id", "")
    return ""


def verify(batch: argparse.Namespace) -> int:
    loc = paths(batch)
    summary_path = getattr(batch, "summary", None) or loc["summary"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    group_id = summary["group_id"]

    response = requests.get(REQUESTS_URL, params={"group_id": group_id}, verify=False, timeout=60)
    items = response.json().get("data") or []

    req_status = Counter(item.get("request_status") for item in items)
    item_status = Counter()
    for req in items:
        for it in req.get("request_items") or []:
            item_status[it.get("status")] += 1

    print(f"group_id: {group_id}")
    print(f"request_status: {dict(req_status)}")
    print(f"item_status: {dict(item_status)}")

    sample_ids = [req["request_id"] for req in summary["requests"][:5]]
    reports_ok = 0
    for rid in sample_ids:
        report = ETC_OUTPUT_ROOT / rid / "final_report.csv"
        if report.is_file() and "SUCCESS" in report.read_text(encoding="utf-8", errors="replace"):
            reports_ok += 1

    print(f"sample final_report SUCCESS: {reports_ok}/{len(sample_ids)}")

    if req_status.get("SUCCESS", 0) == len(items) and not item_status.get("ERROR"):
        print("VERIFY: PASS")
        return 0

    print("VERIFY: INCOMPLETE OR FAILED")
    return 1


def main() -> int:
    batch = parse_args()
    if batch.command == "prepare":
        return prepare(batch)
    if batch.command == "submit":
        return submit(batch)
    if batch.command == "check":
        return check(batch)
    if batch.command == "verify":
        return verify(batch)
    if batch.command == "coverage":
        return coverage_report(batch)
    if batch.command == "run":
        code = prepare(batch)
        if code != 0 or batch.dry_run:
            return code
        return submit(batch)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
