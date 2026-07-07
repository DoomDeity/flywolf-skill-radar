#!/usr/bin/env python3
"""Standalone video copy extractor (multi-backend edition).

Speech-to-text backends (auto-fallback in priority order, skipping any
backend whose credentials are missing):

1. funasr  (本地 FunASR, 阿里达摩院) -- Offline. No API key, no OSS. Handles
                                    local audio natively. Models download on
                                    first use (~1 GB). Zero cost, private.
2. openai  (OpenAI gpt-4o-mini-transcribe) -- Cloud. Handles BOTH local and
                                    URL audio perfectly. Needs OPENAI_API_KEY
                                    and network access to api.openai.com.
3. aliyun  (阿里云百炼 Paraformer)  -- Cloud. Needs DASHSCOPE_API_KEY.
                                    Paraformer only accepts a public URL, so a
                                    local file needs OSS configured
                                    (OSS_BUCKET/OSS_ENDPOINT/OSS_KEY_ID/
                                    OSS_KEY_SECRET); without OSS it is skipped.

Which backend runs first is decided by <skill-dir>/config/preference.json:
  "local"  -> [funasr, openai, aliyun]
  "openai" -> [openai, funasr, aliyun]
  "online" -> [aliyun, funasr, openai]
  unset/*  -> [funasr, openai, aliyun]   (safe default: local-first)
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, quote
from urllib.request import ProxyHandler, build_opener

REDFOX_API_URL = "https://redfox.hk/story/api/parseWork/parse"
DASHSCOPE_CREATE_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
DASHSCOPE_QUERY_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"
OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MODEL = "gpt-4o-mini-transcribe"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".flv"}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/134 Safari/537.36"
ALIYUN_POLL_SECONDS = 5
ALIYUN_POLL_LIMIT = 120  # 最多轮询 ~10 分钟

# Priority order per persisted mode (read from config/preference.json).
BACKEND_ORDERS = {
    "local": ["funasr", "openai", "aliyun"],
    "openai": ["openai", "funasr", "aliyun"],
    "online": ["aliyun", "funasr", "openai"],
}
DEFAULT_ORDER = BACKEND_ORDERS["local"]


# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------
def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True)


def sanitize_filename(name: str | None, fallback: str = "video") -> str:
    raw = (name or fallback).strip() or fallback
    cleaned = re.sub(r'[\\/*?:"<>|]+', "", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (cleaned[:120] or fallback).strip(". ")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
    die(f"too many existing files matching {path.name}")


def looks_meaningless(stem: str) -> bool:
    cleaned = stem.strip().lower()
    return (
        not cleaned
        or bool(re.fullmatch(r"[a-z0-9_-]{1,18}", cleaned))
        or bool(re.fullmatch(r"(vid|img|video|douyin|xhs|bili|download|untitled)[-_ ]?\d*", cleaned))
        or bool(re.fullmatch(r"\d{6,}", cleaned))
    )


def suggest_filename(transcript: str, fallback_stem: str) -> str:
    first_line = next((line.strip() for line in transcript.splitlines() if line.strip()), "")
    if not first_line:
        return f"{fallback_stem}-needs-title"
    title = re.split(r"[.!?\n]", first_line, maxsplit=1)[0]
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r'[\\/*?:"<>|#`]+', "", title).strip()
    return title[:40] or f"{fallback_stem}-needs-title"


def http_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(str(exc)) from exc


def download_binary(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".part")
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with request.urlopen(req, timeout=180) as resp, tmp_path.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        tmp_path.replace(output_path)
        return output_path
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(str(exc)) from exc


def download_with_redfox(source_url: str, download_dir: Path) -> Path:
    api_key = os.getenv("REDFOX_API_KEY")
    if not api_key:
        raise RuntimeError("REDFOX_API_KEY is not set")
    result = http_json(
        REDFOX_API_URL,
        {"url": source_url, "source": "video-copy-extractor"},
        {"Content-Type": "application/json", "X-API-KEY": api_key},
    )
    code = str(result.get("code", ""))
    if not code.startswith("2"):
        raise RuntimeError(f"RedFox API error {result.get('code')}: {result.get('msg', '')}")
    data = result.get("data") or {}
    video_url = data.get("videoUrl") or data.get("downloadUrl") or data.get("download_url")
    if not video_url:
        raise RuntimeError("RedFox did not return a video URL")
    title = sanitize_filename(data.get("title"), "video")
    return download_binary(str(video_url), unique_path(download_dir / f"{title}.mp4")).resolve()


def newest_video(directory: Path, before: set[Path]) -> Path | None:
    candidates = [
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS and path not in before
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def download_with_ytdlp(source_url: str, download_dir: Path) -> Path:
    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        raise RuntimeError("yt-dlp is not installed")
    before = {p for p in download_dir.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS}
    result = run_command([ytdlp, "--no-playlist", "-o", str(download_dir / "%(title).120s.%(ext)s"), source_url])
    if result.returncode != 0:
        raise RuntimeError("\n".join(part for part in [result.stdout, result.stderr] if part.strip()).strip())
    video = newest_video(download_dir, before)
    if not video:
        raise RuntimeError("yt-dlp finished but no video file was found")
    return video.resolve()


def resolve_source(source: str, download_dir: Path) -> tuple[Path, str]:
    if is_url(source):
        download_dir.mkdir(parents=True, exist_ok=True)
        redfox_error = None
        try:
            return download_with_redfox(source, download_dir), source
        except Exception as exc:
            redfox_error = str(exc)
            warn(f"RedFox unavailable: {redfox_error}")
        try:
            warn("Trying yt-dlp fallback. Watermark-free output is not guaranteed.")
            return download_with_ytdlp(source, download_dir), source
        except Exception as exc:
            die(f"video download failed. RedFox: {redfox_error}; yt-dlp: {exc}")

    path = Path(source).expanduser().resolve()
    if not path.exists():
        die(f"video file not found: {path}")
    return path, str(path)


# --------------------------------------------------------------------------
# audio extraction (ffmpeg)
# --------------------------------------------------------------------------
def extract_audio(video_path: Path, work_dir: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        die("ffmpeg not found on PATH. ASR needs audio; install ffmpeg first.")
    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = unique_path(work_dir / f"{video_path.stem}.wav")
    cmd = [
        ffmpeg, "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(audio_path),
    ]
    result = run_command(cmd)
    if result.returncode != 0 or not audio_path.exists():
        raise RuntimeError("ffmpeg audio extraction failed:\n" + (result.stderr or "").strip())
    return audio_path.resolve()


# --------------------------------------------------------------------------
# backend 1: 阿里云百炼 Paraformer (pure stdlib REST)
# --------------------------------------------------------------------------
def _aliyun_oss_url(audio_path: Path) -> str:
    try:
        import oss2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("oss2 not installed (needed to host local files for Aliyun)") from exc
    bucket = os.getenv("OSS_BUCKET")
    endpoint = os.getenv("OSS_ENDPOINT")
    key_id = os.getenv("OSS_KEY_ID")
    key_secret = os.getenv("OSS_KEY_SECRET")
    if not (bucket and endpoint and key_id and key_secret):
        raise RuntimeError(
            "OSS not configured (need OSS_BUCKET/OSS_ENDPOINT/OSS_KEY_ID/OSS_KEY_SECRET); "
            "Aliyun Paraformer requires a public URL for local files"
        )
    auth = oss2.Auth(key_id, key_secret)
    b = oss2.Bucket(auth, endpoint, bucket)
    key = f"video-copy-extractor/{audio_path.name}"
    b.put_object_from_file(key, str(audio_path))
    return b.sign_url("GET", key, 7200)


def _aliyun_create_task(file_url: str, api_key: str, language: str | None) -> str:
    hints = ["zh", "en"] if not language else [language]
    payload = {
        "model": "paraformer-v2",
        "input": {"file_urls": [file_url]},
        "parameters": {"language_hints": hints},
    }
    resp = http_json(
        DASHSCOPE_CREATE_URL,
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
    )
    task_id = (resp.get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"aliyun create task failed: {resp}")
    return task_id


def _aliyun_poll(task_id: str, api_key: str) -> str:
    url = f"{DASHSCOPE_QUERY_URL}/{task_id}"
    req = request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    for _ in range(ALIYUN_POLL_LIMIT):
        try:
            with request.urlopen(req, timeout=30) as resp:
                resp_json = json.loads(resp.read().decode("utf-8", errors="replace"))
        except HTTPError as exc:
            raise RuntimeError(f"aliyun poll HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"aliyun poll: {exc}") from exc
        status = (resp_json.get("output") or {}).get("task_status")
        if status == "SUCCEEDED":
            results = (resp_json.get("output") or {}).get("results") or []
            if results:
                return results[0]["transcription_url"]
            raise RuntimeError("aliyun task succeeded but no result url")
        if status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"aliyun task {status}: {resp_json}")
        time.sleep(ALIYUN_POLL_SECONDS)
    raise RuntimeError("aliyun transcription timed out")


def transcribe_aliyun(audio_path: Path, language: str | None) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set")

    if is_url(str(audio_path)):
        file_url = str(audio_path)
    else:
        file_url = _aliyun_oss_url(audio_path)

    task_id = _aliyun_create_task(file_url, api_key, language)
    result_url = _aliyun_poll(task_id, api_key)

    try:
        with request.urlopen(result_url, timeout=60) as r:
            result_json = json.loads(r.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"aliyun fetch result: {exc}") from exc
    transcripts = result_json.get("transcripts") or []
    text = (transcripts[0].get("text") if transcripts else "") or ""
    return text.strip()


# --------------------------------------------------------------------------
# backend 2: 本地 FunASR (offline; no API key)
# --------------------------------------------------------------------------
def transcribe_funasr(audio_path: Path, language: str | None) -> str:
    try:
        from funasr import AutoModel  # type: ignore
    except ImportError as exc:
        raise RuntimeError("funasr not installed (local offline backend)") from exc
    model = AutoModel(
        model="paraformer-zh", model_revision="v2.0.4",
        vad_model="fsmn-vad", vad_model_revision="v2.0.4",
        punc_model="ct-punc", punc_model_revision="v2.0.4",
    )
    res = model.generate(input=str(audio_path), batch_size_s=300)
    if not res:
        return ""
    item = res[0]
    text = item.get("text") or ""
    if not text and isinstance(item.get("sentences"), list):
        text = " ".join(s.get("text", "") for s in item["sentences"])
    return text.strip()


# --------------------------------------------------------------------------
# backend 3: OpenAI gpt-4o-mini-transcribe (handles local + URL audio)
# --------------------------------------------------------------------------
def _proxy_opener():
    """Return an opener that honours HTTP(S)_PROXY env (needed for OpenAI in CN)."""
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        return build_opener(ProxyHandler({"http": proxy, "https": proxy}))
    return request


def transcribe_openai(audio_path: Path, language: str | None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    ctype = mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
    boundary = "----openaiboundary7Q27Xk9"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{audio_path.name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode("utf-8")
    fields = (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\n'
        f"{OPENAI_MODEL}\r\n"
    ).encode("utf-8")
    if language:
        fields += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="language"\r\n\r\n'
            f"{language}\r\n"
        ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = head + audio_path.read_bytes() + fields + tail
    req = request.Request(
        OPENAI_TRANSCRIBE_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    opener = _proxy_opener()
    try:
        with opener.open(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        raise RuntimeError(f"openai HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"openai request failed: {exc} (needs network/VPN to api.openai.com)") from exc
    text = data.get("text") if isinstance(data, dict) else None
    if not text:
        raise RuntimeError(f"openai returned no text: {data}")
    return text.strip()


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------
def load_mode() -> str:
    pref = Path(__file__).resolve().parent.parent / "config" / "preference.json"
    if pref.exists():
        try:
            data = json.loads(pref.read_text(encoding="utf-8"))
            mode = data.get("mode")
            if mode in BACKEND_ORDERS:
                return mode
        except Exception:
            pass
    return "local"  # safe default: local-first


def _call_aliyun(audio_path: Path, language: str | None) -> str:
    return transcribe_aliyun(audio_path, language)


def _call_funasr(audio_path: Path, language: str | None) -> str:
    return transcribe_funasr(audio_path, language)


def _call_openai(audio_path: Path, language: str | None) -> str:
    return transcribe_openai(audio_path, language)


def transcribe(video_path: Path, source_is_url: bool, language: str | None,
               forced: str | None, mode: str) -> str:
    work_dir = video_path.parent / "video-copy-audio"
    audio_path = extract_audio(video_path, work_dir)

    dispatch = {
        "funasr": lambda: _call_funasr(audio_path, language),
        "openai": lambda: _call_openai(audio_path, language),
        "aliyun": lambda: _call_aliyun(audio_path, language),
    }
    order = [forced] if forced else BACKEND_ORDERS.get(mode, DEFAULT_ORDER)

    errors: list[str] = []
    for name in order:
        fn = dispatch.get(name)
        if fn is None:
            warn(f"unknown backend: {name}")
            continue
        try:
            print(f"[backend] trying {name} ...", file=sys.stderr)
            text = fn()
            if text:
                print(f"[backend] {name} succeeded", file=sys.stderr)
                return text
            raise RuntimeError("empty transcript")
        except Exception as exc:  # noqa: BLE001 - fall through to next backend
            errors.append(f"{name}: {exc}")
            warn(f"{name} failed: {exc}")

    raise RuntimeError("all backends failed:\n" + "\n".join(errors))


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------
def build_output(transcript: str, source_label: str, video_path: Path, fmt: str, suggested: str | None) -> str:
    if fmt == "md":
        lines = [f"# {video_path.stem}", "", f"- Source: {source_label}", f"- Video: {video_path}"]
        if suggested:
            lines.append(f"- Suggested filename: {suggested}")
        lines.extend(["", "## Transcript", "", transcript or "(No speech transcript was produced.)", ""])
        return "\n".join(lines)
    lines = []
    if suggested:
        lines.append(f"Suggested filename: {suggested}")
    lines.extend([f"Source: {source_label}", f"Video: {video_path}", "", transcript or "(No speech transcript was produced.)", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--format", choices=("txt", "md"), default="txt")
    parser.add_argument("--out-dir")
    parser.add_argument("--download-dir")
    parser.add_argument("--language")
    parser.add_argument("--backend", choices=("aliyun", "funasr", "openai"),
                        help="Force a single backend (skip auto-fallback).")
    args = parser.parse_args()

    download_dir = Path(args.download_dir).expanduser().resolve() if args.download_dir else Path.cwd() / "video-copy-downloads"
    video_path, source_label = resolve_source(args.source, download_dir)
    mode = load_mode()
    transcript = transcribe(video_path, is_url(args.source), args.language, args.backend, mode).strip()
    suggested = suggest_filename(transcript, video_path.stem) if looks_meaningless(video_path.stem) else None
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else video_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = unique_path(out_dir / f"{video_path.stem}.{args.format}")
    output_path.write_text(build_output(transcript, source_label, video_path, args.format, suggested), encoding="utf-8")
    print(f"video_path={video_path}")
    print(f"transcript_path={output_path}")
    if suggested:
        print(f"suggested_filename={suggested}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
