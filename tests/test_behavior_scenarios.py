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
    def test_generated_cases_use_persistent_threads_for_native_delegation(self):
        with tempfile.TemporaryDirectory() as directory:
            cases, expectations = [], []
            behavior_scenarios.register(
                cases, expectations, case_id="delegated-fix", project=Path(directory),
                bundle=ROOT / "plugins" / "cstack", skill="cstack", roles=[],
                body="Correct the user message locally.", expected_children=1,
            )
            self.assertIs(cases[0].get("ephemeral"), False)

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
            self.assertEqual(len(cases), 24)
            self.assertEqual(len(expectations), 24)
            self.assertEqual(len({case["cwd"] for case in cases}), len(cases))

            routing = {
                case["id"]: case["routing"]
                for case in expectations
                if case["id"].startswith("routing_")
            }
            self.assertEqual(routing, {
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
            })
            for value in routing.values():
                for route in value["expected"] + value["forbidden"]:
                    self.assertFalse(route.startswith("skills/principle-"))
                    self.assertTrue((ROOT / "plugins" / "cstack" / route).is_file())
            for case in expectations:
                if case["id"].startswith("routing_"):
                    self.assertNotIn("expected_children", case)

            by_id = {case["id"]: case for case in expectations}
            arena = by_id["arena_verified_selection"]
            self.assertEqual(arena["expected_children"], 5)
            self.assertEqual(len(arena["role_metadata"]["arena runners"]), 3)
            self.assertEqual(len(arena["role_metadata"]["arena cross-judge pool"]), 1)
            authoring = by_id["authoring_rule_baseline_first"]
            self.assertEqual(authoring["routing"], {
                "expected": [
                    "skills/cstack/playbooks/authoring-a-skill.md",
                    "skills/cstack/references/rule-pressure-tests.md",
                ],
                "forbidden": [],
            })
            self.assertEqual(authoring["min_children"], 2)
            self.assertNotIn("expected_children", authoring)
            self.assertEqual(authoring["expected_artifacts"], [
                ".cstack/tasks/*/pressure/base.md",
                ".cstack/tasks/*/pressure/regle-1.md",
            ])
            verification = next(case for case in cases if case["id"] == "create_verification_cli_verdicts")
            self.assertIn("pilote la fonctionnalité sync, sans NOTES_TOKEN", verification["prompt"])
            for case_id in ("interrogate_partial_set_baseline", "interrogate_partial_set_proposed"):
                self.assertEqual(by_id[case_id]["expected_children"], 3)
                project = Path(next(case["cwd"] for case in cases if case["id"] == case_id))
                self.assertIn("legacy_total", (project / "src" / "reports.py").read_text(encoding="utf-8"))
                self.assertNotIn("legacy_total", (project / "src" / "billing.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
