"""Track outcomes from a local mbox file. No IMAP login, no network.

Confirmation emails are the only INDEPENDENT proof that an application went
through; a prefilled tab or an agent's report proves nothing on its own. Most
desktop mail clients (Thunderbird, for one) keep synced IMAP folders as plain
mbox files, so this reads the same bytes the client shows.

Only the tail of each mbox is scanned (messages are appended in arrival order),
which keeps multi-gigabyte archives cheap.
"""
from __future__ import annotations

import datetime as dt
import email
import email.header
import email.utils
import os
import re

DEFAULT_RECRUITING = (r"ashbyhq|greenhouse|lever\.co|workday|recruit|talent|hiring|"
                      r"careers?@|jobs@|application")

VERDICTS = [  # first match wins
    ("INTERVIEW", re.compile(r"interview|schedule|chat with|next step|availability|"
                             r"phone screen|hiring manager|meet the team", re.I)),
    ("REJECTED", re.compile(r"unfortunately|not (moving|proceed|be moving)|another candidate|"
                            r"decided not to|update on your application|no longer", re.I)),
    ("RECEIVED", re.compile(r"thank you for applying|thanks for applying|thanks for your "
                            r"application|application (received|submitted)|we.{0,5}ve received",
                            re.I)),
    ("ACCOUNT", re.compile(r"security code|verify|password|sign ?in|magic link", re.I)),
]
ORDER = {"INTERVIEW": 0, "REJECTED": 1, "RECEIVED": 2, "ACCOUNT": 3, "OTHER": 4}


def classify(subject: str) -> str:
    for label, pat in VERDICTS:
        if pat.search(subject or ""):
            return label
    return "OTHER"


def _decode(value) -> str:
    if not value:
        return ""
    try:
        return "".join(b.decode(c or "utf-8", "replace") if isinstance(b, bytes) else b
                       for b, c in email.header.decode_header(value))
    except Exception:
        return str(value)


def scan(path: str, since: dt.datetime, recruiting: str = DEFAULT_RECRUITING,
         tail_mb: int = 700) -> list[dict]:
    pat = re.compile(recruiting, re.I)
    if since.tzinfo is None:
        since = since.replace(tzinfo=dt.timezone.utc)
    hits = []

    def handle(chunk):
        if not chunk:
            return
        msg = email.message_from_bytes(b"".join(chunk))
        try:
            when = email.utils.parsedate_to_datetime(msg.get("Date"))
        except (TypeError, ValueError):
            return
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        sender, subject = _decode(msg.get("From")), _decode(msg.get("Subject"))
        if when < since or not pat.search(f"{sender} {subject}"):
            return
        hits.append({"when": when, "from": sender.strip(), "subject": subject.strip(),
                     "verdict": classify(subject)})

    size = os.path.getsize(path)
    start = max(0, size - tail_mb * 1024 * 1024)
    with open(path, "rb") as fh:
        fh.seek(start)
        if start:
            fh.readline()  # drop the partial line the seek landed in
        chunk = []
        for line in fh:
            if line.startswith(b"From ") and chunk:
                handle(chunk)
                chunk = [line]
            else:
                chunk.append(line)
        handle(chunk)

    seen, unique = set(), []
    for h in hits:  # mail clients sometimes store a message twice
        k = (h["from"], h["subject"], h["when"].strftime("%Y%m%d%H%M"))
        if k not in seen:
            seen.add(k)
            unique.append(h)
    unique.sort(key=lambda h: (ORDER[h["verdict"]], h["when"]))
    return unique


def report(hits: list[dict]) -> str:
    if not hits:
        return "No application mail in range."
    lines, current = [], None
    for h in hits:
        if h["verdict"] != current:
            current = h["verdict"]
            lines.append(f"\n-- {current} " + "-" * (60 - len(current)))
        lines.append(f"  {h['when']:%Y-%m-%d %H:%M}  {h['from'][:40]:40}  {h['subject'][:60]}")
    received = sum(1 for h in hits if h["verdict"] == "RECEIVED")
    interviews = sum(1 for h in hits if h["verdict"] == "INTERVIEW")
    lines.append(f"\n{len(hits)} messages. {received} confirmed submissions, "
                 f"{interviews} interview requests.")
    return "\n".join(lines)
