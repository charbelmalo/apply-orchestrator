# apply-orchestrator

A job-application pipeline where the agent does the clicking and code does the checking.

Roles are discovered from public job boards without a model. Each application is drafted
as a reviewable packet and has to pass truthfulness, writing and positioning gates plus an
explicit human approval before any browser opens. Then one computer-use agent fills one
form, takes a fresh snapshot, and verifies every field before it is allowed to submit.

This is the automation layer I built for my own applications, published with every piece
of real data removed. The candidate, companies and postings in `demo/` are fictional.

```
 discover ──> shortlist ──> packet + thesis ──> quality gates ──> human approval ──> brief
 (public       (apply-now /   (one Markdown     guardrails        approvals.json     one per role,
  ATS JSON,     gated /        file per role)   prose lint        auto-submit or     minimal context
  no model)     demoted)                        positioning       prefill-only            │
                                  ^             same-co overlap                            v
                                  └──── revise ◀── BLOCKED                one computer-use agent,
                                                                          strictly one at a time
                                                                                     │
      track (mbox) <── ledger <── notify (one push per <── SUBMITTED <── pre-submit gate on a
                                  application sent)       STOPPED         FRESH form snapshot
                                                          READY_FOR_HUMAN
```

## Run the demo

Python 3.9+ and nothing else (standard library only). It runs offline: boards come from
fixtures, and forms are simulated.

```bash
python3 -m applyorch demo          # the whole pipeline, twice: dry-run and mock-submit
python3 -m unittest discover -s tests -t .
```

What the demo shows, with four fictional packets:

| Packet | dry-run | mock-submit | Why |
|---|---|---|---|
| `quillfeather-fde-eval` | READY_FOR_HUMAN | SUBMITTED | Clean and approved for auto-submit. Every field verified on the simulated form. One notification, one ledger row with the confirmation text. |
| `lumen-orchard-applied-ai` | STOPPED | STOPPED | The upload control opens a sandboxed picker (a snag seen on a real form). The gate sees no resume attached and refuses to submit. |
| `harbor-pine-data-eng` | BLOCKED | BLOCKED | The letter claims a PhD the profile rules out. The guardrail blocks it before any browser opens. |
| `harbor-pine-ml-platform` | AWAITING_APPROVAL | AWAITING_APPROVAL | Clean, but nobody approved it. |

It also discovers 7 roles from 3 fixture boards (Greenhouse, Ashby and Lever payload
shapes) and reports a 4th "bespoke" board as needing a browser fallback. It builds a
Greenhouse answers file that leaves the arbitration question for the applicant, and it
classifies a fictional inbox into received, interview and rejected.

## What the code enforces

These are code paths with tests, not instructions to a model:

- **Truthfulness guardrails.** The profile lists claims that must never appear (a
  credential, a team size, an unmeasured multiplier). One hit blocks the packet.
- **Prose lint.** Blocks dashes, lists of three, "not X but Y", stock AI vocabulary and
  contraction-free prose in anything a reviewer will read. Letters must be 240 to 400 words.
  Letters to the same company may not share an 8-word run.
- **Positioning thesis.** Each role has a thesis written before the answers. The evidence
  it requires must be present, and the opening 40 words of any answer may not lead with what
  it rules out.
- **Human approval.** Only `approvals.json`, written by a person, lets a role past the
  gates, and its `mode` decides whether the agent may press Submit at all.
- **Holds.** A packet marked `hold:` (for example, eligibility not yet verified) never
  reaches a browser.
- **Pre-submit gate.** Run on a fresh snapshot of the form, it checks the right role is on
  the page, every required field is filled, every known value matches exactly, and the
  resume is attached. Legal fields (arbitration, attestations) must be untouched. A form
  that has them is left for the applicant to submit.
- **One browser, one agent.** An exclusive lock makes a second concurrent run fail fast.
- **Notifications.** Exactly one push per application actually sent (Bark or ntfy, URL from
  the environment), fired only once the confirmation text was seen. The URL never reaches a
  log or the ledger.
- **Legal answers.** The Greenhouse answers builder never answers legal questions and lists
  any required question it can't map.

## What it does not do

- **This repository's code never presses Submit on a real website.** For a real
  application, `run --mode agent` runs every gate and writes a brief. You hand that brief to
  a computer-use subagent (I used a Claude Code subagent with a computer-use MCP server),
  which runs the same workflow and gate inside a real browser. The `mock-submit` mode
  presses Submit on a simulated form only.
- It does not generate letters or render PDFs. Packets are written by you, or by a model
  you then review. This layer checks them and gets them into forms.
- It does not mass-apply. It is built to slow a submit down until it is checked.

## Layout

```
applyorch/            the pipeline (stdlib Python)
  discover.py         public Greenhouse / Ashby / Lever boards -> scored, deduped roles.jsonl
  shortlist.py        apply-now / gated / demoted buckets
  packets.py          per-role Markdown packet parser (authoring notes stripped)
  guardrails.py       profile never_claim rules
  lint.py             prose tells, letter length, same-company overlap
  positioning.py      thesis check
  answers.py          Greenhouse question-label -> field-id answers (legal never answered)
  fields.py           form label -> expected value resolution
  gate.py             the pre-submit verification
  brief.py            renders templates/submit-agent-brief.md for one subagent
  drivers/mock.py     simulated forms with real-world quirks
  drivers/agent.py    hand-off to a computer-use subagent
  orchestrate.py      gates -> hold -> approval -> brief -> driver -> notify -> ledger
  notify.py           Bark / ntfy / stdout / mock outbox
  ledger.py, track.py submissions ledger, mbox outcome classifier
  lock.py             one-browser lock
templates/            subagent brief, packet template
config/               scoring and shortlist config, MCP wiring example
docs/                 computer-use recipe, including the resume-picker snag
tools/                Playwright prefill-and-stop for Greenhouse (not covered by tests)
demo/                 fictional candidate, boards, packets, forms, inbox
scripts/scrub_check.py  pre-publish scan for personal data and secrets
```

Running it on your own applications: see [RUNBOOK.md](RUNBOOK.md).

## Privacy

Real profiles, packets and approvals belong outside the repository or in the git-ignored
`private/` folder. Before publishing a copy, run
`python3 scripts/scrub_check.py --denylist <private file>`. It scans for real-looking
emails and phone numbers, home-directory paths and token shapes. The private denylist adds
your own terms (name variants, employers, companies applied to), and only counts are
printed. The test suite runs the generic scan on every run.

## Credits

This layer was built alongside a self-hosted copy of
[career-ops](https://github.com/santifer/career-ops) by Santiago Fernández de Valderrama
(santifer, MIT licence), an open-source job-search system. No code from career-ops is copied
here. Two ideas overlap: both poll the public Greenhouse, Ashby and Lever job-board APIs,
and both leave the final, binding parts of an application to the applicant. If you want
evaluation reports and CV rendering, use career-ops. This repository covers what happens
between an approved packet and a submitted form.

## Licence

MIT. See [LICENSE](LICENSE).
