"""Les choix de modèles résistent à la configuration, aux anciens formats, aux panels et aux écritures refusées."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/cstack/skills/setup-cstack/scripts/models.py"
SPEC = importlib.util.spec_from_file_location("cstack_models", SCRIPT)
models = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(models)
CATALOG = {"gpt-5.6-luna": ["low", "medium", "high", "xhigh", "max"],
           "gpt-6-astra": ["low", "medium", "high", "xhigh", "max", "ultra"]}
RUNTIME_CATALOG = {"runtimes": {
    "codex-native": CATALOG,
    "codex-cli": {"gpt-6-astra": ["low"], "shared-slug": ["high"]},
    "claude-code": {"shared-slug": ["sonnet"], "claude-opus": ["think"]},
    "cursor-agent": {"cursor-agent-default": []},
    "grok": {"grok-code": []},
}}


class ModelSetupTests(unittest.TestCase):
    def test_recommended_setup_resolves_exact_model_and_effort_for_every_role(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cstack/models.json"
            config, digest = models.read_config(path)
            preview = models.preview(config, digest, CATALOG)
            self.assertFalse(path.exists(), "l’aperçu doit rester en lecture seule")
            choices = {}
            expected = {}
            groups = {}
            for name, group in preview["recommendations"].items():
                self.assertIsNone(group["unavailable"])
                choices.update(group["choices"])
                for role, value in group["choices"].items():
                    expected[role] = value
                    groups[role] = name
            saved = models.apply_choices(path, choices, digest, CATALOG)
            self.assertEqual(set(saved), models.ROLES)
            for role, value in expected.items():
                resolved = models.resolve(saved, role, CATALOG)
                if role in models.PANELS:
                    self.assertEqual(resolved, [models.selection(item) for item in value])
                else:
                    self.assertEqual(resolved, [models.selection(value)])
            for role in models.ROLES:
                resolved = models.resolve(saved, role, CATALOG)
                self.assertTrue(all(set(item) == {"model", "reasoning_effort"} for item in resolved))
                self.assertEqual(len(resolved), models.PANELS.get(role, 1))
            development = groups["feature, refactoring"]
            for role in ("bug-fix", "perf-issue", "hillclimb"):
                self.assertEqual(groups[role], development)
                self.assertEqual(models.resolve(saved, role, CATALOG),
                                 models.resolve(saved, "feature, refactoring", CATALOG))

    def test_customization_preserves_legacy_values_and_explicit_inheritance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.json"
            old = {"feature, refactoring": "gpt-6-astra",
                   "arena runners": ["inherit-parent", "gpt-5.6-luna"]}
            path.write_text(json.dumps(old))
            config, digest = models.read_config(path)
            self.assertEqual(models.resolve(config, "simple edits", CATALOG), [{"model": "gpt-6-astra"}])
            new = models.apply_choices(path, {"bug-fix": {"model": "gpt-6-astra", "reasoning_effort": "medium"}}, digest, CATALOG)
            self.assertEqual(new["arena runners"], old["arena runners"])
            self.assertEqual(models.resolve(new, "arena runners", CATALOG), [{}, {"model": "gpt-5.6-luna"}])
            self.assertEqual(models.resolve({}, "architect runners", None), [{}, {}, {}])
            self.assertEqual(models.resolve({}, "arena cross-judge pool", None), [{}])
            self.assertEqual(models.resolve({"simple edits": "inherit-parent", **old}, "simple edits", CATALOG), [{}])

    def test_invalid_choices_and_stale_preview_never_replace_existing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.json"
            path.write_text('{"documentation": "inherit-parent"}\n')
            original = path.read_bytes()
            _, digest = models.read_config(path)
            invalid = [
                {"unknown": "inherit-parent"}, {"bug-fix": []},
                {"arena runners": []}, {"architect runners": ["inherit-parent"]},
                {"bug-fix": {"model": "gpt-6-astra", "reasoning_effort": "imaginary"}},
                {"bug-fix": {"model": "inherit-parent", "reasoning_effort": "low"}},
                {"bug-fix": {"model": "gpt-6-astra", "reasoning_effort": "low", "extra": True}},
                {"bug-fix": {"runtime": "codex-native"}},
                {"bug-fix": {"runtime": "claude"}},
                {"bug-fix": {"runtime": "cursor"}},
                {"bug-fix": {"runtime": "claude-code", "model": None}},
                {"bug-fix": {"runtime": "claude-code", "model": None, "reasoning_effort": "think"}},
                {"bug-fix": {"runtime": "claude-code", "model": "claude-opus", "reasoning_effort": None}},
                {"bug-fix": {"runtime": "claude-code", "reasoning_effort": "think"}},
                {"bug-fix": "unavailable-model"}, {"bug-fix": " "},
            ]
            for choices in invalid:
                with self.subTest(choices=choices), self.assertRaises(ValueError):
                    models.apply_choices(path, choices, digest, CATALOG)
                self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                models.apply_choices(path, {"documentation": "inherit-parent"}, "stale", CATALOG)
            with patch.object(models.os, "replace", side_effect=OSError("échec de sauvegarde simulé")):
                with self.assertRaises(OSError):
                    models.apply_choices(path, {"documentation": "inherit-parent"}, digest, CATALOG)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_malformed_existing_config_is_not_repaired_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.json"
            for raw in ["", "[", "[]", '{"bug-fix":null}', '{"unknown":"inherit-parent"}']:
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    models.apply_choices(path, {}, "unused", CATALOG)
                self.assertEqual(path.read_text(), raw)

    def test_live_catalog_and_missing_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps({"models": [
                {"slug": name, "visibility": "list", "supported_reasoning_levels": [{"effort": level} for level in levels]}
                for name, levels in CATALOG.items()]}))
            self.assertEqual(models.read_catalog(path), CATALOG)
            path.write_text(json.dumps(RUNTIME_CATALOG))
            self.assertEqual(models.read_catalog(path), RUNTIME_CATALOG)
        preview = models.preview({}, "unused", None)
        self.assertTrue(all(group["unavailable"] for group in preview["recommendations"].values()))
        with self.assertRaises(ValueError):
            models.resolve({"bug-fix": "gpt-6-astra"}, "bug-fix", None)
        self.assertEqual(models.resolve({"bug-fix": "inherit-parent"}, "bug-fix", None), [{}])

    def test_runtime_selections_are_preserved_and_scoped_to_their_catalog(self):
        runtime_only = {"bug-fix": {"runtime": "claude-code"}}
        models.validate(runtime_only, None, check_available=True)
        self.assertEqual(models.resolve(runtime_only, "bug-fix", None),
                         [{"runtime": "claude-code"}])
        explicit = {"bug-fix": {"runtime": "claude-code", "model": "shared-slug", "reasoning_effort": "sonnet"}}
        self.assertEqual(models.resolve(explicit, "bug-fix", RUNTIME_CATALOG),
                         [{"runtime": "claude-code", "model": "shared-slug", "reasoning_effort": "sonnet"}])
        with self.assertRaises(ValueError):
            models.resolve(explicit, "bug-fix", {"shared-slug": ["sonnet"]})
        with self.assertRaises(ValueError):
            models.resolve({"bug-fix": {"runtime": "claude-code", "model": "shared-slug", "reasoning_effort": "high"}},
                           "bug-fix", RUNTIME_CATALOG)
        with self.assertRaises(ValueError):
            models.resolve({"bug-fix": {"runtime": "claude-code", "model": "gpt-6-astra"}},
                           "bug-fix", RUNTIME_CATALOG)

    def test_mixed_panel_keeps_legacy_native_and_runtime_entries(self):
        config = {"interrogate reviewers": [
            "inherit-parent",
            {"model": "gpt-6-astra", "reasoning_effort": "low"},
            {"runtime": "grok"},
            {"runtime": "claude-code", "model": "claude-opus", "reasoning_effort": "think"},
            {"runtime": "cursor-agent"},
        ]}
        self.assertEqual(models.resolve(config, "interrogate reviewers", RUNTIME_CATALOG), [
            {},
            {"model": "gpt-6-astra", "reasoning_effort": "low"},
            {"runtime": "grok"},
            {"runtime": "claude-code", "model": "claude-opus", "reasoning_effort": "think"},
            {"runtime": "cursor-agent"},
        ])

    def test_symlinked_state_does_not_write_outside_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external"
            external.mkdir()
            state = root / ".cstack"
            state.symlink_to(external, target_is_directory=True)
            path = state / "models.json"
            _, digest = models.read_config(path)
            with self.assertRaises(ValueError):
                models.apply_choices(path, {"documentation": "inherit-parent"}, digest, None)
            self.assertEqual(list(external.iterdir()), [])

    def test_apply_creates_cstack_gitignore_without_clobbering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cstack/models.json"
            _, digest = models.read_config(path)
            models.apply_choices(path, {"documentation": "inherit-parent"}, digest, None)
            ignore = path.parent / ".gitignore"
            self.assertEqual(ignore.read_text(), "*\n")
            ignore.write_text("keep\n")
            _, digest = models.read_config(path)
            models.apply_choices(path, {"simple edits": "inherit-parent"}, digest, None)
            self.assertEqual(ignore.read_text(), "keep\n")


if __name__ == "__main__":
    unittest.main()
