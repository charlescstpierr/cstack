"""Model choices survive setup, legacy configs, panels and rejected writes."""

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


class ModelSetupTests(unittest.TestCase):
    def test_recommended_setup_resolves_exact_model_and_effort_for_every_role(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".cstack/models.json"
            config, digest = models.read_config(path)
            preview = models.preview(config, digest, CATALOG)
            self.assertFalse(path.exists(), "preview must be read-only")
            choices = {}
            for group in preview["recommendations"].values():
                self.assertIsNone(group["unavailable"])
                choices.update(group["choices"])
            saved = models.apply_choices(path, choices, digest, CATALOG)
            self.assertEqual(set(saved), models.ROLES)
            expected = {
                "how explorer": ("gpt-5.6-luna", "max"),
                "simple edits": ("gpt-5.6-luna", "max"),
                "feature, refactoring": ("gpt-6-astra", "low"),
                "bug-fix": ("gpt-6-astra", "medium"),
                "judgment and prose": ("gpt-6-astra", "low"),
                "hardest tasks": ("gpt-6-astra", "xhigh"),
                "documentation": ("gpt-5.6-luna", "max"),
            }
            for role, (model, effort) in expected.items():
                self.assertEqual(models.resolve(saved, role, CATALOG),
                                 [{"model": model, "reasoning_effort": effort}])
            for role in models.ROLES:
                resolved = models.resolve(saved, role, CATALOG)
                self.assertTrue(all(set(item) == {"model", "reasoning_effort"} for item in resolved))
                self.assertEqual(len(resolved), models.PANELS.get(role, 1))

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
                {"bug-fix": "unavailable-model"}, {"bug-fix": " "},
            ]
            for choices in invalid:
                with self.subTest(choices=choices), self.assertRaises(ValueError):
                    models.apply_choices(path, choices, digest, CATALOG)
                self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                models.apply_choices(path, {"documentation": "inherit-parent"}, "stale", CATALOG)
            with patch.object(models.os, "replace", side_effect=OSError("simulated failed save")):
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
        preview = models.preview({}, "unused", None)
        self.assertTrue(all(group["unavailable"] for group in preview["recommendations"].values()))
        with self.assertRaises(ValueError):
            models.resolve({"bug-fix": "gpt-6-astra"}, "bug-fix", None)
        self.assertEqual(models.resolve({"bug-fix": "inherit-parent"}, "bug-fix", None), [{}])

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


if __name__ == "__main__":
    unittest.main()
