# Export / Distribution Notes

This is the source bundle of `video-copy-extractor`. Copy this folder into the
recipient agent's skills directory (e.g. `~/.workbuddy/skills/video-copy-extractor/`,
or any skill folder your agent reads).

## What's in the box

- `SKILL.md` — agent instructions, including the first-run 3-choice backend picker.
- `scripts/extract_video_copy.py` — the transcription engine (multi-backend).
- `setup_local.py` — one-shot installer for the local (FunASR) backend.
- `requirements.txt` — local-backend dependencies.
- `config/preference.json` — starts as `{"mode": "unset"}`; the agent writes `local`/`online`/`openai`.
- `agents/openai.yaml` — optional WorkBuddy agent default prompt.
- `README.md` — end-user overview.

> The `.venv` (FunASR + CPU torch, ~1.5 GB) and ASR models (~1 GB) are **not** bundled,
> to keep the package portable. The local backend builds them on first use via `setup_local.py`.

## Recipient Setup

1. **ffmpeg** must be on PATH (ASR accepts audio, not video; the script extracts a
   16 kHz mono WAV automatically).
2. On **first use**, the skill asks the user to choose a backend:
   - **① 本地版 (FunASR)** — run once:
     ```text
     # Windows
     <skill-dir>\.venv\Scripts\python.exe "<skill-dir>\setup_local.py"
     # macOS / Linux
     <skill-dir>/.venv/bin/python "<skill-dir>/setup_local.py"
     ```
     (If `.venv` is missing, the agent creates it with `python3.11 -m venv "<skill-dir>/.venv"`
     first.) Models (~1 GB) auto-download on first transcription.
   - **② 阿里云 (Paraformer)** — set env vars (never paste keys in chat):
     ```text
     # Windows (PowerShell)
     setx DASHSCOPE_API_KEY "你的key"
     # macOS / Linux
     export DASHSCOPE_API_KEY="你的key"
     ```
     For local video files also configure OSS:
     ```text
     # Windows (PowerShell)
     setx OSS_BUCKET "..."; setx OSS_ENDPOINT "https://oss-cn-xxx.aliyuncs.com"
     setx OSS_KEY_ID "..."; setx OSS_KEY_SECRET "..."
     # macOS / Linux
     export OSS_BUCKET="..."; export OSS_ENDPOINT="https://oss-cn-xxx.aliyuncs.com"
     export OSS_KEY_ID="..."; export OSS_KEY_SECRET="..."
     ```
     A direct URL input needs only `DASHSCOPE_API_KEY`.
   - **③ OpenAI (gpt-4o-mini-transcribe)** — set env vars:
     ```text
     # Windows (PowerShell)
     setx OPENAI_API_KEY "你的key"
     setx HTTPS_PROXY "http://127.0.0.1:端口"   # 翻墙/代理必需（国内不可直连）
     # macOS / Linux
     export OPENAI_API_KEY="你的key"
     export HTTPS_PROXY="http://127.0.0.1:端口"
     ```
3. Optional: `REDFOX_API_KEY` for no-watermark short-video download; `yt-dlp` for generic URL fallback.

## Backends (3, auto-fallback)

| Backend | Required env | Notes |
|---|---|---|
| ① 本地 FunASR (default first) | none | No API key, no OSS. Handles local audio natively. Runs in the agent sandbox. |
| ② 阿里云百炼 Paraformer | `DASHSCOPE_API_KEY` (+ OSS 四件套 for local files) | Paraformer only accepts public URLs; local files need OSS upload. Skipped if OSS not set. |
| ③ OpenAI gpt-4o-mini-transcribe | `OPENAI_API_KEY` (+ VPN/proxy) | Handles local + URL audio. Data leaves China; needs network to api.openai.com. |

The chosen backend is tried first; on failure it auto-falls through the others
(local → openai → aliyun / online → funasr → openai / openai → funasr → aliyun).

## Included Logic

- Local video / URL → transcript (`.txt` / `.md`).
- RedFox URL parsing/download (when `REDFOX_API_KEY` set), `yt-dlp` fallback.
- ffmpeg audio extraction (16 kHz mono WAV).
- Auto-fallback across the 3 backends.

## Removed

- 讯飞 / 火山引擎: dropped — 讯飞 console config too complex for easy reuse; 火山 integration
  most complex (HMAC-SHA256 + TOS + polling) and pricier than Aliyun.
