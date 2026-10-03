"""Positioning gate: does this application argue for the job being hired?

A perfectly human-sounding application can still argue for the wrong
candidate, and nobody writes back to say you were mispositioned. So every role
gets a thesis, written BEFORE the answers, and this check enforces its
deterministic half:

* ``must_evidence``     markers the thesis says the role is decided on; each
                        must appear somewhere in the sendable prose.
* ``do_not_lead_with``  terms allowed later but never in the first 40 words of
                        any answer (the opening move).

It cannot judge tone or emphasis; ``predicted_title`` is printed for a human
to disagree with.
"""
from __future__ import annotations

LEAD_WORDS = 40


def check(packet, thesis: dict | None) -> list[str]:
    if thesis is None:
        return ["no positioning thesis: nothing decided what argument this application makes"]
    fields = [(label, text) for label, text in packet.prose() if len(text.split()) >= 12]
    corpus = "\n".join(t for _, t in fields).lower()
    failures = []
    for marker in thesis.get("must_evidence") or []:
        if marker.lower() not in corpus:
            failures.append(f"missing required evidence: {marker!r}")
    for term in thesis.get("do_not_lead_with") or []:
        for label, text in fields:
            lead = " ".join(text.split()[:LEAD_WORDS]).lower()
            if term.lower() in lead:
                failures.append(f"leads with {term!r} in {label} (allowed later, never in the "
                                f"first {LEAD_WORDS} words)")
    return failures
