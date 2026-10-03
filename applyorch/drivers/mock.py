"""Mock driver: a simulated ATS form that follows the computer-use workflow.

It performs the same steps a real computer-use agent performs (open the URL,
read the page, fill by label, attach the resume, take a fresh snapshot, run the
pre-submit gate) against a JSON form fixture, and records each step as a
trajectory of tool-like actions. Nothing leaves the machine.

Fixture quirks reproduce failure modes seen on real forms:
  "resume_upload": "sandboxed-picker"  the browser opens a non-native picker, upload fails
  "drops_value": ["Phone"]             a field silently rejects typed input
  "page_title": "..."                  the tab shows a different or closed role

Modes:
  dry-run      fill, verify, stop before Submit (never submits)
  mock-submit  fill, verify, and press Submit on the SIMULATED form only
"""
from __future__ import annotations

import json
import os

from ..fields import resolve
from ..gate import verify


class SimulatedForm:
    def __init__(self, spec: dict):
        self.spec = spec
        self.quirks = spec.get("quirks", {})
        self.values = {f["id"]: "" for f in spec["fields"]}
        self.resume_attached = False
        self.submitted = False

    def type_text(self, field_id: str, value: str):
        label = next(f["label"] for f in self.spec["fields"] if f["id"] == field_id)
        if label in self.quirks.get("drops_value", []):
            return  # the input swallowed the keystrokes
        self.values[field_id] = value

    def attach(self, path: str) -> bool:
        if self.quirks.get("resume_upload") == "sandboxed-picker":
            return False
        self.resume_attached = os.path.isfile(path)
        return self.resume_attached

    def snapshot(self) -> dict:
        return {
            "page_title": self.spec.get("page_title", ""),
            "resume_attached": self.resume_attached,
            "fields": [dict(label=f["label"], type=f.get("type", "text"),
                            required=bool(f.get("required")), legal=bool(f.get("legal")),
                            value=self.values[f["id"]]) for f in self.spec["fields"]],
        }

    def submit(self) -> str:
        missing = [f["label"] for f in self.spec["fields"]
                   if f.get("required") and not self.values[f["id"]] and f.get("type") != "file"]
        if missing or not self.resume_attached:
            raise RuntimeError(f"form refused submit: missing {missing}")
        self.submitted = True
        return self.spec.get("confirmation", "Application submitted")


class MockDriver:
    name = "mock"

    def __init__(self, forms_dir: str, mode: str = "dry-run"):
        if mode not in ("dry-run", "mock-submit"):
            raise ValueError(mode)
        self.forms_dir, self.mode = forms_dir, mode
        self.last_form = None

    def run(self, packet, expected: dict, resume_path: str, session: str,
            may_submit: bool) -> dict:
        trail = [f"start_session({session})", "launch_app(browser)", f"open({packet.apply_url})"]
        with open(os.path.join(self.forms_dir, f"{packet.key}.json"), encoding="utf-8") as fh:
            form = SimulatedForm(json.load(fh))
        self.last_form = form

        def done(status, problems=(), left=(), confirmation=""):
            trail.append(f"end_session({session})")
            return {"status": status, "problems": list(problems), "left_for_human": list(left),
                    "confirmation": confirmation, "trajectory": trail, "submitted": form.submitted}

        trail.append("get_window_state")
        for f in form.spec["fields"]:
            if f.get("legal") or f.get("type") == "file":
                continue
            value = resolve(f["label"], expected)
            if value is not None:
                form.type_text(f["id"], value)
                trail.append(f"type_text[{f['label']}]")
        trail.append("get_window_state  # verify values landed")

        trail.append("click[resume] -> open panel -> cmd+shift+g -> path -> return")
        if not form.attach(resume_path):
            trail.append("resume NOT attached")

        trail.append("get_window_state  # fresh snapshot for the pre-submit gate")
        result = verify(form.snapshot(), expected, packet.title)
        if result["problems"]:
            return done("STOPPED", result["problems"], result["left_for_human"])
        if self.mode == "dry-run" or not may_submit or result["left_for_human"]:
            return done("READY_FOR_HUMAN", (), result["left_for_human"])
        trail.append("click[Submit]")
        confirmation = form.submit()
        trail.append("get_window_state  # capture confirmation")
        return done("SUBMITTED", confirmation=confirmation)
