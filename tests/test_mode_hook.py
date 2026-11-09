"""Hook de rappel du mode cstack : silencieux hors cstack, rappel à chaque message après activation."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
        env = {key: value for key, value in os.environ.items() if key != "PLUGIN_DATA"}
        if data:
            env["PLUGIN_DATA"] = str(self.data)
        result = subprocess.run([sys.executable, "-S", str(HOOK)], input=raw if raw is not None else json.dumps(event),
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
        self.assertIn("$cstack:cstack", first)
        self.assertEqual(self.prompt("Et ajoute un test."), first)
        self.assertEqual(self.prompt("Autre conversation.", session="s2"), "")
        # Le rappel reste court, comme le `reminder:` de pstack, bien sous la limite d'injection.
        self.assertLess(len(first.split()), 30)

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
            "$cstack:cstack explique la compétence, mais ne pas activer cstack",
            "$cstack:cstack Explique la compétence. Ne pas utiliser cstack.",
            "$cstack:cstack Explique la compétence. Ne pas l'activer.",
            "$cstack:cstack Explique la compétence. Ne pas l'utiliser.",
            "$cstack:cstack Explique la compétence. Ne pas l’appliquer.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Explique la compétence. Ne pas appliquer cstack.",
            "$cstack:cstack pour expliquer sa signification. Ne l'active pas.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Explain the skill. Do not activate it.",
            "$cstack:cstack N'active pas cstack.",
            "$cstack:cstack explique la compétence, mais n'utilise pas cstack.",
            "$cstack:cstack explique la compétence, mais n’applique pas cstack.",
            "$cstack:cstack explique la compétence, mais n’utilise pas cstack.",
            "$cstack:cstack explique la compétence, mais n'applique pas cstack.",
            "$cstack:cstack explique la compétence, mais n'utilisez pas cstack.",
            "$cstack:cstack explique la compétence, mais n’utilisez pas cstack.",
            "$cstack:cstack explique la compétence, mais n'appliquez pas cstack.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) explique la compétence, mais n’appliquez pas cstack.",
            "$cstack:cstack Do not activate it.",
            "$cstack:cstack Explain its behavior, but do not activate cstack.",
            "$cstack:cstack Explain it, but do not activate this skill",
            "$cstack:cstack Explain it, but do not activate this cstack skill.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Explain it, but do not activate the cstack skill.",
            "$cstack:cstack Do not activate $cstack:cstack.",
            "$cstack:cstack Explique la compétence, mais ne pas activer « cstack ».",
            "$cstack:cstack Explique la compétence, mais n'utilise pas \"cstack\".",
            "$cstack:cstack Explain the skill, but do not activate `cstack`.",
            "$cstack:cstack Explain the skill, but do not activate 'cstack'.",
            "$cstack:cstack Explain the skill, but don't activate “this skill”.",
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
            "$cstack:cstack Corrige ceci, mais ne pas activer le mode debug.",
            "$cstack:cstack Corrige ceci. Ne pas utiliser le réseau.",
            "$cstack:cstack Corrige ceci. Ne pas appliquer la configuration réseau.",
            "$cstack:cstack Corrige ceci. N'appliquez pas la configuration debug.",
            "$cstack:cstack Corrige ceci. N’utilisez pas le réseau.",
            "[$cstack:cstack](/plugins/cstack/skills/cstack/SKILL.md) Corrige ceci. N'active pas le réseau.",
        )):
            with self.subTest(prompt=text):
                session = f"feature-{index}"
                first = self.prompt(text, session=session)
                self.assertIn("Mode cstack actif", first)
                self.assertEqual(self.prompt("Continue cette tâche.", session=session), first)

    def test_quoted_refusals_are_content_and_unquoted_refusals_still_apply(self):
        for index, content in enumerate((
            "« ne pas utiliser cstack »",
            '"ne pas utiliser cstack"',
            "'do not activate cstack'",
            "'don't activate it; ne pas utiliser cstack'",
            "“n’utilise pas cstack”",
            "‘don't activate it’",
            "‘don’t activate it; ne pas utiliser cstack’",
            "`ne pas utiliser cstack`",
            "``ne pas utiliser cstack``",
            "```text\nne pas utiliser cstack\n```",
            "~~~text\nne pas utiliser cstack\n~~~",
        )):
            with self.subTest(content=content):
                prompt = f"$cstack:cstack Ajoute au README la phrase {content}"
                active_session = f"quoted-{index}"
                first = self.prompt(prompt, session=active_session)
                self.assertIn("Mode cstack actif", first)
                self.assertEqual(self.prompt("Continue cette tâche.", session=active_session), first)
                markers = set((self.data / "sessions").iterdir())
                refused_session = f"unquoted-refusal-{index}"
                self.assertEqual(self.prompt(prompt + ". Ne l'active pas.", session=refused_session), "")
                self.assertEqual(self.prompt("Une autre question.", session=refused_session), "")
                self.assertEqual(self.run_hook({"hook_event_name": "SessionStart", "session_id": refused_session,
                                               "source": "resume"}), "")
                self.assertEqual(set((self.data / "sessions").iterdir()), markers)

    def test_long_prompts_full_of_unclosed_quotes_activate_within_the_hook_timeout(self):
        # Le hook a cinq secondes : une recherche de fermeture relancée à chaque apostrophe les dépassait.
        fillers = ("&'a str, " * 10000, "‘l’a " * 10000, "`a ``b ```c " * 10000, "`" * 100000, "~" * 100000,
                   " ".join("`" * size for size in range(1, 400)))
        for index, filler in enumerate(fillers):
            with self.subTest(filler=filler[:12]):
                started = time.monotonic()
                out = self.prompt("$cstack:cstack Analyse ce texte :\n" + filler, session=f"long-{index}")
                self.assertLess(time.monotonic() - started, 2.5)
                self.assertIn("Mode cstack actif", out)

    def test_markdown_quote_lines_are_content(self):
        quoted = "$cstack:cstack Ajoute au README ce passage :\n> ne pas utiliser cstack\n  > n'utilise pas cstack"
        self.assertIn("Mode cstack actif", self.prompt(quoted, session="quote-1"))
        refused = "$cstack:cstack Ajoute ce passage :\n> un texte\nFinalement, ne pas utiliser cstack."
        self.assertEqual(self.prompt(refused, session="quote-2"), "")
        # Une ligne `>` située dans une citation déjà ouverte ne doit pas avaler sa fermeture.
        nested = "$cstack:cstack Lis «\n> exemple »\nNe pas utiliser cstack. Réponds « OK »."
        self.assertEqual(self.prompt(nested, session="quote-3"), "")
        # Un retour chariot seul termine la ligne citée ; `>` au milieu d'une ligne est du texte.
        self.assertEqual(self.prompt("$cstack:cstack Lis :\n> exemple\r\rNe l'active pas.", session="quote-4"), "")
        self.assertEqual(self.prompt("$cstack:cstack > Ne l'active pas.", session="quote-5"), "")
        self.assertIn("Mode cstack actif", self.prompt("$cstack:cstack Recopie :\r\n> ne pas utiliser cstack\r\nMerci.", session="quote-6"))

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
