# GitHub Skill Radar / GitHub Skill 雷达

Find trending GitHub skills, MCP servers, agent plugins, and reusable agent-tool projects, then decide whether they are worth installing, auditing, watching, or skipping.

它用于定期发现 GitHub 上值得关注的 Skill、MCP server、Agent 插件，以及适合封装成 AI Agent Skill 的项目，并结合用户画像和已安装 Skill 给出安装/审计/观察/跳过建议。

## What It Produces

| Section | Purpose |
|---|---|
| Overall Top 10 | Durable high-value projects, with repeat appearances tracked. |
| Fastest Growing | Projects gaining momentum since the previous run. |
| Analysis Advice | Human-readable judgment based on owner profile, installed skills, duplication, risk, and next step. |

## 输出内容

| 板块 | 说明 |
|---|---|
| 综合 Top 10 | 长期高价值项目，并记录第几次出现、是否重复霸榜。 |
| 本期增长最快 | 根据历史记录比较 stars、fork 和活跃度变化。 |
| 分析建议 | 结合用户画像、已安装 Skill、重复度和风险，给出是否值得安装、审计、观察或跳过。 |

## Features / 特点

- **Owner-aware**: reads `RADAR_PROFILE.md`, `USER_PROFILE.md`, `OWNER_PROFILE.md`, or explicit `--profile` when available.
- **Duplicate-aware**: compares candidates with installed skills passed through `--installed-dir`.
- **History-aware**: stores lightweight history in `.github-skill-radar/history.json` to track repeat appearances and growth.
- **Safe by default**: never installs or modifies third-party projects; it only reports recommendations.
- **Portable**: uses only Python standard library; no package installation required.

- **按当前使用者判断**：有用户画像时按用户画像分析，而不是写死作者自己的偏好。
- **会做重复判断**：通过 `--installed-dir` 对比本机已安装 Skill，避免重复安装。
- **会记录历史**：用 `.github-skill-radar/history.json` 记录出现次数和增长。
- **默认安全**：只输出建议，不自动安装、更新或启用任何第三方项目。
- **一键可跑**：只依赖 Python 标准库，不需要额外安装 Python 包。

## Quick Start

```bash
python scripts/github_skill_radar.py --output github-skill-radar.md
```

Use a GitHub token to reduce API rate limits:

```bash
GITHUB_TOKEN=... python scripts/github_skill_radar.py --output github-skill-radar.md
```

With owner profile and installed skills:

```bash
python scripts/github_skill_radar.py \
  --profile RADAR_PROFILE.md \
  --installed-dir ~/.codex/skills \
  --history .github-skill-radar/history.json \
  --output github-skill-radar.md
```

Lightweight test run:

```bash
python scripts/github_skill_radar.py \
  --no-default-queries \
  --query "mcp server pushed:>2026-01-01" \
  --per-query 5 \
  --output github-skill-radar.md
```

## Directory Structure

```text
FlyWolf-github-skill-radar/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── scripts/
    └── github_skill_radar.py
```

## Notes

- `SKILL.md` is the agent-facing instruction file.
- `scripts/github_skill_radar.py` is the runnable scanner/report generator.
- `agents/openai.yaml` is optional UI metadata.
- Generated reports and history files are ignored by `.gitignore` at the repository root.

## License

MIT
