---
name: github-skill-radar
description: Use when finding, ranking, and assessing trending GitHub skills, MCP servers, agent plugins, agent workflows, or projects that could be packaged as reusable AI-agent skills.
---

# GitHub Skill Radar

Find public GitHub projects that may be useful as skills, MCP servers, plugins, or agent workflow components. Rank both durable leaders and fast-growing newcomers, then judge whether the current owner should install, audit, watch, or ignore them.

## Quick Start

Run the bundled script from any workspace:

```bash
python scripts/github_skill_radar.py --output github-skill-radar.md
```

Use a GitHub token when available to reduce API limits:

```bash
GITHUB_TOKEN=... python scripts/github_skill_radar.py --output github-skill-radar.md
```

Useful options:

```bash
python scripts/github_skill_radar.py \
  --profile RADAR_PROFILE.md \
  --installed-dir ~/.codex/skills \
  --history .github-skill-radar/history.json \
  --days 180 \
  --limit 10 \
  --growth-limit 10 \
  --output github-skill-radar.md
```

For a narrow test run or low-rate-limit environment:

```bash
python scripts/github_skill_radar.py \
  --no-default-queries \
  --query "mcp server pushed:>2026-01-01" \
  --per-query 5 \
  --output github-skill-radar.md
```

## Owner Fit

This skill must adapt to the current owner, not the skill author.

Before judging fit, look for owner context in this order:

1. Explicit user instructions in the current conversation.
2. `--profile` file if provided.
3. Local files named `RADAR_PROFILE.md`, `USER_PROFILE.md`, `OWNER_PROFILE.md`, or `AGENTS.md` in the current workspace.
4. Installed skill names from `--installed-dir`.
5. If no profile is available, use generic fit and say the judgment is profile-light.

Do not hard-code any person, machine path, or private preference into public output.

## Output Contract

Return concise Markdown with these sections:

```markdown
# GitHub Skill Radar - YYYY-MM-DD

## Summary

## Overall Top 10
| Rank | Project | What It Does | Analysis Advice | Heat | Duration |

## Fastest Growing This Run
| Rank | Project | What It Does | Analysis Advice | Heat | Growth |

## Recommended Actions

## Limitations
```

For Chinese output, the same columns should be:

```markdown
| 排名 | 项目名字 | 用途介绍 | 分析建议 | 热度 | 持续时长 |
| 排名 | 项目名字 | 用途介绍 | 分析建议 | 热度 | 涨幅情况 |
```

## Analysis Advice Style

Write like a human decision maker, not a classifier.

Good:
- "比较匹配，但你已经有 `headroom`，能力高度相似，所以不建议重复安装。可以只观察它的 MCP 实现。"
- "值得审计，可能补强代码库理解；它和 `headroom` 都在节省上下文，但一个偏压缩输出，一个偏构建代码知识图谱，不算非常重复。"
- "这类合集里一部分可能有价值，比如 review/testing；但很多会和 `systematic-debugging`、`test-driven-development` 重复，所以不要整包安装，只挑缺口审计。"

Avoid:
- "High: install"
- "Medium: watch"
- "Good fit"
- Separate `type`, `fit`, and `decision` columns.

## Candidate Rules

Include a repository only when at least one is true:

- It is a skill, skill collection, MCP server, Codex/Claude/OpenCode/Cursor extension, or agent engineering add-on.
- It can clearly be packaged as a local skill, MCP tool, CLI tool, or automation.
- It improves agent work on search, browser control, codebase understanding, token compression, testing, review, documentation, content growth, or research automation.

Exclude broad AI apps, chat UIs, low-code platforms, model weights, generic learning repos, pure prompt collections, and unrelated large repos unless they expose reusable skill/MCP/CLI value.

## History And Deduping

Use the history file to avoid noisy repeats while still allowing durable winners to remain visible.

- Default history path: `.github-skill-radar/history.json`
- Overall Top 10 may repeat old winners, but must show duration.
- Fastest Growing should highlight changes since the previous run.
- If there is no history, mark growth as first record instead of inventing deltas.

Never install, update, delete, or enable a repository automatically. Recommend audit/install only as a next step.
