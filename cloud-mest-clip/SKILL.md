---
name: cloud-mest-clip
description: Runs cloud-mest for a clip name by resolving brain type from DE and MEST bundle paths from the FPAAEB Latest versions and cmls Confluence table. Use when the user gives a clip name and asks to run cloud-mest, MEST on a clip, or generate itrk for MEDebugger.
---

# Cloud-MEST for Clip

Source of truth: [Latest versions and cmls](https://confluence.mobileye.com/spaces/FPAAEB/pages/259580052/Latest+versions+and+cmls) (page `259580052`, space `FPAAEB`).

Local cache: [versions_cache.json](versions_cache.json)

## Goal

User provides **clip name** → agent resolves brain + MEST binaries → submits **cloud-mest** → optionally converts to PEXT for MEDebugger.

## Master checklist

```
Task Progress:
- [ ] 1. Resolve clip brain type (DE)
- [ ] 2. Map brain → version profile (Confluence table / cache)
- [ ] 3. Validate MEST paths exist
- [ ] 4. Submit cloud-mest
- [ ] 5. (Optional) Poll until done + verify itrk
- [ ] 6. (Optional) Convert itrk → pext for MEDebugger
```

---

## Step 1 — Resolve and run (preferred)

Dry-run first (show resolved command, do not submit):

```bash
bash ~/.cursor/skills/cloud-mest-clip/scripts/run_cloud_mest_for_clip.sh \
  <CLIP_NAME> --dry-run
```

Submit cloud-mest:

```bash
bash ~/.cursor/skills/cloud-mest-clip/scripts/run_cloud_mest_for_clip.sh \
  <CLIP_NAME> --poll
```

Force a specific version profile from cache:

```bash
bash ~/.cursor/skills/cloud-mest-clip/scripts/run_cloud_mest_for_clip.sh \
  <CLIP_NAME> --profile sp4_mono8l --poll
```

---

## Step 2 — What the script does

1. Queries **DE** for `continuousSession.brain_type`
2. Picks profile from `versions_cache.json` (`brain_to_profile` mapping)
3. Builds paths:
   - `.../CV_GV.s6`
   - `.../lib<Brain>.so`
   - `.../brainLibs/`
4. Creates single-clip `.list` file
5. Runs `cloud-mest` with default params from cache

Default output dir:

```
/mobileye/Calibration/AdasAlgoExecution/<user>/mest_<CLIP_NAME>
```

---

## Step 3 — Refresh versions from Confluence

When user asks to update versions or FPAAEB table changed:

1. Fetch page `259580052` via Confluence MCP (`confluence_get_page`)
2. Update `versions_cache.json` profiles (`bundle_version`, `cf_notation`, `brains`)
3. Re-run with `--dry-run` and verify paths exist

If Confluence is blocked, ask user to paste the relevant table row or grant FPAAEB access.

Helper:

```bash
python3 ~/.cursor/skills/cloud-mest-clip/scripts/sync_versions_from_confluence.py
```

---

## Step 4 — After MEST completes

Verify itrk:

```bash
bash ~/.cursor/skills/clip-sanity-check/scripts/verify_mest_output.sh \
  /mobileye/Calibration/AdasAlgoExecution/<user>/mest_<CLIP_NAME>
```

Poll job manually:

```bash
cloud-poll -r <RUN_ID> -L di@us-east-1 -s -v
```

Run ID file: `<output_dir>/runlog/run_id.txt`

---

## Step 5 — Optional: MEDebugger path

Chain to itrk→pext skill:

```bash
bash ~/.cursor/skills/itrk-to-pext/scripts/itrk_to_pext.sh \
  --mest-dir /mobileye/Calibration/AdasAlgoExecution/<user>/mest_<CLIP_NAME> \
  --out-dir /mobileye/Calibration/AdasAlgoExecution/<user>/pext_<CLIP_NAME>
```

Open MED source: the pext output directory.

---

## Agent workflow

When user says: "תריץ cloud-mest על קליפ X":

1. Run `--dry-run` for clip `X`
2. Show resolved brain, profile, output dir, and full command
3. If paths missing → refresh `versions_cache.json` from Confluence or ask user which profile to use
4. Run without `--dry-run` (add `--poll` if user wants to wait)
5. On success → offer itrk→pext conversion

---

## Report format

```
CLOUD-MEST: PASS | FAIL

Clip:    <name>
Brain:   <brain_type>
Profile: <profile_id> (<label>)
Output:  <output_dir>
Run ID:  <from runlog/run_id.txt or pending>

Next:    itrk verify / itrk-to-pext / MEDebugger
```

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| `No profile for brain` | Add mapping in `versions_cache.json` or pass `--profile` |
| MEST paths not found | Update `bundle_version` / `cf_notation` from Confluence table |
| DE token missing | Set `DE_TOKEN` from [DE Search portal](https://di-portal.mobileye.com/de-search/) |
| Job fails in cloud | `cloud-jobs -r <RUN_ID> -L di@us-east-1` |
| DynamoDB warning on submit | Usually non-blocking; job may still run |

See [reference.md](reference.md) for command template and cache schema.
