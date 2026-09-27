"""Hook de rappel du mode cstack : silencieux hors cstack, rappel à chaque message après activation."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins/cstack/hooks/mode.py"


class ModeHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, event, *, data=True, raw=None):
        env = {key: value for key, value in os.environ.items() if key not in {"PLUGIN_DATA", "CLAUDE_PLUGIN_DATA"}}
        if data:
            env["PLUGIN_DATA"] = str(self.data)
        result = subprocess.run([sys.executable, str(HOOK)], input=raw if raw is not None else json.dumps(event),
                                capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def prompt(self, text, session="s1"):
        return self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": session, "prompt": text})

    def test_silent_outside_cstack(self):
        self.assertEqual(self.prompt("Corrige ce bug."), "")
        self.assertEqual(self.run_hook({"hook_event_name": "SessionStart", "session_id": "s1", "source": "compact"}), "")

    def test_reminder_after_activation_on_every_turn_of_that_session_only(self):
        first = self.prompt("$cstack:cstack Corrige ce bug.")
        self.assertIn("Mode cstack actif", first)
        self.assertIn("runtime/base.md", first)
        self.assertEqual(self.prompt("Et ajoute un test."), first)
        self.assertEqual(self.prompt("Autre conversation.", session="s2"), "")
        # Le rappel reste court, comme le `reminder:` de pstack, bien sous la limite d'injection.
        self.assertLess(len(first.split()), 80)

    def test_stop_request_ends_the_reminder(self):
        self.prompt("$cstack:cstack Refactorise ce module.")
        self.assertEqual(self.prompt("Merci, arrête cstack maintenant."), "")
        self.assertEqual(self.prompt("Une question simple."), "")
        self.assertIn("Mode cstack actif", self.prompt("$cstack:cstack On reprend."))

    def test_reminder_survives_compaction_and_resume(self):
        self.prompt("$cstack:cstack Migration en plusieurs phases.")
        for source in ("compact", "resume"):
            text = self.run_hook({"hook_event_name": "SessionStart", "session_id": "s1", "source": source})
            self.assertIn("Mode cstack actif", text)
            self.assertIn(".cstack/", text)

    def test_failures_never_block_the_message(self):
        self.assertEqual(self.run_hook(None, raw="pas du json"), "")
        self.assertEqual(self.run_hook(None, raw="[]"), "")
        self.assertEqual(self.run_hook({"hook_event_name": "UserPromptSubmit", "prompt": "$cstack:cstack"}), "")
        self.assertEqual(self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": "s1",
                                        "prompt": "$cstack:cstack"}, data=False), "")

    def test_only_hashed_session_ids_are_stored(self):
        self.prompt("$cstack:cstack Travail.", session="../../évasion")
        stored = [path.name for path in (self.data / "sessions").iterdir()]
        self.assertEqual(len(stored), 1)
        self.assertRegex(stored[0], r"^[0-9a-f]{64}$")

    def test_hook_config_runs_only_this_script_on_two_events(self):
        config = json.loads((ROOT / "plugins/cstack/hooks/hooks.json").read_text())["hooks"]
        self.assertEqual(sorted(config), ["SessionStart", "UserPromptSubmit"])
        self.assertEqual(config["SessionStart"][0]["matcher"], "compact|resume")
        for groups in config.values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertEqual(hook["command"], 'python3 "${PLUGIN_ROOT}/hooks/mode.py"')


if __name__ == "__main__":
    unittest.main()
