#!/usr/bin/env python3
"""One-shot installer for the local (FunASR) backend of video-copy-extractor.

Run this with a Python 3.11+ interpreter the first time a user chooses the
*local* version. It creates a self-contained venv inside the skill directory
and installs FunASR + CPU-only PyTorch. Idempotent: safe to re-run.

Usage (agent side)::

    py -3.11 -m venv "<skill-dir>/.venv"
    "<skill-dir>/.venv/Scripts/python.exe" "<skill-dir>/setup_local.py"

Or simply::

    py -3.11 "<skill-dir>/setup_local.py"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
VENV_DIR = SKILL_DIR / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    if not VENV_DIR.exists():
        print(f"[setup] creating venv at {VENV_DIR}")
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print(f"[setup] venv already exists at {VENV_DIR}, reusing")

    run([str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"])
    # CPU-only PyTorch (smaller download, no CUDA needed)
    run(
        [
            str(VENV_PY), "-m", "pip", "install",
            "--index-url", "https://download.pytorch.org/whl/cpu",
            "torch", "torchaudio",
        ]
    )
    # FunASR (Alibaba Damo Academy) for local speech-to-text
    run([str(VENV_PY), "-m", "pip", "install", "funasr", "oss2"])

    # sanity check
    run([str(VENV_PY), "-c", "import funasr, torch, oss2; print('funasr', funasr.__version__, '| torch', torch.__version__)"])
    print(f"\n[setup] done. Local backend installed at {VENV_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
