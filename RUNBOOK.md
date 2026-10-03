# Runbook: running an application wave

How to run a wave end to end without re-deciding anything. Your real data lives outside
this repository (or in the git-ignored `private/` folder): a profile, packets, theses and
an approvals file shaped like the ones in `demo/`.

## 0. Standing decisions (settle once, then stop re-litigating)

1. **Location is a tag, not a filter.** Every role is tagged with its work-authorisation
   reality (shortlist buckets: apply-now, gated, demoted). Nothing is submitted blind.
2. **Draft everything, submit selectively.** Packets are cheap. Submits are not.
3. **Recurring discovery runs on no model at all.** `discover` is deterministic. A cheap
   model, or you, reads only the short digest it prints.
4. **Hybrid approval.** Simple forms you have approved as `auto-submit` may be submitted by
   the agent after the gate passes. Everything else is `prefill-only`: the agent fills,
   verifies and stops.
5. **Research before drafting.** Each packet carries a "what this team wants" block,
   written from the posting before the letter. Market hard, but only with true claims.
6. **The profile is the only source of facts.** If it isn't in the profile, it doesn't go
   in a packet.

## 1. Discover and shortlist

```bash
python3 -m applyorch discover --targets private/targets.json --roles run/roles.jsonl
python3 -m applyorch shortlist --roles run/roles.jsonl
```

Targets list `company`, `ats` (`greenhouse`, `ashby`, `lever`, or anything else for a
browser fallback) and the board `slug`. Scoring weights live in
`config/pipeline.example.json`; copy it and tune it to your lane.

To schedule it with no model involved, add a crontab line that runs `discover` daily and
writes the digest to a file. If you want a model to read the digest, keep its prompt tiny
and tell it not to draft, submit or email anything.

## 2. Write the packet and the thesis

- One packet per role: copy `templates/packet.template.md` to `private/packets/<role>.md`.
- One thesis per role in `private/theses.json`: what the role is decided on
  (`must_evidence`) and what the application must not open with (`do_not_lead_with`).
  Write it BEFORE the answers. Evidence is chosen because the argument needs it.
- List every claim you nearly made but couldn't verify under "Unverified claims I avoided".

## 3. Run the gates

```bash
python3 -m applyorch check --packets private/packets --profile private/profile.json \
  --theses private/theses.json
```

Fix every block and re-run. This is the revise loop: nothing reaches a browser until it is
clean. The gates are truthfulness guardrails (the profile's `never_claim` rules), the prose
lint (machine-written tells and letter length), same-company overlap, and the thesis check.

## 4. Approve

Add the role to `private/approvals.json` yourself:

```json
{"<role>": {"approved": true, "by": "me", "on": "2026-10-03", "mode": "prefill-only"}}
```

The orchestrator never writes this file.

## 5. Rehearse, then run

```bash
# rehearsal against your own simulated form fixtures, nothing leaves the machine
python3 -m applyorch run ... --forms private/forms --mode dry-run

# real run: gates, then one brief per approved role in run/briefs/
python3 -m applyorch run --packets private/packets --profile private/profile.json \
  --theses private/theses.json --approvals private/approvals.json --mode agent
```

Dispatch each brief to ONE computer-use subagent, strictly one after another. See
`docs/computer-use-recipe.md` for the wiring, the form workflow and the known resume-picker
snag. Validate your upload method before you trust an autonomous submit.

## 6. Record and notify

```bash
python3 -m applyorch record --packets private/packets --key <role> \
  --status SUBMITTED --confirmation "<exact confirmation text>"
```

Exactly one push notification per application actually sent, and only once the
confirmation text was seen. Set `BARK_URL` or `NTFY_URL` in the environment from your
keychain. Never write either to a tracked file, a log, or a chat.

## 7. Track

```bash
python3 -m applyorch track --mbox "<path to your mail client's synced INBOX mbox>" --since 2026-10-01
```

Confirmation emails are the only independent proof that a submit landed. Compare them with
the ledger in `run/ledger.jsonl`.

## 8. Holds

Put `hold: <reason>` in a packet's Role section when something must be verified first (for
example nationality or clearance eligibility for a public-sector role). A held packet never
reaches a browser, even if it is approved.

## 9. Before publishing anything from your private copy

```bash
python3 scripts/scrub_check.py --denylist ~/somewhere-private/denylist.txt
```

The denylist holds your name variants, employers, and every company you have applied to. It
stays outside the repository. Only counts are printed.
