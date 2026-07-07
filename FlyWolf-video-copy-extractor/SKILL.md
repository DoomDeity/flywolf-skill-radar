---
name: FlyWolf-video-copy-extractor
aliases: ["视频文案提取器", "视频文案提取"]
description: Standalone skill for extracting spoken copy/transcripts from local video files or short-video URLs into same-name .txt or .md files. Multi-backend speech-to-text (本地 FunASR / 阿里云 Paraformer / OpenAI). First run asks the user to choose a backend; the choice is remembered. Use when the user asks to turn a video into copy, extract video copy, transcribe Xiaohongshu/Douyin/Bilibili/Kuaishou links, save transcripts beside a video, or produce reusable text from uploaded/local videos.
---

# Video Copy Extractor (multi-backend)

Extract spoken copy from a local video path or video URL and save a transcript file
with the same base name as the video. Speech-to-text runs on one of three backends,
chosen on first use and remembered afterwards.

Users just say conversationally: *"extract the copy from this video"*, *"download this
Xiaohongshu video and transcribe it"*. The command below is for agents/debugging only.

```text
<skill-dir>/.venv/bin/python  (macOS/Linux)   OR
<skill-dir>\.venv\Scripts\python.exe  (Windows)
  "<skill-dir>/scripts/extract_video_copy.py" "<video-path-or-url>"
```

> Cross-platform note: this skill ships **source only** — it does NOT bundle the
> Python runtime or models. The first time you pick the local (FunASR) backend,
> `setup_local.py` builds a local `.venv` and downloads FunASR + CPU torch + oss2
> (~1.5 GB) plus the ASR models (~1 GB) on first run. Cloud backends (Aliyun /
> OpenAI) need only an API key and no local install.

---

## Step 0 — First run only: choose a backend (ask the user)

Before any transcription, **read `<skill-dir>/config/preference.json`**:

- If `mode` is `unset` (file missing or value `unset`) → this is the **first use**. Ask the
  user with `AskUserQuestion`: **本地版 / 阿里云 / OpenAI 三个里选哪个？** and show the
  comparison table below.
- If `mode` is already `local` / `online` / `openai` → **do NOT ask again**, go straight to
  Step 2 (Run). The choice is remembered permanently in `config/preference.json`.

> The question only appears on first use. Once chosen, the skill defaults to that backend
> (and its fallback order) every time.

### 三选一对比

| 维度 | ① 本地版（FunASR，阿里达摩院） | ② 阿里云（Paraformer） | ③ OpenAI（gpt-4o-mini-transcribe） |
|---|---|---|---|
| 需要 API Key | 否 | 是（`DASHSCOPE_API_KEY`） | 是（`OPENAI_API_KEY`） |
| 处理本地视频 | 原生支持，直接转 | 本地文件需配 OSS；给 URL 则只需 Key | 原生支持，本地/URL 都行 |
| 处理网页/短视频 URL | 下载后本地转，支持 | 下载后本地转，需 OSS 才转 | 下载后上传云端转，支持 |
| 联网要求 | 仅首次下模型需网，之后离线 | 每次需联网 | 每次需联网（且需翻墙/代理） |
| 费用 | 免费 | 约 0.29 元/小时（每月送 10 小时） | 按分钟计费（约 $0.004/分钟） |
| 速度 | CPU 推理，数十秒~数分钟 | 云端秒级~数十秒 | 云端，秒级~数十秒 |
| 隐私 | 数据不出本机 | 音频发往阿里云（国内） | 音频发往 OpenAI（出境） |
| 安装 | 首次自动装（约 1.5GB 运行时 + 首次 ~1GB 模型） | 仅配 Key | 仅配 Key |
| 中文效果 | 顶级（Paraformer 同源） | 顶级 | 强，但中文专有名词略逊于前两者 |
| 翻墙需求 | 否 | 否 | 是（需访问 api.openai.com） |

**怎么选：**
- 想要零配置、零费用、隐私最好、本地/网页视频通吃 → 选 **① 本地版（默认推荐）**。
- 不想装环境、有阿里云账号、主要转网页视频 → 选 **② 阿里云**。
- 本地视频也想走云端、不介意翻墙和数据出境 → 选 **③ OpenAI**。

选定后写入 `config/preference.json` 的 `mode`：①→`local`、②→`online`、③→`openai`。
之后自动兜底顺序为：
- `local`：FunASR → OpenAI → 阿里云
- `online`：阿里云 → FunASR → OpenAI
- `openai`：OpenAI → FunASR → 阿里云

### 选 ① 本地版 (FunASR)
1. 安装本地后端（自动：建 venv + 装 FunASR + CPU torch + oss2，约 1.5GB；已装则跳过）：
   ```text
   # Windows
   <skill-dir>\.venv\Scripts\python.exe "<skill-dir>\setup_local.py"
   # macOS / Linux
   <skill-dir>/.venv/bin/python "<skill-dir>/setup_local.py"
   ```
   若 `.venv` 尚不存在，agent 先用 Python 3.11 建 venv：
   ```text
   # Windows
   py -3.11 -m venv "<skill-dir>\.venv"
   <skill-dir>\.venv\Scripts\python.exe "<skill-dir>\setup_local.py"
   # macOS / Linux
   python3.11 -m venv "<skill-dir>/.venv"
   <skill-dir>/.venv/bin/python "<skill-dir>/setup_local.py"
   ```
2. 写 `config/preference.json` → `{"mode": "local"}`。
3. 进入 Step 2（Run）。

### 选 ② 阿里云 (Paraformer)
1. 让用户去申请 API Key（给链接+教程），**用本机环境变量配置，切勿把 Key 贴进对话**：
   ```text
   # Windows (PowerShell)
   setx DASHSCOPE_API_KEY "你的key"
   # macOS / Linux
   export DASHSCOPE_API_KEY="你的key"
   ```
   - 申请地址（创建 API Key）：https://bailian.console.aliyun.com/cn-beijing#/home
   - 计费说明：https://help.aliyun.com/zh/isi/developer-reference/metering-and-billing
2. **本地视频文件**需要 OSS（Paraformer 只收公网 URL）：
   ```text
   # Windows (PowerShell)
   setx OSS_BUCKET "你的bucket"
   setx OSS_ENDPOINT "https://oss-cn-xxx.aliyuncs.com"
   setx OSS_KEY_ID "你的keyid"
   setx OSS_KEY_SECRET "你的keysecret"
   # macOS / Linux
   export OSS_BUCKET="你的bucket"
   export OSS_ENDPOINT="https://oss-cn-xxx.aliyuncs.com"
   export OSS_KEY_ID="你的keyid"
   export OSS_KEY_SECRET="你的keysecret"
   ```
   直接给 URL 输入则只需 Key，无需 OSS。（若不想配 OSS，本地文件会自动落到 FunASR/OpenAI 兜底。）
3. 写 `config/preference.json` → `{"mode": "online"}`。
4. 进入 Step 2（Run）。

### 选 ③ OpenAI (gpt-4o-mini-transcribe)
1. 让用户去申请 API Key（给链接），**用本机环境变量配置，切勿贴进对话**：
   ```text
   # Windows (PowerShell)
   setx OPENAI_API_KEY "你的key"
   # macOS / Linux
   export OPENAI_API_KEY="你的key"
   ```
   - 申请地址：https://platform.openai.com/api-keys
2. **翻墙/代理必需**：OpenAI 接口在国内不可直连。全局 VPN 可直接用；若是应用层代理，设置：
   ```text
   # Windows (PowerShell)
   setx HTTPS_PROXY "http://127.0.0.1:端口"
   # macOS / Linux
   export HTTPS_PROXY="http://127.0.0.1:端口"
   ```
   （脚本会自动读取 `HTTPS_PROXY`/`HTTP_PROXY` 环境变量走代理。）
3. 写 `config/preference.json` → `{"mode": "openai"}`。
4. 进入 Step 2（Run）。

---

## Step 1 — Scope

- Local video → `.txt` or `.md`.
- URL download before transcription (RedFox preferred when `REDFOX_API_KEY` is set, otherwise `yt-dlp` fallback).
- Speech-to-text only, via the chosen backend + auto-fallback.
- No source-video renaming.
- When the source filename looks meaningless, a suggested filename is written into the
  transcript header.

## Step 2 — Run (every invocation after the backend is chosen)

1. Identify whether the input is a local file or URL.
2. For URLs, try RedFox first when `REDFOX_API_KEY` exists; otherwise `yt-dlp` fallback.
3. Extract audio to a 16 kHz mono WAV with ffmpeg.
4. Transcribe: run the script *without* `--backend`; it reads `config/preference.json` and
   uses the chosen backend first, then auto-fallbacks through the rest.
   - Debug / force a single backend: `--backend funasr` / `--backend openai` / `--backend aliyun`.
5. Save `<video-stem>.txt` or `<video-stem>.md`, never overwriting existing files.
6. Report the transcript path (and the downloaded video path when applicable).

### Run command
```text
# Windows
<skill-dir>\.venv\Scripts\python.exe "<skill-dir>\scripts\extract_video_copy.py" "<source>" --format txt
# macOS / Linux
<skill-dir>/.venv/bin/python "<skill-dir>/scripts/extract_video_copy.py" "<source>" --format txt
```

---

## Transcription backends (3, auto-fallback)

1. **本地 FunASR (阿里达摩院)** — Offline. No API key, no OSS, native local-file support.
   Runs in the agent sandbox; models auto-download on first use (~1 GB). Chinese quality
   is top-tier. **Default first priority** (mode `local`).
2. **OpenAI gpt-4o-mini-transcribe** — Cloud. Handles both local and URL audio perfectly.
   Needs `OPENAI_API_KEY` + network/VPN to `api.openai.com`. Audio leaves China.
3. **阿里云百炼 Paraformer** — Cloud. Needs `DASHSCOPE_API_KEY`. Paraformer only accepts a
   public URL, so local files need OSS (OSS_BUCKET / OSS_ENDPOINT / OSS_KEY_ID /
   OSS_KEY_SECRET); without OSS it is skipped for local files.

### Why these three
- 讯飞 and 火山引擎 were dropped: 讯飞's console setup is too complex (WebAPI must be
  activated separately, keys scattered across services) for a "anyone can use it" skill;
  火山's integration is the most complex (HMAC-SHA256 + TOS upload + polling) and its unit
  price is higher than Aliyun's.
- OpenAI was added back because it handles **both local and URL audio** with zero extra
  setup (unlike Aliyun's public-URL-only limit), making it the most flexible cloud option.
  Its only downside is the VPN requirement and data leaving China.

## Runtime Requirements

- Python 3.11 venv is created inside the skill dir as `.venv`; FunASR + CPU torch + oss2 are
  installed via `setup_local.py`. **Always run the script with the skill's `.venv` interpreter**
  (`.venv/bin/python` on macOS/Linux, `.venv\Scripts\python.exe` on Windows), otherwise
  `funasr` is not found.
- **ffmpeg** on PATH (ASR accepts audio, not video; the script extracts a 16 kHz mono WAV).
- Cloud backends need their API keys as env vars (see Step 0). Keys must never be pasted
  into chat — use env vars.

## CLI options

- `source` (required): video path or URL.
- `--format txt|md` (default txt)
- `--out-dir` / `--download-dir`
- `--language` (e.g. `zh` / `en`)
- `--backend funasr|openai|aliyun` (force a single backend, skip auto-fallback)

## Failure Handling

- Missing ffmpeg: tell the user to install it; never paste secrets in chat.
- No backend usable: the script reports each skipped backend and exits with a combined error.
- Download failure: show the platform/API error and do not create an empty transcript.
- Empty speech: save a small file recording the source and limitation.
