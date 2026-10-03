"""The pre-submit gate: verify the form as it actually is, field by field.

This runs on a FRESH snapshot of the form (for a computer-use agent, a new
accessibility-tree read taken after filling), never on what the agent believes
it typed. Any problem means the agent stops, reports, and does not submit.

Checks:
  1. the page shows the role being applied for (wrong-tab / closed-posting guard)
  2. every required field is filled
  3. every field with a known expected value holds exactly that value
  4. the resume is attached
  5. legal fields (arbitration, attestations) are untouched; they're the
     applicant's own act, so a form that has them is left for a human to submit
"""
from __future__ import annotations

from .fields import norm, resolve


def verify(snapshot: dict, expected: dict, role_title: str) -> dict:
    """snapshot = {page_title, fields: [{label, type, required, value, legal}], resume_attached}

    Returns {"problems": [...], "left_for_human": [...]}. Empty problems = pass.
    """
    problems, left = [], []
    if norm(role_title) not in norm(snapshot.get("page_title", "")):
        problems.append(f"page does not show the role {role_title!r} "
                        f"(saw {snapshot.get('page_title', '')!r})")

    for f in snapshot.get("fields", []):
        label, value = f["label"], f.get("value")
        if f.get("legal"):
            if value:
                problems.append(f"legal field {label!r} was touched; only the applicant may")
            elif f.get("required"):
                left.append(label)
            continue
        if f.get("type") == "file":
            continue
        want = resolve(label, expected)
        if f.get("required") and not value:
            problems.append(f"required field {label!r} is empty"
                            + ("" if want is not None else " and has no known answer"))
            continue
        if want is not None and value and norm(value) != norm(want):
            problems.append(f"field {label!r} holds {str(value)[:40]!r}, expected "
                            f"{str(want)[:40]!r}")

    if not snapshot.get("resume_attached"):
        problems.append("resume is not attached")
    return {"problems": problems, "left_for_human": left}
