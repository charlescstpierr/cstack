import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "behavior-scenarios.py"
SPEC = importlib.util.spec_from_file_location("behavior_scenarios", MODULE_PATH)
behavior_scenarios = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(behavior_scenarios)


class BehaviorScenarioGeneratorTests(unittest.TestCase):
    def test_routing_expectations_match_current_bundle_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cases"
            result = behavior_scenarios.main([
                "--baseline", str(ROOT / "plugins" / "cstack"),
                "--proposed", str(ROOT / "plugins" / "cstack"),
                "--output", str(output),
            ])

            self.assertEqual(result, 0)
            cases = json.loads((output / "cases.json").read_text(encoding="utf-8"))
            expectations = json.loads((output / "expectations.json").read_text(encoding="utf-8"))["cases"]
            self.assertEqual(len(cases), 32)
            self.assertEqual(len(expectations), 32)
            self.assertEqual(len({case["cwd"] for case in cases}), len(cases))
            self.assertTrue(all(Path(case["bundle"]).is_dir() for case in cases))

            routing = {
                case["id"]: case["routing"]
                for case in expectations
                if case["id"].startswith("routing_")
            }
            self.assertEqual(len(routing), 17)
            for case_id, expected in {
                "routing_one_word_user_string": {
                    "expected": ["skills/cstack/playbooks/bug-fix.md"],
                    "forbidden": [
                        "skills/cstack/references/principles/laziness-protocol.md",
                    ],
                },
                "routing_typed_external_boundary": {
                    "expected": [
                        "skills/cstack/references/principles/boundary-discipline.md",
                        "skills/cstack/references/principles/foundational-thinking.md",
                        "skills/cstack/references/principles/type-system-discipline.md",
                    ],
                    "forbidden": [],
                },
                "routing_internal_api_replacement": {
                    "expected": [
                        "skills/cstack/playbooks/refactoring.md",
                        "skills/cstack/references/principles/migrate-callers-then-delete-legacy-apis.md",
                    ],
                    "forbidden": [],
                },
                "routing_live_process_diagnosis": {
                    "expected": ["skills/cstack/playbooks/runtime-forensics.md"],
                    "forbidden": ["skills/cstack/playbooks/trace-forensics.md"],
                },
            }.items():
                self.assertEqual(routing[case_id], expected)
            self.assertIn("skills/arena/SKILL.md", routing["routing_competing_feature_shapes"]["expected"])
            self.assertIn("skills/cstack/playbooks/hillclimb.md", routing["routing_one_off_performance"]["forbidden"])
            for value in routing.values():
                for route in value["expected"] + value["forbidden"]:
                    self.assertFalse(route.startswith("skills/principle-"))
                    self.assertTrue((ROOT / "plugins" / "cstack" / route).is_file())
            for case in expectations:
                if case["id"].startswith("routing_"):
                    self.assertNotIn("expected_children", case)


if __name__ == "__main__":
    unittest.main()
