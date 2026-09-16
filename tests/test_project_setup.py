"""Les plans de configuration du projet sont figés, reprenables et prudents."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/cstack/skills/setup-cstack/scripts/project.py"
MODELS = ROOT / "plugins/cstack/skills/setup-cstack/scripts/models.py"
SPEC = importlib.util.spec_from_file_location("cstack_project", SCRIPT)
project = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(project)

CATALOG = {
    "gpt-5.6-luna": ["low", "medium", "high", "xhigh", "max"],
    "gpt-6-astra": ["low", "medium", "high", "xhigh", "max", "ultra"],
}


class ProjectSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_cli_argument_errors_are_french_and_keep_argument_values(self) -> None:
        literal = "unrecognized arguments: invalid choice: (choose from error)"
        for script, command, required in [(SCRIPT, "preview", "--options"), (MODELS, "resolve", "role")]:
            cases = [
                ([], "arguments requis", "command"),
                ([command], "arguments requis", required),
                (["inconnue"], "choix invalide", "inconnue"),
                (["--workspace"], "un argument attendu", "--workspace"),
                (["--help=" + literal], "argument explicite ignoré", literal),
            ]
            if script == SCRIPT:
                cases.append((["preview", "--options", "unused.json", "--inconnue"], "arguments non reconnus", "--inconnue"))
            else:
                cases.extend([
                    (["resolve", literal], "choix invalide", literal),
                    (["resolve", "documentation", "--inconnue"], "arguments non reconnus", "--inconnue"),
                ])
            for args, expected, value in cases:
                with self.subTest(script=script.name, args=args):
                    result = subprocess.run([sys.executable, str(script), *args], cwd=self.root, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("utilisation:", result.stderr)
                    self.assertIn(": erreur:", result.stderr)
                    self.assertIn(expected, result.stderr)
                    self.assertIn(value, result.stderr)
        help_result = subprocess.run([sys.executable, str(MODELS), "resolve", "--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("arguments positionnels:", help_result.stdout)
        self.assertNotIn("positional arguments:", help_result.stdout)
        self.assertEqual(list(self.root.iterdir()), [])

    def _options(self, value: dict | None = None) -> Path:
        path = self.root / "options.json"
        path.write_text(json.dumps(value or {}), encoding="utf-8")
        return path

    def _catalog(self) -> Path:
        path = self.root / "catalog.json"
        path.write_text(json.dumps({"models": [
            {"slug": name, "visibility": "list", "supported_reasoning_levels": [{"effort": effort} for effort in levels]}
            for name, levels in CATALOG.items()
        ]}), encoding="utf-8")
        return path

    def _cli(self, command: str, *extra: str, options: Path | None = None, catalog: Path | None = None) -> subprocess.CompletedProcess[str]:
        options = options or self._options()
        command_line = [sys.executable, str(SCRIPT), "--workspace", str(self.root)]
        if catalog is not None:
            command_line.extend(["--catalog", str(catalog)])
        command_line.extend([command, "--options", str(options), *extra])
        return subprocess.run(command_line, cwd=ROOT, text=True, capture_output=True, check=False)

    def _preview(self, value: dict | None = None, *, catalog: Path | None = None) -> tuple[Path, dict]:
        options = self._options(value)
        result = self._cli("preview", options=options, catalog=catalog)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["status"], "preview")
        path = self.root / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return options, plan

    def _apply(self, options: Path, plan: dict, *, catalog: Path | None = None) -> subprocess.CompletedProcess[str]:
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        return self._cli("apply", "--plan", str(plan_path), "--expected-plan-sha256", plan["plan_sha256"], options=options, catalog=catalog)

    def test_fresh_setup_is_preview_only_then_creates_passive_docs(self) -> None:
        options, plan = self._preview()
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertEqual({entry["path"] for entry in plan["files"]}, {"AGENTS.md", "docs/agents/cstack.md", ".gitignore"})
        result = self._apply(options, plan)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / ".gitignore").read_bytes(), b".cstack/\n")
        agents = (self.root / "AGENTS.md").read_text()
        self.assertIn("cstack:managed:start", agents)
        self.assertIn("seulement après invocation explicite d’une skill cstack par l’utilisateur", agents)
        guide = (self.root / "docs/agents/cstack.md").read_text()
        self.assertIn("| `clarify` | `$cstack:clarify` | 0 par défaut; un explorateur par fait indépendant délégué | `how explorer` |", guide)
        self.assertIn("| `domain` | `$cstack:domain` | 0 par défaut; délégation factuelle optionnelle | `how explorer`, `documentation`, `judgment and prose` |", guide)
        self.assertIn("| `horizon` | `$cstack:horizon` | enfants de recherche variables; 1 synthèse optionnelle (judgment and prose) |", guide)
        self.assertIn("| `audit-architecture` | `$cstack:audit-architecture` | au plus 1 explorateur initial | `how explorer` |", guide)
        self.assertIn("choix de modèles et d’effort de raisonnement", guide)
        self.assertIn("Utiliser `hardest tasks` seulement pour l’architecture complexe explicite", guide)
        self.assertFalse((self.root / "CONTEXT.md").exists())
        self.assertFalse((self.root / "ADR").exists())

    def test_preview_does_not_write_into_trusted_bundle(self) -> None:
        bundle = self.root / "bundle"
        bundle.mkdir()
        for source in (SCRIPT, MODELS):
            (bundle / source.name).write_bytes(source.read_bytes())
        workspace = self.root / "workspace"
        workspace.mkdir()
        before = {p.name: p.read_bytes() for p in bundle.iterdir()}
        result = subprocess.run([sys.executable, str(bundle / "project.py"),
                                 "--workspace", str(workspace), "preview", "--options", str(self._options())],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in bundle.iterdir()}, before)

    def test_reapplying_the_same_plan_is_a_noop_and_gitignore_preserves_crlf(self) -> None:
        (self.root / ".cstack").mkdir()
        (self.root / ".gitignore").write_bytes(b"dist\r\n")
        options, plan = self._preview()
        first = self._apply(options, plan)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual((self.root / ".gitignore").read_bytes(), b"dist\r\n.cstack/\r\n")
        before = sorted((path.relative_to(self.root), path.read_bytes()) for path in self.root.rglob("*") if path.is_file() and path.name not in {"options.json", "plan.json"})
        second = self._apply(options, plan)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout)["status"], "noop")
        after = sorted((path.relative_to(self.root), path.read_bytes()) for path in self.root.rglob("*") if path.is_file() and path.name not in {"options.json", "plan.json"})
        self.assertEqual(before, after)

    def test_manual_text_crlf_and_existing_claude_are_preserved(self) -> None:
        (self.root / "AGENTS.md").write_bytes("règle humaine\r\n".encode("utf-8"))
        (self.root / "CLAUDE.md").write_bytes("# Règles existantes\r\n".encode("utf-8"))
        docs = self.root / "docs/agents"
        docs.mkdir(parents=True)
        (docs / "cstack.md").write_bytes("préfixe manuel\r\n".encode("utf-8") + project.START + b"\r\nold\r\n" + project.END + b"\r\nsuffixe manuel\r\n")
        tracker = docs / "issue-tracker.md"
        tracker.write_bytes(b"suivi existant\r\n")
        options, plan = self._preview()
        result = self._apply(options, plan)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        agents = (self.root / "AGENTS.md").read_bytes()
        self.assertTrue(agents.startswith("règle humaine\r\n".encode("utf-8")))
        self.assertIn(b"[CLAUDE.md](CLAUDE.md)", agents)
        updated = (docs / "cstack.md").read_bytes()
        self.assertTrue(updated.startswith("préfixe manuel\r\n".encode("utf-8")))
        self.assertTrue(updated.endswith(b"suffixe manuel\r\n"))
        self.assertEqual(tracker.read_bytes(), b"suivi existant\r\n")
        self.assertEqual((self.root / "CLAUDE.md").read_bytes(), "# Règles existantes\r\n".encode("utf-8"))

    def test_explicit_tracker_modes_are_local_and_github_is_validation_only(self) -> None:
        options, plan = self._preview({"tracker": {"mode": "github", "owner": "acme", "repo": "app"}})
        result = self._apply(options, plan)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tracker = (self.root / "docs/agents/issue-tracker.md").read_text()
        self.assertIn("https://github.com/acme/app", tracker)
        self.assertFalse((self.root / ".github").exists())
        local_options, local_plan = self._preview({"tracker": {"mode": "local"}})
        local_result = self._apply(local_options, local_plan)
        self.assertEqual(local_result.returncode, 0, local_result.stdout + local_result.stderr)
        local_tracker = (self.root / "docs/agents/issue-tracker.md").read_text()
        self.assertIn(".cstack/horizon/<slug>/map.md", local_tracker)
        self.assertIn("tickets/<id>-<slug>.md", local_tracker)
        self.assertIn("research/<id>.md", local_tracker)
        self.assertIn("ready", local_tracker)
        self.assertIn("blocked_by", local_tracker)
        self.assertIn("Enregistrer la réponse avant de mettre un ticket à `resolved`", local_tracker)
        bad = self._cli("preview", options=self._options({"tracker": {"mode": "github", "owner": "bad/name", "repo": "app"}}))
        self.assertNotEqual(bad.returncode, 0)

    def test_malformed_markers_and_unmanaged_generated_docs_are_rejected(self) -> None:
        (self.root / "AGENTS.md").write_bytes(project.START + b"\n" + project.START + b"\n" + project.END)
        result = self._cli("preview")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "rejected")
        (self.root / "AGENTS.md").unlink()
        docs = self.root / "docs/agents"
        docs.mkdir(parents=True)
        (docs / "cstack.md").write_text("document de l’utilisateur\n")
        result = self._cli("preview")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "rejected")

    def test_unknown_and_tampered_plan_content_are_rejected(self) -> None:
        options, plan = self._preview()
        unknown = self._cli("preview", options=self._options({"unknown": True}))
        self.assertNotEqual(unknown.returncode, 0)
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        wrong_sha = self._cli("apply", "--plan", str(plan_path), "--expected-plan-sha256", "0" * 64, options=options)
        self.assertNotEqual(wrong_sha.returncode, 0)
        tampered = json.loads(json.dumps(plan))
        tampered["files"][0]["path"] = "CLAUDE.md"
        tampered["plan_sha256"] = project._sha(project._canonical({key: value for key, value in tampered.items() if key != "plan_sha256"}))
        result = self._apply(options, tampered)
        self.assertNotEqual(result.returncode, 0)
        tampered = json.loads(json.dumps(plan))
        tampered["files"][0]["new_content"] += "tampered"
        tampered["files"][0]["new_sha256"] = project._sha(tampered["files"][0]["new_content"].encode())
        tampered["plan_sha256"] = project._sha(project._canonical({key: value for key, value in tampered.items() if key != "plan_sha256"}))
        result = self._apply(options, tampered)
        self.assertNotEqual(result.returncode, 0)

    def test_symlink_parent_and_stale_preview_are_rejected_without_writes(self) -> None:
        workspace_alias = self.root.parent / f"workspace-link-{self.root.name}"
        workspace_alias.symlink_to(self.root, target_is_directory=True)
        try:
            result = subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(workspace_alias), "preview", "--options", str(self._options())], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("workspace", result.stdout)
        finally:
            workspace_alias.unlink(missing_ok=True)
        outside = self.root.parent / f"outside-{self.root.name}"
        outside.mkdir()
        try:
            (self.root / "docs").symlink_to(outside, target_is_directory=True)
            result = self._cli("preview")
            self.assertNotEqual(result.returncode, 0)
        finally:
            (self.root / "docs").unlink(missing_ok=True)
            outside.rmdir()
        options, plan = self._preview()
        (self.root / "AGENTS.md").write_text("modification manuelle\n")
        result = self._apply(options, plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "modification manuelle\n")
        self.assertFalse((self.root / "docs/agents/cstack.md").exists())

    def test_model_choices_use_existing_validator_and_preserve_other_roles(self) -> None:
        state = self.root / ".cstack"
        state.mkdir()
        old = {"feature, refactoring": "gpt-6-astra", "arena runners": ["inherit-parent", "gpt-5.6-luna", "gpt-6-astra"]}
        models_path = state / "models.json"
        models_path.write_text(json.dumps(old), encoding="utf-8")
        before_models = MODELS.read_bytes()
        options, plan = self._preview({"model_choices": {"bug-fix": {"model": "gpt-6-astra", "reasoning_effort": "medium"}}}, catalog=self._catalog())
        self.assertIn(".cstack/models.json", {entry["path"] for entry in plan["files"]})
        result = self._apply(options, plan, catalog=self._catalog())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        saved = json.loads(models_path.read_text())
        self.assertEqual(saved["feature, refactoring"], old["feature, refactoring"])
        self.assertEqual(saved["arena runners"], old["arena runners"])
        self.assertEqual(saved["bug-fix"], {"model": "gpt-6-astra", "reasoning_effort": "medium"})
        self.assertEqual(MODELS.read_bytes(), before_models)
        invalid = self._cli("preview", options=self._options({"model_choices": {"no-such-role": "inherit-parent"}}), catalog=self._catalog())
        self.assertNotEqual(invalid.returncode, 0)
        self.assertEqual(json.loads(models_path.read_text()), saved)

    def test_write_error_rolls_back_and_interruption_can_resume_same_plan(self) -> None:
        options, plan = self._preview()
        original_replace = project.os.replace
        calls = 0

        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("échec d’écriture simulé")
            return original_replace(source, target)

        project.os.replace = fail_second
        try:
            rolled = project.apply_plan(self.root, plan, json.loads(options.read_text()), None)
        finally:
            project.os.replace = original_replace
        self.assertEqual(rolled["status"], "rolled_back")
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "docs/agents/cstack.md").exists())

        calls = 0

        def interrupt_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()
            return original_replace(source, target)

        project.os.replace = interrupt_second
        try:
            with self.assertRaises(project.InterruptedApply):
                project.apply_plan(self.root, plan, json.loads(options.read_text()), None)
        finally:
            project.os.replace = original_replace
        resumed = project.apply_plan(self.root, plan, json.loads(options.read_text()), None)
        self.assertEqual(resumed["status"], "applied")
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertTrue((self.root / "docs/agents/cstack.md").exists())

    def test_manual_edit_during_staging_is_not_overwritten(self) -> None:
        options, plan = self._preview()
        original_temp = project._temp
        injected = False

        def edit_after_first_temp(parent, data, mode):
            nonlocal injected
            temp = original_temp(parent, data, mode)
            if not injected:
                (self.root / "AGENTS.md").write_bytes("modification manuelle pendant la préparation\n".encode("utf-8"))
                injected = True
            return temp

        project._temp = edit_after_first_temp
        try:
            result = project.apply_plan(self.root, plan, json.loads(options.read_text()), None)
        finally:
            project._temp = original_temp
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), "modification manuelle pendant la préparation\n".encode("utf-8"))
        self.assertFalse((self.root / "docs/agents/cstack.md").exists())

    def test_rollback_removes_directories_created_during_staging(self) -> None:
        options, plan = self._preview()
        original_replace = project.os.replace
        calls = 0

        def fail_second(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("échec d’écriture simulé")
            return original_replace(source, target)

        project.os.replace = fail_second
        try:
            rolled = project.apply_plan(self.root, plan, json.loads(options.read_text()), None)
        finally:
            project.os.replace = original_replace
        self.assertEqual(rolled["status"], "rolled_back")
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "docs").exists())
        self.assertFalse((self.root / "docs/agents").exists())

    def test_interrupt_during_staging_reports_partial_and_removes_created_dirs(self) -> None:
        options, plan = self._preview()
        original_temp = project._temp

        calls = 0

        def interrupt(parent, data, mode):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_temp(parent, data, mode)
            raise KeyboardInterrupt()

        project._temp = interrupt
        try:
            with self.assertRaises(project.InterruptedApply) as ctx:
                project.apply_plan(self.root, plan, json.loads(options.read_text()), None)
        finally:
            project._temp = original_temp
        self.assertEqual(ctx.exception.applied, [])
        planned = sorted(entry["path"] for entry in plan["files"] if entry["action"] != "unchanged")
        self.assertEqual(sorted(ctx.exception.skipped), planned)
        self.assertFalse((self.root / "docs").exists())
        self.assertFalse((self.root / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
