"""Regression tests: MARS observer does not treat missing workers as executed."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from scripts.wealth_loop_readiness import assess, main


class ReadinessTests(unittest.TestCase):
    def test_absent_worker_blocked(self):
        with TemporaryDirectory() as td:
            result = assess(Path(td))
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(result["worker_source_present"])
            self.assertEqual(result["worker_state"], "missing")
            self.assertFalse(result["production_readiness"])

    def test_present_worker_still_not_approved(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "src/nexus/sync_wealth_loop.py"
            path.parent.mkdir(parents=True)
            path.write_text("print('not executed')\n", encoding="utf-8")
            result = assess(Path(td))
            self.assertTrue(result["worker_source_present"])
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["independent_approval_receipt"], "not_verified")
            self.assertFalse(result["production_readiness"])
            self.assertEqual(result["agents_executed"], 0)

    def test_symlink_is_not_accepted_as_worker_evidence(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            outside = base / "other.py"
            outside.write_text("print('no')\n", encoding="utf-8")
            path = base / "src/nexus/sync_wealth_loop.py"
            path.parent.mkdir(parents=True)
            path.symlink_to(outside)
            self.assertFalse(assess(base)["worker_source_present"])

    def test_report_is_machine_readable_and_no_side_effects(self):
        with TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            self.assertEqual(main(["--repo-root", td, "--output", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["messages_sent"], 0)
            self.assertEqual(report["payments_attempted"], 0)
            self.assertEqual(report["durable_dispatch_receipt"], "not_verified")

    def test_missing_root_rejected(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                assess(Path(td) / "missing")


if __name__ == "__main__":
    unittest.main()
