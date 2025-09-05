# -*- coding: utf-8 -*-
print(">>> env.py 로드됨", flush=True)

from pathlib import Path
import os
from dotenv import load_dotenv

def load_env() -> None:
    print(">>> load_env 함수 실행됨", flush=True)
    
    """
    .env 탐색 우선순위:
    1) 3TEAM/Python/Sentiment/.env
    2) 3TEAM/Python/.env
    3) 3TEAM/.env (옵션)
    """
    here = Path(__file__).resolve()
    candidates = [
        # here.parents[1] / ".env",  # 3TEAM/Python/Sentiment/.env
        here.parents[2] / ".env",  # 3TEAM/Python/.env
        here.parents[3] / ".env",  # 3TEAM/.env (있으면 로드)
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)

def env(name: str, default=None, required: bool=False):
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        raise RuntimeError(f"환경변수 {name} 가 비어있어요")
    return v
