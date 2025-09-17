# -*- coding: utf-8 -*-
from pathlib import Path
import os
from dotenv import load_dotenv

print(">>> env.py loaded", flush=True)


def load_env() -> None:
    print(">>> load_env()", flush=True)
    """
    .env is located in the project root directory (3TEAM).
    """
    here = Path(__file__).resolve()
    # Path to 3TEAM/.env
    p = here.parents[3] / ".env"
    if p.exists():
        load_dotenv(p, override=False)


def env(name: str, default=None, required: bool = False):
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"Environment variable {name} is empty")
    return v

