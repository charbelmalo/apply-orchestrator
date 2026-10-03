"""Resolve the label a form shows to the value the candidate gives.

Expected values = the profile's ``standard_fields`` overridden by the packet's
``Form fields`` table, plus the cover letter. Form labels vary per ATS ("LinkedIn
profile URL", "Do you require visa sponsorship?"), so each canonical label
carries a few alias patterns. Unknown labels resolve to ``None`` and are left
blank unless the field is required, in which case the gate stops the run.
"""
from __future__ import annotations

import re

DEFAULT_ALIASES = {
    "First name": [r"^first name", r"given name"],
    "Last name": [r"^last name", r"surname", r"family name"],
    "Full name": [r"^full name", r"^name$", r"^your name"],
    "Email": [r"e-?mail"],
    "Phone": [r"phone", r"mobile"],
    "LinkedIn": [r"linkedin"],
    "Website": [r"website", r"portfolio", r"personal site"],
    "GitHub": [r"github", r"code samples?"],
    "Location": [r"location", r"city", r"where are you based"],
    "Current company": [r"current (company|employer)"],
    "Current title": [r"current (title|role|position)"],
    "Work authorization": [r"sponsor", r"work authori[sz]ation", r"right to work", r"visa"],
    "How did you hear about us": [r"how did you hear", r"referr?al source", r"where did you find"],
    "Years of experience": [r"years of (relevant )?experience"],
    "Salary expectation": [r"salary", r"compensation expectation"],
    "Cover letter": [r"cover letter", r"anything else", r"additional information"],
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def expected_values(profile: dict, packet) -> dict:
    values = dict(profile.get("standard_fields") or {})
    values.update(packet.fields)
    for question, answer in packet.qa:
        values.setdefault(question, answer)
    if packet.letter:
        values["Cover letter"] = packet.letter
    return values


def resolve(label: str, values: dict, aliases: dict | None = None) -> str | None:
    aliases = aliases or DEFAULT_ALIASES
    low = norm(label)
    for canon, value in values.items():
        if norm(canon) == low:
            return value
    for canon, patterns in aliases.items():
        if canon in values and any(re.search(p, low) for p in patterns):
            return values[canon]
    for canon, value in values.items():  # packet-specific labels, matched loosely
        if len(canon) > 6 and norm(canon) in low:
            return value
    return None
