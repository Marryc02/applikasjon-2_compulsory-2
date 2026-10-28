"""Configuration and paths. Secrets come only from the environment."""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent  # repo root
CONTEXT_DIR = ROOT / "harness" / "context"
OUT_DIR = ROOT / "out"
OSLO = ZoneInfo("Europe/Oslo")


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader: KEY=VALUE lines, does not override existing env vars."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


def get_secret(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None
