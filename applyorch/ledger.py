"""Submissions ledger: one JSONL line per orchestrated application, every outcome.

A submitted form proves nothing until the ATS confirmation arrives, so the
ledger keeps the exact confirmation text the driver saw, and ``track`` later
matches it against confirmation emails.
"""
from __future__ import annotations

import json
import os
from datetime import date


def append(path: str, result: dict, today: str | None = None) -> dict:
    row = {
        "date": today or date.today().isoformat(),
        "key": result["key"],
        "company": result["company"],
        "role": result["title"],
        "ats": result.get("ats", ""),
        "url": result.get("url", ""),
        "status": result["status"],
        "confirmation": result.get("confirmation", ""),
        "reasons": result.get("reasons", []),
    }
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def table(rows: list[dict]) -> str:
    out = ["| Date | Company | Role | ATS | Status | Confirmation |",
           "|------|---------|------|-----|--------|--------------|"]
    for r in rows:
        out.append(f"| {r['date']} | {r['company']} | {r['role']} | {r['ats']} | "
                   f"{r['status']} | {r['confirmation'] or '-'} |")
    return "\n".join(out)
