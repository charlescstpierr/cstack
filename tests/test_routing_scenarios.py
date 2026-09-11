import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "routing-scenarios.py"
SPEC = importlib.util.spec_from_file_location("routing_scenarios", MODULE_PATH)
routing_scenarios = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing_scenarios)
VERIFY_PATH = ROOT / "scripts" / "verify-behavior.py"
VERIFY_SPEC = importlib.util.spec_from_file_location("verify_behavior", VERIFY_PATH)
verify_behavior = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(verify_behavior)


CATALOG = {
    "local-fast": ["low", "medium"],
    "local-deep": ["high", "max"],
}


class RoutingScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.baseline = self._plugin("input-a")
        self.proposed = self._plugin("input-b")
        self.catalog = self.root / "catalog.json"
        self.catalog.write_text(json.dumps(CATALOG))

    def tearDown(self):
        self.temp.cleanup()

    def _plugin(self, name: str) -> Path:
        root = self.root / name
        for spec in routing_scenarios.fixture_specs():
            skill = root / "skills" / spec["skill"]
            skill.mkdir(parents=True, exist_ok=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {spec['skill']}\ndescription: local skill\n---\n\n# {spec['skill']}\n\nDo the requested local work.\n"
            )
        return root

    def _run(self, *extra: str) -> Path:
        output = self.root / f"out-{len(list(self.root.glob('out-*')))}"
        argv = ["--baseline", str(self.baseline), "--proposed", str(self.proposed),
                "--output", str(output), "--catalog", str(self.catalog), *extra]
        self.assertEqual(routing_scenarios.main(argv), 0)
        return output

    def test_generates_neutral_harness_cases_with_clean_isolated_git_roots(self):
        role_models = self.root / "roles.json"
        role_models.write_text(json.dumps({"bug-fix": {"model": "local-fast", "reasoning_effort": "medium"}}))
        output = self._run("--role-models", str(role_models))
        cases = json.loads((output / "cases.json").read_text())
        expectations = json.loads((output / "expectations.json").read_text())
        self.assertEqual(len(cases), 30)
        parsed = verify_behavior.read_cases(output / "cases.json")
        self.assertEqual(len(parsed), 30)
        self.assertTrue(all(case["ephemeral"] is False for case in cases))
        self.assertTrue(all(case["ephemeral"] is False for case in parsed))
        self.assertEqual(len(expectations["cases"]), 30)
        self.assertEqual({row["variant"] for row in expectations["cases"]},
                         {"shippedbaseline", "minimal_call_control", "proposedriskaware"})
        self.assertTrue(all("expected_children" not in row for row in expectations["cases"]))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertRegex(case["id"], r"^case_\d\d_[abc]$")
                self.assertIn("Use $cstack:cstack.", case["prompt"])
                self.assertNotRegex(case["prompt"], r"evaluation|judge|candidate|baseline|proposed|minimal")
                status = subprocess.check_output(["git", "status", "--porcelain"], cwd=case["cwd"], text=True)
                self.assertEqual(status, "")
        control_skill = (output / "resources/cedar/skills/cstack/SKILL.md").read_text()
        self.assertTrue(control_skill.startswith("---\nname: cstack\n"))
        self.assertIn("## Local Routing Policy", control_skill.split("---", 2)[2])
        self.assertIn("local-fast", json.dumps(expectations["cases"]))

    def test_fixture_groundtruth_matches_seeded_behavior(self):
        output = self._run()
        by_class = {row["fixture_class"]: row for row in json.loads((output / "expectations.json").read_text())["cases"]}
        trivial = Path(json.loads((output / "cases.json").read_text())[0]["cwd"])
        namespace = {}
        exec((trivial / "calc.py").read_text(), namespace)
        self.assertEqual(namespace["total"]([2, 3, 5]), 5)
        self.assertIn("total([2, 3, 5]) returns 10", by_class["triviallocalbug"]["required_outputs"])

        regression_case = next(row for row in json.loads((output / "cases.json").read_text()) if row["id"] == "case_02_a")
        regression = Path(regression_case["cwd"])
        log = subprocess.check_output(["git", "log", "--oneline"], cwd=regression, text=True)
        self.assertIn("change local behavior", log)
        namespace = {}
        exec((regression / "parser.py").read_text(), namespace)
        self.assertEqual(namespace["parse_count"](""), 0)
        self.assertEqual(by_class["historydependentregression"]["classification"], "read_only_history_cause")

    def test_stateful_and_migration_contracts_are_real_seed_failures(self):
        output = self._run()
        cases = json.loads((output / "cases.json").read_text())
        stateful = Path(next(row for row in cases if row["id"] == "case_04_a")["cwd"])
        migration = Path(next(row for row in cases if row["id"] == "case_10_a")["cwd"])
        self.assertNotEqual(subprocess.run(["python3", "verify_reservations.py"], cwd=stateful).returncode, 0)
        self.assertNotEqual(subprocess.run(["python3", "verify_migration.py"], cwd=migration).returncode, 0)
        truth = {row["fixture_class"]: row for row in json.loads((output / "expectations.json").read_text())["cases"]}
        self.assertEqual(truth["statefulmoduleboundary"]["classification"], "stateful_cross_module_fix")
        self.assertEqual(truth["multiphasemigration"]["classification"], "multi_module_data_shape_migration")

    def test_inputs_and_existing_output_are_not_modified(self):
        before_baseline = routing_scenarios.behavior.tree_hash(self.baseline)
        before_proposed = routing_scenarios.behavior.tree_hash(self.proposed)
        output = self._run()
        self.assertEqual(routing_scenarios.behavior.tree_hash(self.baseline), before_baseline)
        self.assertEqual(routing_scenarios.behavior.tree_hash(self.proposed), before_proposed)
        marker = output / "marker.txt"
        marker.write_text("keep")
        with self.assertRaises(SystemExit):
            routing_scenarios.main(["--baseline", str(self.baseline), "--proposed", str(self.proposed),
                                    "--output", str(output), "--catalog", str(self.catalog)])
        self.assertEqual(marker.read_text(), "keep")

    def test_invalid_role_models_fail_before_output_write(self):
        role_models = self.root / "roles.json"
        role_models.write_text(json.dumps({"bug-fix": {"model": "missing", "reasoning_effort": "medium"}}))
        output = self.root / "bad-out"
        with self.assertRaises(SystemExit):
            routing_scenarios.main(["--baseline", str(self.baseline), "--proposed", str(self.proposed),
                                    "--output", str(output), "--catalog", str(self.catalog),
                                    "--role-models", str(role_models)])
        self.assertFalse(output.exists())

    def test_invalid_inputs_fail_before_output_write(self):
        output = self.root / "bad-input-out"
        with self.assertRaises(SystemExit):
            routing_scenarios.main(["--baseline", str(self.root / "missing"), "--proposed", str(self.proposed),
                                    "--output", str(output)])
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
