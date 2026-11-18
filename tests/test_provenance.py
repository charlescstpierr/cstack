"""Replay provenance findings against both public hash consumers."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(os.environ.get("CSTACK_PROVENANCE_SCRIPTS", ROOT / "scripts"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = load("behavior-scenarios")
runner = load("verify-behavior")


class ProvenanceTests(unittest.TestCase):
    def fingerprints(self, root):
        generated = generator.tree_hash(root)
        verified = runner.tree_hash(root, None)["sha256"]
        self.assertEqual(generated, verified)
        return generated

    def rejected(self, root):
        with self.assertRaises(ValueError):
            generator.tree_hash(root)
        with self.assertRaises(runner.HarnessError):
            runner.tree_hash(root, None)

    def git(self, root, *args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE).strip()

    def repo(self, root, commit=True):
        self.git(root, "init", "--initial-branch=main")
        self.git(root, "config", "user.name", "Provenance")
        self.git(root, "config", "user.email", "provenance@example.invalid")
        (root / "file").write_text("one")
        self.git(root, "add", "file")
        if commit:
            self.git(root, "commit", "-m", "base")

    def test_4211195095_files_and_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "file"
            entry.write_text("one")
            entry.chmod(0o644)
            before = self.fingerprints(root)
            entry.chmod(0o755)
            self.assertNotEqual(before, self.fingerprints(root))
            before = self.fingerprints(root)
            entry.write_text("two")
            self.assertNotEqual(before, self.fingerprints(root))

    def test_4211983053_directory_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = self.fingerprints(root)
            entry = root / "empty"
            entry.mkdir(mode=0o755)
            self.assertNotEqual(before, self.fingerprints(root))
            before = self.fingerprints(root)
            entry.chmod(0o700)
            self.assertNotEqual(before, self.fingerprints(root))
            before = self.fingerprints(root)
            entry.rename(root / "renamed")
            self.assertNotEqual(before, self.fingerprints(root))

    def test_4210984697_directory_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target").mkdir()
            (root / "link").symlink_to("target", target_is_directory=True)
            self.rejected(root)

    def test_4212089947_file_symlink_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a", "b"):
                (root / name).write_text("identical bytes")
            link = root / "link"
            link.symlink_to("a")
            before = self.fingerprints(root)
            link.unlink()
            link.symlink_to("b")
            self.assertNotEqual(before, self.fingerprints(root))
            before = self.fingerprints(root)
            link.unlink()
            link.write_text("identical bytes")
            self.assertNotEqual(before, self.fingerprints(root))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX entries required")
    def test_4211485693_special_entries(self):
        for kind in ("fifo", "socket", "device-link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                entry = root / "special"
                live = None
                try:
                    if kind == "fifo":
                        os.mkfifo(entry)
                    elif kind == "socket":
                        live = socket.socket(socket.AF_UNIX)
                        live.bind(str(entry))
                    else:
                        entry.symlink_to("/dev/null")
                    self.rejected(root)
                finally:
                    if live:
                        live.close()

    def test_4211983045_git_head_index_and_refs(self):
        for mutation in ("head", "index", "refs"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.repo(root)
                if mutation == "index":
                    (root / "file").write_text("two")
                before = self.fingerprints(root)
                if mutation == "head":
                    self.git(root, "commit", "--allow-empty", "-m", "same tree")
                elif mutation == "index":
                    self.git(root, "add", "file")
                else:
                    self.git(root, "branch", "another")
                self.assertNotEqual(before, self.fingerprints(root))

    def test_4212451943_in_progress_git_operations(self):
        for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"):
            with self.subTest(operation=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.repo(root)
                entry = root / ".git" / name
                if name in ("rebase-merge", "rebase-apply", "sequencer"):
                    entry.mkdir()
                else:
                    entry.write_bytes(self.git(root, "rev-parse", "HEAD") + b"\n")
                self.rejected(root)

    def test_4212451953_unborn_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.repo(root, commit=False)
            before = self.fingerprints(root)
            self.git(root, "commit", "-m", "first commit")
            self.assertNotEqual(before, self.fingerprints(root))

    def test_staging_an_empty_intent_to_add_changes_the_fingerprint(self):
        for commit in (False, True):
            with self.subTest(commit=commit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.repo(root, commit=commit)
                (root / "empty").touch()
                self.git(root, "add", "-N", "empty")
                before = self.fingerprints(root)
                self.git(root, "add", "empty")
                self.assertNotEqual(before, self.fingerprints(root))

    def test_invalid_head_is_rejected(self):
        for corruption in ("invalid-head", "malformed-ref", "missing-object", "blob"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.repo(root)
                if corruption == "invalid-head":
                    (root / ".git/HEAD").write_text("not a HEAD\n")
                else:
                    values = {"malformed-ref": "malformed", "missing-object": "f" * 40,
                              "blob": self.git(root, "rev-parse", "HEAD:file").decode()}
                    (root / ".git/refs/heads/main").write_text(values[corruption] + "\n")
                self.rejected(root)

    def test_repository_must_use_the_attested_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            original.mkdir()
            self.repo(original)
            self.git(original, "config", "core.worktree", str(original))
            copied = root / "copied"
            shutil.copytree(original, copied)
            self.rejected(copied)

    def test_index_cache_refresh_does_not_change_the_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.repo(root)
            index = root / ".git/index"
            original = index.read_bytes()
            before = self.fingerprints(root)
            self.assertEqual(original, index.read_bytes())
            os.utime(root / "file", (1, 1))
            self.git(root, "update-index", "--refresh")
            self.assertEqual(before, self.fingerprints(root))

    def test_invalid_ref_outside_head_is_rejected(self):
        for value in ("not an object ID", "f" * 40, "ref: refs/heads/absent"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.repo(root)
                (root / ".git/refs/heads/broken").write_text(value + "\n")
                self.rejected(root)

    def test_per_worktree_configuration_changes_the_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.repo(root)
            self.git(root, "config", "--local", "extensions.worktreeConfig", "true")
            before = self.fingerprints(root)
            self.git(root, "config", "--worktree", "core.fileMode", "false")
            self.assertNotEqual(before, self.fingerprints(root))

    def test_4212756294_nested_git_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.repo(root)
            nested = root / "nested"
            nested.mkdir()
            self.repo(nested)
            self.rejected(root)

    def test_copy_preserves_every_attested_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            original.mkdir()
            self.repo(original)
            (original / "empty").mkdir()
            (original / "alias").symlink_to("file")
            copied = root / "copied"
            shutil.copytree(original, copied, symlinks=True)
            self.assertEqual(self.fingerprints(original), self.fingerprints(copied))

    def test_absolute_symlink_to_internal_file_is_rejected_before_any_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target").touch()
            (root / "absolute").symlink_to(root / "target")
            self.rejected(root)

    def test_runner_allows_git_operations_only_without_a_project_fingerprint(self):
        for operation in ("merge", "cherry-pick"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / "project"
                project.mkdir()
                self.repo(project)
                expected = self.fingerprints(project)
                self.git(project, "switch", "-c", "side")
                (project / "file").write_text("side")
                self.git(project, "commit", "-am", "side")
                self.git(project, "switch", "main")
                if operation == "merge":
                    self.git(project, "merge", "--no-ff", "--no-commit", "side")
                else:
                    (project / "file").write_text("main")
                    self.git(project, "commit", "-am", "main")
                    result = subprocess.run(["git", "-C", str(project), "cherry-pick", "side"], capture_output=True)
                    self.assertEqual(result.returncode, 1, result.stderr)
                cases = root / "cases.json"
                cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompts": ["Resolve operation"]}]))
                normalized = runner.read_cases(cases)[0]
                expectations = root / "expectations.json"
                expectations.write_text(json.dumps({"schema_version": 1, "cases": [{
                    "id": "one", "hash_algorithm": runner.TREE_HASH_ALGORITHM,
                    "case_sha256": runner.case_hash(normalized), "project_sha256": expected,
                }]}))
                with patch.object(runner, "AppServer", self.completed_server()), \
                        patch.object(runner, "build_command", return_value=["fake"]):
                    with self.assertRaisesRegex(runner.HarnessError, "opération Git"):
                        runner.main(["--cases", str(cases), "--output", str(root / "attested"),
                                     "--expectations", str(expectations)])
                    self.assertFalse((root / "attested").exists())
                    output = root / "legacy"
                    self.assertEqual(runner.main(["--cases", str(cases), "--output", str(output)]), 0)
                    saved = json.loads((output / "summary.json").read_text())["cases"][0]
                    self.assertEqual(saved["status"], "completed")
                    self.assertIsNone(saved["before_project_hash"]["git_sha256"])

    def completed_server(self, during_turn=None):
        class Server:
            def __init__(self, command, cwd, raw, stderr):
                self.cwd = cwd
                raw.write_text('"retained raw event"\n')
                stderr.write_text("")
            def request(self, method, params, timeout, on_event):
                if method == "thread/start":
                    return {"thread": {"id": "parent"}}
                if method == "turn/start":
                    if during_turn:
                        during_turn(self.cwd)
                    return {"turn": {"id": "turn"}}
                if method == "thread/read":
                    return {"thread": {"id": "parent", "model": "fixture"}}
                return {}
            def notify(self, method):
                pass
            def read(self, deadline):
                return {"method": "turn/completed", "params": {"threadId": "parent", "turn": {"id": "turn", "status": "completed"}}}
            def close(self):
                pass
        return Server

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX entries required")
    def test_4212089956_postrun_hash_error_keeps_receipt(self):
        for name in ("created-fifo", os.fsdecode(b"created-fifo-\xff"), "cycle"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / "project"
                project.mkdir()
                output = root / "results"
                cases = root / "cases.json"
                cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompts": ["Create fifo"]}]))
                def during_turn(cwd):
                    if name == "cycle":
                        (cwd / name).symlink_to(name)
                    else:
                        os.mkfifo(cwd / name)
                with patch.object(runner, "AppServer", self.completed_server(during_turn)), \
                        patch.object(runner, "build_command", return_value=["fake"]):
                    self.assertEqual(runner.main(["--cases", str(cases), "--output", str(output)]), 2)
                saved = json.loads((output / "summary.json").read_text())["cases"][0]
                self.assertEqual(saved["status"], "completed")
                self.assertIsNone(saved["after_project_hash"])
                self.assertIsNone(saved["project_hash_changed"])
                self.assertIn(name, saved["project_hash_error"])
                self.assertEqual(saved["verdicts"]["workflow"]["status"], "unverified")
                self.assertEqual(saved["verdicts"]["outcome"]["status"], "unverified")
                self.assertEqual(saved["turns"][0]["status"], "completed")
                self.assertTrue(Path(saved["raw_stream"]).read_text())


if __name__ == "__main__":
    unittest.main()
