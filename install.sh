#!/usr/bin/env bash
# Link team skills from this repo into ~/.cursor/skills/
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${HOME}/.cursor/skills"

mkdir -p "${SKILLS_DIR}"

linked=0
for skill_dir in "${REPO_DIR}"/*/; do
  [[ -f "${skill_dir}/SKILL.md" ]] || continue
  name="$(basename "${skill_dir}")"
  target="${SKILLS_DIR}/${name}"

  if [[ -L "${target}" ]]; then
    rm "${target}"
  elif [[ -e "${target}" ]]; then
    echo "SKIP ${name}: ${target} exists and is not a symlink (remove manually to link)"
    continue
  fi

  ln -sfn "${skill_dir%/}" "${target}"
  echo "Linked ${name} -> ${target}"
  linked=$((linked + 1))
done

if [[ "${linked}" -eq 0 ]]; then
  echo "No skills found (expected subdirs with SKILL.md)"
  exit 1
fi

echo "Done. ${linked} skill(s) linked under ${SKILLS_DIR}"
