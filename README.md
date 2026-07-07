# FlyWolf Skill Radar

Public Codex skill for finding trending GitHub skills, MCP servers, agent plugins, and projects that can be packaged as reusable AI-agent skills.

## Quick Start

```bash
python scripts/github_skill_radar.py --output github-skill-radar.md
```

Optional:

```bash
GITHUB_TOKEN=... python scripts/github_skill_radar.py \
  --profile RADAR_PROFILE.md \
  --installed-dir ~/.codex/skills \
  --output github-skill-radar.md
```

The script uses only Python's standard library. By default, it stores lightweight history in `.github-skill-radar/history.json`.
