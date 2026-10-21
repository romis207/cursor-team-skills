#!/usr/bin/env python3
"""Resolve cloud-mest configuration for a clip name."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CACHE_FILE = SKILL_DIR / "versions_cache.json"
YARONRI_UTILS = "/homes/yaronri/scripts/shell"


def load_cache() -> dict:
    with open(CACHE_FILE, encoding="utf-8") as f:
        return json.load(f)


def query_brain_type(clip_name: str) -> str:
    sys.path.append(YARONRI_UTILS)
    import utils  # type: ignore

    clips_info = utils.load_clips_info([clip_name], requested_fields=["continuousSession"])
    if not clips_info:
        raise RuntimeError(f"DE returned no info for clip: {clip_name}")
    brain = clips_info[0].continuous_session.brain_type
    if not brain:
        raise RuntimeError(f"No brain_type on clip: {clip_name}")
    return brain


def pick_profile(cache: dict, brain: str, profile_override: str | None) -> tuple[str, dict]:
    profiles = cache["profiles"]
    if profile_override:
        if profile_override not in profiles:
            raise RuntimeError(
                f"Unknown profile '{profile_override}'. Available: {', '.join(sorted(profiles))}"
            )
        return profile_override, profiles[profile_override]

    mapped = cache.get("brain_to_profile", {}).get(brain)
    if mapped and mapped in profiles:
        return mapped, profiles[mapped]

    for name, profile in profiles.items():
        if brain in profile.get("brains", []):
            return name, profile

    raise RuntimeError(
        f"No profile for brain '{brain}'. Set --profile or update {CACHE_FILE}"
    )


def build_paths(cache: dict, profile: dict, brain: str) -> dict:
    tmpl = cache["path_template"]
    root = profile.get("root") or tmpl["bundle_root"].format(
        bundle_version=profile["bundle_version"],
        cf_notation=profile["cf_notation"],
        eyeq=profile["eyeq"],
        build_mode=profile["build_mode"],
    )
    mest = os.path.join(root, tmpl["mest_suffix"].format(cvapp=profile["cvapp"]))
    lib = os.path.join(root, tmpl["lib_suffix"].format(brain=brain))
    brainlibs = os.path.join(root, tmpl["brainlibs_dir"])
    return {"mest": mest, "lib": lib, "brainlibs": brainlibs, "root": root}


def validate_paths(paths: dict) -> list[str]:
    missing = []
    for key in ("mest", "lib", "brainlibs"):
        if not os.path.exists(paths[key]):
            missing.append(f"{key}: {paths[key]}")
    return missing


def write_cliplist(clip_name: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cliplist = out_dir / f"{clip_name}.list"
    cliplist.write_text(clip_name + "\n", encoding="utf-8")
    return cliplist


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve cloud-mest config for a clip")
    parser.add_argument("clip_name", help="Clip name")
    parser.add_argument("--profile", help="Force versions_cache profile id")
    parser.add_argument("--run-name", help="cloud-mest -n value (default: clip short name)")
    parser.add_argument(
        "--output-dir",
        help="cloud-mest -o directory (default: /mobileye/Calibration/AdasAlgoExecution/<user>/mest_<clip>)",
    )
    parser.add_argument("--work-dir", help="Directory for cliplist + metadata")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved config only")
    parser.add_argument("--json", action="store_true", help="Print JSON config")
    args = parser.parse_args()

    clip_name = args.clip_name.strip()
    cache = load_cache()
    brain = query_brain_type(clip_name)
    profile_name, profile = pick_profile(cache, brain, args.profile)
    paths = build_paths(cache, profile, brain)
    missing = validate_paths(paths)
    if missing:
        print("ERROR: MEST paths not found:", file=sys.stderr)
        for line in missing:
            print(f"  - {line}", file=sys.stderr)
        print(
            f"Update {CACHE_FILE} from Confluence page {cache.get('source_page_id')}",
            file=sys.stderr,
        )
        return 2

    user = os.environ.get("USER", "romis")
    run_name = args.run_name or clip_name.split("_s00")[0].replace("/", "_")[:40]
    output_dir = args.output_dir or f"/mobileye/Calibration/AdasAlgoExecution/{user}/mest_{clip_name}"
    work_dir = Path(args.work_dir or f"/tmp/cloud_mest_clip_{user}_{clip_name}")

    cliplist = write_cliplist(clip_name, work_dir)
    mest_params = cache.get("default_mest_params", "")
    cloud_flags = cache.get("default_cloud_flags", [])

    cmd = [
        "cloud-mest",
        "-m", paths["mest"],
        paths["lib"],
        paths["brainlibs"],
        "-p", f" {mest_params} ",
        *cloud_flags,
        "-o", output_dir,
        "-n", run_name,
        "-c", str(cliplist),
    ]

    result = {
        "clip_name": clip_name,
        "brain_type": brain,
        "profile": profile_name,
        "profile_label": profile.get("label"),
        "bundle_version": profile["bundle_version"],
        "cf_notation": profile["cf_notation"],
        "paths": paths,
        "cliplist": str(cliplist),
        "output_dir": output_dir,
        "run_name": run_name,
        "mest_params": mest_params,
        "cloud_flags": cloud_flags,
        "command": cmd,
    }

    if args.json or args.dry_run:
        print(json.dumps(result, indent=2))
        return 0

    meta = work_dir / "resolved_config.json"
    meta.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("\nSubmitting cloud-mest...\n")
    os.execvp(cmd[0], cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
