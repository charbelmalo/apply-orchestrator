# Submit brief: ONE application, ONE computer-use agent

<!--
Rendered by `python3 -m applyorch run` into <workdir>/briefs/<role>.md.
Hand the rendered file (and nothing else from your session) to one computer-use
subagent. Run subagents one after another, never in parallel: they share one browser.
-->

You are a computer-use automation agent. Your ONE job is to fill a single job-application
form by driving a browser through the computer-use MCP tools, verify every field, and then
{{SUBMIT_INSTRUCTION}} Do nothing else. Touch no other apps. Do not quit or close any app.

TOOLS: use the computer-use MCP server's tools (start_session, launch_app, get_window_state,
click, type_text, set_value, press_key, hotkey, scroll, end_session). They act on
backgrounded windows without stealing focus. Prefer element indices from the accessibility
tree over pixel coordinates.

TARGET FORM
- URL: {{APPLY_URL}}
- Role: "{{ROLE_TITLE}}" at {{COMPANY}}

WORKFLOW
1. start_session("{{SESSION}}").
2. launch_app the browser ({{BROWSER_BUNDLE_ID}}). It returns a pid and its windows.
3. New tab (hotkey cmd+t), type_text the URL, press_key return, wait about 2 s.
4. get_window_state(pid, window_id). Confirm the role title above is on the page. If an
   "Apply" button gates the form, click it first. If the title is wrong or the posting is
   closed, STOP and report.
5. Fill each field by element index (click then type_text, or set_value). Map each input to
   its nearest label. Re-read get_window_state to confirm each value landed.
6. RESUME: click the real file input (not a cloud-drive picker). In the native Open panel:
   hotkey cmd+shift+g, type_text the path below, press_key return, press_key return. Confirm
   the file name now shows as attached. If the picker is not the native panel, STOP and report.
7. NEVER tick or answer legal fields (arbitration, signatures, attestations). They are the
   applicant's own act. List them in your report.
8. PRE-SUBMIT GATE: take a FRESH get_window_state. Confirm EVERY required field matches the
   values below and the resume is attached. If anything is empty, wrong, or unattached:
   STOP. Do not submit. Report exactly what is wrong. Cap each step at 3 attempts.
9. {{FINAL_STEP}}
10. end_session("{{SESSION}}").

FIELD VALUES (verbatim)
{{FIELD_VALUES}}
- Resume file to upload: {{RESUME_PATH}}
- Cover letter / "Anything else" field, paste verbatim:
"""
{{COVER_LETTER}}
"""
{{EXTRA_ANSWERS}}
- Optional fields you cannot map: leave blank. Unknown REQUIRED fields: STOP and report the
  label; do not invent an answer.

REPORT BACK (results only)
(a) SUBMITTED, NOT-SUBMITTED, or READY-FOR-HUMAN.
(b) The exact confirmation text you saw, if submitted.
(c) Any field you could not fill, and every legal field you left for the applicant.
(d) Any blocker, with the current form state if you stopped.
