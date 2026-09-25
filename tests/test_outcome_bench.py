import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "outcome-bench.py"
SPEC = importlib.util.spec_from_file_location("outcome_bench", MODULE_PATH)
outcome_bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outcome_bench)

BUGGY = "def add(a, b):\n    return a - b\n\n\ndef neg(a):\n    return -a\n"
FIXED = "def add(a, b):\n    return a + b\n\n\ndef neg(a):\n    return -a\n"
NEG_TEST = "from calc import neg\nassert neg(2) == -2\n"
ADD_TEST = "from calc import add\nassert add(2, 3) == 5\n"


def git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def local_test(image, workdir, command, timeout):
    result = subprocess.run(["sh", "-c", command], cwd=workdir, capture_output=True, text=True, timeout=timeout)
    return {"passed": result.returncode == 0, "exit_code": result.returncode, "timed_out": False, "tail": ""}


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        upstream = root / "upstream"
        upstream.mkdir()
        git(upstream, "init", "-q", "-b", "main")
        (upstream / "calc.py").write_text(BUGGY)
        (upstream / "tests").mkdir()
        (upstream / "tests" / "test_neg.py").write_text(NEG_TEST)
        git(upstream, "add", ".")
        git(upstream, "commit", "-q", "-m", "base")
        self.base = git(upstream, "rev-parse", "HEAD")
        (upstream / "calc.py").write_text(FIXED)
        (upstream / "tests" / "test_add.py").write_text(ADD_TEST)
        git(upstream, "add", ".")
        git(upstream, "commit", "-q", "-m", "fix add")
        self.fix = git(upstream, "rev-parse", "HEAD")
        self.tasks = root / "suite"
        self.task_dir = self.tasks / "tasks" / "calc-add"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "Dockerfile").write_text("FROM python:3.12-slim\n")
        self.task = {
            "id": "calc-add", "repo": upstream.resolve().as_uri(), "source": "fixture",
            "language": "python", "kind": "bug", "base_sha": self.base, "fix_sha": self.fix,
            "merged_at": "2026-09-01T00:00:00Z",
            "prompt": "add() soustrait au lieu d’additionner. Corrige la fonction.",
            "hidden_paths": ["tests/test_add.py"],
            "fail_to_pass": [{"id": "add", "command": "PYTHONPATH=. python3 tests/test_add.py"}],
            "pass_to_pass": [{"id": "neg", "command": "PYTHONPATH=. python3 tests/test_neg.py"}],
        }
        self.write()

    def write(self, **changes):
        task = dict(self.task, **changes)
        (self.task_dir / "task.json").write_text(json.dumps(task))
        (self.tasks / "suite.json").write_text(json.dumps({"merged_after": "2026-06-01", "tasks": ["calc-add"]}))

    def load(self):
        return outcome_bench.load_suite(self.tasks)[1][0]


class FakeRunner:
    def __init__(self, edit, commands=None):
        self.edit = edit
        self.commands = commands or []
        self.cases = []
        self.seen_models = []

    def run_case(self, case, output, command, model, effort, timeout):
        self.cases.append(case)
        models = Path(case["cwd"]) / ".cstack" / "models.json"
        self.seen_models.append(json.loads(models.read_text()) if models.exists() else None)
        self.edit(Path(case["cwd"]))
        return {
            "actual_commands": self.commands,
            "status": "completed", "wall_seconds": 1.5, "questions": [], "native_child_thread_ids": ["c1"],
            "after_turn_actual_metadata": [{"token_usage": [{"total": {"totalTokens": 100}}]}],
            "child_metadata": [{"thread_id": "c1", "token_usage": [{"total": {"totalTokens": 40}}]}],
        }


class OutcomeBenchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.fixture = Fixture(self.root)
        self.work = self.root / "work"

    def tearDown(self):
        self.directory.cleanup()

    def test_task_schema_rejects_unsafe_or_contaminated_tasks(self):
        self.assertEqual(self.fixture.load()["id"], "calc-add")
        cases = {
            "fusionné avant": {"merged_at": "2026-01-01T00:00:00Z"},
            "libellé de mesure": {"prompt": "Corrige add() pour le benchmark."},
            "hors du dépôt": {"hidden_paths": ["../secret.py"]},
            "fail_to_pass": {"fail_to_pass": []},
            "SHA complet": {"base_sha": "abc"},
        }
        for message, change in cases.items():
            with self.subTest(message=message):
                self.fixture.write(**change)
                with self.assertRaisesRegex(outcome_bench.BenchError, message):
                    self.fixture.load()
        self.fixture.write()
        (self.fixture.task_dir / "Dockerfile").unlink()
        with self.assertRaisesRegex(outcome_bench.BenchError, "Dockerfile"):
            self.fixture.load()

    def test_workspace_holds_base_history_but_never_the_fix(self):
        task = self.fixture.load()
        source = outcome_bench.mirror(task, self.work)
        workspace = outcome_bench.checkout(source, task["base_sha"], self.work / "ws", history=True)
        self.assertEqual(git(workspace, "rev-parse", "HEAD"), self.fixture.base)
        missing = subprocess.run(["git", "cat-file", "-e", self.fixture.fix], cwd=workspace)
        self.assertNotEqual(missing.returncode, 0)
        self.assertEqual(git(workspace, "remote"), "")
        self.assertFalse((workspace / "tests" / "test_add.py").exists())

    def test_validation_accepts_real_red_green_and_rejects_already_green_task(self):
        with patch.object(outcome_bench, "run_test", local_test), \
                patch.object(outcome_bench, "build_image", return_value="image"):
            receipt = outcome_bench.validate_task(self.fixture.load(), self.work)
            self.assertTrue(receipt["valid"], receipt["problems"])
            self.fixture.write(fail_to_pass=[{"id": "neg", "command": "PYTHONPATH=. python3 tests/test_neg.py"}])
            receipt = outcome_bench.validate_task(self.fixture.load(), self.work)
        self.assertFalse(receipt["valid"])
        self.assertIn("fail_to_pass:neg passe déjà sur la base", receipt["problems"])

    def test_plan_is_seeded_balanced_and_interleaved(self):
        tasks = [{"id": "a"}, {"id": "b"}]
        first = outcome_bench.plan_runs(tasks, 3, 7)
        self.assertEqual(first, outcome_bench.plan_runs(tasks, 3, 7))
        self.assertNotEqual([run["run_id"] for run in first], [run["run_id"] for run in outcome_bench.plan_runs(tasks, 3, 8)])
        self.assertEqual(len(first), 12)
        for arm in outcome_bench.DEFAULT_ARMS:
            self.assertEqual(sum(run["arm"] == arm for run in first), 6)
        three = outcome_bench.plan_runs(tasks, 3, 7, outcome_bench.ARMS)
        self.assertEqual(len(three), 18)
        self.assertEqual(sum(run["arm"] == "pstack" for run in three), 6)

    def test_arms_share_the_request_and_each_package_adds_only_its_entry(self):
        task = self.fixture.load()
        pstack = self.root / "pstack"
        (pstack / "skills" / "poteto-mode").mkdir(parents=True)
        bundles = {"cstack": ROOT / "plugins" / "cstack", "pstack": pstack}
        vanilla = outcome_bench.arm_prompt(task, "vanilla", bundles)
        cstack = outcome_bench.arm_prompt(task, "cstack", bundles)
        poteto = outcome_bench.arm_prompt(task, "pstack", bundles)
        self.assertIn(task["prompt"], vanilla)
        self.assertIn(outcome_bench.SCOPE_NOTE, vanilla)
        self.assertNotIn("$cstack", vanilla)
        for prompt in (cstack, poteto):
            self.assertIn(vanilla, prompt)
            self.assertRegex(prompt, "(?i)d[ée]l[èe]gu|delegate")
        self.assertIn("$cstack:cstack", cstack)
        self.assertIn(str(bundles["cstack"] / "skills" / "cstack" / "SKILL.md"), cstack)
        self.assertIn(str(pstack / "skills" / "poteto-mode" / "SKILL.md"), poteto)
        self.assertNotIn("$cstack", poteto)

    def run_with(self, edit, arm="vanilla", base="vanilla", models=None, commands=()):
        task = self.fixture.load()
        runner = FakeRunner(edit, list(commands))
        context = {
            "output": self.root / "out", "work": self.work, "bundles": {"cstack": ROOT / "plugins" / "cstack"},
            "runner": runner, "command": [], "model": None, "effort": None, "turn_timeout": 10,
            "arm_bases": {arm: base}, "arm_models": {arm: models} if models is not None else {},
        }
        run = {"run_id": f"calc-add--{arm}--r1", "task_id": "calc-add", "arm": arm, "repetition": 1}
        with patch.object(outcome_bench, "run_test", local_test):
            return outcome_bench.execute_run(run, task, "image", context), runner

    def test_correct_fix_resolves_and_metrics_are_recorded(self):
        row, runner = self.run_with(lambda cwd: (cwd / "calc.py").write_text(FIXED))
        self.assertTrue(row["resolved"])
        self.assertEqual(row["tokens"], 140)
        self.assertEqual(row["tokens_source"], "per_thread")
        self.assertEqual(row["children"], 1)
        self.assertEqual(row["diff"]["files_changed"], 1)
        self.assertEqual(row["diff"]["files_outside_reference"], [])
        self.assertNotIn("$cstack", runner.cases[0]["prompts"][0])

    def test_hidden_tests_overwrite_agent_edits_and_regressions_fail(self):
        def cheat(cwd):
            (cwd / "tests" / "test_add.py").write_text("pass\n")
            (cwd / "notes.md").write_text("x\n")
        row, _ = self.run_with(cheat)
        self.assertFalse(row["resolved"])
        self.assertEqual(row["diff"]["hidden_paths_touched"], ["tests/test_add.py"])
        self.assertEqual(row["diff"]["files_outside_reference"], ["notes.md"])

        def break_neg(cwd):
            (cwd / "calc.py").write_text(FIXED.replace("return -a", "return a"))
        row, _ = self.run_with(break_neg)
        self.assertFalse(row["resolved"])
        self.assertFalse(row["tests"]["pass_to_pass:neg"]["passed"])

    def test_agent_commits_are_graded_and_state_dir_is_ignored(self):
        def commit_fix(cwd):
            (cwd / "calc.py").write_text(FIXED)
            (cwd / ".cstack").mkdir()
            (cwd / ".cstack" / "models.json").write_text("{}")
            git(cwd, "commit", "-qam", "fix")
        row, _ = self.run_with(commit_fix)
        self.assertTrue(row["resolved"])
        self.assertEqual(row["diff"]["files_changed"], 1)

    def test_token_metrics_fall_back_when_a_child_is_unobserved(self):
        result = {
            "native_child_thread_ids": ["c1", "c2"],
            "after_turn_actual_metadata": [{"total": {"totalTokens": 10}}],
            "child_metadata": [{"token_usage": [{"total": {"totalTokens": 5}}]}],
            "token_usage": [{"total": {"totalTokens": 30}}],
        }
        self.assertEqual(outcome_bench.token_metrics(result), {"tokens": 30, "tokens_source": "stream_max"})
        self.assertEqual(outcome_bench.token_metrics({}), {"tokens": None, "tokens_source": "unknown"})

    def test_summary_pairs_tasks_and_excludes_infra_errors(self):
        def row(task, arm, resolved, status="completed", tokens=100):
            return {"task_id": task, "arm": arm, "resolved": resolved, "agent_status": status, "tokens": tokens,
                    "wall_seconds": 2, "children": 0, "questions": 0,
                    "diff": {"lines_added": 1, "lines_removed": 1, "hidden_paths_touched": []}}
        rows = [
            row("a", "vanilla", False), row("a", "cstack", True, tokens=300),
            row("b", "vanilla", True), row("b", "cstack", True),
            row("b", "cstack", False, status="infra_error"),
        ]
        summary = outcome_bench.summarize(rows)
        self.assertEqual(summary["arms"]["cstack"]["runs"], 2)
        self.assertEqual(summary["arms"]["cstack"]["infra_errors"], 1)
        self.assertEqual(summary["arms"]["cstack"]["tokens_per_resolved"], 200)
        self.assertEqual(summary["paired"], {
            "cstack_vs_vanilla": {"tasks": 2, "cstack_better": 1, "vanilla_better": 0, "ties": 1},
        })

    def test_summary_compares_every_pair_of_present_arms(self):
        rows = [
            {"task_id": "a", "arm": arm, "resolved": resolved, "agent_status": "completed", "tokens": 1,
             "wall_seconds": 1, "diff": {"lines_added": 0, "lines_removed": 0, "hidden_paths_touched": []}}
            for arm, resolved in (("vanilla", False), ("cstack", False), ("pstack", True))
        ]
        paired = outcome_bench.summarize(rows)["paired"]
        self.assertEqual(sorted(paired), ["cstack_vs_vanilla", "pstack_vs_cstack", "pstack_vs_vanilla"])
        self.assertEqual(paired["pstack_vs_cstack"]["pstack_better"], 1)

    def test_pstack_fetch_accepts_only_the_pinned_inventory(self):
        upstream = self.root / "plugins-upstream"
        (upstream / "pstack" / "skills" / "poteto-mode").mkdir(parents=True)
        (upstream / "pstack" / "skills" / "poteto-mode" / "SKILL.md").write_text("# Poteto mode\n")
        (upstream / "other.txt").write_text("hors paquet\n")
        git(upstream, "init", "-q", "-b", "main")
        git(upstream, "add", ".")
        git(upstream, "commit", "-q", "-m", "pstack")
        commit = git(upstream, "rev-parse", "HEAD")
        blob = git(upstream, "rev-parse", "HEAD:pstack/skills/poteto-mode/SKILL.md")
        pin = {"repository": upstream.resolve().as_uri(), "commit": commit, "subdirectory": "pstack",
               "blobs": {"pstack/skills/poteto-mode/SKILL.md": blob}}
        with patch.object(outcome_bench, "upstream_pin", return_value=pin):
            root = outcome_bench.fetch_pstack(self.work)
            self.assertEqual(root, outcome_bench.default_pstack(self.work))
            self.assertTrue((root / "skills" / "poteto-mode" / "SKILL.md").is_file())
            pin["blobs"] = {"pstack/skills/poteto-mode/SKILL.md": "0" * 40}
            with self.assertRaisesRegex(outcome_bench.BenchError, "UPSTREAM.json"):
                outcome_bench.fetch_pstack(self.work)

    def test_arm_specs_accept_named_cstack_variants_only(self):
        arms = outcome_bench.parse_arms("vanilla,cstack,cstack-mixed=cstack:panels.json")
        self.assertEqual([(arm["name"], arm["base"]) for arm in arms],
                         [("vanilla", "vanilla"), ("cstack", "cstack"), ("cstack-mixed", "cstack")])
        self.assertEqual(arms[2]["models"], Path("panels.json"))
        for text, message in (
            ("vanilla,pstack=pstack:m.json", "seule une base cstack"),
            ("vanilla=vanilla:m.json,cstack", "seule une base cstack"),
            ("cstack,cstack", "noms distincts"),
            ("vanilla,bad name=cstack", "bras invalide"),
            ("vanilla,x=claude", "bras invalide"),
        ):
            with self.subTest(text=text), self.assertRaisesRegex(outcome_bench.BenchError, message):
                outcome_bench.parse_arms(text)

    def test_arm_models_are_validated_with_the_setup_helper(self):
        good = self.root / "mixed.json"
        good.write_text(json.dumps({"interrogate reviewers": [{"runtime": "codex-cli"}, {"runtime": "claude-code"}]}))
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"unknown role": "inherit-parent"}))
        arms = outcome_bench.parse_arms(f"cstack,mixed=cstack:{good}")
        self.assertEqual(list(outcome_bench.load_arm_models(arms)), ["mixed"])
        with self.assertRaisesRegex(outcome_bench.BenchError, "config de modèles invalide"):
            outcome_bench.load_arm_models(outcome_bench.parse_arms(f"cstack,bad=cstack:{bad}"))
        with self.assertRaisesRegex(outcome_bench.BenchError, "vide ou absente"):
            outcome_bench.load_arm_models(outcome_bench.parse_arms(f"cstack,none=cstack:{self.root / 'none.json'}"))
        with self.assertRaisesRegex(outcome_bench.BenchError, "invalide"):
            outcome_bench.main(["run", "--tasks", str(self.fixture.tasks), "--work", str(self.work),
                                "--output", str(self.root / "c"), "--seed", "1", "--arms", f"cstack,bad=cstack:{bad}"])

    def test_arm_models_reach_the_workspace_but_not_the_diff(self):
        models = {"arena runners": [{"runtime": "claude-code"}]}
        row, runner = self.run_with(lambda cwd: (cwd / "calc.py").write_text(FIXED),
                                    arm="mixed", base="cstack", models=models)
        self.assertEqual(runner.seen_models, [models])
        self.assertIn("$cstack:cstack", runner.cases[0]["prompts"][0])
        self.assertEqual((row["arm"], row["base"]), ("mixed", "cstack"))
        self.assertTrue(row["resolved"])
        self.assertEqual(row["diff"]["files_changed"], 1)
        self.assertNotIn(".cstack", Path(row["patch"]).read_text())
        _, plain = self.run_with(lambda cwd: None)
        self.assertEqual(plain.seen_models, [None])

    def test_fetching_the_fix_is_flagged_and_excluded_from_rates(self):
        row, _ = self.run_with(lambda cwd: (cwd / "calc.py").write_text(FIXED),
                               commands=["git log --oneline", "curl -s https://github.com/o/r/pull/1.diff"])
        self.assertTrue(row["possible_leak"])
        clean, _ = self.run_with(lambda cwd: None, commands=["git status", "python3 -m pytest"])
        self.assertFalse(clean["possible_leak"])
        task = self.fixture.load()
        self.assertTrue(outcome_bench.possible_leak(task, [f"cat {task['repo'].split('://', 1)[1]}/x"]))
        summary = outcome_bench.summarize([
            dict(row, tokens=1), dict(clean, arm="cstack", tokens=1),
            dict(clean, run_id="x", tokens=1),
        ])
        self.assertEqual(summary["arms"]["vanilla"]["possible_leaks"], 1)
        self.assertEqual(summary["arms"]["vanilla"]["runs"], 1)

    def test_network_flag_reaches_the_command_and_manifest(self):
        with patch.object(outcome_bench, "build_image", return_value="image"), \
                patch.object(outcome_bench, "run_test", local_test):
            outcome_bench.command_validate(outcome_bench.argparse.Namespace(
                tasks=self.fixture.tasks, work=self.work, task_ids=None))
        output = self.root / "net"
        seen = {}

        class Runner(FakeRunner):
            def build_command(self):
                return ["codex", "app-server"]

            def scrub(self, value):
                return value

            def run_case(self, case, output_dir, command, model, effort, timeout):
                seen["command"] = command
                return super().run_case(case, output_dir, command, model, effort, timeout)

        with patch.object(outcome_bench, "load_runner", return_value=Runner(lambda cwd: None)), \
                patch.object(outcome_bench, "run_test", local_test):
            outcome_bench.main(["run", "--tasks", str(self.fixture.tasks), "--work", str(self.work),
                                "--output", str(output), "--seed", "1", "--repetitions", "1", "--network"])
        self.assertEqual(seen["command"][-2:], outcome_bench.NETWORK_FLAG)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertTrue(manifest["network"])
        self.assertEqual([arm["name"] for arm in manifest["arms"]], ["vanilla", "cstack"])
        self.assertEqual(len((output / "results.jsonl").read_text().splitlines()), 2)

    def test_run_rejects_bad_arm_lists_and_missing_pstack_checkout(self):
        common = ["run", "--tasks", str(self.fixture.tasks), "--work", str(self.work),
                  "--output", str(self.root / "campaign"), "--seed", "1"]
        for arms in ("cstack", "cstack,cstack", "vanilla,claude"):
            with self.subTest(arms=arms), self.assertRaises(SystemExit):
                outcome_bench.main([*common, "--arms", arms])
        with self.assertRaisesRegex(outcome_bench.BenchError, "fetch-pstack"):
            outcome_bench.main([*common, "--arms", "cstack,pstack"])

    def test_pinned_upstream_inventory_names_the_pstack_entry(self):
        pin = outcome_bench.upstream_pin()
        self.assertIn("pstack/skills/poteto-mode/SKILL.md", pin["blobs"])
        self.assertRegex(pin["commit"], "^[0-9a-f]{40}$")

    def test_run_refuses_unvalidated_tasks_and_foreign_campaigns(self):
        common = ["--tasks", str(self.fixture.tasks), "--work", str(self.work)]
        output = self.root / "campaign"
        with self.assertRaisesRegex(outcome_bench.BenchError, "validate"):
            outcome_bench.main(["run", *common, "--output", str(output), "--seed", "1"])
        output.mkdir()
        (output / "other.txt").write_text("preuve")
        with self.assertRaisesRegex(outcome_bench.BenchError, "absent, vide"):
            outcome_bench.main(["run", *common, "--output", str(output), "--seed", "1"])
        self.assertEqual((output / "other.txt").read_text(), "preuve")


if __name__ == "__main__":
    unittest.main()
