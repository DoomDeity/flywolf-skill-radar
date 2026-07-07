# FlyWolf Skills

Public skill collection for Codex and AI-agent workflows.

This repository can host multiple standalone skills. Each skill lives in its own folder and contains its own `SKILL.md`.

## Skills

### `flywolf-github-skill-radar`

Finds trending GitHub skills, MCP servers, agent plugins, and reusable agent-tool projects.

It produces:

- **Overall Top 10**: durable high-value projects with repeat appearances tracked.
- **Fastest Growing**: projects gaining momentum since the previous run.
- **Analysis Advice**: whether to install, audit, watch, or skip based on the current user's profile and installed skills.

Run directly:

```bash
cd flywolf-github-skill-radar
python scripts/github_skill_radar.py --output github-skill-radar.md
```

Optional:

```bash
GITHUB_TOKEN=... python scripts/github_skill_radar.py \
  --profile RADAR_PROFILE.md \
  --installed-dir ~/.codex/skills \
  --output github-skill-radar.md
```

## 中文说明

这是 FlyWolf 的公开 Skill 合集仓库，用来存放可复用的 Codex / AI Agent 工作流 Skill。

每个 Skill 都是一个独立目录，目录里包含自己的 `SKILL.md`。因此仓库名不需要和某一个 Skill 完全一致。

### `flywolf-github-skill-radar`

用于发现 GitHub 上值得关注的 Skill、MCP server、Agent 插件，以及可以封装成 Skill 的项目。

它会输出：

- **综合 Top 10**：长期高价值项目，并记录重复出现次数。
- **本期增长最快**：根据历史记录看 stars、fork 和活跃度变化。
- **分析建议**：结合用户画像和已安装 Skill，判断是否值得安装、审计、观察或跳过。

它不会自动安装任何项目。
