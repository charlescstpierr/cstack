import importlib.util
import json
import os
import shutil
import socket
import subprocess
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
    def test_git_hash_ignores_cache_timestamps_and_preserves_normalized_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = behavior_scenarios.interrogate_project(root, "alder", None)
            (project / "alias.md").symlink_to("README.md")
            behavior_scenarios.git(project, "add", "alias.md")
            index = project / ".git/index"
            before = index.read_bytes()
            expected = behavior_scenarios.git_hash(project)
            self.assertEqual(index.read_bytes(), before, "provenance reads must not rewrite index cache")
            self.assertEqual(verify_behavior.git_hash(project), expected)
            self.assertEqual(index.read_bytes(), before)
            os.utime(project / "README.md", None)
            subprocess.run(["git", "-C", str(project), "update-index", "--refresh"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.assertEqual(behavior_scenarios.git_hash(project), expected)
            copied = root / "copied"
            shutil.copytree(project, copied)
            self.assertFalse((copied / "alias.md").is_symlink())
            self.assertEqual(behavior_scenarios.tree_hash(copied), behavior_scenarios.tree_hash(project))
            self.assertEqual(behavior_scenarios.git_hash(copied), expected)
            self.assertEqual(verify_behavior.git_hash(copied), expected)
            behavior_scenarios.git(project, "config", "core.worktree", str(project))
            copied_absolute = root / "copied-absolute"
            shutil.copytree(project, copied_absolute)
            with self.assertRaisesRegex(ValueError, "racine Git"):
                behavior_scenarios.git_hash(copied_absolute)
            with self.assertRaisesRegex(verify_behavior.HarnessError, "racine Git"):
                verify_behavior.git_hash(copied_absolute)

    def test_git_review_inputs_are_frozen_even_when_worktree_bytes_are_unchanged(self):
        for mutation in ("unstage", "commit", "ref", "intent-to-add"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                factory = behavior_scenarios.interrogate_project if mutation == "unstage" else behavior_scenarios.partial_set_project
                project = factory(root, "alder", None)
                if mutation == "intent-to-add":
                    (project / "empty").touch()
                    behavior_scenarios.git(project, "add", "-N", "empty")
                bundle = root / "bundle"
                skill = bundle / "skills/cstack/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("skill")
                cases, expectations = [], []
                behavior_scenarios.register(cases, expectations, case_id="one", project=project,
                    bundle=bundle, skill="cstack", roles=[], body="Review the staged change.")
                if mutation == "unstage":
                    behavior_scenarios.git(project, "reset", "HEAD", "--", "README.md")
                elif mutation == "commit":
                    behavior_scenarios.git(project, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "-m", "move HEAD")
                elif mutation == "ref":
                    behavior_scenarios.git(project, "branch", "inspection-ref")
                else:
                    behavior_scenarios.git(project, "add", "empty")
                self.assertEqual(behavior_scenarios.tree_hash(project), expectations[0]["project_sha256"])
                case_path, expected_path = root / "cases.json", root / "expectations.json"
                case_path.write_text(json.dumps(cases))
                expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations}))
                with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                     patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                    with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte.*Git"):
                        verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                            "--output", str(root / "results")])
                    build.assert_not_called()
                    launch.assert_not_called()
                self.assertFalse((root / "results").exists())

    def test_empty_directories_and_directory_permissions_are_in_the_frozen_tree(self):
        for mutation in ("project-empty", "bundle-empty", "root-mode", "nested-mode"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = behavior_scenarios.create_project(root, "alder", {"folder/input.txt": "original"}, [])
                bundle = root / "bundle"
                skill = bundle / "skills/cstack/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("skill")
                cases, expectations = [], []
                behavior_scenarios.register(cases, expectations, case_id="one", project=project,
                    bundle=bundle, skill="cstack", roles=[], body="Read the code.")
                try:
                    if mutation.endswith("empty"):
                        ((project if mutation == "project-empty" else bundle) / "empty").mkdir()
                    elif mutation == "root-mode":
                        project.chmod(0o555)
                        if os.geteuid() != 0:
                            with self.assertRaises(PermissionError):
                                (project / "denied.txt").write_text("denied")
                    else:
                        (project / "folder").chmod(0o700)
                    case_path, expected_path = root / "cases.json", root / "expectations.json"
                    case_path.write_text(json.dumps(cases))
                    expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations}))
                    with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                         patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                        with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte"):
                            verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                                "--output", str(root / "results")])
                        build.assert_not_called()
                        launch.assert_not_called()
                    self.assertFalse((root / "results").exists())
                finally:
                    project.chmod(0o755)
                    (project / "folder").chmod(0o755)

    @unittest.skipUnless(hasattr(os, "geteuid") and hasattr(os, "seteuid"), "Unix permissions required")
    def test_unreadable_directory_refuses_hashing_and_launch_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            project = root / "project"
            unreadable = project / "unreadable"
            unreadable.mkdir(parents=True)
            (unreadable / "behavior.py").write_text("original code")
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Read."}]))
            original_euid = os.geteuid()
            try:
                unreadable.chmod(0)
                if original_euid == 0:
                    os.chown(root, 65534, -1)
                    os.seteuid(65534)
                try:
                    list(unreadable.iterdir())
                except PermissionError:
                    pass
                else:
                    self.skipTest("chmod 000 does not prevent traversal for this UID")
                with self.subTest(hasher="generator"), self.assertRaisesRegex(ValueError, "parcours.*incomplet"):
                    behavior_scenarios.tree_hash(project)
                with self.subTest(hasher="runner"), self.assertRaisesRegex(verify_behavior.HarnessError, "parcours.*incomplet"):
                    verify_behavior.tree_hash(project, None)
                with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                     patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                    with self.subTest(hasher="preflight"), self.assertRaisesRegex(verify_behavior.HarnessError, "parcours.*incomplet"):
                        verify_behavior.main(["--cases", str(cases), "--output", str(root / "results")])
                    build.assert_not_called()
                    launch.assert_not_called()
                self.assertFalse((root / "results").exists())
            finally:
                if os.geteuid() != original_euid:
                    os.seteuid(original_euid)
                unreadable.chmod(0o700)

    def test_execution_case_mutations_are_rejected_before_any_launch(self):
        for field in ("prompt", "prompts", "sandbox", "ephemeral", "cwd", "bundle", "case-hash-removed", "git-hash-removed"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = behavior_scenarios.create_project(root, "alder", {"file.txt": "original"}, [])
                bundle = root / "bundle"
                skill = bundle / "skills/cstack/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("skill")
                cases, expectations = [], []
                behavior_scenarios.register(cases, expectations, case_id="one", project=project,
                    bundle=bundle, skill="cstack", roles=[], body="Read the code.")
                if field == "case-hash-removed":
                    expectations[0].pop("case_sha256")
                elif field == "git-hash-removed":
                    expectations[0].pop("git_sha256")
                elif field in ("cwd", "bundle"):
                    changed = root / ("other-" + field)
                    shutil.copytree(project if field == "cwd" else bundle, changed)
                    cases[0][field] = str(changed)
                elif field == "prompts":
                    cases[0].pop("prompt")
                    cases[0]["prompts"] = ["Perform another task."]
                else:
                    cases[0][field] = {"prompt": "Perform another task.", "sandbox": "read-only", "ephemeral": True}[field]
                case_path, expected_path = root / "cases.json", root / "expectations.json"
                case_path.write_text(json.dumps(cases))
                expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations}))
                with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                     patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                    with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte.*(?:cas|Git)"):
                        verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                            "--output", str(root / "results")])
                    build.assert_not_called()
                    launch.assert_not_called()
                self.assertFalse((root / "results").exists())

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(socket, "AF_UNIX"), "Unix entries required")
    def test_nonregular_entries_are_rejected_by_hashes_and_before_launch(self):
        for kind in ("fifo", "socket", "linked-device"):
            for scope in ("project", "bundle"):
                with self.subTest(kind=kind, scope=scope), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    project = behavior_scenarios.create_project(root, "alder", {"file.txt": "original"}, [])
                    bundle = root / "bundle"
                    skill = bundle / "skills/cstack/SKILL.md"
                    skill.parent.mkdir(parents=True)
                    skill.write_text("skill")
                    cases, expectations = [], []
                    behavior_scenarios.register(cases, expectations, case_id="one", project=project,
                        bundle=bundle, skill="cstack", roles=[], body="Read the code.")
                    entry = (project if scope == "project" else bundle) / "unsupported"
                    live_socket = None
                    try:
                        if kind == "fifo":
                            os.mkfifo(entry)
                        elif kind == "socket":
                            live_socket = socket.socket(socket.AF_UNIX)
                            live_socket.bind(str(entry))
                        else:
                            entry.symlink_to("/dev/null")
                        case_path, expected_path = root / "cases.json", root / "expectations.json"
                        case_path.write_text(json.dumps(cases))
                        expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations}))
                        with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                             patch.object(verify_behavior, "run_case", return_value={"id": "one", "status": "completed"}) as launch:
                            with self.assertRaisesRegex(verify_behavior.HarnessError, "réguli"):
                                verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                                    "--output", str(root / "results")])
                            build.assert_not_called()
                            launch.assert_not_called()
                        with self.assertRaisesRegex(ValueError, "réguli"):
                            behavior_scenarios.tree_hash(entry.parent)
                        with self.assertRaisesRegex(verify_behavior.HarnessError, "réguli"):
                            verify_behavior.tree_hash(entry.parent, None)
                        self.assertFalse((root / "results").exists())
                        with patch.object(verify_behavior, "build_command", return_value=["fake"]) as build, \
                             patch.object(verify_behavior, "run_case") as launch:
                            with self.assertRaisesRegex(verify_behavior.HarnessError, "réguli"):
                                verify_behavior.main(["--cases", str(case_path), "--output", str(root / "legacy-results")])
                            build.assert_not_called()
                            launch.assert_not_called()
                        self.assertFalse((root / "legacy-results").exists())
                    finally:
                        if live_socket is not None:
                            live_socket.close()

    def test_chmod_of_project_bundle_or_file_link_target_invalidates_provenance(self):
        for scope in ("project", "bundle", "file-link"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project, bundle = root / "project", root / "bundle"
                project.mkdir()
                bundle.mkdir()
                hashed = bundle if scope == "bundle" else project
                script = hashed / "tool.sh"
                script.write_text("#!/bin/sh\nexit 0\n")
                script.chmod(0o755)
                if scope == "file-link":
                    (project / "alias.sh").symlink_to("tool.sh")
                subprocess.run([str(script)], check=True)
                digest = behavior_scenarios.tree_hash(hashed)
                expectation = {"id": "one", "hash_algorithm": "cstack-tree-sha256-v2"}
                if scope == "bundle":
                    expectation["source_sha256"] = {"bundle": digest}
                else:
                    expectation["project_sha256"] = digest
                case = {"id": "one", "cwd": project, "bundle": bundle, "prompts": ["Read."]}
                expectation["case_sha256"] = behavior_scenarios.case_hash(case)
                expectation["git_sha256"] = behavior_scenarios.git_hash(project)
                verify_behavior.verify_provenance(case, expectation)
                script.chmod(0o644)
                with self.assertRaises(PermissionError):
                    subprocess.run([str(script)], check=True)
                with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte"):
                    verify_behavior.verify_provenance(case, expectation)
                self.assertNotEqual(behavior_scenarios.tree_hash(hashed), digest)
                self.assertEqual(behavior_scenarios.tree_hash(hashed), verify_behavior.tree_hash(hashed, None)["sha256"])

    def test_directory_links_cannot_receive_project_or_bundle_provenance(self):
        for scope in ("project", "bundle"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project, bundle = root / "project", root / "bundle"
                project.mkdir()
                skill = bundle / "skills/cstack/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("skill")
                external = root / "external"
                external.mkdir()
                (external / "file.txt").write_text("external code")
                case = {"id": "one", "cwd": project, "bundle": bundle, "prompts": ["Read."]}
                expectation = {"id": "one", "hash_algorithm": "cstack-tree-sha256-v2"}
                expectation["case_sha256"] = behavior_scenarios.case_hash(case)
                expectation["git_sha256"] = behavior_scenarios.git_hash(project)
                hashed = project if scope == "project" else bundle
                digest = behavior_scenarios.tree_hash(hashed)
                if scope == "project":
                    expectation["project_sha256"] = digest
                else:
                    expectation["source_sha256"] = {"bundle": digest}
                (hashed / "external-code").symlink_to(external, target_is_directory=True)
                with self.assertRaisesRegex(verify_behavior.HarnessError, "symbolique"):
                    verify_behavior.verify_provenance(case, expectation)
                with self.assertRaisesRegex(ValueError, "symbolique"):
                    behavior_scenarios.tree_hash(hashed)

    def test_excluded_directory_links_remain_outside_declared_hash_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, external = root / "project", root / "external"
            project.mkdir()
            external.mkdir()
            (project / "file.txt").write_text("code")
            before = behavior_scenarios.tree_hash(project)
            for name in (".git", "node_modules", "__pycache__"):
                (project / name).symlink_to(external, target_is_directory=True)
            self.assertEqual(behavior_scenarios.tree_hash(project), before)
            self.assertEqual(verify_behavior.tree_hash(project, None)["sha256"], before)

    def test_tree_digest_distinguishes_file_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.bin").write_bytes(b"x")
            (root / "b.bin").write_bytes(b"y")
            expected = behavior_scenarios.tree_hash(root)
            case = {"id": "one", "cwd": root, "bundle": None, "prompts": ["Read."]}
            expectation = {"id": "one", "project_sha256": expected, "hash_algorithm": "cstack-tree-sha256-v2"}
            expectation["case_sha256"] = behavior_scenarios.case_hash(case)
            expectation["git_sha256"] = behavior_scenarios.git_hash(root)
            verify_behavior.verify_provenance(case, expectation)
            (root / "a.bin").write_bytes(b"xb.bin\0y")
            (root / "b.bin").unlink()
            with self.assertRaisesRegex(verify_behavior.HarnessError, "empreinte projet"):
                verify_behavior.verify_provenance(case, expectation)
            self.assertNotEqual(behavior_scenarios.tree_hash(root), expected)
            self.assertEqual(behavior_scenarios.tree_hash(root), verify_behavior.tree_hash(root, None)["sha256"])

    def test_file_links_are_hashed_as_materialized_copies_and_repeats_stay_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = behavior_scenarios.create_project(root, "alder", {"a.bin": "original"}, [])
            (project / "a.bin").chmod(0o755)
            alias = project / "alias.bin"
            alias.symlink_to("a.bin")
            bundle = root / "bundle"
            skill = bundle / "skills/cstack/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("skill")
            cases, expectations = [], []
            behavior_scenarios.register(cases, expectations, case_id="one", project=project,
                bundle=bundle, skill="cstack", roles=[], body="Read the code.")
            case_path, expected_path = root / "cases.json", root / "expectations.json"
            case_path.write_text(json.dumps(cases))
            expected_path.write_text(json.dumps({"schema_version": 1, "cases": expectations}))

            def modify_copy(case, *args):
                copied = case["cwd"] / "alias.bin"
                self.assertFalse(copied.is_symlink())
                self.assertEqual(copied.stat().st_mode & 0o7777, 0o755)
                self.assertEqual((case["cwd"] / "a.bin").stat().st_mode & 0o7777, 0o755)
                self.assertEqual(verify_behavior.tree_hash(case["cwd"], None)["sha256"], expectations[0]["project_sha256"])
                copied.write_text("changed")
                self.assertEqual((case["cwd"] / "a.bin").read_text(), "original")
                return {"id": case["id"], "cwd": str(case["cwd"]), "status": "completed", "native_child_thread_ids": []}

            with patch.object(verify_behavior, "build_command", return_value=["fake"]), \
                 patch.object(verify_behavior, "run_case", side_effect=modify_copy) as launch:
                code = verify_behavior.main(["--cases", str(case_path), "--expectations", str(expected_path),
                    "--output", str(root / "results"), "--repeats", "2"])
                self.assertEqual(code, 0)
                self.assertEqual(launch.call_count, 2)
            self.assertTrue(alias.is_symlink())
            self.assertEqual(alias.read_text(), "original")
            self.assertEqual((project / "a.bin").read_text(), "original")

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
            old_expectation["case_sha256"] = behavior_scenarios.case_hash(old_case)
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
                    "--case-id", "one", "--output", str(root / "results"), "--repeats", "2",
                    "--model", "native-choice", "--effort", "max", "--turn-timeout", "12"])
            self.assertEqual(code, 0)
            self.assertEqual(launch.call_count, 2)
            self.assertEqual((Path(cases[0]["cwd"]) / "events.py").read_text(), "original")
            receipts = json.loads((root / "results/summary.json").read_text())["cases"]
            for receipt in receipts:
                self.assertEqual(receipt["source_case_id"], "one")
                self.assertEqual(receipt["case_sha256"], expectations[0]["case_sha256"])
                self.assertTrue(receipt["case_hash_verified"])
                self.assertTrue(receipt["git_hash_verified"])
                self.assertEqual(receipt["git_sha256"], expectations[0]["git_sha256"])
                self.assertEqual(receipt["effective_case_sha256"], behavior_scenarios.case_hash(receipt["effective_case"]))
                self.assertNotEqual(receipt["effective_case_sha256"], receipt["case_sha256"])
                self.assertEqual(receipt["effective_case"]["id"], receipt["id"])
                self.assertEqual(receipt["effective_case"]["cwd"], receipt["cwd"])
                self.assertEqual(receipt["requested_runtime_config"], {
                    "model": "native-choice", "effort": "max", "turn_timeout": 12.0, "trace_routes": False})

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
