import os
import tempfile
import unittest

from tests.helpers import DEMO, load
from applyorch import guardrails, lint, packets, positioning

PK = os.path.join(DEMO, "packets")


def packet(key):
    return packets.parse(os.path.join(PK, key + ".md"))


class PacketParseTest(unittest.TestCase):
    def test_sections(self):
        p = packet("quillfeather-fde-eval")
        self.assertEqual(p.company, "Quillfeather Labs")
        self.assertEqual(p.ats, "greenhouse")
        self.assertEqual(p.apply_url, "https://boards.example.com/quillfeather/jobs/4401")
        self.assertEqual(p.fields["What is the earliest you could start?"],
                         "Within 30 days of an offer.")
        self.assertEqual([q for q, _ in p.qa][0], "Why Quillfeather Labs?")
        self.assertEqual(p.resume, "demo/resume/robin-example-resume.txt")

    def test_authoring_notes_never_reach_the_letter(self):
        p = packet("quillfeather-fde-eval")
        self.assertNotIn("words)", p.letter)
        self.assertNotIn("What this team wants", p.letter)
        self.assertTrue(p.letter.startswith("Dear Quillfeather Labs hiring team"))


class LintTest(unittest.TestCase):
    def test_flags_machine_tells(self):
        bad = ("Moreover, I am excited to leverage my skills — it is a pivotal moment. "
               "I would bring rigour, speed, and taste. It is not about code, but about people.")
        checks = {f["check"] for f in lint.blocking(lint.prose_tells(bad))}
        for c in ("em-dash", "ai-vocab", "tricolon", "not-x-but-y", "no-contractions"):
            self.assertIn(c, checks)

    def test_demo_letters_are_clean(self):
        for key in ("quillfeather-fde-eval", "lumen-orchard-applied-ai", "harbor-pine-ml-platform"):
            self.assertEqual(lint.lint_packet(packet(key))["blocks"], [], key)

    def test_length_bounds(self):
        self.assertIsNone(lint.letter_length("word " * 300))
        self.assertIn("100 words", lint.letter_length("word " * 100))

    def test_same_company_overlap_only(self):
        a, b = packet("harbor-pine-ml-platform"), packet("harbor-pine-ml-platform")
        b.key = "copy"
        self.assertEqual(len(lint.cross_overlap([a, b])), 1)
        c = packet("quillfeather-fde-eval")
        c.letter = a.letter  # identical text but a different company is not flagged
        self.assertEqual(lint.cross_overlap([a, c]), [])


class GuardrailTest(unittest.TestCase):
    def test_ruled_out_claim_blocks(self):
        hits = guardrails.scan_packet(packet("harbor-pine-data-eng"), load("profile.json"))
        self.assertEqual(len(hits), 1)
        self.assertIn("does not hold a PhD", hits[0])

    def test_clean_packet_passes(self):
        self.assertEqual(guardrails.scan_packet(packet("quillfeather-fde-eval"),
                                                load("profile.json")), [])


class PositioningTest(unittest.TestCase):
    def test_thesis_rules(self):
        p = packet("quillfeather-fde-eval")
        self.assertEqual(positioning.check(p, load("theses.json")[p.key]), [])
        self.assertIn("no positioning thesis", positioning.check(p, None)[0])
        fails = positioning.check(p, {"must_evidence": ["kubernetes"],
                                      "do_not_lead_with": ["Quillfeather"]})
        self.assertTrue(any("kubernetes" in f for f in fails))
        self.assertTrue(any("leads with" in f for f in fails))


if __name__ == "__main__":
    unittest.main()
