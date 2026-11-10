import json
import os
import re
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
    import json, os, sys, shutil
    state_path = os.path.join(os.environ["CODEX_HOME"], "state.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"source": None, "installed": False}
    args = sys.argv[1:]
    with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
        log.write(("trial: " if os.environ["CODEX_HOME"] != os.environ["FAKE_MAIN_HOME"] else "") + " ".join(args) + "\\n")
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
        entries = [{"name": "cstack", "root": os.path.join(os.environ["CODEX_HOME"], "marketplace"),
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
        cache = os.path.join(os.environ["CODEX_HOME"], "marketplace")
        os.makedirs(cache, exist_ok=True)
        saved = os.path.join(args[3], "snapshot.txt")
        with open(os.path.join(cache, "snapshot.txt"), "w") as snapshot:
            snapshot.write(open(saved).read() if os.path.isfile(saved) else source)
        for manifest, plugin_source in [(".agents/plugins/marketplace.json", {"source": "local", "path": "./plugin"}), (".claude-plugin/marketplace.json", "./plugin")]:
            target = os.path.join(cache, manifest)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            json.dump({"plugins": [{"name": "cstack", "source": plugin_source}]}, open(target, "w"))
        os.makedirs(os.path.join(cache, "plugin"), exist_ok=True)
        shutil.copyfile(os.path.join(cache, "snapshot.txt"), os.path.join(cache, "plugin", "snapshot.txt"))
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
        if os.environ.get("FAKE_CODEX_LIST_FAILS") or os.environ.get("FAKE_PLUGIN_LIST_FAILS"):
            fail("marketplace `cstack` is not configured")
        enabled = state["installed"] and not state.get("disabled")
        entry = {"pluginId": "cstack@cstack", "installed": state["installed"], "enabled": enabled, "version": "0.6.0"}
        listed = [entry] if state["source"] else []
        print(json.dumps({"installed": [e for e in listed if e["installed"]],
                          "available": [e for e in listed if not e["installed"]]}))
    elif args[:2] == ["plugin", "add"]:
        if not state["source"]:
            fail("marketplace `cstack` is not configured")
        broken = os.environ.get("FAKE_BROKEN_REF")
        if state["source"].endswith(("--ref no-plugin", "--ref cache-full-fresh")) or (broken and state["source"].endswith("--ref " + broken)):
            fail("plugin `cstack` was not found in marketplace `cstack`")
        # Cache plein dans le vrai CODEX_HOME seulement : l'essai réussit, l'installation réelle échoue.
        if state["source"].endswith("--ref cache-full") and os.environ["CODEX_HOME"] == os.environ["FAKE_MAIN_HOME"]:
            fail("failed to write plugin cache: No space left on device")
        plugin_cache = os.path.join(os.environ["CODEX_HOME"], "plugins/cache/cstack/cstack/0.6.0")
        shutil.copytree(os.path.join(os.environ["CODEX_HOME"], "marketplace/plugin"), plugin_cache, dirs_exist_ok=True)
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
    # `git -C <clone> …` : clone de Codex sur main, sauf FAKE_GIT_DETACHED ; HEAD illisible avec FAKE_GIT_NO_HEAD.
    if [ "$1" = -C ]; then
      case "$3" in
        symbolic-ref) [ -z "$FAKE_GIT_DETACHED" ] && echo main ;;
        rev-parse) [ -z "$FAKE_GIT_NO_HEAD" ] && echo 4ca420fb91c4b1a989072fd57e9aeb4da35ae044 ;;
      esac
      exit
    fi
    case "$3" in https://*) transport=https ;; *) transport=ssh ;; esac
    case " $FAKE_GIT_DENY " in *" $transport "*) exit 128 ;; esac
""")

# Reproduit les sorties JSON de `claude plugin` observées avec Claude Code 2.1.321.
FAKE_CLAUDE = textwrap.dedent("""\
    import json, os, sys, shutil
    home = os.environ["CLAUDE_CONFIG_DIR"]
    state_path = os.path.join(home, "state.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"source": None, "installed": False}
    args = sys.argv[1:]
    with open(os.environ["FAKE_CLAUDE_LOG"], "a") as log:
        log.write(("trial: " if home != os.environ["FAKE_MAIN_CLAUDE_HOME"] else "") + " ".join(args) + "\\n")
    def save():
        json.dump(state, open(state_path, "w"))
    def fail(message):
        print(message, file=sys.stderr)
        sys.exit(1)
    def entry(source):
        base, _, ref = source.partition("#")
        if base.startswith("/"):
            return {"name": "cstack", "source": "directory", "path": base, "installLocation": os.path.join(home, "marketplace")}
        shape = {"name": "cstack", "source": "git", "url": base} if base.startswith("git@") else {"name": "cstack", "source": "github", "repo": base}
        shape["installLocation"] = os.path.join(home, "marketplace")
        return {**shape, "ref": ref} if ref else shape
    main_home = home == os.environ["FAKE_MAIN_CLAUDE_HOME"]
    if args == ["--version"]:
        print("2.1.321 (Claude Code)")
    elif args[:3] == ["plugin", "marketplace", "list"]:
        if os.environ.get("FAKE_CLAUDE_LIST_FAILS"):
            fail("failed to read settings")
        print(json.dumps([entry(state["source"])] if state["source"] else []))
    elif args[:3] == ["plugin", "marketplace", "add"]:
        if args[3].endswith("#missing"):
            fail("Failed to clone marketplace repository: ref missing not found")
        # Panne réseau dans le vrai profil seulement : l'essai réussit, le remplacement échoue.
        if args[3].endswith("#flaky") and main_home:
            fail("Failed to clone marketplace repository: connection reset")
        # Claude Code garde la source existante sans erreur : il faut retirer avant de changer de ref.
        state["source"] = state["source"] or args[3]
        cache = os.path.join(home, "marketplace")
        os.makedirs(cache, exist_ok=True)
        saved = os.path.join(args[3], "snapshot.txt")
        with open(os.path.join(cache, "snapshot.txt"), "w") as snapshot:
            snapshot.write(open(saved).read() if os.path.isfile(saved) else state["source"])
        for manifest, plugin_source in [(".agents/plugins/marketplace.json", {"source": "local", "path": "./plugin"}), (".claude-plugin/marketplace.json", "./plugin")]:
            target = os.path.join(cache, manifest)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            json.dump({"plugins": [{"name": "cstack", "source": plugin_source}]}, open(target, "w"))
        os.makedirs(os.path.join(cache, "plugin"), exist_ok=True)
        shutil.copyfile(os.path.join(cache, "snapshot.txt"), os.path.join(cache, "plugin", "snapshot.txt"))
        save()
    elif args[:3] == ["plugin", "marketplace", "remove"]:
        state.update(source=None, installed=False)
        save()
    elif args[:3] == ["plugin", "marketplace", "update"]:
        pass
    elif args[:2] in (["plugin", "install"], ["plugin", "update"]):
        if not state["source"]:
            fail("Plugin not found in any marketplace")
        if state["source"].endswith("#no-plugin"):
            fail("Plugin cstack not found in marketplace cstack")
        plugin_cache = os.path.join(home, "plugins/cache/cstack/cstack/0.8.0")
        shutil.copytree(os.path.join(home, "marketplace/plugin"), plugin_cache, dirs_exist_ok=True)
        state["installed"] = True
        save()
    elif args[:2] == ["plugin", "uninstall"]:
        state["installed"] = False
        save()
    elif args[:2] == ["plugin", "list"]:
        print(json.dumps([{"id": "cstack@cstack", "version": "0.8.0", "enabled": True, "installPath": os.path.join(home, "plugins/cache/cstack/cstack/0.8.0")}] if state["installed"] else []))
    else:
        fail("unexpected arguments: " + " ".join(args))
""")

FAKE_BUN = "#!/bin/sh\n[ \"$1\" = --version ] && echo 1.4.0 || echo '  --no-env-file'\n"


class InstallHarness(unittest.TestCase):
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
            "XDG_STATE_HOME": str(Path(self.temp.name) / "state"),
            # Jamais le vrai `claude` de la machine : il modifierait le profil de l'utilisateur.
            "CSTACK_CLAUDE": str(self.bin / "absent-claude"),
            **env,
        }
        return subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True, env=environment)

    def calls(self):
        return [call for call in self.log.read_text().splitlines() if "--json" not in call and not call.startswith("trial: ")]

    def source(self):
        return json.loads(self.state.read_text())["source"] if self.state.exists() else None

    def installed(self):
        return json.loads(self.state.read_text())["installed"]


class InstallScriptTest(InstallHarness):

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
        self.assertTrue(self.installed())
        self.assertNotIn("plugin marketplace remove cstack", self.calls())

    def test_source_without_the_plugin_keeps_the_current_installation(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "no-plugin")
        self.assertEqual(result.returncode, 1)
        self.assertIn("L'installation actuelle est conservée", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack")
        self.assertTrue(self.installed())

    def test_failed_switch_restores_the_previous_source(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "flaky")
        self.assertEqual(result.returncode, 1)
        self.assertIn("est restaurée", result.stderr)
        self.assertTrue(self.source().startswith(str(Path(self.temp.name) / "state")))
        self.assertEqual((Path(self.source()) / "snapshot.txt").read_text(), "charlescstpierr/cstack")

    def test_failed_plugin_install_after_switch_restores_the_previous_source(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "cache-full")
        self.assertEqual(result.returncode, 1)
        self.assertIn("est restaurée", result.stderr)
        self.assertTrue(self.source().startswith(str(Path(self.temp.name) / "state")))
        self.assertEqual((Path(self.source()) / "snapshot.txt").read_text(), "charlescstpierr/cstack")
        self.assertTrue(self.installed())

    def test_failed_fresh_install_removes_the_marketplace_it_added(self):
        result = self.run_script("install", "--ref", "cache-full-fresh")
        self.assertEqual(result.returncode, 1)
        self.assertIn("installation du plugin impossible", result.stderr)
        self.assertIsNone(self.source())

    def set_state(self, **changes):
        state = json.loads(self.state.read_text())
        state.update(changes)
        self.state.write_text(json.dumps(state))

    def test_rollback_keeps_an_uninstalled_plugin_uninstalled(self):
        self.run_script("install")
        self.set_state(installed=False)
        result = self.run_script("install", "--ref", "flaky")
        self.assertEqual(result.returncode, 1)
        self.assertIn("est restaurée", result.stderr)
        self.assertFalse(self.installed())

    def test_rollback_messages_hide_url_credentials(self):
        self.run_script("install")
        self.set_state(source="https://user:s3cret@github.com/charlescstpierr/cstack.git")
        result = self.run_script("install", "--ref", "flaky")
        self.assertEqual(result.returncode, 1)
        self.assertIn("https://***@github.com", result.stderr)
        self.assertNotIn("s3cret", result.stdout + result.stderr)

    def test_disabled_plugin_is_not_silently_reenabled(self):
        self.run_script("install")
        self.set_state(disabled=True)
        for args in (("update",), ("install", "--ref", "v1.0.0"), ("install",)):
            result = self.run_script(*args)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn("cstack est désactivé", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack")
        self.assertNotIn("plugin marketplace remove cstack", self.calls())

    def test_unreadable_plugin_state_stops_before_any_change(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "v1.0.0", FAKE_PLUGIN_LIST_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("état du plugin illisible", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack")
        self.assertNotIn("plugin marketplace remove cstack", self.calls())

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
        self.assertEqual(self.source(), "charlescstpierr/cstack --ref main")
        self.assertEqual(self.calls()[-2:], ["plugin marketplace add charlescstpierr/cstack --ref main", "plugin add cstack@cstack"])
        self.run_script("install", "--local")
        result = self.run_script("update")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Source locale", result.stdout)
        self.assertNotIn("plugin marketplace upgrade cstack", self.calls()[-2:])

    def test_update_with_the_same_ref_refreshes_the_snapshot(self):
        self.run_script("install", "--ref", "main")
        result = self.run_script("update", "--ref", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[-3:], ["plugin marketplace remove cstack",
                                             "plugin marketplace add charlescstpierr/cstack --ref main",
                                             "plugin add cstack@cstack"])

    def test_update_of_a_pinned_commit_explains_how_to_move_on(self):
        self.run_script("install", "--ref", "4ca420f")
        result = self.run_script("update", FAKE_GIT_DETACHED="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("install.sh install --ref main", result.stderr)

    def test_update_to_a_broken_branch_tip_keeps_the_current_installation(self):
        self.run_script("install")
        result = self.run_script("update", FAKE_BROKEN_REF="main")
        self.assertEqual(result.returncode, 1)
        self.assertIn("L'installation actuelle est conservée", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack")
        self.assertTrue(self.installed())
        self.assertNotIn("plugin marketplace remove cstack", self.calls())

    def test_unreadable_current_commit_stops_before_any_change(self):
        self.run_script("install")
        result = self.run_script("install", "--ref", "v1.0.0", FAKE_GIT_NO_HEAD="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("commit actuel illisible", result.stderr)
        self.assertEqual(self.source(), "charlescstpierr/cstack")
        self.assertNotIn("plugin marketplace remove cstack", self.calls())

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
        self.assertTrue(self.installed())

    def test_doctor_reports_a_missing_git(self):
        (self.bin / "git").unlink()
        bare = Path(self.temp.name) / "bare"
        bare.mkdir()
        for tool in ("python3", "bash", "awk", "sed", "grep", "tail", "mktemp", "rm", "cat", "dirname"):
            found = shutil.which(tool)
            if found:
                (bare / tool).symlink_to(found)
        result = self.run_script("doctor", PATH="{}{}{}".format(self.bin, os.pathsep, bare))
        self.assertIn("✗ git introuvable", result.stdout)
        self.assertNotIn("gh auth login", result.stdout)

    def test_doctor_flags_a_bun_without_no_env_file(self):
        (self.bin / "bun").write_text("#!/bin/sh\n[ \"$1\" = --version ] && echo 1.0.0\nexit 0\n")
        result = self.run_script("doctor")
        self.assertIn("! Bun 1.0.0 trop ancien", result.stdout)

    def test_invalid_arguments_are_rejected(self):
        self.assertEqual(self.run_script("bogus").returncode, 2)
        self.assertEqual(self.run_script("install", "--ref").returncode, 1)
        self.assertEqual(self.run_script("install", "--ref", "").returncode, 1)
        self.assertEqual(self.run_script("update", "--ref", "").returncode, 1)
        self.assertEqual(self.run_script("install", "--ref", "main", "--local").returncode, 1)
        self.assertEqual(self.run_script("update", "--local").returncode, 1)
        self.assertEqual(self.run_script("doctor", "--local").returncode, 2)
        self.assertEqual(self.calls(), [])


class AgentRunbookTest(unittest.TestCase):
    """INSTALL-AGENT.md doit citer les messages que install.sh affiche réellement."""

    @classmethod
    def setUpClass(cls):
        cls.runbook = (REPO / "INSTALL-AGENT.md").read_text()

    def test_known_failures_quote_real_messages(self):
        script = SCRIPT.read_text()
        quoted = []
        for line in self.runbook.split("## Pannes connues", 1)[1].splitlines():
            if line.startswith("| `"):
                quoted += re.findall(r"`([^`]+)`", line.split("|")[1])
        self.assertGreaterEqual(len(quoted), 6)
        for message in quoted:
            with self.subTest(message=message):
                self.assertIn(message.replace("charlescstpierr/cstack", "${REPO}"), script)

    def test_named_skills_exist(self):
        names = set(re.findall(r"\$cstack:([a-z0-9-]+)", self.runbook))
        self.assertTrue(names)
        for name in names:
            with self.subTest(skill=name):
                self.assertTrue((REPO / "plugins/cstack/skills" / name / "SKILL.md").is_file())

    def test_runbook_uses_the_readme_download_and_is_linked(self):
        readme = (REPO / "README.md").read_text()
        download = "curl -fsSL https://raw.githubusercontent.com/charlescstpierr/cstack/main/install.sh -o "
        self.assertIn(download, self.runbook)
        self.assertIn(download, readme)
        self.assertIn("(INSTALL-AGENT.md)", readme)
        self.assertIn("main/INSTALL-AGENT.md", readme)

class ClaudeInstallTest(InstallHarness):
    def setUp(self):
        super().setUp()
        root = Path(self.temp.name)
        self.claude = self.bin / "fake-claude"
        self.claude.write_text("#!{}\n{}".format(sys.executable, FAKE_CLAUDE))
        self.claude.chmod(0o755)
        self.claude_home = root / "claude-home"
        self.claude_home.mkdir()
        self.claude_state = self.claude_home / "state.json"
        self.claude_log = root / "claude.log"
        self.claude_log.touch()

    def run_claude_script(self, *args, codex=True, **env):
        claude = {"CSTACK_CLAUDE": str(self.claude), "CLAUDE_CONFIG_DIR": str(self.claude_home),
                  "FAKE_MAIN_CLAUDE_HOME": str(self.claude_home), "FAKE_CLAUDE_LOG": str(self.claude_log)}
        if not codex:
            claude["CSTACK_CODEX"] = str(self.bin / "absent-codex")
        return self.run_script(*args, **claude, **env)

    def claude_calls(self):
        return [call for call in self.claude_log.read_text().splitlines() if "--json" not in call and not call.startswith("trial: ")]

    def test_install_covers_codex_and_claude(self):
        result = self.run_claude_script("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["plugin marketplace add charlescstpierr/cstack", "plugin add cstack@cstack"])
        self.assertEqual(self.claude_calls(), ["plugin marketplace add charlescstpierr/cstack", "plugin install cstack@cstack"])
        self.assertIn("$cstack:cstack", result.stdout)
        self.assertIn("/cstack:cstack", result.stdout)

    def test_claude_alone_is_enough(self):
        result = self.run_claude_script("install", "--ref", "main", codex=False, FAKE_GIT_DENY="https")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.claude_calls(), ["plugin marketplace add git@github.com:charlescstpierr/cstack.git#main",
                                               "plugin install cstack@cstack"])
        self.assertNotIn("$cstack:cstack", result.stdout)
        doctor = self.run_claude_script("doctor", codex=False)
        self.assertEqual(doctor.returncode, 0, doctor.stdout)
        self.assertIn("✓ plugin cstack@cstack dans Claude Code : installed, enabled 0.8.0", doctor.stdout)
        self.assertIn("! Codex CLI absent", doctor.stdout)

    def test_claude_alone_stops_when_the_private_repo_is_unreachable(self):
        result = self.run_claude_script("install", codex=False, FAKE_GIT_DENY="https ssh")
        self.assertEqual(result.returncode, 1)
        self.assertIn("gh auth setup-git", result.stderr)
        self.assertEqual(self.claude_calls(), [])

    def test_claude_ref_replaces_the_existing_source(self):
        self.run_claude_script("install", codex=False)
        result = self.run_claude_script("update", "--ref", "v1.0.0", codex=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.claude_profile(),
                         {"source": "charlescstpierr/cstack#v1.0.0", "installed": True})

    def test_claude_update_and_uninstall(self):
        self.run_claude_script("install", codex=False)
        self.assertEqual(self.run_claude_script("update", codex=False).returncode, 0)
        self.assertEqual(self.claude_calls()[-3:], ["plugin marketplace remove cstack", "plugin marketplace add charlescstpierr/cstack#main", "plugin install cstack@cstack"])
        result = self.run_claude_script("uninstall", codex=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.claude_state.read_text()), {"source": None, "installed": False})

    def claude_profile(self):
        return json.loads(self.claude_state.read_text())

    def test_unusable_claude_ref_keeps_the_current_installation(self):
        self.run_claude_script("install", codex=False)
        for ref in ("missing", "no-plugin"):
            with self.subTest(ref=ref):
                result = self.run_claude_script("update", "--ref", ref, codex=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn("L'installation actuelle est conservée", result.stderr)
                self.assertEqual(self.claude_profile(), {"source": "charlescstpierr/cstack", "installed": True})

    def test_failed_claude_replacement_restores_the_previous_source(self):
        self.run_claude_script("install", "--ref", "v1.0.0", codex=False)
        result = self.run_claude_script("update", "--ref", "flaky", codex=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("est restaurée", result.stderr)
        profile = self.claude_profile()
        self.assertTrue(profile["installed"])
        self.assertEqual((Path(profile["source"]) / "snapshot.txt").read_text(), "charlescstpierr/cstack#v1.0.0")

    def test_unreadable_claude_state_stops_uninstall_before_any_removal(self):
        self.run_claude_script("install")
        result = self.run_claude_script("uninstall", FAKE_CLAUDE_LIST_FAILS="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("impossible de lire l'état de Claude Code", result.stderr)
        self.assertNotIn("cstack est retiré", result.stdout)
        self.assertTrue(self.installed())
        self.assertEqual(self.claude_profile(), {"source": "charlescstpierr/cstack", "installed": True})

    def test_without_any_host_nothing_is_installed(self):
        result = self.run_script("install", CSTACK_CODEX=str(self.bin / "absent-codex"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Claude Code aussi", result.stderr)


if __name__ == "__main__":
    unittest.main()
