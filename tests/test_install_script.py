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

# Reproduit les sorties JSON et les erreurs de `codex plugin` observées avec codex-cli 0.157.1.
FAKE_CODEX = textwrap.dedent("""\
    import json, os, sys
    state_path = os.path.join(os.environ["CODEX_HOME"], "state.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"source": None, "installed": False}
    args = sys.argv[1:]
    with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
        log.write(" ".join(args) + "\\n")
    def save():
        json.dump(state, open(state_path, "w"))
    def fail(message):
        print("Error: " + message, file=sys.stderr)
        sys.exit(1)
    def source_type():
        return "local" if state["source"].startswith("/") else "git"
    if args == ["--version"]:
        if os.environ.get("FAKE_CODEX_VERSION_FAILS"):
            fail("error while loading shared libraries")
        print("codex-cli 0.157.1")
    elif args[:3] == ["plugin", "marketplace", "list"]:
        if os.environ.get("FAKE_CODEX_LIST_FAILS"):
            fail("failed to read config.toml")
        url = state["source"].split(" ")[0] if state["source"] else None
        entries = [{"name": "cstack", "root": "/codex/marketplaces/cstack",
                    "marketplaceSource": {"sourceType": source_type(), "source": url}}] if url else []
        print(json.dumps({"marketplaces": entries}))
    elif args[:3] == ["plugin", "marketplace", "add"]:
        source = " ".join(args[3:])
        # Hypothèse la plus défavorable : le conflit de source est signalé avant la validation de la ref.
        if state["source"] not in (None, source):
            fail("marketplace 'cstack' is already added from a different source; remove it before adding this source")
        if source.endswith("--ref missing"):
            fail("git checkout missing failed with status exit status: 1")
        # Réussit dans le CODEX_HOME d'essai, échoue dans le vrai : une panne entre l'essai et l'ajout.
        if source.endswith("--ref flaky") and os.environ["CODEX_HOME"] == os.environ["FAKE_MAIN_HOME"]:
            fail("failed to clone: connection reset")
        state["source"] = source
        save()
        print("Added marketplace `cstack` from " + source + ".")
    elif args[:3] == ["plugin", "marketplace", "upgrade"]:
        if "--ref 4ca420f" in (state["source"] or ""):
            fail("git ls-remote returned empty output for marketplace source")
        if state["source"] and source_type() == "local":
            fail("marketplace `cstack` is not configured as a Git marketplace")
    elif args[:3] == ["plugin", "marketplace", "remove"]:
        if not state["source"]:
            fail("marketplace `cstack` is not configured or installed")
        state["source"] = None
        save()
    elif args[:2] == ["plugin", "list"]:
        if os.environ.get("FAKE_CODEX_LIST_FAILS"):
            fail("marketplace `cstack` is not configured")
        entry = {"pluginId": "cstack@cstack", "installed": state["installed"], "enabled": state["installed"], "version": "0.6.0"}
        listed = [entry] if state["source"] else []
        print(json.dumps({"installed": [e for e in listed if e["installed"]],
                          "available": [e for e in listed if not e["installed"]]}))
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

# `git ls-remote <url> HEAD` : FAKE_GIT_DENY liste les transports refusés (https, ssh).
FAKE_GIT = textwrap.dedent("""\
    #!/bin/sh
    # `git -C <clone> symbolic-ref` : le clone de Codex est sur la branche main.
    if [ "$1" = -C ]; then [ "$3" = symbolic-ref ] && echo main; exit 0; fi
    case "$3" in https://*) transport=https ;; *) transport=ssh ;; esac
    case " $FAKE_GIT_DENY " in *" $transport "*) exit 128 ;; esac
""")

FAKE_BUN = "#!/bin/sh\n[ \"$1\" = --version ] && echo 1.4.0 || echo '  --no-env-file'\n"


class InstallScriptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        for name, body in [("codex", "#!{}\n{}".format(sys.executable, FAKE_CODEX)), ("git", FAKE_GIT),
                           ("bun", FAKE_BUN), ("gh", "#!/bin/sh\nexit 0\n")]:
            tool = self.bin / name
            tool.write_text(body)
            tool.chmod(0o755)
        self.home = root / "codex-home"
        self.home.mkdir()
        self.state = self.home / "state.json"
        self.log = root / "codex.log"
        self.log.touch()

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *args, **env):
        environment = {
            **os.environ,
            "PATH": "{}{}{}".format(self.bin, os.pathsep, os.environ["PATH"]),
            "CODEX_HOME": str(self.home),
            "FAKE_MAIN_HOME": str(self.home),
            "FAKE_CODEX_LOG": str(self.log),
            **env,
        }
        return subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True, env=environment)

    def calls(self):
        return [call for call in self.log.read_text().splitlines() if "--json" not in call]

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

    def test_ssh_is_used_when_https_is_denied(self):
        result = self.run_script("install", "--ref", "main", FAKE_GIT_DENY="https")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.source(), "git@github.com:charlescstpierr/cstack.git --ref main")

    def test_install_stops_before_codex_when_the_private_repo_is_unreachable(self):
        result = self.run_script("install", FAKE_GIT_DENY="https ssh")
        self.assertEqual(result.returncode, 1)
        self.assertIn("gh auth setup-git", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_ref_or_local_replaces_the_existing_source(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "v1.0.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Changement de source", result.stdout)
        self.assertEqual(self.source(), "charlescstpierr/cstack --ref v1.0.0")
        result = self.run_script("install", "--local")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.source(), str(REPO))

    def test_unusable_new_source_keeps_the_current_installation(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "missing")
        self.assertEqual(result.returncode, 1)
        self.assertIn("L'installation actuelle est conservée", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack")
        self.assertTrue(json.loads(self.state.read_text())["installed"])
        self.assertNotIn("plugin marketplace remove cstack", self.calls())

    def test_failed_switch_restores_the_previous_source(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "flaky")
        self.assertEqual(result.returncode, 1)
        self.assertIn("est restaurée", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack --ref main")

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
        self.assertNotIn("plugin marketplace upgrade cstack", self.calls()[-2:])

    def test_update_of_a_pinned_commit_explains_how_to_move_on(self):
        self.run_script("install", "--ref", "4ca420f")
        result = self.run_script("update")
        self.assertEqual(result.returncode, 1)
        self.assertIn("install.sh install --ref main", result.stderr)

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
        self.assertIn("✗ plugin cstack@cstack : absent", missing.stdout)
        self.run_script("install")
        installed = self.run_script("doctor")
        self.assertEqual(installed.returncode, 0, installed.stdout)
        self.assertIn("✓ plugin cstack@cstack : installed, enabled 0.6.0", installed.stdout)
        self.assertIn("✓ Bun : 1.4.0", installed.stdout)

    def test_doctor_reports_a_failing_plugin_list(self):
        result = self.run_script("doctor", FAKE_CODEX_LIST_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("✗ plugin cstack@cstack : état illisible", result.stdout)

    def test_doctor_reports_an_unusable_codex(self):
        result = self.run_script("doctor", FAKE_CODEX_VERSION_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("✗ Codex CLI inutilisable : Error: error while loading shared libraries", result.stdout)

    def test_uninstall_stops_when_codex_state_is_unreadable(self):
        self.run_script("install")
        result = self.run_script("uninstall", FAKE_CODEX_LIST_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("impossible de lire l'état de Codex", result.stderr)
        self.assertTrue(json.loads(self.state.read_text())["installed"])

    def test_doctor_flags_a_bun_without_no_env_file(self):
        (self.bin / "bun").write_text("#!/bin/sh\n[ \"$1\" = --version ] && echo 1.0.0\nexit 0\n")
        result = self.run_script("doctor")
        self.assertIn("! Bun 1.0.0 trop ancien", result.stdout)

    def test_invalid_arguments_are_rejected(self):
        self.assertEqual(self.run_script("bogus").returncode, 2)
        self.assertEqual(self.run_script("install", "--ref").returncode, 1)
        self.assertEqual(self.run_script("install", "--ref", "main", "--local").returncode, 1)
        self.assertEqual(self.run_script("update", "--local").returncode, 1)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
