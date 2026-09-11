from pathlib import Path
import tempfile
import unittest

from reprokit import verify

ROOT = Path(__file__).resolve().parents[1]


class VerificationTests(unittest.TestCase):
    def test_demo_and_no_source_mutation(self):
        source = ROOT / "examples/before/pricing.py"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            result = verify(ROOT / "examples/before", ROOT / "examples/after",
                            ROOT / "examples/test_discount.py", Path(temp) / "result")
            self.assertEqual(result["status"], "verified_regression")
            self.assertTrue((Path(temp) / "result/report.md").exists())
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse((source.parent / "_reprokit_test.py").exists())

    def test_passing_before_is_not_reproduction(self):
        with tempfile.TemporaryDirectory() as temp:
            result = verify(ROOT / "examples/after", ROOT / "examples/after",
                            ROOT / "examples/test_discount.py", Path(temp) / "result")
            self.assertEqual(result["status"], "not_reproduced")

    def test_bad_import_is_environment_error(self):
        with tempfile.TemporaryDirectory() as temp:
            test = Path(temp) / "test_missing.py"
            test.write_text("import nonexistent_reprokit_dependency\n", encoding="utf-8")
            result = verify(ROOT / "examples/before", ROOT / "examples/after",
                            test, Path(temp) / "result")
            self.assertEqual(result["status"], "environment_error")

    def test_same_bug_stays_failing(self):
        with tempfile.TemporaryDirectory() as temp:
            result = verify(ROOT / "examples/before", ROOT / "examples/before",
                            ROOT / "examples/test_discount.py", Path(temp) / "result")
            self.assertEqual(result["status"], "still_failing")


if __name__ == "__main__":
    unittest.main()
