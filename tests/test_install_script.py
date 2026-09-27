import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "install.sh"
BASH = shutil.which("bash")

# Reproduit les sorties et erreurs de `codex plugin` observées avec codex-cli 0.157.1.
FAKE_CODEX = textwrap.dedent("""\
    import json, os, sys
    state_path = os.environ["FAKE_CODEX_STATE"]
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"source": None, "installed": False}
    args = sys.argv[1:]
    with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
        log.write(" ".join(args) + "\\n")
    def save():
        json.dump(state, open(state_path, "w"))
    def fail(message):
        print("Error: " + message, file=sys.stderr)
        sys.exit(1)
    if args == ["--version"]:
        print("codex-cli 0.157.1")
    elif args[:3] == ["plugin", "marketplace", "list"]:
        print("MARKETPLACE  ROOT\\ncstack       /root" if state["source"] else "No plugin marketplaces in scope.")
    elif args[:3] == ["plugin", "marketplace", "add"]:
        if state["source"] not in (None, args[3]):
            fail("marketplace 'cstack' is already added from a different source; remove it before adding this source")
        state["source"] = args[3]
        save()
        print("Added marketplace `cstack` from " + args[3] + ".")
    elif args[:3] == ["plugin", "marketplace", "upgrade"]:
        if state["source"] and state["source"].startswith("/"):
            fail("marketplace `cstack` is not configured as a Git marketplace")
    elif args[:3] == ["plugin", "marketplace", "remove"]:
        if not state["source"]:
            fail("marketplace `cstack` is not configured or installed")
        state["source"] = None
        save()
    elif args[:2] == ["plugin", "list"]:
        status = "installed, enabled  0.6.0" if state["installed"] else "not installed"
        print("PLUGIN         STATUS              VERSION  SOURCE")
        print("cstack@cstack  " + status + "    /root/plugins/cstack")
    elif args[:2] == ["plugin", "add"]:
        if not state["source"]:
            fail("marketplace `cstack` is not configured")
        state["installed"] = True
        save()
        print("Added plugin `cstack` from marketplace `cstack`.")
    elif args[:2] == ["plugin", "remove"]:
        state["installed"] = False
        save()
        print("Removed plugin `cstack` from marketplace `cstack`.")
    else:
        fail("unexpected arguments: " + " ".join(args))
""")

FAKE_GIT = "#!/bin/sh\n[ -z \"$FAKE_GIT_DENIED\" ]\n"


class InstallScriptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        codex = self.bin / "codex"
        codex.write_text("#!{}\n{}".format(sys.executable, FAKE_CODEX))
        git = self.bin / "git"
        git.write_text(FAKE_GIT)
        for tool in (codex, git):
            tool.chmod(0o755)
        self.state = root / "state.json"
        self.log = root / "codex.log"
        self.log.touch()

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *args, **env):
        environment = {
            **os.environ,
            "PATH": "{}{}{}".format(self.bin, os.pathsep, os.environ["PATH"]),
            "FAKE_CODEX_STATE": str(self.state),
            "FAKE_CODEX_LOG": str(self.log),
            **env,
        }
        return subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True, env=environment)

    def calls(self):
        return self.log.read_text().splitlines()

    def source(self):
        return json.loads(self.state.read_text())["source"]

    def test_install_adds_the_github_marketplace_then_the_plugin(self):
        result = self.run_script("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["plugin marketplace add charlescstpierr/cstack", "plugin add cstack@cstack"])
        self.assertIn("$cstack:cstack", result.stdout)

    def test_install_is_idempotent(self):
        self.run_script("install")
        result = self.run_script("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Changement de source", result.stdout)

    def test_ref_or_local_replaces_the_existing_source(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "v1.0.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Changement de source", result.stdout)
        self.assertEqual(self.source(), "charlescstpierr/cstack@v1.0.0")
        result = self.run_script("install", "--local")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.source(), str(REPO))

    def test_install_stops_before_codex_when_the_private_repo_is_unreachable(self):
        result = self.run_script("install", FAKE_GIT_DENIED="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("gh auth setup-git", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_missing_codex_is_reported(self):
        result = self.run_script("install", CSTACK_CODEX="codex-absent")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Codex CLI introuvable", result.stderr)

    def test_update_requires_an_installation(self):
        result = self.run_script("update")
        self.assertEqual(result.returncode, 1)
        self.assertIn("install.sh install", result.stderr)

    def test_update_pulls_git_sources_and_recopies_local_ones(self):
        self.run_script("install")
        result = self.run_script("update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-2:], ["plugin marketplace upgrade cstack", "plugin add cstack@cstack"])
        self.run_script("install", "--local")
        result = self.run_script("update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Source locale", result.stdout)

    def test_uninstall_removes_plugin_and_source_and_can_repeat(self):
        self.run_script("install")
        first = self.run_script("uninstall")
        second = self.run_script("uninstall")
        self.assertEqual((first.returncode, second.returncode), (0, 0), first.stderr + second.stderr)
        self.assertEqual(self.calls().count("plugin marketplace remove cstack"), 1)
        self.assertIn(".cstack/", first.stdout)

    def test_doctor_reports_the_plugin_status(self):
        missing = self.run_script("doctor")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("✗ plugin cstack@cstack : not installed", missing.stdout)
        self.run_script("install")
        installed = self.run_script("doctor")
        self.assertEqual(installed.returncode, 0, installed.stdout)
        self.assertIn("✓ plugin cstack@cstack : installed, enabled 0.6.0", installed.stdout)

    def test_invalid_arguments_are_rejected(self):
        self.assertEqual(self.run_script("bogus").returncode, 2)
        self.assertEqual(self.run_script("install", "--ref").returncode, 1)
        self.assertEqual(self.run_script("install", "--ref", "main", "--local").returncode, 1)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
