import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "plugins/cstack/skills/cstack/scripts/session-bridge.sh"


class SessionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        fake = self.directory / "agit"
        fake.write_text(
            '#!/usr/bin/env python3\n'
            'import json, os, sys\n'
            'with open(os.environ["AGIT_CALLS"], "a") as output:\n'
            '    output.write(json.dumps(sys.argv[1:]) + "\\n")\n'
            'sys.exit(int(os.environ.get("AGIT_EXIT", "0")))\n'
        )
        fake.chmod(0o755)
        self.calls = self.directory / "calls.jsonl"
        self.env = {**os.environ, "PATH": f'{self.directory}:{os.environ.get("PATH", "")}', "AGIT_CALLS": str(self.calls)}

    def invoke(self, *arguments, env=None):
        return subprocess.run(
            ["bash", str(BRIDGE), *arguments],
            capture_output=True,
            text=True,
            env=self.env if env is None else env,
        )

    def recorded(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_lineage_preview_does_not_import(self):
        result = self.invoke("lineage", "codex", "native-123", "charles/sessions@topic")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["import", "native-123", "--from", "codex", "--into", "charles/sessions@topic", "--propose-lineage"]])

    def test_import_uses_explicit_independent_lineage(self):
        result = self.invoke("import", "cursor", "native-123", "charles/sessions@topic", "independent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["import", "native-123", "--from", "cursor", "--into", "charles/sessions@topic", "--independent"]])

    def test_import_can_attach_to_a_selected_lineage(self):
        result = self.invoke("import", "codex", "native-123", "charles/sessions@topic", "onto", "a1b2c3d4")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["import", "native-123", "--from", "codex", "--into", "charles/sessions@topic", "--onto", "a1b2c3d4"]])

    def test_import_without_lineage_choice_is_refused(self):
        result = self.invoke("import", "codex", "native-123", "charles/sessions@topic")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.recorded(), [])

    def test_checkpoint_records_locally_without_push(self):
        result = self.invoke("checkpoint", "charles/sessions@topic", "reviewed the router")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["commit", "charles/sessions@topic", "--milestone=reviewed the router"]])

    def test_resume_preserves_native_fast_path_when_runtime_omitted(self):
        result = self.invoke("resume", "charles/sessions@topic")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["resume", "charles/sessions@topic"]])

    def test_fork_can_select_another_supported_runtime(self):
        result = self.invoke("fork", "charles/sessions@topic#2", "new-direction", "codex", "--accept-loss")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["fork", "charles/sessions@topic#2", "-b", "new-direction", "--resume", "--as", "codex"]])

    def test_cursor_target_is_refused_before_agit_runs(self):
        result = self.invoke("resume", "charles/sessions@topic", "cursor", "--accept-loss")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cursor", result.stderr)
        self.assertEqual(self.recorded(), [])

    def test_explicit_conversion_requires_loss_acknowledgment(self):
        for arguments in [("resume", "charles/sessions@topic", "codex"),
                          ("fork", "charles/sessions@topic#2", "new-direction", "claude-code")]:
            with self.subTest(arguments=arguments):
                result = self.invoke(*arguments)
                self.assertEqual(result.returncode, 2)
        self.assertEqual(self.recorded(), [])

    def test_acknowledged_resume_selects_target_runtime(self):
        result = self.invoke("resume", "charles/sessions@topic", "claude-code", "--accept-loss")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["resume", "charles/sessions@topic", "--as", "claude-code"]])

    def test_missing_explicit_target_is_refused_before_agit_runs(self):
        result = self.invoke("checkpoint", "topic", "summary")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.recorded(), [])

    def test_agit_failure_is_propagated(self):
        result = self.invoke("log", "charles/sessions@topic", env={**self.env, "AGIT_EXIT": "7"})
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.recorded(), [["log", "charles/sessions@topic"]])

    def test_missing_agit_reports_prerequisite(self):
        result = self.invoke("log", "charles/sessions@topic", env={**self.env, "PATH": "/usr/bin:/bin"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("agit", result.stderr)
        self.assertEqual(self.recorded(), [])


if __name__ == "__main__":
    unittest.main()
