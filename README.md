# Cursor Team Skills

Shared [Cursor Agent Skills](https://cursor.com/docs/agent/skills) for the team.

## Quick start

```bash
git clone <YOUR_INTERNAL_GIT_URL>/cursor-team-skills.git ~/cursor-team-skills
bash ~/cursor-team-skills/install.sh
```

Restart Cursor (or open a new chat) so skills are picked up.

## What gets installed

`install.sh` symlinks each skill under `~/.cursor/skills/`:

```
~/.cursor/skills/bulk-etc-change -> ~/cursor-team-skills/bulk-etc-change
```

## Updating

```bash
cd ~/cursor-team-skills
git pull
```

No reinstall needed — symlinks point at the repo.

## Adding a new skill

1. Create a folder with a `SKILL.md` file (see `bulk-etc-change/` as a template).
2. Open a PR or push to `main`.
3. Teammates run `git pull` in their clone.

## Available skills

| Skill | Description |
|-------|-------------|
| [bulk-etc-change](bulk-etc-change/) | Bulk ETC file replacement for GM sessions (ext_calib.conf, all views) |

## Usage in Cursor

After install, invoke in chat:

```
/bulk-etc-change for <session list or source paths>
```

Or describe the task naturally — the agent should pick up the skill from its description.

## Repo setup (maintainers)

```bash
# one-time: create empty repo on internal Git (GitLab / Bitbucket / etc.)
# then:
cd ~/cursor-team-skills
git init -b main
git add .
git commit -m "Initial commit: bulk-etc-change skill"
git remote add origin <YOUR_INTERNAL_GIT_URL>/cursor-team-skills.git
git push -u origin main
```
