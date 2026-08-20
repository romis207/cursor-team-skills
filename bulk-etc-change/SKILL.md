---
name: bulk-etc-change
description: >-
  Runs bulk ETC file replacement for a list of sessions via the etc-change API.
  Copies source files to etc_change_input, builds CSV for all session views,
  opens Jira-tracked ETC requests, and verifies cloud coverage. Use when the
  user gives session names or paths to new ETC files (e.g. ext_calib.conf) and
  asks for bulk ETC change, ETC update, replace_file, or gm_calibration_request.
---

# Bulk ETC Change

Confluence: [Bulk ETC-Change process](https://confluence.mobileye.com/spaces/DI/pages/93116723/Bulk+ETC-Change+process)

**Do not use** `/mobileye/DPT/Dev/etc_change_prod/.../etc_change_bulk.py` — outdated (`fileType: list` vs current API `path`).

## Goal

User provides sessions + new ETC files → agent updates **all required views per session** → submits ETC-change requests → monitors and verifies cloud coverage.

## GM Sil2 default views (ext_calib.conf)

**Always update all 4 views per session** unless the user specifies otherwise:

| view_name | sub_session |
|-----------|-------------|
| `p_Front-SV2` | `s001` |
| `p_Surround-SV2` | `s001` |
| `s_Front-1CAM-GM1` | `s001` |
| `s_Front-2CAM-GM1` | `s001` |

Same `ext_calib.conf` file is applied to every view in the session.

Submit groups by session: **1 ETC request per session** containing all views (typically 4).

## Master checklist

```
Task Progress:
- [ ] 1. Parse user input (session list or source file paths)
- [ ] 2. prepare — copy files + build CSV (sessions × views)
- [ ] 3. Show user summary; get approval before submit
- [ ] 4. submit — open ETC requests (Jira)
- [ ] 5. check — poll until all SUCCESS
- [ ] 6. coverage — verify all views per session in cloud
- [ ] 7. verify — final_report + API item statuses
```

---

## Step 1 — Prepare

```bash
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <short_label> \
  --requestor <USER> \
  --comment "GM calibration - replace ext_calib.conf on all views" \
  prepare /path/to/sources.list
```

Default `--views` is all 4 GM views. Override only if user asks:

```bash
# single view only
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <label> --view p_Front-SV2 prepare sources.list

# custom view set
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <label> \
  --views p_Surround-SV2,s_Front-1CAM-GM1,s_Front-2CAM-GM1 \
  prepare sources.list
```

Input: full paths like `/path/to/run_etc/<SESSION>/etc/ext_calib.conf`, or a `.list` file.

Outputs under `~/bulk_etc_change/<batch-name>/`:
- `bulk_etc_change.csv` — `sessions × views` rows
- `sessions.list` — unique session names
- `prepare_meta.json`

Copied files:
`/mobileye/DPT/Dev/etc_change_input/<USER>/<batch-name>/<SESSION>/ext_calib.conf`

**Critical:** session list files for submit must be under `/mobileye/DPT/Dev/etc_change_input/` — never `/homes/`.

---

## Step 2 — Submit (requires user approval)

```bash
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <short_label> \
  --comment "<reason>" \
  submit
```

Or prepare + submit:

```bash
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <short_label> \
  --comment "<reason>" \
  run /path/to/sources.list
```

Save `group_id` and `submit_summary.json`.

---

## Step 3 — Monitor

```bash
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <short_label> \
  check
```

Poll until all requests are `SUCCESS`.

---

## Step 4 — Verify cloud coverage (all views)

```bash
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <short_label> \
  coverage
```

Reports per-session which views reached `aws/SUCCESS`. Flags sessions where views are missing in cloud (`no_clips_or_sessions`).

Optional manual check with `cloud-local-mount`:

```bash
cloud-local-mount --clip <SESSION>_s001_p_Surround-SV2_s60_0001 --shell --timeout 30
diff \
  /tmp/$(whoami)/mounted_clips/<SESSION>/s001/p_Surround-SV2/s60/<CLIP>/etc/ext_calib.conf \
  /mobileye/DPT/Dev/etc_change_input/<USER>/<batch>/<SESSION>/ext_calib.conf
```

---

## Step 5 — Verify request status

```bash
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py \
  --batch-name <short_label> \
  verify
```

---

## Report to user

```markdown
## Bulk ETC Change — <batch-name>

- Sessions: N
- Views per session: 4 (p_Front-SV2, p_Surround-SV2, s_Front-1CAM-GM1, s_Front-2CAM-GM1)
- group_id: `<group_id>`
- Tickets: DPT-XXXXX .. DPT-YYYYY
- Cloud coverage: X/N sessions with all views

### Verify
python3 ~/.cursor/skills/bulk-etc-change/scripts/bulk_etc_change.py --batch-name <batch-name> coverage
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Only `p_Front-SV2` updated | Re-run with default `--views` (all 4) |
| `no lists found` + `no_clips_or_sessions` | Views not registered in cloud — cannot ETC-update; escalate to data team |
| `file does not exist` for `.list` under `/homes/` | Lists must be under `etc_change_input` (script handles this) |
| `fileType` validation error | Use this skill's script, not old `etc_change_bulk.py` |
| Session partial (e.g. 1/4 views) | Check `coverage`; missing views likely absent from cloud catalog |
| >5000 CSV rows | Split into multiple batches (API limit) |

See [reference.md](reference.md) for CSV format, API details, and cloud verification.
