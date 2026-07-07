# FlyWolf GitHub Skill Radar

Public Codex skill for discovering trending GitHub skills, MCP servers, agent plugins, and projects that can become reusable AI-agent skills.

It produces two practical rankings:

- **Overall Top 10**: durable high-value projects, with repeat appearances tracked.
- **Fastest Growing**: projects gaining momentum since the previous run.

The report also explains whether each project is worth installing, auditing, watching, or skipping based on the current user's profile and installed skills.

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

## 中文说明

这是一个公开版 Codex Skill，用来定期发现 GitHub 上值得关注的 Skill、MCP server、Agent 插件，以及可以封装成 Skill 的项目。

它会输出两张榜单：

- **综合 Top 10**：长期高价值项目，会标记第几次出现，避免重复霸榜看不清。
- **本期增长最快**：根据历史记录看 stars、fork 和活跃度变化，发现新机会。

它不会自动安装任何项目，只会给出“建议审计 / 继续观察 / 不建议安装 / 与已有 Skill 重复”等判断。

如果你提供 `RADAR_PROFILE.md` 或 `--installed-dir`，它会根据你的目标和已安装 Skill 做更准确的适配分析。
