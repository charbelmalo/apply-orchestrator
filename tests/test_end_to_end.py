"""The mock run: every stage of the pipeline on the fictional demo data, offline."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import DEMO, ROOT, load
from applyorch import orchestrate, packets, track
from applyorch.__main__ import demo
from applyorch.drivers.mock import MockDriver
from applyorch.notify import OutboxNotifier

EXPECTED = {
    "dry-run": {"quillfeather-fde-eval": "READY_FOR_HUMAN",
                "lumen-orchard-applied-ai": "STOPPED",
                "harbor-pine-data-eng": "BLOCKED",
                "harbor-pine-ml-platform": "AWAITING_APPROVAL"},
    "mock-submit": {"quillfeather-fde-eval": "SUBMITTED",
                    "lumen-orchard-applied-ai": "STOPPED",
                    "harbor-pine-data-eng": "BLOCKED",
                    "harbor-pine-ml-platform": "AWAITING_APPROVAL"},
}


class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="applyorch-test-")
        cls.out = demo(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_statuses(self):
        for mode, want in EXPECTED.items():
            got = {r["key"]: r["status"] for r in self.out["runs"][mode]}
            self.assertEqual(got, want, mode)

    def test_nothing_submitted_in_dry_run(self):
        self.assertFalse(any(r["submitted"] for r in self.out["runs"]["dry-run"]))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "dry-run", "outbox.jsonl")))

    def test_exactly_one_notification_per_sent_application(self):
        with open(os.path.join(self.tmp, "mock-submit", "outbox.jsonl")) as fh:
            lines = [json.loads(x) for x in fh]
        self.assertEqual(len(lines), 1)
        self.assertIn("Quillfeather Labs", lines[0]["body"])

    def test_ledger_records_every_outcome(self):
        for mode in EXPECTED:
            with open(os.path.join(self.tmp, mode, "ledger.jsonl")) as fh:
                rows = [json.loads(x) for x in fh]
            self.assertEqual(len(rows), 4)
        sent = [r for r in rows if r["status"] == "SUBMITTED"]
        self.assertTrue(sent[0]["confirmation"].startswith("Thank you for applying"))

    def test_briefs_only_for_gated_and_approved_roles(self):
        briefs = sorted(os.listdir(os.path.join(self.tmp, "mock-submit", "briefs")))
        self.assertEqual(briefs, ["lumen-orchard-applied-ai.md", "quillfeather-fde-eval.md"])

    def test_hold_beats_approval(self):
        pk = [packets.parse(os.path.join(DEMO, "packets", "quillfeather-fde-eval.md"))]
        pk[0].hold = "verify work-authorization eligibility first"
        wd = os.path.join(self.tmp, "hold")
        res = orchestrate.run(pk, load("profile.json"), load("theses.json"),
                              load("approvals.json"), MockDriver(os.path.join(DEMO, "forms"),
                                                                 "mock-submit"),
                              OutboxNotifier(os.path.join(wd, "outbox.jsonl")), wd, ROOT)
        self.assertEqual(res[0]["status"], "HELD")

    def test_discovery_answers_and_tracking_ran(self):
        self.assertEqual(len(self.out["discover"]["new"]), 7)
        self.assertEqual(self.out["answers"]["skip_legal"], ["question_5005"])
        verdicts = sorted(h["verdict"] for h in self.out["mail"])
        self.assertEqual(verdicts, ["INTERVIEW", "RECEIVED", "REJECTED"])

    def test_cli_demo_exits_zero(self):
        r = subprocess.run([sys.executable, "-m", "applyorch", "demo"], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SUBMITTED", r.stdout)


class TrackTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(track.classify("Thanks for applying!"), "RECEIVED")
        self.assertEqual(track.classify("Next steps: interview availability"), "INTERVIEW")
        self.assertEqual(track.classify("Unfortunately we won't proceed"), "REJECTED")
        self.assertEqual(track.classify("Weekend sale"), "OTHER")

    def test_cutoff_and_noise(self):
        hits = track.scan(os.path.join(DEMO, "inbox.mbox"), dt.datetime(2026, 7, 1))
        self.assertEqual(len(hits), 4)  # the August message now counts, the sale never does
        self.assertFalse(any("sale" in h["subject"].lower() for h in hits))


class ScrubTest(unittest.TestCase):
    def test_repository_is_clean(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import scrub_check
        r = scrub_check.scan(ROOT)
        self.assertEqual({k: v for k, v in r["generic"].items() if v}, {})

    def test_detectors_fire(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import scrub_check
        samples = {
            "email (non-example domain)": "someone" + "@" + "mail-provider.org",
            "phone (non-fictional)": "+44 " + "20 7946 0958",
            "absolute home path": "/Use" + "rs/someone/file",
            "huggingface token": "hf" + "_" + "a" * 30,
            "github token": "gh" + "p_" + "b" * 30,
            "bark device key in url": "api.day" + ".app/" + "C" * 20,
        }
        for label, text in samples.items():
            self.assertTrue(scrub_check.GENERIC[label].search(text), label)
        self.assertIsNone(scrub_check.GENERIC["email (non-example domain)"].search(
            "robin" + "@" + "example.com"))


if __name__ == "__main__":
    unittest.main()
