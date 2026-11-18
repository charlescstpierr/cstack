import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify-behavior.py"
SPEC = importlib.util.spec_from_file_location("verify_behavior", MODULE_PATH)
verify_behavior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_behavior)


def state():
    return {
        "child_ids": [],
        "messages": [],
        "message_indices": {},
        "questions": [],
        "question_keys": set(),
        "dispatch_metadata": [],
        "dispatch_indices": {},
        "metadata_gaps": [],
        "actual_commands": [],
        "token_usage": [],
        "token_usage_keys": set(),
    }


class BehaviorRunnerTests(unittest.TestCase):
    def test_case_hash_normalizes_prompt_and_defaults_but_preserves_turn_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = {"id": "one", "cwd": str(root), "prompt": "Read."}
            cases = root / "cases.json"
            cases.write_text(json.dumps([raw]))
            normalized = verify_behavior.read_cases(cases)[0]
            self.assertEqual(verify_behavior.case_hash(raw), verify_behavior.case_hash(normalized))
            equivalent = dict(normalized, prompts=["Read."])
            self.assertEqual(verify_behavior.case_hash(raw), verify_behavior.case_hash(equivalent))
            first = dict(normalized, prompts=["Read.", "Fix."])
            second = dict(normalized, prompts=["Fix.", "Read."])
            self.assertNotEqual(verify_behavior.case_hash(first), verify_behavior.case_hash(second))

    def test_output_cannot_overlap_bundle_or_its_ancestors(self):
        for placement in ("descendant", "equal", "ancestor"):
            with self.subTest(placement=placement), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / "project"
                project.mkdir()
                bundle = root / "sources/bundle"
                skill = bundle / "skills/cstack/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("skill")
                output = {"descendant": bundle / "results", "equal": bundle, "ancestor": bundle.parent}[placement]
                cases = root / "cases.json"
                cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "bundle": str(bundle), "prompt": "Read."}]))
                before = verify_behavior.tree_hash(bundle, None)
                with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                     patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                    with self.assertRaisesRegex(verify_behavior.HarnessError, "bundle"):
                        verify_behavior.main(["--cases", str(cases), "--output", str(output)])
                    build.assert_not_called()
                    launch.assert_not_called()
                self.assertEqual(verify_behavior.tree_hash(bundle, None), before)
                self.assertFalse((output / "summary.json").exists())
                if placement == "descendant":
                    self.assertFalse(output.exists())

    def test_completed_turn_with_missing_required_route_fails_requested_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "missing-review", "cwd": str(project),
                                         "bundle": str(MODULE_PATH.parents[1] / "plugins/cstack"),
                                         "prompt": "Review the fix."}]))
            expectations = root / "expectations.json"
            expectations.write_text(json.dumps({"schema_version": 1, "cases": [{
                "id": "missing-review", "routing": {"expected": ["skills/interrogate/SKILL.md"], "forbidden": []}}]}))
            completed = {"id": "missing-review", "status": "completed", "cwd": str(project),
                         "route_observation": {"opened": [], "direct_reads": [],
                                               "ambiguous_path": False, "trace_files": 1}}
            with patch.object(verify_behavior, "require_route_trace"), \
                 patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", return_value=completed):
                code = verify_behavior.main(["--cases", str(cases), "--output", str(root / "results"),
                                             "--trace-routes", "--expectations", str(expectations)])
            self.assertEqual(code, 1, "a completed turn must not hide a missing required review")
            result = json.loads((root / "results/summary.json").read_text())["cases"][0]
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["verdicts"]["workflow"]["status"], "fail")
            self.assertEqual(result["verdicts"]["outcome"]["status"], "unverified")

    def test_workflow_checks_delegation_and_keeps_missing_observations_unverified(self):
        result = {"status": "completed", "native_child_thread_ids": [], "cwd": "/unused"}
        report = verify_behavior.evaluate_case(result, {"expected_children": 1})
        self.assertEqual(report["turn"], "completed")
        self.assertEqual(report["workflow"]["status"], "fail")
        ambiguous = {"status": "completed", "route_score": {
            "false_negative": [], "false_positive": [],
            "unknown_expected": ["skills/how/SKILL.md"], "unknown_forbidden": []}}
        report = verify_behavior.evaluate_case(ambiguous, {"routing": {
            "expected": ["skills/how/SKILL.md"], "forbidden": []}})
        self.assertEqual(report["workflow"]["status"], "unverified")
        self.assertEqual(verify_behavior.evaluate_case({"status": "completed"}, {})["outcome"]["status"], "unverified")

    def test_frozen_outcome_check_runs_real_code_and_rejects_wrong_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            target = project / "message.txt"
            target.write_text("could not proccess invoice")
            result = {"status": "completed", "cwd": directory, "native_child_thread_ids": []}
            expectation = {"expected_children": 0, "outcome_checks": [{
                "id": "correct-message", "argv": [sys.executable, "-c",
                "from pathlib import Path; assert Path('message.txt').read_text() == 'could not process invoice'"]}]}
            failed = verify_behavior.evaluate_case(result, expectation, verify_outcomes=True)
            self.assertEqual(failed["turn"], "completed")
            self.assertEqual(failed["workflow"]["status"], "pass")
            self.assertEqual(failed["outcome"]["status"], "fail")
            self.assertNotEqual(failed["outcome"]["checks"][0]["returncode"], 0)
            target.write_text("could not process invoice")
            passed = verify_behavior.evaluate_case(result, expectation, verify_outcomes=True)
            self.assertEqual(passed["outcome"]["status"], "pass")
            passive = verify_behavior.evaluate_case(result, expectation)
            self.assertEqual(passive["outcome"]["status"], "unverified")

    def test_outcome_check_timeout_is_unverified_and_later_checks_still_run(self):
        with tempfile.TemporaryDirectory() as directory:
            expectation = {"outcome_checks": [
                {"id": "slow", "argv": [sys.executable, "-c", "import time; time.sleep(2)"], "timeout": 0.05},
                {"id": "wrong", "argv": [sys.executable, "-c", "raise SystemExit(1)"]}]}
            report = verify_behavior.evaluate_case({"status": "completed", "cwd": directory}, expectation, True)
            self.assertEqual(report["outcome"]["checks"][0]["status"], "unverified")
            self.assertEqual(report["outcome"]["checks"][1]["status"], "fail")
            self.assertEqual(report["outcome"]["status"], "fail")

    def test_outcome_commands_require_opt_in_and_a_completed_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed.txt"
            expectation = {"outcome_checks": [{"id": "marker", "argv": [sys.executable, "-c",
                "from pathlib import Path; Path('executed.txt').write_text('executed')"]}]}
            verify_behavior.evaluate_case({"status": "completed", "cwd": directory}, expectation)
            self.assertFalse(marker.exists())
            verify_behavior.evaluate_case({"status": "needs_input", "cwd": directory}, expectation, True)
            self.assertFalse(marker.exists())
            report = verify_behavior.evaluate_case({"status": "completed", "cwd": directory}, expectation, True)
            self.assertEqual(report["outcome"]["status"], "pass")
            self.assertTrue(marker.exists())

    def test_outcome_output_is_scrubbed_before_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            expectation = {"outcome_checks": [{"id": "no-secret", "argv": [sys.executable, "-c",
                "print('api_key=' + 'A' * 5000)"]}]}
            report = verify_behavior.evaluate_case({"status": "completed", "cwd": directory}, expectation, True)
            output = report["outcome"]["checks"][0]["stdout"]
            self.assertIn("<REDACTED>", output)
            self.assertNotIn("A" * 100, output)
            self.assertLessEqual(len(output), 4096)

    def test_malformed_expectations_fail_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expectations.json"
            for rows in ([{"id": "one", "expected_children": True}],
                         [{"id": "one", "requires_independent_review": "true"}],
                         [{"id": "one", "requires_independent_review": 1}],
                         [{"id": "one", "requires_independent_review": None}],
                         [{"id": "one", "expected_artifact": "missing.txt"}],
                         [{"id": "one", "project_sha256": "not-a-hash"}],
                         [{"id": "one", "source_sha256": {"unexpected": "a" * 64}}],
                         [{"id": "one", "role_metadata": []}],
                         [{"id": "one", "skill_path": "../SKILL.md"}],
                         [{"id": "one"}, {"id": "one"}],
                         [{"id": "one", "routing": {"expected": ["x"], "forbidden": ["x"]}}],
                         [{"id": "one", "outcome_checks": [{"id": "test", "argv": "echo yes"}]}],
                         [{"id": "one", "outcome_checks": [{"id": "test", "argv": ["true"], "timeout": float("nan")}]}]):
                with self.subTest(rows=rows):
                    path.write_text(json.dumps({"schema_version": 1, "cases": rows}))
                    with self.assertRaises(verify_behavior.HarnessError):
                        verify_behavior.read_expectations(path)

    def test_outcome_only_success_does_not_require_an_undeclared_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Verify."}]))
            expectations = root / "expectations.json"
            expectations.write_text(json.dumps({"schema_version": 1, "cases": [{"id": "one", "outcome_checks": [
                {"id": "ok", "argv": [sys.executable, "-c", "print(1)"], "expected_json": 1}]}]}))
            completed = {"id": "one", "status": "completed", "cwd": str(project)}
            with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", return_value=completed):
                code = verify_behavior.main(["--cases", str(cases), "--expectations", str(expectations),
                                             "--output", str(root / "results"), "--verify-outcomes"])
            self.assertEqual(code, 0)
            receipt = json.loads((root / "results/summary.json").read_text())["cases"][0]
            self.assertEqual(receipt["verdicts"]["workflow"]["status"], "unverified")
            self.assertEqual(receipt["verdicts"]["outcome"]["status"], "pass")

    def test_independent_review_requirement_preserves_unverified_cli_result(self):
        for required, expected_code in ((False, 0), (True, 2)):
            with self.subTest(required=required), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / "project"
                project.mkdir()
                cases = root / "cases.json"
                cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Prepare."}]))
                expectations = root / "expectations.json"
                expectations.write_text(json.dumps({"schema_version": 1, "cases": [{
                    "id": "one", "requires_independent_review": required,
                    "outcome_checks": [{"id": "value", "argv": [sys.executable, "-c", "print(1)"],
                                        "expected_json": 1}]}]}))
                completed = {"id": "one", "status": "completed", "cwd": str(project),
                             "independent_review": {"status": "pass"}}
                with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                     patch.object(verify_behavior, "run_case", return_value=completed):
                    code = verify_behavior.main(["--cases", str(cases), "--expectations", str(expectations),
                                                 "--output", str(root / "results"), "--verify-outcomes"])
                self.assertEqual(code, expected_code)
                receipt = json.loads((root / "results/summary.json").read_text())["cases"][0]
                self.assertEqual(receipt["verdicts"]["outcome"]["status"], "unverified" if required else "pass")

    def test_unknown_case_and_envelope_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(root), "prompt": "Verify.", "promt": "typo"}]))
            with self.assertRaises(verify_behavior.HarnessError):
                verify_behavior.read_cases(cases)
            expectations = root / "expectations.json"
            expectations.write_text(json.dumps({"schema_version": 1, "cases": [{"id": "one"}], "expected_child": 1}))
            with self.assertRaises(verify_behavior.HarnessError):
                verify_behavior.read_expectations(expectations)

    def test_unversioned_or_old_tree_hashes_require_regeneration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expectations.json"
            for version in (None, "cstack-tree-sha256-v1", "cstack-tree-sha256-v2"):
                with self.subTest(version=version):
                    row = {"id": "one", "project_sha256": "a" * 64}
                    if version is not None:
                        row["hash_algorithm"] = version
                    path.write_text(json.dumps({"schema_version": 1, "cases": [row]}))
                    with self.assertRaisesRegex(verify_behavior.HarnessError, "régén"):
                        verify_behavior.read_expectations(path)

    def test_cli_verifies_outcome_without_route_trace_and_refuses_missing_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            target = project / "message.txt"
            target.write_text("wrong")
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Fix the message."}]))
            expectations = root / "expectations.json"
            checks = [{"id": "message", "argv": [sys.executable, "-c",
                       "from pathlib import Path; assert Path('message.txt').read_text() == 'correct'"]}]
            row = {"id": "one", "expected_children": 0, "outcome_checks": checks}
            expectations.write_text(json.dumps({"schema_version": 1, "cases": [row]}))
            completed = {"id": "one", "status": "completed", "cwd": str(project), "native_child_thread_ids": []}
            with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", return_value=completed):
                for label, text, expected in (("wrong", "wrong", 1), ("correct", "correct", 0)):
                    target.write_text(text)
                    code = verify_behavior.main(["--cases", str(cases), "--output", str(root / label),
                                                 "--expectations", str(expectations), "--verify-outcomes"])
                    self.assertEqual(code, expected)
                code = verify_behavior.main(["--cases", str(cases), "--output", str(root / "workflow-only"),
                                             "--expectations", str(expectations)])
                self.assertEqual(code, 0, "outcome checks remain opt-in when only workflow was requested")
                passive = json.loads((root / "workflow-only/summary.json").read_text())["cases"][0]
                self.assertEqual(passive["verdicts"]["outcome"]["status"], "unverified")
                expectations.write_text(json.dumps({"schema_version": 1, "cases": [{"id": "one"}]}))
                code = verify_behavior.main(["--cases", str(cases), "--output", str(root / "unverified"),
                                             "--expectations", str(expectations), "--verify-outcomes"])
                self.assertEqual(code, 2)
            result = json.loads((root / "correct/summary.json").read_text())["cases"][0]
            self.assertEqual(result["verdicts"]["outcome"]["status"], "pass")
            self.assertEqual(len(result["expectation_sha256"]), 64)

    def test_route_trace_scores_actual_opens_and_negative_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "resources" / "candidate"
            prefix = Path(directory) / "route-open"
            (Path(directory) / "route-open.101").write_text(
                f'openat(AT_FDCWD, "{bundle}/skills/cstack/playbooks/feature.md", O_RDONLY) = 3\n'
                f'openat(AT_FDCWD, "{bundle}/skills/how/SKILL.md", O_RDONLY) = 4\n'
                f'openat(AT_FDCWD, "{bundle}/skills/arena/SKILL.md", O_RDONLY) = -1 ENOENT\n'
            )
            opened = verify_behavior.observed_routes(prefix, bundle, [
                f"cat {bundle}/skills/cstack/playbooks/feature.md",
                f"sed -n '1,80p' {bundle}/skills/how/SKILL.md",
            ], Path(directory))
            score = verify_behavior.score_routes(opened, {"routing": {
                "expected": ["skills/cstack/playbooks/feature.md", "skills/arena/SKILL.md"],
                "forbidden": ["skills/how/SKILL.md", "skills/why/SKILL.md"],
            }})
        self.assertEqual(score["true_positive"], ["skills/cstack/playbooks/feature.md"])
        self.assertEqual(score["false_negative"], ["skills/arena/SKILL.md"])
        self.assertEqual(score["false_positive"], ["skills/how/SKILL.md"])
        self.assertEqual(score["known_true_negative"], ["skills/why/SKILL.md"])

    def test_bulk_scan_is_unknown_not_a_loaded_capability(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "resources" / "candidate"
            prefix = Path(directory) / "route-open"
            (Path(directory) / "route-open.101").write_text(
                f'openat(AT_FDCWD, "{bundle}/skills/arena/SKILL.md", O_RDONLY) = 3\n'
            )
            opened = verify_behavior.observed_routes(
                prefix, bundle, [f"rg arena {bundle}/skills"], Path(directory)
            )
            required = verify_behavior.score_routes(opened, {"routing": {
                "expected": ["skills/arena/SKILL.md"], "forbidden": [],
            }})
            forbidden = verify_behavior.score_routes(opened, {"routing": {
                "expected": [], "forbidden": ["skills/arena/SKILL.md"],
            }})
        self.assertEqual(opened["direct_reads"], [])
        self.assertEqual(required["unknown_expected"], ["skills/arena/SKILL.md"])
        self.assertEqual(forbidden["unknown_forbidden"], ["skills/arena/SKILL.md"])
        self.assertEqual(required["true_positive"], [])
        self.assertEqual(forbidden["false_positive"], [])

    def test_repeats_copy_fixtures_and_preserve_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (project / "source.txt").write_text("original")
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Lecture seule."}]))

            def fake_run(case, output, command, model, effort, timeout, trace_routes=False):
                (case["cwd"] / "source.txt").write_text("changed")
                return {"id": case["id"], "status": "completed"}

            with patch.object(verify_behavior, "build_command", return_value=["codex"]), \
                 patch.object(verify_behavior, "run_case", side_effect=fake_run):
                self.assertEqual(verify_behavior.main([
                    "--cases", str(cases), "--output", str(root / "results"), "--repeats", "3"
                ]), 0)
            summary = json.loads((root / "results" / "summary.json").read_text())
            self.assertEqual([case["id"] for case in summary["cases"]],
                             ["one__run_01", "one__run_02", "one__run_03"])
            self.assertEqual((project / "source.txt").read_text(), "original")

    def test_repeats_reject_linked_git_worktrees_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, linked = root / "original", root / "linked"
            original.mkdir()
            subprocess.run(["git", "init", "-q", str(original)], check=True)
            (original / "source.txt").write_text("original")
            subprocess.run(["git", "-C", str(original), "add", "."], check=True)
            subprocess.run(["git", "-C", str(original), "-c", "user.name=test",
                            "-c", "user.email=test@example.invalid", "commit", "-qm", "initial"], check=True)
            subprocess.run(["git", "-C", str(original), "worktree", "add", "-qb", "linked", str(linked)], check=True)
            head = subprocess.check_output(["git", "-C", str(linked), "rev-parse", "HEAD"])
            index = Path(subprocess.check_output(["git", "-C", str(linked), "rev-parse",
                                                "--git-path", "index"], text=True).strip())
            before_index = index.read_bytes()
            cases = root / "cases.json"
            (linked / "subdir").mkdir()
            project = root / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / "linked-dependency").symlink_to(linked, target_is_directory=True)
            for cwd in (linked, linked / "subdir", project):
                with self.subTest(cwd=cwd):
                    cases.write_text(json.dumps([{"id": "linked", "cwd": str(cwd), "prompt": "Commit a fix."}]))
                    with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                         patch.object(verify_behavior, "run_case", return_value={"id": "linked", "status": "completed"}) as launch:
                        with self.assertRaisesRegex(verify_behavior.HarnessError, "dépôt Git|symbolique"):
                            verify_behavior.main(["--cases", str(cases), "--output", str(root / "results"), "--repeats", "2"])
                        launch.assert_not_called()
            self.assertEqual(subprocess.check_output(["git", "-C", str(linked), "rev-parse", "HEAD"]), head)
            self.assertEqual(index.read_bytes(), before_index)
            self.assertFalse((root / "results").exists())

    def test_repeated_standalone_git_commits_leave_fixture_head_and_index_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()

            def git(cwd, *args):
                return subprocess.check_output(["git", "-C", str(cwd), "-c", "user.name=test",
                    "-c", "user.email=test@example.invalid", *args], stderr=subprocess.DEVNULL)

            git(project, "init", "-q")
            (project / "source.txt").write_text("original")
            git(project, "add", ".")
            git(project, "commit", "-qm", "initial")
            head, index = git(project, "rev-parse", "HEAD"), (project / ".git/index").read_bytes()
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Commit the fix."}]))

            def commit_fix(case, *args):
                self.assertEqual(git(case["cwd"], "rev-parse", "HEAD"), head)
                (case["cwd"] / "source.txt").write_text("fixed")
                git(case["cwd"], "add", ".")
                git(case["cwd"], "commit", "-qm", "fix")
                return {"id": case["id"], "status": "completed"}

            with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", side_effect=commit_fix) as launch:
                self.assertEqual(verify_behavior.main(["--cases", str(cases), "--output", str(root / "results"),
                                                      "--repeats", "2"]), 0)
                self.assertEqual(launch.call_count, 2)
            self.assertEqual(git(project, "rev-parse", "HEAD"), head)
            self.assertEqual((project / ".git/index").read_bytes(), index)
            self.assertEqual((project / "source.txt").read_text(), "original")

    @unittest.skipUnless(shutil.which("strace"), "strace requis")
    def test_relative_strace_open_cannot_be_a_known_negative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            skill = bundle / "skills/how/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("how")
            prefix = root / "route-open"
            subprocess.run(["strace", "-ff", "-e", "trace=openat,openat2", "-o", str(prefix),
                            "cat", "bundle/skills/how/SKILL.md"], cwd=root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            observed = verify_behavior.observed_routes(prefix, bundle, ["cat bundle/skills/how/SKILL.md"], root)
            score = verify_behavior.score_routes(observed, {"routing": {
                "expected": [], "forbidden": ["skills/how/SKILL.md"]}})
            self.assertEqual(score["known_true_negative"], [])
            self.assertEqual(score["unknown_forbidden"], ["skills/how/SKILL.md"])
            self.assertTrue(observed["ambiguous_path"])


    def test_dispatch_never_counts_parent_as_child(self):
        current = state()
        verify_behavior.update_state({
            "method": "item/completed",
            "params": {"threadId": "parent", "item": {
                "type": "collabAgentToolCall", "id": "dispatch-1",
                "agentThreadId": "parent", "receiverThreadIds": ["parent", "child"],
                "events": [{"type": "subagentActivity", "agentThreadId": "parent"}],
            }},
        }, current, "parent")
        self.assertEqual(current["child_ids"], ["child"])
        self.assertEqual(current["dispatch_metadata"][0]["receiver_thread_ids"], ["parent", "child"])

    def test_cases_preserve_ephemeral_and_reject_non_boolean_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases_path = root / "cases.json"
            rows = [
                {"id": "default", "cwd": directory, "prompt": "A"},
                {"id": "durable", "cwd": directory, "prompt": "B", "ephemeral": False},
                {"id": "temporary", "cwd": directory, "prompt": "C", "ephemeral": True},
            ]
            cases_path.write_text(json.dumps(rows))
            cases = verify_behavior.read_cases(cases_path)
            self.assertEqual([case["ephemeral"] for case in cases], [True, False, True])
            for invalid in (None, 0, 1, "false", [], {}):
                with self.subTest(invalid=invalid):
                    cases_path.write_text(json.dumps([{**rows[1], "ephemeral": invalid}]))
                    with self.assertRaises(verify_behavior.HarnessError):
                        verify_behavior.read_cases(cases_path)

    def test_run_case_sends_durable_thread_and_excludes_parent_from_children(self):
        class FakeAppServer:
            instances = []

            def __init__(self, *args):
                self.requests = []
                self.__class__.instances.append(self)

            def request(self, method, params, timeout, on_event):
                self.requests.append((method, params))
                if method == "thread/start":
                    on_event({
                        "method": "item/completed",
                        "params": {"threadId": "parent", "item": {
                            "type": "collabAgentToolCall", "id": "early", "agentThreadId": "parent",
                            "receiverThreadIds": ["parent", "child"],
                        }},
                    })
                    return {"thread": {"id": "parent"}}
                if method == "turn/start":
                    on_event({
                        "method": "item/completed",
                        "params": {"threadId": "parent", "item": {
                            "type": "collabAgentToolCall", "id": "later",
                            "receiverThreadIds": ["parent", "child"],
                            "events": [{"type": "subagentActivity", "agentThreadId": "parent"}],
                        }},
                    })
                    return {"turn": {"id": "turn-1"}}
                if method == "thread/read":
                    return {"thread": {"id": params["threadId"], "model": "model-observed"}}
                return {}

            def notify(self, method):
                pass

            def read(self, deadline):
                return {"method": "turn/completed", "params": {
                    "threadId": "parent", "turn": {"id": "turn-1", "status": "completed"},
                }}

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            output = root / "output"
            cases_path = root / "cases.json"
            cases_path.write_text(json.dumps([{
                "id": "durable", "cwd": str(project), "prompt": "Inspecter.", "ephemeral": False,
            }]))
            case = verify_behavior.read_cases(cases_path)[0]
            with patch.object(verify_behavior, "AppServer", FakeAppServer):
                result = verify_behavior.run_case(case, output, ["fake-app-server"], None, None, 1)

        requests = FakeAppServer.instances[0].requests
        self.assertIs(next(params for method, params in requests if method == "thread/start")["ephemeral"], False)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["native_child_thread_ids"], ["child"])
        self.assertEqual([params["threadId"] for method, params in requests if method == "thread/read"], ["parent", "child"])
        self.assertEqual([row["thread_id"] for row in result["child_metadata"]], ["child"])
        self.assertEqual(result["after_turn_actual_metadata"][0]["metadata"]["thread"]["id"], "parent")
        self.assertEqual(len(result["dispatch_metadata"]), 3)

    def test_rejects_overlapping_or_nonempty_output_before_native_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Lecture seule."}]))
            evidence = root / "evidence"
            evidence.mkdir()
            saved = evidence / "summary.json"
            saved.write_text("conserver les preuves précédentes")
            with patch.object(verify_behavior, "build_command") as build:
                for output in (project, project / "results", root, evidence):
                    with self.subTest(output=output), self.assertRaises(verify_behavior.HarnessError):
                        verify_behavior.main(["--cases", str(cases), "--output", str(output)])
                build.assert_not_called()
            self.assertEqual(saved.read_text(), "conserver les preuves précédentes")

    def test_dispatch_metadata_is_recorded_separately_from_effective_metadata(self):
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "parent",
                    "item": {
                        "type": "collabAgentToolCall",
                        "id": "dispatch-1",
                        "tool": "spawnAgent",
                        "status": "completed",
                        "receiverThreadIds": ["closed-child"],
                        "model": "model-requested",
                        "reasoningEffort": "max",
                    },
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["child_ids"], ["closed-child"])
        self.assertEqual(current["dispatch_metadata"][0]["requested_model"], "model-requested")
        self.assertNotIn("effective_model", current["dispatch_metadata"][0])

    def test_closed_child_thread_is_a_metadata_gap_not_case_failure(self):
        class ClosedChildServer:
            def request(self, *args, **kwargs):
                raise verify_behavior.HarnessError("conversation non chargée : child")

        current = state()
        metadata = verify_behavior.capture_thread_metadata(
            ClosedChildServer(), "child", 1, current, "parent", "child"
        )
        self.assertIsNone(metadata)
        self.assertEqual(current["metadata_gaps"][0]["thread_id"], "child")
        self.assertIn("thread/read indisponible", current["metadata_gaps"][0]["reason"])

    def test_agent_message_with_null_questions_is_not_input(self):
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/started",
                "params": {
                    "threadId": "parent",
                    "item": {"type": "agentMessage", "id": "m1", "text": "", "questions": None},
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["questions"], [])

    def test_native_user_input_rpc_stops_without_answer(self):
        current = state()
        with self.assertRaises(verify_behavior.NeedsInput):
            verify_behavior.update_state(
                {
                    "id": 42,
                    "method": "item/requestUserInput",
                    "params": {"questions": [{"id": "choice"}]},
                },
                current,
                "parent",
            )
        self.assertEqual(current["questions"][0]["method"], "item/requestUserInput")

    def test_nonempty_async_questions_are_recorded_without_stopping(self):
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/started",
                "params": {
                    "threadId": "parent",
                    "item": {
                        "type": "agentMessage",
                        "id": "m1",
                        "text": "question en attente",
                        "questions": [{"id": "choice", "text": "Quelle politique ?"}],
                    },
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["questions"][0][0]["id"], "choice")
        self.assertEqual(current["messages"], ["question en attente"])
        verify_behavior.update_state(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "parent",
                    "item": {"type": "agentMessage", "id": "m1", "text": "réponse finale", "questions": []},
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["messages"], ["réponse finale"])

    def test_missing_codex_config_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}):
                with self.assertRaises(verify_behavior.HarnessError) as ctx:
                    verify_behavior.config_names()
        self.assertIn(str(home / "config.toml"), str(ctx.exception))

    def test_config_names_reads_plugins_from_codex_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "config.toml").write_text("unused")
            fake = types.ModuleType("tomllib")
            fake.TOMLDecodeError = type("TOMLDecodeError", (Exception,), {})
            fake.loads = lambda text: {"plugins": {"alpha": {}}, "mcp_servers": {"omega": {}}}
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}):
                with patch.dict(sys.modules, {"tomllib": fake}):
                    plugins, mcp_servers = verify_behavior.config_names()
        self.assertEqual(plugins, ["alpha"])
        self.assertEqual(mcp_servers, ["omega"])

    def test_invalid_toml_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "config.toml").write_text("not toml")
            fake = types.ModuleType("tomllib")
            error_type = type("TOMLDecodeError", (Exception,), {})
            fake.TOMLDecodeError = error_type
            fake.loads = lambda text: (_ for _ in ()).throw(error_type("bad"))
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}):
                with patch.dict(sys.modules, {"tomllib": fake}):
                    with self.assertRaises(verify_behavior.HarnessError) as ctx:
                        verify_behavior.config_names()
        self.assertIn("impossible de lire la configuration Codex", str(ctx.exception))

    def test_python39_requires_tomllib_to_parse_config(self):
        if sys.version_info >= (3, 11):
            self.skipTest("cet interpréteur peut lire le TOML")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "config.toml").write_text("[plugins]\n")
            with patch.dict(os.environ, {"CODEX_HOME": str(home)}):
                with patch.dict(sys.modules, {"tomllib": None}):
                    with self.assertRaises(verify_behavior.HarnessError) as ctx:
                        verify_behavior.config_names()
        self.assertIn("3.11", str(ctx.exception))

    def test_scrub_redacts_normalized_secret_keys(self):
        payload = {
            "x-api-key": "one",
            "API_KEY": "two",
            "Api-Key": "three",
            "private-token": "four",
            "access-token": "five",
            "set-cookie": "six",
            "tokenizer": "keep",
            "token_usage": {"input": 3},
        }
        result = verify_behavior.scrub(payload)
        for key in ("x-api-key", "API_KEY", "Api-Key", "private-token", "access-token", "set-cookie"):
            self.assertEqual(result[key], "<REDACTED>")
        self.assertEqual(result["tokenizer"], "keep")
        self.assertEqual(result["token_usage"], {"input": 3})

    def test_scrub_redacts_secret_shaped_values_not_digests(self):
        git_sha = "e83c5163316f89bfbde7d9ab23ca2e25604af290"
        digest = "649cf39c9a6e81e21b88747946236d33e7ed2efa3512d8b8447b1889006a61f0"
        path = "/private/tmp/cstack-work/scripts/verify-behavior.py"
        bearer = "Bearer ghp_0123456789abcdefghijABCDEFGHIJ0123"
        result = verify_behavior.scrub(
            {
                "header": bearer + " trailing",
                "url": "https://api.example.com/v1?access_token=abcdef123456&page=2",
                "nested": {"items": [bearer, git_sha, digest, path, 12, True, None], "ok": False},
                "git_sha": git_sha,
                "digest": digest,
                "path": path,
                "count": 7,
            }
        )
        self.assertEqual(result["header"], "Bearer <REDACTED> trailing")
        self.assertEqual(result["url"], "https://api.example.com/v1?access_token=<REDACTED>&page=2")
        self.assertEqual(result["nested"]["items"][0], "Bearer <REDACTED>")
        self.assertEqual(result["nested"]["items"][1:], [git_sha, digest, path, 12, True, None])
        self.assertIs(result["nested"]["ok"], False)
        self.assertEqual(result["git_sha"], git_sha)
        self.assertEqual(result["digest"], digest)
        self.assertEqual(result["path"], path)
        self.assertEqual(result["count"], 7)

    def test_write_summary_scrubs_agent_text_and_commands(self):
        token = "ghp_" + "B" * 36
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/started",
                "params": {
                    "threadId": "parent",
                    "item": {"type": "agentMessage", "id": "m1", "text": f"contact support with {token}"},
                },
            },
            current,
            "parent",
        )
        verify_behavior.update_state(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "parent",
                    "item": {
                        "type": "commandExecution",
                        "command": f"gh api user --with-token {token}",
                    },
                },
            },
            current,
            "parent",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            verify_behavior.write_summary(
                output,
                [{
                    "id": "one",
                    "input_prompts": [f"please use {token}"],
                    "actual_commands": current["actual_commands"],
                    "native_child_thread_ids": ["thread_abc"],
                    "turns": [{
                        "prompt": f"please use {token}",
                        "final_text": "\n\n".join(current["messages"]),
                    }],
                    "error": f"failed {token}",
                    "metadata_gaps": [{"kind": "child", "error": f"gap {token}"}],
                }],
                ["one"],
            )
            payload = (output / "summary.json").read_text()
        self.assertNotIn(token, payload)
        self.assertIn("contact support with <REDACTED>", payload)
        self.assertIn("gh api user --with-token <REDACTED>", payload)
        self.assertIn("thread_abc", payload)

    def test_scrub_redacts_extended_secret_shapes(self):
        rows = (
            ("aws_key_id", "id AKIAIOSFODNN7EXAMPLE end", "AKIAIOSFODNN7EXAMPLE"),
            ("aws_secret_assign", "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
            ("openai_sk", "sk-abcdefghijklmnopqrstuvwxyzABCDEF12", "sk-abcdefghijklmnopqrstuvwxyzABCDEF12"),
            ("openai_sk_proj", "sk-proj-abcdefghijklmnopqrstuvwxyzABCDEF12", "sk-proj-abcdefghijklmnopqrstuvwxyzABCDEF12"),
            ("anthropic_sk_ant", "sk-ant-api03-abcdefghijklmnopqrstuvwxyzABCDEF12", "sk-ant-api03-abcdefghijklmnopqrstuvwxyzABCDEF12"),
            ("slack_xoxb", "xoxb-123456789012-abcdefghijklmnopqrstuv", "xoxb-123456789012-abcdefghijklmnopqrstuv"),
            ("jwt", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.signaturetrail", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.signaturetrail"),
            ("basic_auth", "Authorization: Basic dXNlcjpwYXNz", "dXNlcjpwYXNz"),
            ("url_userinfo", "https://user:hunter2@example.com/v1", "user:hunter2"),
            ("flag_password_space", "tool --password hunter2", "hunter2"),
            ("flag_p_space", "tool -p hunter2", "hunter2"),
            ("flag_with_token", "tool --with-token abcdef123456", "abcdef123456"),
            ("export_assign", "export OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyzABCDEF12", "sk-abcdefghijklmnopqrstuvwxyzABCDEF12"),
            ("pem", "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----", "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"),
            ("npm", "npm_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL", "npm_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL"),
            ("gitlab", "glpat-abcdefghijklmnopqrstuvwxyz", "glpat-abcdefghijklmnopqrstuvwxyz"),
            ("google_api", "AIzaSyABCDEfghijklmnopqrstuvwxyz0123456", "AIzaSyABCDEfghijklmnopqrstuvwxyz0123456"),
            ("header_line", "X-Api-Key: supersecretvalue123", "supersecretvalue123"),
        )
        for name, text, secret in rows:
            with self.subTest(name=name):
                result = verify_behavior.scrub_text(text)
                self.assertNotIn(secret, result)
                self.assertIn("<REDACTED>", result)

    def test_scrub_preserves_non_secret_evidence(self):
        rows = (
            ("git_sha", "e83c5163316f89bfbde7d9ab23ca2e25604af290"),
            ("sha256", "649cf39c9a6e81e21b88747946236d33e7ed2efa3512d8b8447b1889006a61f0"),
            ("abs_path", "/private/tmp/cstack-work/scripts/verify-behavior.py"),
            ("thread_id", "thread_7f3a9c2e-1b44-4d90-ae11-88c01d2f4a77"),
            ("model_name", "gpt-5.4-codex"),
            ("git_status", "git status"),
            ("plain_sentence", "The worker finished the turn without asking for input."),
        )
        for name, text in rows:
            with self.subTest(name=name):
                self.assertEqual(verify_behavior.scrub_text(text), text)

    def test_secret_key_policy_matches_documented_markers(self):
        for key in (
            "password", "secret", "api_key", "authorization", "cookie",
            "private_key", "credentials", "passwd", "pwd", "jwt", "bearer",
            "ssh_key", "aws_access_key_id", "access_token",
        ):
            with self.subTest(secret=key):
                self.assertTrue(verify_behavior.secret_key(key), key)
        for key in ("auth", "key", "tokenizer", "token_usage", "model", "oauth_client_id"):
            with self.subTest(kept=key):
                self.assertFalse(verify_behavior.secret_key(key), key)


if __name__ == "__main__":
    unittest.main()
