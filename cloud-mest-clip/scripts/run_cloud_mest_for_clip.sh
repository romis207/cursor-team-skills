#!/usr/bin/env bash
# Run cloud-mest for a single clip using versions_cache.json + DE brain lookup.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-/homes/yaronri/.conda/envs/p310/bin/python3}"

CLIP=""
PROFILE=""
OUTPUT_DIR=""
RUN_NAME=""
DRY_RUN=0
JSON_ONLY=0
POLL=0

usage() {
  cat <<'EOF'
Usage:
  run_cloud_mest_for_clip.sh <clip_name> [options]

Options:
  --profile NAME     Force versions_cache profile (e.g. pc1_mono8l, sp4_mono8l)
  --output-dir DIR   cloud-mest output directory
  --run-name NAME    cloud-mest -n value
  --dry-run          Resolve config only, do not submit
  --json             Print resolved JSON only
  --poll             After submit, poll until completion (reads run_id.txt)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --run-name) RUN_NAME="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --json) JSON_ONLY=1; shift ;;
    --poll) POLL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    *)
      if [[ -z "$CLIP" ]]; then
        CLIP="$1"
      else
        echo "Unexpected argument: $1" >&2
        usage
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$CLIP" ]]; then
  usage
  exit 1
fi

args=("$SCRIPT_DIR/resolve_and_run_cloud_mest.py" "$CLIP")
[[ -n "$PROFILE" ]] && args+=(--profile "$PROFILE")
[[ -n "$OUTPUT_DIR" ]] && args+=(--output-dir "$OUTPUT_DIR")
[[ -n "$RUN_NAME" ]] && args+=(--run-name "$RUN_NAME")
[[ "$DRY_RUN" -eq 1 ]] && args+=(--dry-run)
[[ "$JSON_ONLY" -eq 1 ]] && args+=(--json)

if [[ "$DRY_RUN" -eq 1 || "$JSON_ONLY" -eq 1 ]]; then
  exec "$PYTHON" "${args[@]}"
fi

"$PYTHON" "${args[@]}"

if [[ "$POLL" -eq 1 ]]; then
  OUT="${OUTPUT_DIR:-/mobileye/Calibration/AdasAlgoExecution/${USER}/mest_${CLIP}}"
  RUN_ID_FILE="$OUT/runlog/run_id.txt"
  if [[ -f "$RUN_ID_FILE" ]]; then
    RUN_ID="$(cat "$RUN_ID_FILE")"
    echo "Polling run: $RUN_ID"
    cloud-poll -r "$RUN_ID" -L di@us-east-1 -s -v || true
  else
    echo "WARNING: run_id not found at $RUN_ID_FILE" >&2
  fi
fi
