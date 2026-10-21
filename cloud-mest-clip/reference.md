# Cloud-MEST Clip — Reference

## Confluence source

- Page: [Latest versions and cmls](https://confluence.mobileye.com/spaces/FPAAEB/pages/259580052/Latest+versions+and+cmls)
- Page ID: `259580052`
- Space: `FPAAEB`

The table maps brain/project → bundle version → CF notation → MEST executables.

## Path pattern

```
/mobileye/trees_archive/PSW/bundle/{bundle_version}/pre-release/{cf_notation}/executables/{eyeq}/{build_mode}/CV_GV.s6
/mobileye/trees_archive/PSW/bundle/{bundle_version}/pre-release/{cf_notation}/executables/{eyeq}/{build_mode}/lib{Brain}.so
/mobileye/trees_archive/PSW/bundle/{bundle_version}/pre-release/{cf_notation}/executables/{eyeq}/{build_mode}/brainLibs/
```

## Example cloud-mest command (Mono8L / PC1)

```bash
cloud-mest \
  -m /mobileye/trees_archive/PSW/bundle/4.25.09.01/pre-release/PC1_2026_05_01/executables/eyeq6/release-st/CV_GV.s6 \
  /mobileye/trees_archive/PSW/bundle/4.25.09.01/pre-release/PC1_2026_05_01/executables/eyeq6/release-st/libMono8L.so \
  /mobileye/trees_archive/PSW/bundle/4.25.09.01/pre-release/PC1_2026_05_01/executables/eyeq6/release-st/brainLibs/ \
  -p " detectLtap=false -sPrintFCV_FP -sAllowRunNoYawRate -sAllowRunNoSpeed -sitrk-forceall runFreeSpace=true allowedAlertsOnOncoming=true alertsOnVD3D=true MEST.cfg::General: GFIMode=disable " \
  --budget-group default --sync=true --ignore-missing --overwrite --container-memory 7600 \
  -o /mobileye/Calibration/AdasAlgoExecution/Romi/mest_<CLIP> \
  -n <run_name> \
  -c <clip.list>
```

## versions_cache.json schema

```json
{
  "profiles": {
    "<profile_id>": {
      "label": "human readable",
      "bundle_version": "4.25.09.01",
      "cf_notation": "PC1_2026_05_01",
      "eyeq": "eyeq6",
      "build_mode": "release-st",
      "cvapp": "CV_GV",
      "brains": ["Mono8L"]
    }
  },
  "brain_to_profile": {
    "Mono8L": "pc1_mono8l"
  }
}
```

## Updating cache from Confluence

Agent steps:
1. `confluence_get_page` page_id=`259580052`
2. Extract rows: brain, bundle_version, cf_notation
3. Update `versions_cache.json`
4. Validate with `--dry-run` on a known clip

## Related skills

- `clip-sanity-check` — verify itrk after MEST
- `itrk-to-pext` — convert itrk output for MEDebugger
