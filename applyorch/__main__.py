"""Command line: python3 -m applyorch <command> ...

  discover   fetch boards (or --fixtures), append new scored roles
  shortlist  bucket discovered roles: apply-now / gated / demoted
  check      run every quality gate over the packets (exit 1 on any block)
  answers    build a Greenhouse answers file from a posting's question list
  run        orchestrate packets through approval, brief, driver, notify, ledger
  record     record an agent-reported outcome (ledger + notification)
  track      classify application mail from a local mbox
  demo       the whole pipeline on the fictional demo data, offline
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

from . import answers, discover, ledger, notify, orchestrate, packets, shortlist, track
from .drivers.agent import AgentDriver
from .drivers.mock import MockDriver
from .notify import OutboxNotifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demo")
CONFIG = os.path.join(ROOT, "config", "pipeline.example.json")


def _load(path):
    return orchestrate.load_json(path)


def cmd_discover(a):
    cfg = _load(a.config)["discovery"]
    res = discover.discover(_load(a.targets), cfg, a.roles, a.fixtures)
    print(discover.digest(res))
    return 0


def cmd_shortlist(a):
    cfg = _load(a.config)["shortlist"]
    print(shortlist.render(shortlist.shortlist(shortlist.load_roles(a.roles), cfg)))
    return 0


def cmd_check(a):
    pk = packets.load_all(a.packets)
    profile, theses = _load(a.profile), _load(a.theses)
    bad = 0
    for p in pk:
        reasons = orchestrate.quality_gates(p, pk, profile, theses)
        print(f"{p.key:34} {'clean' if not reasons else str(len(reasons)) + ' BLOCK'}")
        for r in reasons:
            print(f"    x {r}")
        bad += bool(reasons)
    return 1 if bad else 0


def cmd_answers(a):
    p = packets.parse(a.packet)
    out = answers.build(_load(a.job), _load(a.profile), p, p.resume)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"{out['title']}: text={len(out['text'])} select={len(out['select'])} "
          f"long={len(out['long'])} legal-skipped={len(out['skip_legal'])} "
          f"UNMAPPED-REQUIRED={len(out['unmapped'])}")
    return 1 if out["unmapped"] else 0


def _driver(mode, forms):
    return AgentDriver() if mode == "agent" else MockDriver(forms, mode)


def cmd_run(a):
    cfg = _load(a.config)
    pk = packets.load_all(a.packets)
    if a.only:
        pk = [p for p in pk if p.key in a.only]
    mock = a.mode != "agent"
    notifier = OutboxNotifier(os.path.join(a.workdir, "outbox.jsonl")) if mock \
        else notify.from_env()
    os.makedirs(a.workdir, exist_ok=True)
    res = orchestrate.run(pk, _load(a.profile), _load(a.theses), _load(a.approvals),
                          _driver(a.mode, a.forms), notifier, a.workdir, ROOT,
                          cfg.get("browser", {}).get("bundle_id", "com.google.Chrome"))
    print(orchestrate.summary(res))
    return 0


def cmd_record(a):
    p = packets.parse(os.path.join(a.packets, a.key + ".md"))
    res = {"key": p.key, "company": p.company, "title": p.title, "ats": p.ats,
           "url": p.apply_url, "status": a.status, "confirmation": a.confirmation or "",
           "reasons": [a.note] if a.note else []}
    ledger.append(os.path.join(a.workdir, "ledger.jsonl"), res)
    if a.status == "SUBMITTED" and a.confirmation:
        notify.from_env().send("Application sent", f"{p.company}: {p.title} submitted")
    print(f"recorded {p.key}: {a.status}")
    return 0


def cmd_track(a):
    since = dt.datetime.fromisoformat(a.since) if a.since else \
        dt.datetime.now() - dt.timedelta(days=30)
    print(track.report(track.scan(a.mbox, since)))
    return 0


def demo(workdir: str) -> dict:
    """Run every stage on the fictional data. Returns what happened, for tests."""
    cfg = _load(CONFIG)
    os.makedirs(workdir, exist_ok=True)
    roles_path = os.path.join(workdir, "roles.jsonl")
    found = discover.discover(_load(os.path.join(DEMO, "targets.json")), cfg["discovery"],
                              roles_path, os.path.join(DEMO, "boards"))
    buckets = shortlist.shortlist(shortlist.load_roles(roles_path), cfg["shortlist"])

    profile = _load(os.path.join(DEMO, "profile.json"))
    pk = packets.load_all(os.path.join(DEMO, "packets"))
    theses = _load(os.path.join(DEMO, "theses.json"))
    approvals = _load(os.path.join(DEMO, "approvals.json"))
    p1 = next(p for p in pk if p.key == "quillfeather-fde-eval")
    gh = answers.build(_load(os.path.join(DEMO, "questions", "greenhouse-quillfeather-4401.json")),
                       profile, p1, p1.resume)

    runs = {}
    for mode in ("dry-run", "mock-submit"):
        wd = os.path.join(workdir, mode)
        drv = MockDriver(os.path.join(DEMO, "forms"), mode)
        runs[mode] = orchestrate.run(pk, profile, theses, approvals, drv,
                                     OutboxNotifier(os.path.join(wd, "outbox.jsonl")), wd, ROOT,
                                     cfg["browser"]["bundle_id"])
    mail = track.scan(os.path.join(DEMO, "inbox.mbox"), dt.datetime(2026, 9, 1))
    return {"discover": found, "shortlist": buckets, "answers": gh, "runs": runs, "mail": mail,
            "workdir": workdir}


def cmd_demo(a):
    tmp = None
    workdir = a.workdir
    if not workdir:
        tmp = workdir = tempfile.mkdtemp(prefix="applyorch-demo-")
    try:
        out = demo(workdir)
        print("== 1. discover (offline fixtures) ==")
        print(discover.digest(out["discover"]))
        print("\n== 2. shortlist ==")
        print(shortlist.render(out["shortlist"]))
        g = out["answers"]
        print("\n== 3. Greenhouse answers for quillfeather-fde-eval ==")
        print(f"text={len(g['text'])} select={len(g['select'])} long={len(g['long'])} "
              f"legal-skipped={g['skip_legal']} unmapped={len(g['unmapped'])}")
        for mode, res in out["runs"].items():
            print(f"\n== 4. orchestrate, mode={mode} (simulated forms, nothing leaves "
                  f"this machine) ==")
            print(orchestrate.summary(res))
        sent = os.path.join(workdir, "mock-submit", "outbox.jsonl")
        print("\n== 5. notifications (mock outbox) ==")
        print(open(sent).read().strip() if os.path.exists(sent) else "(none)")
        print("\n== 6. track (fictional inbox) ==")
        print(track.report(out["mail"]))
        print("\n== ledger (mock-submit run) ==")
        print(ledger.table(ledger.read(os.path.join(workdir, "mock-submit", "ledger.jsonl"))))
    finally:
        if tmp and not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="applyorch", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("discover")
    s.add_argument("--targets", required=True)
    s.add_argument("--roles", default="run/roles.jsonl")
    s.add_argument("--config", default=CONFIG)
    s.add_argument("--fixtures", help="read boards from this dir instead of the network")
    s.set_defaults(fn=cmd_discover)

    s = sub.add_parser("shortlist")
    s.add_argument("--roles", default="run/roles.jsonl")
    s.add_argument("--config", default=CONFIG)
    s.set_defaults(fn=cmd_shortlist)

    s = sub.add_parser("check")
    s.add_argument("--packets", required=True)
    s.add_argument("--profile", required=True)
    s.add_argument("--theses", required=True)
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("answers")
    s.add_argument("--job", required=True, help="Greenhouse job JSON fetched with ?questions=true")
    s.add_argument("--packet", required=True)
    s.add_argument("--profile", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_answers)

    s = sub.add_parser("run")
    for flag in ("--packets", "--profile", "--theses", "--approvals"):
        s.add_argument(flag, required=True)
    s.add_argument("--forms", help="form fixtures (mock modes)")
    s.add_argument("--config", default=CONFIG)
    s.add_argument("--workdir", default="run")
    s.add_argument("--mode", choices=["dry-run", "mock-submit", "agent"], default="dry-run")
    s.add_argument("--only", nargs="*")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("record")
    s.add_argument("--packets", required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--status", required=True,
                   choices=["SUBMITTED", "READY_FOR_HUMAN", "STOPPED", "NOT_SUBMITTED"])
    s.add_argument("--confirmation")
    s.add_argument("--note")
    s.add_argument("--workdir", default="run")
    s.set_defaults(fn=cmd_record)

    s = sub.add_parser("track")
    s.add_argument("--mbox", required=True)
    s.add_argument("--since")
    s.set_defaults(fn=cmd_track)

    s = sub.add_parser("demo")
    s.add_argument("--workdir")
    s.add_argument("--keep", action="store_true")
    s.set_defaults(fn=cmd_demo)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
