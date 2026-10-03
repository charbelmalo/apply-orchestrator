import os
import tempfile
import unittest

from tests.helpers import DEMO, config, load
from applyorch import discover, shortlist


class DiscoverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.roles = os.path.join(self.tmp, "roles.jsonl")
        self.cfg = config()

    def run_once(self):
        return discover.discover(load("targets.json"), self.cfg["discovery"], self.roles,
                                 os.path.join(DEMO, "boards"), now="2026-10-03T00:00:00Z")

    def test_normalises_all_three_ats_shapes(self):
        gh = discover.normalize("A", "greenhouse", load("boards", "greenhouse-quillfeather.json"))
        ab = discover.normalize("B", "ashby", load("boards", "ashby-lumen-orchard.json"))
        lv = discover.normalize("C", "lever", load("boards", "lever-harbor-pine.json"))
        self.assertEqual(gh[0]["location"], "London, UK")
        self.assertEqual(gh[0]["team"], "Applied AI")
        self.assertEqual(ab[0]["team"], "Agents")
        self.assertEqual(lv[1]["title"], "ML Platform Engineer")
        self.assertTrue(all(r["url"].startswith("https://") for r in gh + ab + lv))

    def test_threshold_dedupe_and_bespoke_failure(self):
        first = self.run_once()
        titles = {r["title"] for r in first["new"]}
        self.assertIn("Forward Deployed Engineer, Evaluation Tooling", titles)
        self.assertNotIn("Office Coordinator", titles)           # below threshold
        self.assertNotIn("Software Engineering Intern", titles)  # junior penalty
        self.assertEqual([c for c, _ in first["failed"]], ["Saltmarsh Robotics"])
        self.assertEqual(first["new"][0]["score"], max(r["score"] for r in first["new"]))
        second = self.run_once()
        self.assertEqual(second["new"], [], "a second sweep must append nothing")

    def test_shortlist_buckets(self):
        self.run_once()
        b = shortlist.shortlist(shortlist.load_roles(self.roles), self.cfg["shortlist"])
        now = {r["title"] for r in b["now"]}
        gated = {r["title"] for r in b["gated"]}
        demoted = {r["title"] for r in b["demoted"]}
        self.assertIn("Applied AI Engineer", now)
        self.assertIn("Senior ML Inference Engineer", gated)          # US-only location
        self.assertIn("Research Scientist, Interpretability", gated)  # credential-gated title
        self.assertIn("Technical Program Manager, Model Evaluation", demoted)


if __name__ == "__main__":
    unittest.main()
