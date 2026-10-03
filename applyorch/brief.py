"""Render the per-application brief handed to ONE computer-use subagent.

Minimal context on purpose: the role's field values, the letter, the resume
path, the URL and the workflow. Never the whole planning conversation, which
costs tokens and leaks unrelated material into a browser session.
"""
from __future__ import annotations

import os
import re

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "templates", "submit-agent-brief.md")


def render(packet, expected: dict, resume_path: str, session: str, browser: str,
           may_submit: bool, template_path: str = TEMPLATE) -> str:
    with open(template_path, encoding="utf-8") as fh:
        t = fh.read()
    t = re.sub(r"<!--.*?-->\n?", "", t, flags=re.S)
    questions = {q for q, _ in packet.qa}
    fields = "\n".join(f"- {k}: {v}" for k, v in expected.items()
                       if k != "Cover letter" and k not in questions)
    extra = "\n".join(f'- If asked "{q}", paste verbatim:\n"""\n{a}\n"""' for q, a in packet.qa)
    if may_submit:
        submit = "submit it, but only if the pre-submit gate passes."
        final = ("If the gate passed and no legal field is pending, click Submit, then "
                 "get_window_state to capture the confirmation text.")
    else:
        submit = "STOP before the final Submit. A human reviews and submits."
        final = "Do NOT click Submit. Leave the tab open and report READY-FOR-HUMAN."
    values = {
        "SUBMIT_INSTRUCTION": submit, "FINAL_STEP": final,
        "APPLY_URL": packet.apply_url, "ROLE_TITLE": packet.title, "COMPANY": packet.company,
        "SESSION": session, "BROWSER_BUNDLE_ID": browser, "FIELD_VALUES": fields,
        "RESUME_PATH": resume_path, "COVER_LETTER": packet.letter, "EXTRA_ANSWERS": extra,
    }
    for k, v in values.items():
        t = t.replace("{{" + k + "}}", v)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", t)
    if leftover:
        raise ValueError(f"unfilled placeholders in brief: {leftover}")
    return t
