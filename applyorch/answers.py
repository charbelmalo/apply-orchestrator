"""Build an answers file for a Greenhouse posting from its public question list.

Question ids differ per posting, so every custom question is matched on its
LABEL and resolved to that posting's own field id. Rules come from the profile
(``answer_rules``), never from code.

Legal questions (arbitration, signatures, attestations) are never answered.
They're legally binding and are the applicant's own act, so they go into
``skip_legal`` and the human ticks them. Required questions no rule covers go
into ``unmapped`` and block the run until someone writes an answer.

Public endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{id}?questions=true
"""
from __future__ import annotations

import re

STANDARD = {"first_name", "last_name", "email", "phone", "resume", "resume_text",
            "cover_letter", "cover_letter_text"}


def build(job: dict, profile: dict, packet, resume_path: str) -> dict:
    rules = profile.get("answer_rules") or {}
    text_rules = [(re.compile(p, re.I), v) for p, v in (rules.get("text") or {}).items()]
    select_rules = [(re.compile(p, re.I), v) for p, v in (rules.get("select") or {}).items()]
    legal = re.compile(rules.get("legal", r"arbitrat|signature|attest"), re.I)
    ident = profile["identity"]

    out = {"job_id": job.get("id"), "title": job.get("title"),
           "url": job.get("absolute_url", ""), "resume": resume_path,
           "text": {"first_name": ident["first_name"], "last_name": ident["last_name"],
                    "email": ident["email"], "phone": ident["phone"]},
           "select": {}, "long": {}, "skip_legal": [], "unmapped": []}

    qa = {q.lower(): a for q, a in packet.qa}
    for q in job.get("questions", []):
        label = (q.get("label") or "").strip()
        low = label.lower()
        for f in q.get("fields", []):
            name, typ = f.get("name"), f.get("type")
            if name in STANDARD:
                continue
            if legal.search(low):
                out["skip_legal"].append(name)
                continue
            if re.search(r"cover letter|additional information|anything else", low):
                out["long"][name] = packet.letter
                continue
            match = next((a for qq, a in qa.items() if qq and (qq in low or low in qq)), None)
            if match and typ == "textarea":
                out["long"][name] = match
                continue
            hit = next((v for pat, v in text_rules if pat.search(low)), None)
            if hit is not None and typ in ("input_text", "textarea"):
                out["text"][name] = hit
                continue
            hit = next((v for pat, v in select_rules if pat.search(low)), None)
            if hit is not None and typ == "multi_value_single_select":
                options = [v.get("label") for v in f.get("values", [])]
                if hit in options:
                    out["select"][name] = hit
                    continue
            if q.get("required"):
                out["unmapped"].append({"name": name, "type": typ, "label": label})
    return out
