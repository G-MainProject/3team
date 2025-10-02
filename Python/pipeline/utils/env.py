# -*- coding: utf-8 -*-
"""Environment file loader with UTF-8-SIG and BOM sanitization.

- Reads .env as UTF-8 with optional BOM (utf-8-sig)
- Ignores comments and empty lines
- Parses KEY=VALUE pairs, strips surrounding quotes
- Sanitizes stray BOM (\ufeff) from keys and values already present in os.environ

Usage:
  from Python.pipeline.utils.env import load_dotenv_utf8sig, sanitize_environ_bom
  load_dotenv_utf8sig()  # idempotent
  sanitize_environ_bom()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

_ENV_LOADED = False


def _project_root_from(path: Path) -> Path:
    cur = path.resolve()
    for p in cur.parents:
        if (p / ".env").exists() or (p / "data").exists() or (p / "Python").exists():
            return p
    return cur.parents[4]


def load_dotenv_utf8sig(path: str | Path = ".env") -> None:
    """Load .env with utf-8-sig, set defaults into os.environ (idempotent)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    p = Path(path)
    if not p.is_absolute():
        # try from project root first
        root = _project_root_from(Path(__file__))
        candidate = root / str(path)
        if candidate.exists():
            p = candidate
    if not p.exists():
        _ENV_LOADED = True
        return
    try:
        text = p.read_text(encoding="utf-8-sig")
    except Exception:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            _ENV_LOADED = True
            return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'").lstrip("\ufeff")
        if key and (key not in os.environ):
            os.environ[key] = value
    sanitize_environ_bom()
    _ENV_LOADED = True


def sanitize_environ_bom(keys: Iterable[str] | None = None) -> None:
    """Remove stray BOM from env keys/values. Copies value to a clean key if needed.

    If a key includes BOM and the clean key is empty, copy the value and keep the
    original for backward safety; subsequent code should read the clean key.
    """
    targets = list(keys) if keys is not None else list(os.environ.keys())
    for k in targets:
        v = os.environ.get(k)
        if v is None:
            continue
        clean_k = k.replace("\ufeff", "")
        clean_v = v.replace("\ufeff", "")
        if clean_k != k and clean_k and clean_k not in os.environ:
            os.environ[clean_k] = clean_v
        elif clean_v != v:
            os.environ[k] = clean_v

