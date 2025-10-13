# -*- coding: utf-8 -*-
"""Fetch the latest DART corpCode.xml and rewrite data/dart_corpcode.csv."""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import zipfile
from pathlib import Path
from typing import Iterable, Tuple
from xml.etree import ElementTree as ET

import requests


def load_dotenv_if_available() -> None:
    """Load .env using the pipeline helper when available."""
    try:
        from Python.pipeline.utils.env import load_dotenv_utf8sig, sanitize_environ_bom
    except Exception:
        return
    try:
        load_dotenv_utf8sig()
        sanitize_environ_bom()
    except Exception:
        pass


def project_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / ".env").exists() or (parent / "Python").exists():
            return parent
    return cur.parents[3]


def download_corpcode_xml(api_key: str) -> bytes:
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": api_key}, timeout=60)
    resp.raise_for_status()
    return resp.content


def parse_corpcode_zip(data: bytes) -> Iterable[Tuple[str, str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml_name = next((name for name in zf.namelist() if name.lower().endswith(".xml")), None)
        if xml_name is None:
            raise RuntimeError("corpCode.zip did not contain an XML file.")
        xml_bytes = zf.read(xml_name)
    root = ET.fromstring(xml_bytes)
    for element in root.findall("list"):
        corp_code = (element.findtext("corp_code") or "").strip()
        corp_name = (element.findtext("corp_name") or "").strip()
        stock_code = (element.findtext("stock_code") or "").strip()
        yield corp_code, corp_name, stock_code


def write_csv(path: Path, rows: Iterable[Tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.writer(fp)
        writer.writerow(["corp_code", "corp_name", "stock_code"])
        for corp_code, corp_name, stock_code in rows:
            writer.writerow([corp_code, corp_name, stock_code])


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_available()
    parser = argparse.ArgumentParser(description="Update data/dart_corpcode.csv using DART corpCode.xml")
    parser.add_argument("--output", type=Path, default=None, help="Output CSV path (default: data/dart_corpcode.csv)")
    args = parser.parse_args(argv)

    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        print("DART_API_KEY 환경변수가 필요합니다.", file=sys.stderr)
        return 2

    try:
        payload = download_corpcode_xml(api_key)
        rows = list(parse_corpcode_zip(payload))
    except Exception as exc:
        print(f"[update_corpcode] Failed to download/parse corpCode.xml: {exc}", file=sys.stderr)
        return 1

    rows.sort(key=lambda r: (0 if r[2] else 1, r[2], r[0]))

    output_path = args.output or (project_root() / "data" / "dart_corpcode.csv")
    try:
        write_csv(output_path, rows)
    except Exception as exc:
        print(f"[update_corpcode] Failed to write CSV: {exc}", file=sys.stderr)
        return 1

    print(f"[update_corpcode] Saved {len(rows)} rows -> {output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

