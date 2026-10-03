"""Shortlist: split discovered roles into apply-now, gated and demoted buckets.

The point is ordering effort: submit first where the candidate can actually be
hired (location and work authorisation), and keep roles that need sponsorship or
are outside the candidate's lane visible but separate.
"""
from __future__ import annotations

import json
import re


def load_roles(path: str) -> list[dict]:
    rows, seen = [], set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            key = (r["company"], re.sub(r"[^a-z0-9]", "", r["title"].lower()))
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
    return rows


def bucket(role: dict, cfg: dict) -> str:
    viable = re.compile(cfg["viable_locations"], re.I)
    demote = re.compile(cfg["demote_titles"], re.I)
    gated = re.compile(cfg.get("gated_titles", r"(?!x)x"), re.I)
    loc, title = role.get("location") or "", role["title"]
    if demote.search(title):
        return "demoted"
    if gated.search(title):
        return "gated"
    if viable.search(loc) or not loc:
        return "now"
    return "gated"


def shortlist(roles: list[dict], cfg: dict) -> dict:
    out = {"now": [], "gated": [], "demoted": []}
    for r in roles:
        out[bucket(r, cfg)].append(r)
    for k in out:
        out[k].sort(key=lambda x: -x["score"])
    return out


def render(buckets: dict, n: int = 30) -> str:
    titles = {
        "now": "APPLY NOW (viable location, in lane)",
        "gated": "GATED (needs sponsorship or a credential; apply only where confirmed)",
        "demoted": "DEMOTED (outside this candidate's lane)",
    }
    lines = []
    for key in ("now", "gated", "demoted"):
        lst = buckets[key]
        lines.append(f"\n=== {titles[key]} ({len(lst)}) ===")
        for r in lst[:n]:
            star = "*" if r.get("priority") == "p1" else " "
            lines.append(f" {star}[{r['score']:>3}] {r['company'][:24]:<24} {r['title'][:52]:<52} "
                         f"{(r.get('location') or 'remote/unspecified')[:22]}")
    return "\n".join(lines)
