import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from tests.helpers import DEMO, ROOT, load
from applyorch import brief, notify, packets
from applyorch.drivers.mock import MockDriver
from applyorch.fields import expected_values
from applyorch.lock import BrowserBusy, browser_lock

FORMS = os.path.join(DEMO, "forms")


def pk(key):
    return packets.parse(os.path.join(DEMO, "packets", key + ".md"))


def drive(key, mode, may_submit=True, forms=FORMS):
    p = pk(key)
    drv = MockDriver(forms, mode)
    out = drv.run(p, expected_values(load("profile.json"), p), p.resume_path(ROOT),
                  "s", may_submit)
    return out, drv.last_form


class MockDriverTest(unittest.TestCase):
    def test_dry_run_never_submits(self):
        out, form = drive("quillfeather-fde-eval", "dry-run")
        self.assertEqual(out["status"], "READY_FOR_HUMAN")
        self.assertFalse(form.submitted)
        self.assertIn("get_window_state  # fresh snapshot for the pre-submit gate",
                      out["trajectory"])

    def test_mock_submit_after_gate(self):
        out, form = drive("quillfeather-fde-eval", "mock-submit")
        self.assertEqual(out["status"], "SUBMITTED")
        self.assertTrue(form.submitted)
        self.assertIn("Thank you for applying", out["confirmation"])

    def test_prefill_only_approval_stops(self):
        out, form = drive("quillfeather-fde-eval", "mock-submit", may_submit=False)
        self.assertEqual(out["status"], "READY_FOR_HUMAN")
        self.assertFalse(form.submitted)

    def test_resume_picker_quirk_stops(self):
        out, form = drive("lumen-orchard-applied-ai", "mock-submit")
        self.assertEqual(out["status"], "STOPPED")
        self.assertEqual(out["problems"], ["resume is not attached"])
        self.assertFalse(form.submitted)

    def test_dropped_keystrokes_stop(self):
        tmp = tempfile.mkdtemp()
        spec = load("forms", "quillfeather-fde-eval.json")
        spec["quirks"] = {"drops_value": ["Phone"]}
        with open(os.path.join(tmp, "quillfeather-fde-eval.json"), "w") as fh:
            json.dump(spec, fh)
        out, form = drive("quillfeather-fde-eval", "mock-submit", forms=tmp)
        self.assertEqual(out["status"], "STOPPED")
        self.assertIn("required field 'Phone' is empty", out["problems"][0])
        self.assertFalse(form.submitted)
        shutil.rmtree(tmp)

    def test_legal_field_leaves_submit_to_human(self):
        out, form = drive("harbor-pine-ml-platform", "mock-submit")
        self.assertEqual(out["status"], "READY_FOR_HUMAN")
        self.assertEqual(out["left_for_human"],
                         ["I attest that the information provided is accurate"])
        self.assertFalse(form.submitted)


class LockTest(unittest.TestCase):
    def test_second_driver_is_refused(self):
        tmp = tempfile.mkdtemp()
        with browser_lock(tmp):
            with self.assertRaises(BrowserBusy):
                with browser_lock(tmp):
                    pass
        with browser_lock(tmp):  # released afterwards
            pass
        shutil.rmtree(tmp)


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class NotifyTest(unittest.TestCase):
    KEY = "FAKEDEVICEKEY0000"

    def test_bark_url_and_redaction(self):
        calls = []
        n = notify.BarkNotifier("https://bark.example.com/" + self.KEY,
                                opener=lambda url, timeout: calls.append(url) or FakeResponse())
        self.assertTrue(n.send("Application sent", "Quillfeather Labs: FDE / Eval submitted"))
        self.assertEqual(calls[0], "https://bark.example.com/" + self.KEY +
                         "/Application%20sent/Quillfeather%20Labs%3A%20FDE%20%2F%20Eval%20submitted")
        self.assertNotIn(self.KEY, repr(n))

    def test_failure_never_prints_the_key(self):
        def boom(url, timeout):
            raise OSError("unreachable " + url)
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = notify.BarkNotifier("https://bark.example.com/" + self.KEY, opener=boom).send("t", "b")
        self.assertFalse(ok)
        self.assertNotIn(self.KEY, buf.getvalue())

    def test_channel_from_env(self):
        self.assertEqual(notify.from_env({"BARK_URL": "https://x.example.com/k"}).channel, "bark")
        self.assertEqual(notify.from_env({"NTFY_URL": "https://x.example.com/t"}).channel, "ntfy")
        self.assertEqual(notify.from_env({}).channel, "stdout")


class BriefTest(unittest.TestCase):
    def render(self, may_submit):
        p = pk("quillfeather-fde-eval")
        return brief.render(p, expected_values(load("profile.json"), p), "resume.pdf", "s1",
                            "com.example.Browser", may_submit)

    def test_placeholders_filled_and_minimal(self):
        t = self.render(True)
        self.assertNotIn("{{", t)
        self.assertIn('Role: "Forward Deployed Engineer, Evaluation Tooling" at Quillfeather Labs', t)
        self.assertIn("Resume file to upload: resume.pdf", t)
        self.assertIn("PRE-SUBMIT GATE", t)
        self.assertIn('If asked "Why Quillfeather Labs?"', t)
        self.assertNotIn("What this team wants", t, "reviewer scaffolding must not reach the agent")

    def test_prefill_only_brief_forbids_submit(self):
        self.assertIn("Do NOT click Submit", self.render(False))


if __name__ == "__main__":
    unittest.main()
