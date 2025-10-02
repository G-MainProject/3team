# -*- coding: utf-8 -*-
"""프로젝트 내 텍스트 파일을 UTF-8(무 BOM)으로 일괄 정규화하고,
파이썬 파일에 UTF-8 코딩 쿠키를 추가하는 유틸리티.

사용 예시(프로젝트 루트):
  python scripts/normalize_utf8.py --apply
  python scripts/normalize_utf8.py --dry-run

대상 경로 기본값:
  - Python/pipeline/**
  - scripts/**

대상 확장자:
  .py, .json, .yaml, .yml, .md, .txt
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


TARGET_DIRS = [
    Path("Python/pipeline"),
    Path("scripts"),
]

EXTS = {".py", ".json", ".yaml", ".yml", ".md", ".txt"}


def iter_files(roots: Iterable[Path]):
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in EXTS:
                yield p


def detect_and_read(path: Path) -> str | None:
    # 시도할 인코딩 우선순위: UTF-8-SIG -> UTF-8 -> CP949 -> EUC-KR -> ISO-8859-1
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr", "iso-8859-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return None


def ensure_python_coding_cookie(text: str) -> str:
    # 첫/둘째 줄 중에 코딩 쿠키가 없으면 첫 줄에 추가
    # PEP 263 준수 (shebang이 첫 줄일 때는 둘째 줄에 배치 가능)
    lines = text.splitlines()
    cookie = "# -*- coding: utf-8 -*-"
    has_cookie = any("coding:" in (lines[i] if i < len(lines) else "") for i in (0, 1))
    if has_cookie:
        return text
    if lines and lines[0].startswith("#!"):
        return "\n".join([lines[0], cookie, *lines[1:]]) + ("\n" if text.endswith("\n") else "")
    return cookie + "\n" + text


def normalize_file(path: Path, *, apply: bool) -> tuple[bool, str]:
    raw = detect_and_read(path)
    if raw is None:
        return False, "unreadable"
    normalized = raw
    # 파이썬 파일은 코딩 쿠키 보강
    if path.suffix == ".py":
        normalized = ensure_python_coding_cookie(normalized)
    # 줄바꿈 LF 통일
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    # UTF-8로만 저장 (BOM 제거 효과는 utf-8로 다시 쓰는 것으로 해결)
    changed = normalized != raw
    if apply and changed:
        path.write_text(normalized, encoding="utf-8", newline="\n")
    return changed, "ok"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="UTF-8(무 BOM) 일괄 정규화")
    p.add_argument("--apply", action="store_true", help="변경사항을 실제로 저장")
    p.add_argument("--dry-run", action="store_true", help="변경 여부만 출력")
    p.add_argument("--root", action="append", type=Path, help="추가 탐색 루트 경로")
    args = p.parse_args(argv)

    roots = list(TARGET_DIRS)
    if args.root:
        roots += list(args.root)

    total = 0
    changed = 0
    for f in iter_files(roots):
        total += 1
        chg, status = normalize_file(f, apply=args.apply and not args.dry_run)
        if chg:
            changed += 1
            print(f"[changed] {f}")
    print(f"Processed {total} files. Changed {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

