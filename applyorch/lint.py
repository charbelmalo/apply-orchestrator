"""Prose lints for everything a hiring panel will read.

Three checks, all deterministic:

* ``prose_tells``   machine-written tells (dashes, tricolons, "not X but Y",
                    stock vocabulary, no contractions). BLOCK findings fail.
* ``letter_length`` cover letters must sit in a normal range (default 240-400 words).
* ``cross_overlap`` two letters to the SAME company must not share 8-word runs;
                    a recruiter reading both would see the template.

Short fields (under 12 words) are skipped: a phone number or a URL has no
register to get wrong.
"""
from __future__ import annotations

import re

MIN_WORDS = 12

# (id, severity, pattern, why)
CHECKS = [
    ("em-dash", "BLOCK", re.compile("[—–]"),
     "Em/en dash. Use a comma, a full stop, or restructure."),
    ("tricolon", "BLOCK", re.compile(
        r"\b\w[\w'-]*(?:\s+\w[\w'-]*){0,3},\s+\w[\w'-]*(?:\s+\w[\w'-]*){0,3},\s+"
        r"(?:and|or)\s+\w"),
     "Three-item list. The rule of three is the loudest tell. Cut to two or split."),
    ("not-x-but-y", "BLOCK", re.compile(
        r"\bnot\s+(?:only\s+)?[\w' ]{3,40}?,?\s+but\s+(?:also\s+)?", re.I),
     "'not X, but Y' antithesis. Say the positive half."),
    ("ai-vocab", "BLOCK", re.compile(
        r"\b(delve|leverage|robust|seamless|testament|tapestry|underscore[sd]?|pivotal|"
        r"crucial|myriad|plethora|holistic|nuanced|multifaceted|resonate[sd]?|embark|realm|"
        r"landscape of|navigate the|moreover|furthermore|thereby|hereby)\b", re.I),
     "Vocabulary that clusters in generated text."),
    ("ai-phrase", "BLOCK", re.compile(
        r"(it'?s worth noting|that said,|at the end of the day|in today'?s|"
        r"i hope this (email |message )?finds you|reach out to|circle back|deep dive|"
        r"game.chang|cutting.edge|state.of.the.art)", re.I),
     "Stock connective or filler phrase."),
    ("hedge-superlative", "WARN", re.compile(
        r"\b(one of (a )?(very )?(small number|the few|the most)|genuinely|truly|"
        r"incredibly|deeply)\b", re.I),
     "Intensifier or hedged superlative. Usually deletable."),
    ("semicolon", "WARN", re.compile(r";"), "Semicolon. Use a full stop."),
]

CONTRACTIBLE = re.compile(
    r"\b(I would|I will|I have|I am|it is|that is|there is|do not|does not|did not|"
    r"cannot|will not|would not|is not|was not|were not|you are|they are|we are)\b", re.I)
CONTRACTION = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.I)


def prose_tells(text: str) -> list[dict]:
    findings = []
    for n, line in enumerate(text.splitlines(), 1):
        for cid, sev, pat, why in CHECKS:
            for m in pat.finditer(line):
                findings.append(dict(check=cid, severity=sev, line=n, hit=m.group(0).strip(),
                                     why=why))
    formal, casual = len(CONTRACTIBLE.findall(text)), len(CONTRACTION.findall(text))
    if formal and casual / max(formal + casual, 1) < 0.34:
        findings.append(dict(check="no-contractions", severity="BLOCK", line=0,
                             hit=f"{casual} contracted / {formal} expanded",
                             why="Expanded forms dominate. People contract: I'd, it's, don't."))
    return findings


def blocking(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f["severity"] == "BLOCK"]


def letter_length(letter: str, lo: int = 240, hi: int = 400) -> str | None:
    n = len(letter.split())
    return None if lo <= n <= hi else f"cover letter is {n} words (allowed {lo}-{hi})"


def shingles(text: str, n: int = 8) -> set:
    w = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def cross_overlap(packets) -> list[str]:
    """Flag shared 8-grams between letters addressed to the same company."""
    issues = []
    for i, a in enumerate(packets):
        for b in packets[i + 1:]:
            if a.company.lower() != b.company.lower() or not a.letter or not b.letter:
                continue
            shared = shingles(a.letter) & shingles(b.letter)
            if shared:
                issues.append(f"{a.key} <-> {b.key}: {len(shared)} shared 8-word runs "
                              f"in letters to the same company ({a.company})")
    return issues


def lint_packet(packet) -> dict:
    """All sendable prose in one packet -> {blocks: [...], warnings: [...]}."""
    blocks, warns = [], []
    for label, text in packet.prose():
        if len(text.split()) < MIN_WORDS:
            continue
        for f in prose_tells(text):
            (blocks if f["severity"] == "BLOCK" else warns).append(
                f"{label}: {f['check']} {f['hit']!r}")
    length = letter_length(packet.letter)
    if length:
        blocks.append(length)
    return {"blocks": blocks, "warnings": warns}
