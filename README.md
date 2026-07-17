# FlyWolf Skills

Reusable skills for Codex and AI-agent workflows.

This repository is a public skill collection. Each folder is an independent skill with its own `SKILL.md`, `README.md`, and optional scripts, configuration, references, or agent metadata.

## Available Skills

| Skill | Purpose |
|---|---|
| `FlyWolf-github-skill-radar` | Finds useful GitHub projects that may be worth installing, auditing, watching, or packaging as reusable AI-agent skills. |
| `FlyWolf-video-copy-extractor` | Extracts spoken copy from local videos or short-video links and saves reusable transcript files. |
| `FlyWolf-fuji-scene-recipe-master` | Analyzes an uploaded scene photo and generates a practical Fujifilm JPEG recipe matched to the light, contrast, color temperature, subject, camera model, and target look. |

## How To Use

Clone the repository:

```bash
git clone https://github.com/DoomDeity/FlyWolf-Skills.git
```

Then copy or reference the skill folder you need:

```text
FlyWolf-github-skill-radar/
FlyWolf-video-copy-extractor/
FlyWolf-fuji-scene-recipe-master/
```

Read the selected folder's `README.md` for user-facing instructions and `SKILL.md` for the exact agent behavior.

## Repository Convention

Each skill follows the same core convention:

```text
FlyWolf-<skill-name>/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── optional files such as scripts/, config/, references/, or requirements.txt
```

Pure instruction skills do not need scripts or runtime dependencies. Tool-based skills may include the additional files required for execution.

## 中文说明

这是 FlyWolf 的公开 Skill 合集仓库，用来存放可复用的 Codex / AI Agent 工作流 Skill。

每个子目录都是一个独立 Skill，统一使用 `FlyWolf-` 前缀，并包含自己的 `SKILL.md`、`README.md` 和可选的脚本、配置、参考资料或 Agent 元数据。

## 当前 Skill

| Skill | 用途 |
|---|---|
| `FlyWolf-github-skill-radar` | 从 GitHub 发现值得安装、审计、观察，或适合封装成 AI Agent Skill 的项目。 |
| `FlyWolf-video-copy-extractor` | 从本地视频或小红书、抖音、B站、快手等链接中提取口播文案并保存为文本文件。 |
| `FlyWolf-fuji-scene-recipe-master` | 根据现场照片分析光线、反差、色温、主体、相机型号和目标风格，并生成可直接设置到富士相机中的 JPEG 直出配方。 |

## 使用方式

克隆仓库：

```bash
git clone https://github.com/DoomDeity/FlyWolf-Skills.git
```

然后复制或引用需要的 Skill 子目录：

```text
FlyWolf-github-skill-radar/
FlyWolf-video-copy-extractor/
FlyWolf-fuji-scene-recipe-master/
```

进入对应目录阅读：

- `README.md`：面向用户的介绍、安装与使用说明。
- `SKILL.md`：面向 Agent 的完整执行规则。

## 目录规范

```text
FlyWolf-<skill-name>/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── 按需添加 scripts/、config/、references/、requirements.txt 等文件
```

纯指令型 Skill 不需要为了形式而增加脚本或依赖；只有真正需要执行代码时才补充相关目录。
