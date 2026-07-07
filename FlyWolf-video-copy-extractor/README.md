# 视频文案提取器 / Video Copy Extractor

把本地视频或短视频链接（小红书 / 抖音 / B站 / 快手 等）里的口播文案提取成同名 `.txt` / `.md` 文本文件。

多后端语音转写，首次使用三选一，之后自动记住并带兜底：

| 后端 | 说明 | 需要 |
|---|---|---|
| ① 本地 FunASR（阿里达摩院） | 离线、免费、中文顶级、本地/网页视频通吃 | 首次自动装 ~1.5GB 运行时 + 首次 ~1GB 模型 |
| ② 阿里云 Paraformer | 云端、中文顶级 | `DASHSCOPE_API_KEY`（本地文件需 OSS）|
| ③ OpenAI gpt-4o-mini-transcribe | 云端、本地/URL 都行 | `OPENAI_API_KEY` + 翻墙/代理 |

兜底顺序：本地→OpenAI→阿里云（可在 `config/preference.json` 切换）。

## 特点

- **只发源码，不打包运行时**：`.venv` 和模型都不在仓库里，用户第一次选本地版时由 `setup_local.py` 自动下载安装。
- **跨平台**：Windows / macOS / Linux 均可，运行命令见 `SKILL.md`（`.venv\Scripts\python.exe` 或 `.venv/bin/python`）。
- **跨 agent**：核心是 `scripts/extract_video_copy.py`，任何能跑 Python 脚本的 agent / 终端都能用；`SKILL.md` 供 WorkBuddy 等技能系统读取，`agents/openai.yaml` 是可选的 WorkBuddy agent 描述。
- **无隐私残留**：不内置任何密钥，所有 Key 都用本机环境变量配置。

## 目录结构

```
video-copy-extractor/
├── SKILL.md              # 技能说明（供 agent 读取，含三选一与跨平台命令）
├── README.md             # 本文件
├── requirements.txt      # Python 依赖
├── setup_local.py        # 本地 FunASR 后端一键安装器
├── agents/
│   └── openai.yaml       # 可选：WorkBuddy agent 描述
├── config/
│   └── preference.json   # {"mode": "unset"} 首用三选一
├── references/
│   └── export.md         # 导出/分发说明
└── scripts/
    └── extract_video_copy.py
```

## 使用

1. 把本仓库放进你的技能目录（如 WorkBuddy 的 `~/.workbuddy/skills/video-copy-extractor/`）。
2. 首次调用时按提示三选一，后端会写入 `config/preference.json`，之后免问。
3. 直接说："提取这个视频的文案" / "把这个抖音链接转成文字"。

详细安装与三种后端配置见 `SKILL.md`。

## 依赖

- Python 3.11
- ffmpeg（在 PATH 中；脚本用它抽 16kHz 单声道 WAV）
- 选本地版：自动装 FunASR + CPU torch + oss2
- 选云端版：仅需要对应 API Key 环境变量

## License

MIT
