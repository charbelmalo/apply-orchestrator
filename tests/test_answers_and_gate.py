import copy
import os
import unittest

from tests.helpers import DEMO, load
from applyorch import answers, gate, packets
from applyorch.fields import expected_values

P1 = packets.parse(os.path.join(DEMO, "packets", "quillfeather-fde-eval.md"))


class AnswersTest(unittest.TestCase):
    def test_greenhouse_mapping(self):
        job = load("questions", "greenhouse-quillfeather-4401.json")
        out = answers.build(job, load("profile.json"), P1, P1.resume)
        self.assertEqual(out["skip_legal"], ["question_5005"], "arbitration is never answered")
        self.assertEqual(out["select"], {"question_5004": "Yes"})
        self.assertTrue(out["long"]["question_5003"].startswith("Because evaluation"))
        self.assertEqual(out["long"]["question_5006"], P1.letter)
        self.assertEqual(out["text"]["question_5007"], "Within 30 days of an offer.")
        self.assertEqual(out["unmapped"], [])

    def test_unknown_required_question_is_surfaced(self):
        job = load("questions", "greenhouse-quillfeather-4401.json")
        job["questions"].append({"label": "Favourite sorting algorithm?", "required": True,
                                 "fields": [{"name": "question_9999", "type": "input_text"}]})
        out = answers.build(job, load("profile.json"), P1, P1.resume)
        self.assertEqual([u["name"] for u in out["unmapped"]], ["question_9999"])


def snapshot(**over):
    expected = expected_values(load("profile.json"), P1)
    snap = {"page_title": "Forward Deployed Engineer, Evaluation Tooling at Quillfeather Labs",
            "resume_attached": True,
            "fields": [
                {"label": "First Name", "required": True, "value": "Robin"},
                {"label": "Email", "required": True, "value": "robin.example@example.com"},
                {"label": "Why Quillfeather Labs?", "required": True,
                 "value": expected["Why Quillfeather Labs?"]},
                {"label": "Resume/CV", "type": "file", "required": True, "value": ""},
            ]}
    snap.update(over)
    return snap, expected


class GateTest(unittest.TestCase):
    def test_pass(self):
        snap, exp = snapshot()
        self.assertEqual(gate.verify(snap, exp, P1.title)["problems"], [])

    def test_each_failure_is_caught(self):
        snap, exp = snapshot(page_title="Office Coordinator at Quillfeather Labs")
        self.assertIn("page does not show", gate.verify(snap, exp, P1.title)["problems"][0])

        snap, exp = snapshot(resume_attached=False)
        self.assertEqual(gate.verify(snap, exp, P1.title)["problems"], ["resume is not attached"])

        snap, exp = snapshot()
        snap["fields"][1]["value"] = ""
        self.assertIn("required field 'Email' is empty",
                      gate.verify(snap, exp, P1.title)["problems"][0])

        snap, exp = snapshot()
        snap["fields"][0]["value"] = "Robyn"
        self.assertIn("holds 'Robyn'", gate.verify(snap, exp, P1.title)["problems"][0])

    def test_legal_fields(self):
        snap, exp = snapshot()
        snap["fields"].append({"label": "I agree to arbitration", "legal": True,
                               "required": True, "value": ""})
        r = gate.verify(snap, exp, P1.title)
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["left_for_human"], ["I agree to arbitration"])
        snap["fields"][-1]["value"] = "on"
        self.assertIn("legal field", gate.verify(snap, exp, P1.title)["problems"][0])


if __name__ == "__main__":
    unittest.main()
