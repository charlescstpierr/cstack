import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "behavior-scenarios.py"
SPEC = importlib.util.spec_from_file_location("behavior_scenarios", MODULE_PATH)
behavior_scenarios = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(behavior_scenarios)
RUNNER_SPEC = importlib.util.spec_from_file_location("verify_behavior", ROOT / "scripts/verify-behavior.py")
verify_behavior = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(verify_behavior)


class BehaviorScenarioGeneratorTests(unittest.TestCase):
    def test_generated_provenance_rejects_changed_project_bundle_and_skill_before_launch(self):
        for mutation in ("project", "bundle", "skill"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = behavior_scenarios.create_project(root, "alder", {"events.py": "original"}, [])
                bundle = root / "bundle"
                skill = bundle / "skills/cstack/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("original skill")
                cases, expectations = [], []
                behavior_scenarios.register(cases, expectations, case_id="one", project=project,
                    bundle=bundle, skill="cstack", roles=[], body="Read the code.")
                if mutation == "project":
                    (project / ".cstack/models.json").write_text('{"changed":true}')
                elif mutation == "bundle":
                    (bundle / "extra.txt").write_text("changed")
                else:
                    skill.write_text("changed skill")
                    # Keep the bundle digest current to exercise the skill hash separately.
                    expectations[0]["source_sha256"]["bundle"] = behavior_scenarios.tree_hash(bundle)
                case_path, expected_path = root / "cases.json", root / "expectations.json"
                case_path.write_text(json.dumps(cases))
                expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations}))
                with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                     patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                    with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte"):
                        verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                                              "--output", str(root / "results"), "--repeats", "2"])
                    launch.assert_not_called()
                self.assertFalse((root / "results").exists())

    def test_provenance_uses_generator_hash_and_selected_cases_for_repeats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            skill = bundle / "skills/cstack/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("original skill")
            cases, expectations = [], []
            for name in ("one", "two"):
                project = behavior_scenarios.create_project(root, name, {"events.py": "original"}, [])
                behavior_scenarios.register(cases, expectations, case_id=name, project=project,
                    bundle=bundle, skill="cstack", roles=[], body="Read the code.")
                self.assertEqual(verify_behavior.tree_hash(project, None)["sha256"], expectations[-1]["project_sha256"])
            (Path(cases[1]["cwd"]) / "events.py").write_text("stale unselected project")
            case_path, expected_path = root / "cases.json", root / "expectations.json"
            case_path.write_text(json.dumps(cases))
            expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations[:1]}))
            old_expectation = dict(expectations[0])
            old_expectation.pop("skill_path")
            old_case = verify_behavior.read_cases(case_path)[0]
            verify_behavior.verify_provenance(old_case, old_expectation)
            old_case["prompts"] = ["No source path supplied."]
            with self.assertRaisesRegex(verify_behavior.HarnessError, "skill_path"):
                verify_behavior.verify_provenance(old_case, old_expectation)
            verify_behavior.verify_provenance(old_case, {"id": "one"})

            def complete(case, *args):
                self.assertEqual(verify_behavior.tree_hash(case["cwd"], None)["sha256"], expectations[0]["project_sha256"])
                (case["cwd"] / "events.py").write_text("changed during run")
                return {"id": case["id"], "cwd": str(case["cwd"]), "status": "completed", "native_child_thread_ids": []}

            with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", side_effect=complete) as launch:
                code = verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                    "--case-id", "one", "--output", str(root / "results"), "--repeats", "2"])
            self.assertEqual(code, 0)
            self.assertEqual(launch.call_count, 2)
            self.assertEqual((Path(cases[0]["cwd"]) / "events.py").read_text(), "original")

            def change_source_after_first_run(case, *args):
                skill.write_text("source changed between repeats")
                return {"id": case["id"], "cwd": str(case["cwd"]), "status": "completed", "native_child_thread_ids": []}

            with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", side_effect=change_source_after_first_run) as launch:
                with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte bundle"):
                    verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                        "--case-id", "one", "--output", str(root / "source-drift"), "--repeats", "2"])
                self.assertEqual(launch.call_count, 1, "source drift must block the next native launch")

    def test_frozen_outcomes_reject_early_exit_and_optimized_wrong_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases, expectations = behavior_scenarios.build_cases(
                ROOT / "plugins/cstack", ROOT / "plugins/cstack", root, None)
            projects = {case["id"]: Path(case["cwd"]) for case in cases}
            by_id = {row["id"]: row for row in expectations}
            for case_id, filename, valid, wrong in (
                ("clear_python_correction_proposed", "events.py",
                 'def filter_events(events, start, today):\n    return [e for e in events if start <= e["date"] <= today]\n',
                 'def filter_events(events, start, today):\n    return []\n'),
                ("routing_one_word_user_string", "src/errors.py",
                 'def fail(code):\n    return f"Error: could not process invoice {code}"\n',
                 'def fail(code):\n    return "wrong"\n'),
            ):
                check = by_id[case_id]["outcome_checks"][0]
                target = projects[case_id] / filename
                early = wrong.replace('return []', 'raise SystemExit(0)').replace('return "wrong"', 'raise SystemExit(0)')
                candidates = [("early-exit", early, False), ("optimized", wrong, True), ("correct", valid, True)]
                if filename == "events.py":
                    candidates.append(("boolean-date", 'def filter_events(events, start, today):\n'
                        '    return [{"date": True}, {"date": 2}]\n', False))
                for label, code, optimized in candidates:
                    with self.subTest(case_id=case_id, label=label):
                        target.write_text(code)
                        env = dict(os.environ, PYTHONOPTIMIZE="1" if optimized else "0", PYTHONDONTWRITEBYTECODE="1")
                        with patch.dict(os.environ, env):
                            report = verify_behavior.evaluate_case(
                                {"status": "completed", "cwd": str(projects[case_id])},
                                {"outcome_checks": [check]}, verify_outcomes=True)
                        self.assertEqual(report["outcome"]["status"], "pass" if label == "correct" else "fail",
                                         f"{label}: {report['outcome']}")

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
            validated = verify_behavior.read_expectations(output / "expectations.json")
            for case in verify_behavior.read_cases(output / "cases.json"):
                verify_behavior.verify_provenance(case, validated[case["id"]])
            self.assertEqual(len(cases), 37)
            self.assertEqual(len(expectations), 37)
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

            by_id = {case["id"]: case for case in expectations}
            arena = by_id["arena_verified_selection"]
            self.assertEqual(arena["expected_children"], 5)
            self.assertEqual(len(arena["role_metadata"]["arena runners"]), 3)
            self.assertEqual(len(arena["role_metadata"]["arena cross-judge pool"]), 1)
            for case_id in ("clear_python_correction_baseline", "clear_python_correction_proposed", "routing_one_word_user_string"):
                self.assertTrue(by_id[case_id]["outcome_checks"])
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
