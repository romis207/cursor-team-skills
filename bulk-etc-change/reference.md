# Bulk ETC Change — Reference

## GM Sil2 views (default)

For `ext_calib.conf` replacement on GM Sil2 sessions, apply the **same file** to all views:

```
p_Front-SV2
p_Surround-SV2
s_Front-1CAM-GM1
s_Front-2CAM-GM1
```

All use `sub_session = s001`.

## CSV format (multi-view)

One row per session × view. Same `value` path for all views in a session:

```csv
session_name,sub_session,view_name,action,file_name,section,field,value
GM1_Sil2_260618_144120_0000,s001,p_Front-SV2,replace_file,ext_calib.conf,,,/mobileye/DPT/Dev/etc_change_input/romis/batch/GM1_Sil2_260618_144120_0000/ext_calib.conf
GM1_Sil2_260618_144120_0000,s001,p_Surround-SV2,replace_file,ext_calib.conf,,,/mobileye/DPT/Dev/etc_change_input/romis/batch/GM1_Sil2_260618_144120_0000/ext_calib.conf
GM1_Sil2_260618_144120_0000,s001,s_Front-1CAM-GM1,replace_file,ext_calib.conf,,,/mobileye/DPT/Dev/etc_change_input/romis/batch/GM1_Sil2_260618_144120_0000/ext_calib.conf
GM1_Sil2_260618_144120_0000,s001,s_Front-2CAM-GM1,replace_file,ext_calib.conf,,,/mobileye/DPT/Dev/etc_change_input/romis/batch/GM1_Sil2_260618_144120_0000/ext_calib.conf
```

Submit groups rows with identical `value` into **one request per session** (list contains all views).

For `replace_file`:
- `section` and `field` must be empty
- `value` = full path under `/mobileye/DPT/Dev/etc_change_input/`

## API payload (current)

```json
{
  "changeType": "ETC",
  "fileType": "path",
  "value": "/mobileye/DPT/Dev/etc_change_input/<user>/<batch>/lists/<group_id>_1.list",
  "username": "<requestor>",
  "changes": [{"action": "replace_file", "file": "ext_calib.conf", "path": "...", "exceptions": []}],
  "comment": "...",
  "status": "APPROVED",
  "group_id": "<user>_<date>_<hex>",
  "jira_required": true
}
```

Example list file content (one session, 4 views):

```
GM1_Sil2_260618_144120_0000/s001/p_Front-SV2
GM1_Sil2_260618_144120_0000/s001/p_Surround-SV2
GM1_Sil2_260618_144120_0000/s001/s_Front-1CAM-GM1
GM1_Sil2_260618_144120_0000/s001/s_Front-2CAM-GM1
```

Endpoints:
- `POST http://etc-change:5000/api/new_request`
- `GET http://etc-change:5000/api/requests?group_id=<group_id>`

## Directory layout

```
~/bulk_etc_change/<batch-name>/
├── bulk_etc_change.csv
├── sessions.list
├── prepare_meta.json
├── submit_summary.json
└── run.log

/mobileye/DPT/Dev/etc_change_input/<user>/<batch-name>/
├── <SESSION>/ext_calib.conf
└── lists/<group_id>_<N>.list

/mobileye/DPT/Dev/etc_change_output/<DPT-XXXXX>/
├── final_report.csv
├── aws_di-session_and_view_1.json
├── no_clips_or_sessions          # views not found in cloud
└── smd-session_and_view/
```

## Verification semantics

| Check | Meaning |
|-------|---------|
| `request_status: SUCCESS` | ETC request completed |
| `aws/SUCCESS` per view | View uploaded to cloud |
| `smd/SUCCESS` | Calibration version created |
| `smd/NOT_REQUIRED` | No effective calibration change |
| `no_clips_or_sessions` | View/session not in cloud catalog — ETC cannot apply |
| `de_artifacts` compare | **Unreliable** for cloud sessions |

## Cloud manual verification

Mount path pattern:

```
/tmp/<user>/mounted_clips/<SESSION>/s001/<VIEW>/s60/<CLIP>/etc/ext_calib.conf
```

Clip name pattern:

```
<SESSION>_s001_<VIEW>_s60_0001
```

Compare mounted file to submitted file:

```bash
diff \
  /tmp/<user>/mounted_clips/<SESSION>/s001/<VIEW>/s60/<CLIP>/etc/ext_calib.conf \
  /mobileye/DPT/Dev/etc_change_input/<user>/<batch>/<SESSION>/ext_calib.conf
```

Empty diff = cloud matches submitted file.

To see actual value changes vs old ETC, diff against a pre-change baseline — not against the submitted file.

## Supported actions

`replace_file`, `add_file`, `replace_field`, `add_field`, `remove_field`, `remove_section`, `remove_file`

Default: `replace_file` for `ext_calib.conf`.
