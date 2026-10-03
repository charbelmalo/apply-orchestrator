"""Truthfulness guardrails.

The profile is the single source of truth. Its ``truthfulness`` block lists
claims that must never appear (``never_claim``: regex -> reason). Every packet
is scanned before it can reach a browser; one hit blocks the application.

This is the post-generation scan, not a fact checker: it catches the specific
claims a human has already ruled out (an inflated title, a credential the
candidate doesn't hold, an excluded project). It cannot catch a new invention,
which is why the packet also carries an "Unverified claims I avoided" section
for the human reviewer.
"""
from __future__ import annotations

import re


def compile_rules(profile: dict) -> list[tuple[re.Pattern, str]]:
    rules = (profile.get("truthfulness") or {}).get("never_claim") or {}
    return [(re.compile(p, re.I), why) for p, why in rules.items()]


def scan_text(text: str, rules) -> list[str]:
    hits = []
    for pat, why in rules:
        for m in pat.finditer(text):
            hits.append(f"{m.group(0)!r}: {why}")
    return hits


def scan_packet(packet, profile: dict) -> list[str]:
    rules = compile_rules(profile)
    out = []
    for label, text in packet.prose():
        out += [f"{label}: {h}" for h in scan_text(text, rules)]
    return out
