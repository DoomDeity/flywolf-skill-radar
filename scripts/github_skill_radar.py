#!/usr/bin/env python3
"""Public GitHub Skill Radar.

Standard-library script that finds GitHub skill/MCP/plugin candidates, tracks
repeat appearances, and emits a concise Markdown report.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import math
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_QUERY_PATTERNS = [
    "codex skill pushed:>{since}",
    "claude skill pushed:>{since}",
    "agent skills pushed:>{since}",
    "mcp server pushed:>{since}",
    "codex plugin pushed:>{since}",
    "ai coding agent skill pushed:>{since}",
    "codebase memory mcp pushed:>{since}",
    "token compression mcp pushed:>{since}",
    "topic:mcp pushed:>{since}",
    "topic:codex pushed:>{since}",
    "topic:claude pushed:>{since}",
]

INCLUDE_TERMS = [
    "skill",
    "skills",
    "mcp",
    "plugin",
    "codex",
    "claude code",
    "opencode",
    "cursor",
    "agent harness",
    "coding agent",
    "codebase",
    "review",
    "testing",
    "browser",
    "research",
    "automation",
    "token",
    "memory",
    "cli",
]

EXCLUDE_TERMS = [
    "model weights",
    "dataset",
    "chat ui",
    "interview guide",
    "learning guide",
    "workflow automation platform",
    "low-code",
    "no-code",
    "chatbot",
]

PROFILE_FILES = ["RADAR_PROFILE.md", "USER_PROFILE.md", "OWNER_PROFILE.md", "AGENTS.md"]


def request_json(url: str, token: str | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-skill-radar-skill",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"GitHub API error {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, http.client.HTTPException, OSError) as exc:
        raise RuntimeError(f"GitHub request failed: {exc}") from exc


def load_text(path: pathlib.Path | None) -> str:
    if path and path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    for name in PROFILE_FILES:
        candidate = pathlib.Path.cwd() / name
        if candidate.exists():
            return candidate.read_text(encoding="utf-8", errors="replace")
    return ""


def load_installed_names(paths: list[str]) -> list[str]:
    names: set[str] = set()
    for raw in paths:
        path = pathlib.Path(raw).expanduser()
        if not path.exists():
            continue
        for child in path.iterdir():
            if child.is_dir():
                names.add(child.name.lower())
    return sorted(names)


def load_history(path: pathlib.Path) -> dict:
    if not path.exists():
        return {"generated_at": None, "repos": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".broken")
        path.replace(backup)
        return {"generated_at": None, "repos": {}}


def save_history(path: pathlib.Path, history: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def search_repos(queries: list[str], per_query: int, token: str | None) -> tuple[dict[str, dict], list[str]]:
    repos: dict[str, dict] = {}
    errors: list[str] = []
    for query in queries:
        encoded = urllib.parse.urlencode(
            {"q": query, "sort": "stars", "order": "desc", "per_page": str(per_query)}
        )
        url = f"https://api.github.com/search/repositories?{encoded}"
        try:
            data = request_json(url, token)
        except RuntimeError as exc:
            errors.append(f"{query}: {exc}")
            continue
        for item in data.get("items", []):
            repos.setdefault(item["full_name"], item)
        time.sleep(0.4)
    return repos, errors


def default_queries(days: int) -> list[str]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    return [pattern.format(since=since) for pattern in DEFAULT_QUERY_PATTERNS]


def relevant(repo: dict) -> bool:
    haystack = " ".join(
        str(repo.get(key) or "")
        for key in ["full_name", "name", "description", "homepage", "language"]
    ).lower()
    if any(term in haystack for term in EXCLUDE_TERMS):
        return False
    return any(term in haystack for term in INCLUDE_TERMS)


def score(repo: dict, history_record: dict | None) -> float:
    stars = int(repo.get("stargazers_count") or 0)
    forks = int(repo.get("forks_count") or 0)
    pushed = repo.get("pushed_at") or ""
    recency = 0.0
    try:
        pushed_dt = dt.datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        days = max(0, (dt.datetime.now(dt.timezone.utc) - pushed_dt).days)
        recency = max(0, 60 - days) / 60
    except ValueError:
        pass
    growth = 0
    if history_record:
        growth = stars - int(history_record.get("last_stars") or 0)
    return math.log10(max(stars, 1)) * 10 + math.log10(max(forks, 1)) * 2 + recency * 5 + growth * 0.05


def compact_number(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f} 万".replace(".0 万", " 万")
    return str(n)


def overlap(repo_name: str, installed: list[str]) -> list[str]:
    base = repo_name.split("/")[-1].lower().replace("_", "-")
    matches = []
    aliases = {
        "headroom": ["headroom"],
        "agent-reach": ["agent-reach"],
        "last30days-skill": ["last30days", "cn-last30days"],
        "superpowers": ["using-superpowers"],
        "ui-ux-pro-max-skill": ["frontend-design", "brand-guidelines"],
        "agent-skills": ["systematic-debugging", "test-driven-development", "requesting-code-review"],
    }
    for key, vals in aliases.items():
        if key in base:
            matches.extend([v for v in vals if v in installed])
    for name in installed:
        if len(name) >= 5 and len(base) >= 5 and (name in base or base in name):
            matches.append(name)
    return sorted(set(matches))


def describe(repo: dict, lang: str) -> str:
    desc = (repo.get("description") or "").strip().rstrip(".")
    if not desc:
        desc = repo["full_name"].split("/")[-1]
    if len(desc) > 110:
        desc = desc[:107].rstrip() + "..."
    return desc


def advice(repo: dict, installed: list[str], profile: str, lang: str) -> str:
    name = repo["full_name"]
    desc = (repo.get("description") or "").lower()
    dupes = overlap(name, installed)
    profile_light = not profile.strip()

    if dupes:
        joined = ", ".join(f"`{d}`" for d in dupes[:4])
        return (
            f"看起来有用，但当前环境已经有 {joined}，能力方向明显重叠；不建议重复安装，最多观察它是否有新的实现方式。"
            if lang == "zh"
            else f"Useful, but this owner already has {joined}; do not install again unless its implementation is clearly different."
        )
    if "awesome" in name.lower():
        return (
            "它更像发现目录，不是要安装的能力；适合作为线索源，后续只挑具体项目审计。"
            if lang == "zh"
            else "Use it as a discovery source, not as something to install."
        )
    if "skills" in name.lower() and name.lower() not in ("anthropics/skills",):
        return (
            "这是合集，可能有局部高价值；不要整包安装，先挑与当前缺口最相关的 1-2 个条目审计。"
            if lang == "zh"
            else "This is a collection; audit one or two relevant items instead of installing the whole set."
        )
    if "mcp" in desc or "mcp" in name.lower():
        return (
            "值得评估，尤其适合补工具层；安装前重点看权限、数据边界和本地索引成本。"
            if lang == "zh"
            else "Worth evaluating for the tool layer; check permissions, data boundaries, and local indexing cost first."
        )
    if profile_light:
        return (
            "可能有价值，但当前没有用户画像；先按通用 Agent 提效判断，只建议观察或审计，不直接安装。"
            if lang == "zh"
            else "Potentially useful, but no owner profile was found; watch or audit before installing."
        )
    return (
        "和 Agent 提效方向相关，建议先读 README 和安装脚本，再决定是否进入审计。"
        if lang == "zh"
        else "Relevant to agent productivity; inspect README and install scripts before audit or adoption."
    )


def duration_text(item: dict, lang: str) -> str:
    first = item["first_seen"]
    previous = item.get("last_seen_previous") or "N/A"
    count = item["seen_count"]
    if lang == "zh":
        return f"第 {count} 次出现；首次 {first}；上次 {previous}"
    return f"{count} appearances; first {first}; previous {previous}"


def growth_text(item: dict, lang: str) -> str:
    sg = item.get("star_growth")
    fg = item.get("fork_growth")
    if sg is None:
        return "首次记录，无法计算环比" if lang == "zh" else "First record; no delta yet"
    if lang == "zh":
        parts = [f"新增 {sg} stars"]
        if fg:
            parts.append(f"新增 {fg} fork")
        return "，".join(parts)
    parts = [f"+{sg} stars"]
    if fg:
        parts.append(f"+{fg} fork")
    return ", ".join(parts)


def heat_text(item: dict, lang: str) -> str:
    stars = compact_number(int(item["stargazers_count"]))
    forks = compact_number(int(item["forks_count"]))
    pushed = (item.get("pushed_at") or "")[:10]
    if lang == "zh":
        return f"{stars} stars，{forks} fork；最近更新 {pushed}"
    return f"{stars} stars, {forks} fork; updated {pushed}"


def annotate(items: list[dict], history: dict) -> list[dict]:
    today = dt.date.today().isoformat()
    repos = history.setdefault("repos", {})
    output = []
    for repo in items:
        key = repo["full_name"]
        old = repos.get(key)
        current = dict(repo)
        current["first_seen"] = old.get("first_seen") if old else today
        current["last_seen_previous"] = old.get("last_seen") if old else None
        current["seen_count"] = (int(old.get("seen_count") or 0) + 1) if old else 1
        current["star_growth"] = (
            int(repo.get("stargazers_count") or 0) - int(old.get("last_stars") or 0)
            if old
            else None
        )
        current["fork_growth"] = (
            int(repo.get("forks_count") or 0) - int(old.get("last_forks") or 0)
            if old
            else None
        )
        output.append(current)
    return output


def update_history(history: dict, items: list[dict]) -> None:
    today = dt.date.today().isoformat()
    history["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    repos = history.setdefault("repos", {})
    for item in items:
        repos[item["full_name"]] = {
            "repo": item["full_name"],
            "url": item["html_url"],
            "first_seen": item["first_seen"],
            "last_seen": today,
            "seen_count": item["seen_count"],
            "consecutive_weeks": item["seen_count"],
            "last_stars": int(item.get("stargazers_count") or 0),
            "last_forks": int(item.get("forks_count") or 0),
            "last_open_issues": int(item.get("open_issues_count") or 0),
            "last_pushed_at": item.get("pushed_at"),
        }


def markdown_table(rows: list[dict], installed: list[str], profile: str, lang: str, growth: bool) -> str:
    if lang == "zh":
        last = "涨幅情况" if growth else "持续时长"
        lines = [
            f"| 排名 | 项目名字 | 用途介绍 | 分析建议 | 热度 | {last} |",
            "|---|---|---|---|---|---|",
        ]
    else:
        last = "Growth" if growth else "Duration"
        lines = [
            f"| Rank | Project | What It Does | Analysis Advice | Heat | {last} |",
            "|---|---|---|---|---|---|",
        ]
    for i, item in enumerate(rows, 1):
        project = f"[{item['full_name']}]({item['html_url']})"
        final = growth_text(item, lang) if growth else duration_text(item, lang)
        lines.append(
            f"| {i} | {project} | {describe(item, lang)} | {advice(item, installed, profile, lang)} | {heat_text(item, lang)} | {final} |"
        )
    return "\n".join(lines)


def build_report(top: list[dict], growth: list[dict], installed: list[str], profile: str, errors: list[str], lang: str) -> str:
    today = dt.date.today().isoformat()
    if lang == "zh":
        lines = [
            f"# GitHub Skill Radar - {today}",
            "",
            "## 本次结论",
            "",
            "本次报告同时保留长期热门项目和增长较快项目；安装前仍应做安全审计，尤其是第三方脚本和需要凭据的工具。",
            "",
            "## 综合 Top 10 候选",
            "",
            markdown_table(top, installed, profile, lang, growth=False),
            "",
            "## 本周增长最快",
            "",
            markdown_table(growth, installed, profile, lang, growth=True),
            "",
            "## 建议动作",
            "",
            "- 可进入审计/安装评估：优先选择分析建议中没有明显重复、且能补足当前工作流缺口的项目。",
            "- 继续观察：热度异常、描述夸张、或安装成本不清楚的项目。",
            "- 不建议投入或不重复安装：已被本地 Skill 覆盖的项目、纯目录项目、泛 AI 应用。",
            "",
            "## 局限",
            "",
        ]
        if errors:
            lines.append("- 部分 GitHub 查询失败：" + "; ".join(errors[:3]))
        if not profile.strip():
            lines.append("- 未找到用户画像文件，本次适配判断偏通用。")
        if not installed:
            lines.append("- 未提供已安装 Skill 目录，重复判断可能不完整。")
        return "\n".join(lines) + "\n"

    lines = [
        f"# GitHub Skill Radar - {today}",
        "",
        "## Summary",
        "",
        "This report keeps both durable leaders and fast-growing candidates. Audit third-party scripts and credential access before installing anything.",
        "",
        "## Overall Top 10",
        "",
        markdown_table(top, installed, profile, lang, growth=False),
        "",
        "## Fastest Growing This Run",
        "",
        markdown_table(growth, installed, profile, lang, growth=True),
        "",
        "## Recommended Actions",
        "",
        "- Audit/install candidates that fill a clear workflow gap and do not duplicate installed skills.",
        "- Watch projects with unusual growth, unclear install behavior, or high maintenance cost.",
        "- Skip duplicate skills, pure directories, and broad AI apps without reusable skill/MCP/CLI value.",
        "",
        "## Limitations",
        "",
    ]
    if errors:
        lines.append("- Some GitHub queries failed: " + "; ".join(errors[:3]))
    if not profile.strip():
        lines.append("- No owner profile found; fit analysis is generic.")
    if not installed:
        lines.append("- No installed skill directories were provided; duplicate detection may be incomplete.")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find trending GitHub skill/MCP/plugin candidates.")
    parser.add_argument("--query", action="append", help="Extra GitHub search query. Can be repeated.")
    parser.add_argument("--no-default-queries", action="store_true", help="Use only --query values.")
    parser.add_argument("--days", type=int, default=180, help="Default pushed:> window in days.")
    parser.add_argument("--per-query", type=int, default=5)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--growth-limit", type=int, default=10)
    parser.add_argument("--history", default=".github-skill-radar/history.json")
    parser.add_argument("--profile", help="Owner profile file, e.g. RADAR_PROFILE.md")
    parser.add_argument("--installed-dir", action="append", default=[], help="Directory containing installed skill folders.")
    parser.add_argument("--output", help="Write Markdown report to this path.")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--json", action="store_true", help="Emit raw annotated JSON instead of Markdown.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    queries = ([] if args.no_default_queries else default_queries(args.days)) + (args.query or [])
    if not queries:
        raise SystemExit("No queries provided. Use --query or omit --no-default-queries.")
    history_path = pathlib.Path(args.history).expanduser()
    profile = load_text(pathlib.Path(args.profile).expanduser() if args.profile else None)
    installed = load_installed_names(args.installed_dir)
    history = load_history(history_path)

    found, errors = search_repos(queries, args.per_query, token)
    filtered = [repo for repo in found.values() if relevant(repo)]
    annotated = annotate(filtered, history)
    annotated.sort(key=lambda item: score(item, history.get("repos", {}).get(item["full_name"])), reverse=True)
    top = annotated[: args.limit]
    growth = sorted(
        annotated,
        key=lambda item: (
            item["star_growth"] if item["star_growth"] is not None else -1,
            item["fork_growth"] if item["fork_growth"] is not None else -1,
            int(item.get("stargazers_count") or 0),
        ),
        reverse=True,
    )[: args.growth_limit]

    update_history(history, annotated)
    save_history(history_path, history)

    if args.json:
        payload = {"top": top, "growth": growth, "errors": errors, "installed": installed}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = build_report(top, growth, installed, profile, errors, args.language)

    if args.output:
        pathlib.Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
