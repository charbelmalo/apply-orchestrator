# Computer-use recipe: driving a real ATS form

This is what the subagent brief (`templates/submit-agent-brief.md`) asks a computer-use
agent to do, with the field notes that came out of running it against real Ashby and
Greenhouse forms. Nothing in this repository's code performs these steps on a live site;
`applyorch/drivers/mock.py` performs them against simulated forms so the gate logic is
tested.

## Wiring

1. Install a computer-use MCP server that can read the macOS accessibility tree and act on
   backgrounded windows (it should expose tools like `start_session`, `launch_app`,
   `get_window_state`, `click`, `type_text`, `set_value`, `press_key`, `hotkey`,
   `end_session`). Grant it Accessibility and Screen Recording permissions.
2. Register it with your agent host. `config/mcp.example.json` shows the shape; replace the
   placeholders. For Claude Code, `claude mcp add` or a project `.mcp.json` works.
3. Check the subagent can actually see the tools before trusting a run: ask it to call
   `get_screen_size` and nothing else.

## One application, one subagent, one at a time

- `python3 -m applyorch run --mode agent ...` runs every offline gate and writes
  `run/briefs/<role>.md` for each approved role.
- Dispatch ONE brief to ONE subagent. A cheaper model is fine for the clicking: the
  judgement already happened in the packet and the gates.
- Wait for its report before dispatching the next. Two agents in one browser clobber each
  other's focus and fields, and these submits are irreversible.
- Give the subagent only the brief. The planning conversation is irrelevant to it and
  leaks material into a browser session.
- Record the outcome: `python3 -m applyorch record --key <role> --status SUBMITTED
  --confirmation "<exact text>"`. That appends to the ledger and fires the notification.

## The form workflow

1. `start_session("<role>-submit")`, then `launch_app` the browser. It returns a pid and
   its windows.
2. New tab (`cmd+t`), type the apply URL, `return`, wait about 2 s.
3. `get_window_state(pid, window_id)` for the accessibility tree with element indices.
   Confirm the role title is on the page. Click an "Apply" gate if there is one.
4. Fill each field by element index. Re-read the tree to confirm each value landed: some
   inputs swallow keystrokes (React-controlled fields, typeaheads).
5. Resume: click the real file input, then in the native Open panel `cmd+shift+g`, type the
   path, `return`, `return`. Confirm the file name shows as attached.
6. Pre-submit gate: a FRESH `get_window_state`. Every required field matches, resume
   attached, legal fields untouched. Anything off means stop and report.
7. Only if approved for autonomous submit: click Submit, then read the confirmation text.
8. `end_session`.

## Known snag: the resume picker

On one Chromium-based browser, clicking an Ashby "Upload File" control opened a
sandboxed directory picker instead of the native macOS Open panel, so `cmd+shift+g` did
nothing and the dialog ignored keyboard and pointer input. The gate caught it (resume not
attached) and the run stopped without submitting, which is the intended behaviour. The
demo reproduces it with the `sandboxed-picker` quirk in
`demo/forms/lumen-orchard-applied-ai.json`.

Validate an upload method before trusting autonomous submit. In order of preference:

1. Use a browser that shows the native Open panel for `<input type=file>`.
2. Make sure the click hit the real file input, not a cloud-drive picker beside it.
3. Drag the file onto the drop zone with the computer-use `drag` tool.
4. Fallback: a human attaches the resume once and the agent fills everything else.

## Greenhouse without computer use

Greenhouse field ids are stable once resolved, so `python3 -m applyorch answers` plus
`tools/greenhouse-prefill.mjs` (Playwright) can prefill a posting and stop, leaving the
legal boxes and the Submit click to the applicant.

## Never

- Never POST to an ATS's private application endpoint. Submit through the real form.
- Never tick arbitration, signature or attestation fields.
- Never defeat a CAPTCHA or anti-bot check. Stop and hand over.
- Never run two browser agents at once.
