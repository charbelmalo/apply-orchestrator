"""The orchestrator: every gate, in order, one application at a time.

For each packet:

  1. quality gates (offline, deterministic)
       truthfulness guardrails   claims the profile rules out
       prose lint                machine-written tells, letter length
       same-company overlap      recycled sentences across letters to one company
       positioning thesis        required evidence present, wrong opening absent
     any failure -> BLOCKED; revise the packet and re-run (the revise loop)
  2. hold                       e.g. eligibility not yet verified -> HELD
  3. human approval             approvals file must say approved -> else AWAITING_APPROVAL
                                approval mode "auto-submit" or "prefill-only" (hybrid approval)
  4. brief                      rendered for one computer-use subagent
  5. driver (under the browser lock, strictly sequential)
       fill -> fresh snapshot -> pre-submit gate -> STOPPED | READY_FOR_HUMAN | SUBMITTED
  6. notify                     only on SUBMITTED with confirmation text seen
  7. ledger                     every outcome, including the ones that stopped
"""
from __future__ import annotations

import json
import os

from . import brief, guardrails, ledger, lint, positioning
from .fields import expected_values
from .lock import browser_lock

ORDERED_STATUSES = ["SUBMITTED", "READY_FOR_HUMAN", "HANDED_OFF", "STOPPED",
                    "AWAITING_APPROVAL", "HELD", "BLOCKED"]


NOTES = {"READY_FOR_HUMAN": "every field verified; stopped before Submit",
         "HANDED_OFF": "brief written; dispatch to one computer-use subagent"}


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def quality_gates(packet, all_packets, profile: dict, theses: dict) -> list[str]:
    reasons = [f"guardrail: {h}" for h in guardrails.scan_packet(packet, profile)]
    reasons += [f"lint: {b}" for b in lint.lint_packet(packet)["blocks"]]
    reasons += [f"overlap: {o}" for o in lint.cross_overlap(all_packets)
                if o.startswith(packet.key + " ") or f"<-> {packet.key}:" in o]
    reasons += [f"positioning: {p}" for p in positioning.check(packet, theses.get(packet.key))]
    return reasons


def run(packets, profile: dict, theses: dict, approvals: dict, driver, notifier,
        workdir: str, repo_root: str, browser: str = "com.google.Chrome",
        today: str | None = None) -> list[dict]:
    os.makedirs(os.path.join(workdir, "briefs"), exist_ok=True)
    ledger_path = os.path.join(workdir, "ledger.jsonl")
    results = []

    for p in packets:  # sequential by construction; the lock enforces it across processes
        res = {"key": p.key, "company": p.company, "title": p.title, "ats": p.ats,
               "url": p.apply_url, "status": "", "reasons": [], "confirmation": "",
               "trajectory": [], "notified": False, "submitted": False}
        reasons = quality_gates(p, packets, profile, theses)
        approval = approvals.get(p.key) or {}
        if reasons:
            res.update(status="BLOCKED", reasons=reasons)
        elif p.hold:
            res.update(status="HELD", reasons=[f"hold: {p.hold}"])
        elif not approval.get("approved"):
            res.update(status="AWAITING_APPROVAL",
                       reasons=["no human approval recorded for this role"])
        else:
            may_submit = approval.get("mode") == "auto-submit"
            expected = expected_values(profile, p)
            resume = p.resume_path(repo_root)
            session = f"{p.key}-submit"
            text = brief.render(p, expected, resume, session, browser, may_submit)
            brief_path = os.path.join(workdir, "briefs", f"{p.key}.md")
            with open(brief_path, "w", encoding="utf-8") as fh:
                fh.write(text)
            with browser_lock(workdir):
                kwargs = {"brief_path": brief_path} if driver.name == "agent" else {}
                out = driver.run(p, expected, resume, session, may_submit, **kwargs)
            res.update(status=out["status"], reasons=out["problems"],
                       confirmation=out["confirmation"], trajectory=out["trajectory"],
                       left_for_human=out["left_for_human"], brief=brief_path,
                       submitted=out["submitted"])
            if out["status"] == "SUBMITTED" and out["confirmation"]:
                res["notified"] = notifier.send("Application sent",
                                                f"{p.company}: {p.title} submitted")
        ledger.append(ledger_path, res, today)
        results.append(res)
    return results


def summary(results: list[dict]) -> str:
    lines = [f"{'role':34} {'status':18} detail"]
    for r in results:
        detail = r["confirmation"] or (r["reasons"][0] if r["reasons"] else "") or \
            NOTES.get(r["status"], "")
        if r.get("left_for_human"):
            detail = (detail + " " if detail else "") + \
                     f"(left for the applicant: {', '.join(r['left_for_human'])})"
        lines.append(f"{r['key'][:34]:34} {r['status']:18} {detail[:90]}")
        for extra in r["reasons"][1:]:
            lines.append(f"{'':34} {'':18} {extra[:90]}")
    return "\n".join(lines)
