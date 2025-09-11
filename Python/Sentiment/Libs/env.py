# -*- coding: utf-8 -*-
from pathlib import Path
import os
from dotenv import load_dotenv

print(">>> env.py loaded", flush=True)


def load_env() -> None:
    print(">>> load_env()", flush=True)
    """
    .env search order:
    1) 3TEAM/Python/.env
    2) 3TEAM/.env (optional)
    """
    here = Path(__file__).resolve()
    candidates = [
        # here.parents[1] / ".env",  # 3TEAM/Python/Sentiment/.env (optional)
        here.parents[2] / ".env",  # 3TEAM/Python/.env
        here.parents[3] / ".env",  # 3TEAM/.env
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)


def env(name: str, default=None, required: bool = False):
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Environment variable {name} is empty")
    return v

