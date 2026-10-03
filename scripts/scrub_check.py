#!/usr/bin/env python3
"""Scan the repository for anything that should never be published.

    python3 scripts/scrub_check.py                         # generic patterns only
    python3 scripts/scrub_check.py --denylist ~/private/denylist.txt

Generic patterns: real-looking email addresses (anything outside the reserved
example.com / example.test domains), phone numbers outside the fictional
555-01xx range, absolute home-directory paths, and common token shapes (Hugging
Face, GitHub, sk- prefixed keys, Slack, AWS, Bark device keys, ntfy topics).

``--denylist`` points at a PRIVATE file kept outside the repo: one term per
line (your name variants, employers, companies you applied to, project names).
Terms are matched case-insensitively on word boundaries. The file itself is
never read into output; only counts are printed, never the matched text, so the
report is safe to paste anywhere.

Exit code 1 if anything is found.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "run", "private", "__pycache__", "node_modules"}

GENERIC = {
    "email (non-example domain)": re.compile(
        r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|test)\b)(?![a-z0-9-]+\.example\b)"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "phone (non-fictional)": re.compile(
        r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}(?:[\s.-]?\d{2,4})?"),
    "absolute home path": re.compile(r"/Users/[A-Za-z]|/home/[a-z]|C:\\\\Users\\\\"),
    "huggingface token": re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "sk- style api key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "slack token": re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}"),
    "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "bark device key in url": re.compile(r"api\.day\.app/(?!<)[A-Za-z0-9]{8,}"),
    "ntfy private topic": re.compile(r"ntfy\.sh/(?!<)[A-Za-z0-9_-]{12,}"),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "generic secret assignment": re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][^'\"<>{}\s]{12,}['\"]"),
}
FICTIONAL_PHONE = re.compile(r"\+1[\s.-]?555[\s.-]?01\d\d\b")


def files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    yield os.path.relpath(path, root), fh.read()
            except (UnicodeDecodeError, OSError):
                continue


def load_denylist(path: str) -> list[re.Pattern]:
    with open(os.path.expanduser(path), encoding="utf-8") as fh:
        terms = [t.strip() for t in fh if t.strip() and not t.startswith("#")]
    return [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I)
            for t in terms]


def scan(root: str = ROOT, denylist: str | None = None, self_path: str | None = None) -> dict:
    counts = {k: 0 for k in GENERIC}
    where = {k: set() for k in GENERIC}
    deny = load_denylist(denylist) if denylist else []
    deny_hits, deny_files = 0, set()
    me = os.path.relpath(self_path or os.path.abspath(__file__), root)
    for rel, text in files(root):
        for label, pat in GENERIC.items():
            if rel == me:
                continue  # this file's own pattern source
            for m in pat.finditer(text):
                if label.startswith("phone") and FICTIONAL_PHONE.match(m.group(0)):
                    continue
                counts[label] += 1
                where[label].add(rel)
        for pat in deny:
            n = len(pat.findall(text))
            if n:
                deny_hits += n
                deny_files.add(rel)
    return {"generic": counts, "where": where, "deny_terms": len(deny),
            "deny_hits": deny_hits, "deny_files": deny_files}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--denylist")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()
    r = scan(a.root, a.denylist)
    total = 0
    for label, n in r["generic"].items():
        total += n
        files_note = f"  in {sorted(r['where'][label])}" if n else ""
        print(f"{label:30} {n}{files_note}")
    if a.denylist:
        total += r["deny_hits"]
        print(f"{'private denylist':30} {r['deny_hits']} hits for {r['deny_terms']} terms"
              + (f"  in {sorted(r['deny_files'])}" if r["deny_hits"] else ""))
    print("CLEAN" if total == 0 else f"{total} finding(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
