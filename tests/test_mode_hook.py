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

    def run_hook(self, event, *, data=True, raw=None, data_variable="PLUGIN_DATA"):
        env = {key: value for key, value in os.environ.items() if key not in ("PLUGIN_DATA", "CLAUDE_PLUGIN_DATA")}
        # Le réglage de la machine du développeur ne doit jamais entrer dans ces tests.
        env["XDG_CONFIG_HOME"] = str(self.data / "config")
        if data:
            env[data_variable] = str(self.data)
        result = subprocess.run([sys.executable, "-S", str(HOOK)], input=raw if raw is not None else json.dumps(event),
                                capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def prompt(self, text, session="s1"):
        return self.run_hook({"hook_event_name": "UserPromptSubmit", "session_id": session, "prompt": text})

    def test_silent_outside_cstack(self):
        self.assertEqual(self.prompt("Corrige ce bug."), "")
        self.assertEqual(self.run_hook({"hook_event_name": "SessionStart", "session_id": "s1", "source": "compact"}), "")

    def switch(self, *arguments, config=None, home=None):
        env = {**os.environ, "XDG_CONFIG_HOME": str(self.data / "config") if config is None else config}
        if home:
            env["HOME"] = home
        return subprocess.run([sys.executable, "-S", str(HOOK), *arguments], capture_output=True, text=True,
                              env=env, check=False, cwd=self.data)

    def start(self, source, session="s1"):
        return self.run_hook({"hook_event_name": "SessionStart", "session_id": session, "source": source})

    def test_automatic_start_is_off_until_the_user_turns_it_on(self):
        for source in ("startup", "clear", "compact", "resume"):
            self.assertEqual(self.start(source), "", source)
        self.assertEqual(self.switch("auto", "status").stdout.split(" (")[0], "démarrage automatique de cstack : éteint")
        self.assertEqual(self.switch("auto", "on").returncode, 0)
        self.assertTrue((self.data / "config/cstack/auto-start").is_file())
        for source in ("startup", "clear", "compact", "resume"):
            text = self.start(source)
            self.assertIn("vaut invocation explicite", text, source)
            self.assertIn(str(ROOT / "plugins/cstack/skills/cstack/SKILL.md"), text)
        self.assertEqual(self.prompt("Corrige ce bug."), "", "aucun rappel par message sans invocation")
        self.assertEqual(self.switch("auto", "off").returncode, 0)
        self.assertEqual(self.switch("auto", "off").returncode, 0, "éteindre deux fois reste sans erreur")
        self.assertEqual(self.start("startup"), "")

    def test_automatic_start_keeps_the_resume_reminder_of_an_invoked_session(self):
        self.switch("auto", "on")
        self.prompt("$cstack:cstack Corrige ce bug.")
        self.assertIn("contexte résumé", self.start("compact"))
        self.assertIn("vaut invocation explicite", self.start("startup", session="s2"))

    def test_stop_holds_through_a_summary_when_automatic_start_is_on(self):
        self.switch("auto", "on")
        self.prompt("$cstack:cstack Corrige ce bug.")
        self.assertEqual(self.prompt("arrête cstack"), "")
        for source in ("compact", "resume"):
            self.assertEqual(self.start(source), "", source)
        self.assertEqual(self.prompt("arrête cstack", session="jamais-invoquée"), "")
        self.assertEqual(self.start("compact", session="jamais-invoquée"), "")
        self.assertIn("vaut invocation explicite", self.start("compact", session="autre"))
        self.assertIn("Mode cstack actif", self.prompt("$cstack:cstack Reprends."))
        self.assertIn("contexte résumé", self.start("compact"))

    def test_a_summary_of_an_automatic_session_points_back_to_its_checkpoint(self):
        self.switch("auto", "on")
        self.assertNotIn("point de reprise", self.start("startup"))
        self.assertIn("point de reprise", self.start("compact"))

    def test_an_abnormal_setting_never_crashes_the_switch_or_the_hook(self):
        setting = self.data / "config/cstack/auto-start"
        setting.mkdir(parents=True)
        for arguments in (("auto", "on"), ("auto", "off")):
            result = self.switch(*arguments)
            self.assertEqual(result.returncode, 1, arguments)
            self.assertNotIn("Traceback", result.stderr)
        self.assertIn("éteint", self.switch("auto", "status").stdout)
        self.assertEqual(self.start("startup"), "")
        setting.rmdir()
        target = self.data / "elsewhere"
        setting.symlink_to(target)
        self.assertEqual(self.switch("auto", "on").returncode, 1)
        self.assertFalse(target.exists())
        self.assertEqual(self.switch("auto", "off").returncode, 0)
        self.assertFalse(setting.is_symlink())
        result = self.switch("auto", "on", config="relative-config", home="relative-home")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.data / "relative-home").exists())

    def test_the_switch_rejects_other_commands_and_ignores_a_relative_config_home(self):
        for arguments in (("auto",), ("auto", "maybe"), ("on",)):
            result = self.switch(*arguments)
            self.assertEqual((result.returncode, result.stdout), (2, ""), arguments)
        home = self.data / "home"
        result = self.switch("auto", "on", config="relative-config", home=str(home))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((home / ".config/cstack/auto-start").is_file())
        self.assertFalse((self.data / "relative-config").exists())

    def test_reminder_after_activation_on_every_turn_of_that_session_only(self):
        first = self.prompt("$cstack:cstack Corrige ce bug.")
        self.assertIn("Mode cstack actif", first)
        self.assertIn("$cstack:cstack", first)
        self.assertEqual(self.prompt("Et ajoute un test."), first)
        self.assertEqual(self.prompt("Autre conversation.", session="s2"), "")
        # Le rappel reste court, comme le `reminder:` de pstack, bien sous la limite d'injection.
        self.assertLess(len(first.split()), 30)

    def test_claude_code_slash_command_activates_with_its_own_data_directory(self):
        event = {"hook_event_name": "UserPromptSubmit", "session_id": "claude", "prompt": "/cstack:cstack Corrige ce bug."}
        first = self.run_hook(event, data_variable="CLAUDE_PLUGIN_DATA")
        self.assertIn("Mode cstack actif", first)
        event["prompt"] = "Et ajoute un test."
        self.assertEqual(self.run_hook(event, data_variable="CLAUDE_PLUGIN_DATA"), first)
        self.assertEqual(self.prompt("/cstack:cstack-extra Corrige ce bug.", session="other"), "")

    def test_mentions_and_explicit_refusals_do_not_activate(self):
        prompts = (
            "Explique ce que signifie la chaîne « $cstack:cstack ». Ne l’active pas.",
            "Ne lance pas $cstack:cstack.",
            "`$cstack:cstack` est-il un skill ?",
            "\"$cstack:cstack\"",
            "```\n$cstack:cstack\n```",
            "Explique [$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md).",
            "`[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md)`",
            "$cstack:cstack Ne l'active pas.",
            "$cstack:cstack Ne l’active pas.",
            "$cstack:cstack Ne l'utilise pas.",
            "$cstack:cstack pour expliquer sa signification. Ne l'active pas.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Explain the skill. Do not activate it.",
            "$cstack:cstack N'active pas cstack.",
            "$cstack:cstack Do not activate it.",
            "$cstack:cstack Explain its behavior, but do not activate cstack.",
            "$cstack:cstack Explain it, but do not activate this skill",
            "$cstack:cstack Explain it, but do not activate this cstack skill.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Explain it, but do not activate the cstack skill.",
            "$cstack:cstack Do not activate $cstack:cstack.",
            "$cstack:cstack N'active pas $cstack:cstack.",
            "$cstack:cstack Don't activate it.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Do not activate it.",
            "[$cstack](/plugins/cstack/skills/how/SKILL.md) Corrige ce bug.",
            "$cstack:cstack-extra Corrige ce bug.",
        )
        for index, text in enumerate(prompts):
            with self.subTest(prompt=text):
                session = f"mention-{index}"
                self.assertEqual(self.prompt(text, session=session), "")
                self.assertEqual(self.prompt("Une autre question.", session=session), "")
                self.assertEqual(self.run_hook({"hook_event_name": "SessionStart", "session_id": session,
                                               "source": "resume"}), "")
        self.assertFalse((self.data / "sessions").exists())

    def test_explicit_commands_and_skill_links_activate(self):
        for index, text in enumerate((
            "$cstack:cstack",
            "  $cstack:cstack\nCorrige ce bug.",
            "Utilise $cstack:cstack pour cette tâche.",
            "Use $cstack:cstack to fix the bug.",
            "$cstack:cstack Corrige ce bug. Ne modifie pas la configuration.",
            "$cstack:cstack Corrige ce bug. N'utilise pas de réseau.",
            "$cstack:cstack Fix the bug. Do not use the network.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Corrige ce bug.",
            "[$cstack](/plugins/cstack/skills/cstack/SKILL.md) Corrige ce bug.",
            "Utilise [$cstack:cstack](</plugins/cstack/skills/cstack/SKILL.md>) pour cette tâche.",
        )):
            with self.subTest(prompt=text):
                self.assertIn("Mode cstack actif", self.prompt(text, session=f"command-{index}"))

    def test_activation_refusals_for_other_features_do_not_disable_cstack(self):
        for index, text in enumerate((
            "$cstack:cstack fix this, but do not activate debug mode",
            "$cstack:cstack Fix this. Don't activate the network adapter.",
            "$cstack:cstack Fix this. Do not activate this debug mode.",
            "$cstack:cstack Corrige ceci. N'active pas le mode debug.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Corrige ceci. N'active pas le réseau.",
        )):
            with self.subTest(prompt=text):
                session = f"feature-{index}"
                first = self.prompt(text, session=session)
                self.assertIn("Mode cstack actif", first)
                self.assertEqual(self.prompt("Continue cette tâche.", session=session), first)

    def test_stop_request_ends_the_reminder(self):
        self.prompt("$cstack:cstack Refactorise ce module.")
        self.assertEqual(self.prompt("Arrête cstack."), "")
        self.assertEqual(self.prompt("Une question simple."), "")
        self.assertIn("Mode cstack actif", self.prompt("$cstack:cstack On reprend."))
        # Seule la commande exacte coupe le rappel ; une phrase plus longue reste au jugement du modèle.
        for text in ("Ne stoppe pas cstack.", "Sors les logs de cstack.", "N'arrête pas cstack !", "Don’t stop cstack", "Merci, arrête cstack maintenant."):
            self.assertIn("Mode cstack actif", self.prompt(text))

    def test_reminder_survives_compaction_and_resume(self):
        self.prompt("$cstack:cstack Migration en plusieurs phases.")
        for source in ("compact", "resume"):
            text = self.run_hook({"hook_event_name": "SessionStart", "session_id": "s1", "source": source})
            self.assertIn("Mode cstack actif", text)
            self.assertIn("runtime/base.md", text)
            self.assertIn("point de reprise", text)
            self.assertIn("le résumé nomme le chemin", text)
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


if __name__ == "__main__":
    unittest.main()
