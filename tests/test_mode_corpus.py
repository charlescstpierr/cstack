"""Historical refusals, unrelated constraints and quotations through the real hook."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = Path(os.environ.get("CSTACK_MODE_HOOK", ROOT / "plugins/cstack/hooks/mode.py"))
CORPUS = json.loads((ROOT / "tests/fixtures/mode-refusals.json").read_text())


class ModeCorpusTests(unittest.TestCase):
    def test_historical_refusals_and_session_lifecycle(self):
        finding = os.environ.get("CSTACK_MODE_FINDING")
        cases = [case for case in CORPUS if not finding or str(case["comment_id"]) == finding]
        self.assertTrue(cases, "unknown historical finding")
        for case in cases:
            with self.subTest(case=case["id"], finding=case["comment_id"]), tempfile.TemporaryDirectory() as data:
                env = dict(os.environ, PLUGIN_DATA=data)
                def submit(prompt=None):
                    event = {"session_id": "corpus", "hook_event_name": "SessionStart" if prompt is None else "UserPromptSubmit"}
                    event.update({"source": "resume"} if prompt is None else {"prompt": prompt})
                    result = subprocess.run([sys.executable, "-S", str(HOOK)], input=json.dumps(event),
                                            text=True, capture_output=True, env=env, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return bool(result.stdout.strip())
                if case["initially_active"]:
                    self.assertTrue(submit("$cstack:cstack Corrige ceci."))
                self.assertEqual(submit(case["prompt"]), case["expected_active"], case["prompt"])
                self.assertEqual(submit("Continue."), case["expected_active"])
                self.assertEqual(submit(), case["expected_active"])
                markers = list((Path(data) / "sessions").glob("*"))
                self.assertEqual(bool(markers), case["expected_active"])


if __name__ == "__main__":
    unittest.main()
