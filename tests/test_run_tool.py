import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / "plugins/cstack/scripts/run-tool.sh"
PY_LAUNCHER = REPO / "plugins/cstack/scripts/run_tool.py"
BASH = shutil.which("bash")


class RunToolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.plugin = root / "read only plugin"
        self.source = self.plugin / "skills/cstack/scripts"
        scripts = self.plugin / "scripts"
        scripts.mkdir(parents=True)
        self.source.mkdir(parents=True)
        shutil.copy2(LAUNCHER, scripts / "run-tool.sh")
        shutil.copy2(PY_LAUNCHER, scripts / "run_tool.py")
        self.cwd = root / "target workspace"
        self.cwd.mkdir()
        self.bin = root / "bin"
        self.bin.mkdir()
        bun = self.bin / "bun"
        bun.write_text(textwrap.dedent("""\
            #!/usr/bin/python3
            import json, os, pathlib, sys, time
            if sys.argv[1] == "-e":
                marker = pathlib.Path.cwd() / "node_modules/.cstack-tools-install-key"
                if not marker.exists():
                    with open(os.environ["FAKE_BUN_INSTALL_LOG"], "a") as log:
                        log.write("install\\n")
                    time.sleep(0.1)
                    marker.parent.mkdir(exist_ok=True)
                    marker.write_text("ready")
                raise SystemExit()
            entry = pathlib.Path(sys.argv[1])
            stage = next((parent for parent in entry.parents if (parent / "package.json").exists()), entry.parent)
            if barrier := os.environ.get("FAKE_BUN_BARRIER"):
                barrier = pathlib.Path(barrier)
                barrier.mkdir(exist_ok=True)
                (barrier / str(os.getpid())).touch()
                deadline = time.monotonic() + 2
                while len(list(barrier.iterdir())) < 2 and time.monotonic() < deadline:
                    time.sleep(0.01)
                if len(list(barrier.iterdir())) < 2:
                    raise SystemExit("helpers did not overlap")
            print(json.dumps({
                "argv": sys.argv[2:], "cwd": os.getcwd(),
                "entry": str(entry), "content": entry.read_text(),
                "node_modules": (stage / "node_modules").exists(),
                "ignored_module": (stage / "node_modules/ignored").exists(),
                "cache": (stage / "cache").exists(),
            }))
            """))
        bun.chmod(0o755)
        self.env = os.environ | {"PATH": f"{self.bin}:{os.environ['PATH']}"}

    def tearDown(self):
        self._make_writable(self.plugin)
        self.temp.cleanup()

    @staticmethod
    def _make_writable(root):
        for path in [root, *root.rglob("*")]:
            if not path.is_symlink():
                path.chmod(path.stat().st_mode | stat.S_IWUSR)

    def run_tool(self, entry, *args, check=True, env=None):
        return subprocess.run(
            [BASH, str(self.plugin / "scripts/run-tool.sh"), str(entry), *args],
            cwd=self.cwd, env=env or self.env, text=True, capture_output=True,
            check=check,
        )

    def test_stages_read_only_sources_and_preserves_cwd_and_arguments(self):
        helper = self.source / "watch-pr/watch-pr"
        helper.parent.mkdir()
        helper.write_text("version one\n")
        (self.source / "node_modules").mkdir()
        (self.source / "node_modules/ignored").write_text("ignored")
        (self.source / "cache").mkdir()
        (self.source / "cache/ignored").write_text("ignored")
        (self.source / "package.json").write_text("{}")
        (self.source / "bun.lock").write_text("")
        (self.source / "bootstrap.ts").write_text("")
        before = sorted((p.relative_to(self.plugin), p.read_bytes()) for p in self.plugin.rglob("*") if p.is_file())
        for path in [*self.plugin.rglob("*"), self.plugin]:
            if not path.is_symlink():
                path.chmod(0o555 if path.is_dir() else 0o444)

        install_log = self.bin.parent / "installs"
        env = self.env | {"FAKE_BUN_INSTALL_LOG": str(install_log)}
        result = self.run_tool("watch-pr/watch-pr", "space value", "$(literal)", "", env=env)
        data = json.loads(result.stdout)

        self.assertEqual(data["argv"], ["space value", "$(literal)", ""])
        self.assertEqual(data["cwd"], str(self.cwd))
        self.assertEqual(data["content"], "version one\n")
        self.assertTrue(data["node_modules"])
        self.assertFalse(data["ignored_module"])
        self.assertFalse(data["cache"])
        after = sorted((p.relative_to(self.plugin), p.read_bytes()) for p in self.plugin.rglob("*") if p.is_file())
        self.assertEqual(after, before)
        self.assertTrue(Path(data["entry"]).is_relative_to(self.cwd / ".cstack/tools"))
        self.assertFalse(Path(data["entry"]).exists())
        self.assertEqual(list((self.cwd / ".cstack/tools").iterdir()), [])

    def test_source_change_is_reflected_in_a_new_stage(self):
        helper = self.source / "tool.ts"
        helper.write_text("one")
        first = json.loads(self.run_tool("tool.ts").stdout)
        helper.write_text("two")
        second = json.loads(self.run_tool("tool.ts").stdout)

        self.assertEqual(first["content"], "one")
        self.assertEqual(second["content"], "two")
        self.assertNotEqual(Path(first["entry"]).parent, Path(second["entry"]).parent)
        self.assertFalse(Path(first["entry"]).exists())
        self.assertFalse(Path(second["entry"]).exists())

    def test_ignores_preplanted_code_and_dependency_markers(self):
        (self.source / "tool.ts").write_text("trusted")
        (self.source / "package.json").write_text("{}")
        (self.source / "bun.lock").write_text("")
        (self.source / "bootstrap.ts").write_text("trusted bootstrap")
        tools = self.cwd / ".cstack/tools"
        planted = tools / ("0" * 64)
        (planted / "node_modules").mkdir(parents=True)
        (planted / "tool.ts").write_text("tampered")
        (planted / "bootstrap.ts").write_text("tampered bootstrap")
        (planted / "node_modules/.cstack-tools-install-key").write_text("forged")
        install_log = self.bin.parent / "installs"
        env = self.env | {"FAKE_BUN_INSTALL_LOG": str(install_log)}
        data = json.loads(self.run_tool("tool.ts", env=env).stdout)

        self.assertEqual(data["content"], "trusted")
        self.assertNotEqual(Path(data["entry"]).parent, planted)
        self.assertEqual(install_log.read_text().splitlines(), ["install"])
        self.assertEqual([path for path in tools.iterdir()], [planted])

    def test_shell_helpers_run_with_bash(self):
        helper = self.source / "show.sh"
        helper.write_text("printf '%s\\n' \"$PWD\" \"$@\"\n")
        result = self.run_tool("show.sh", "a b", "$(literal)")
        self.assertEqual(result.stdout.splitlines(), [str(self.cwd), "a b", "$(literal)"])

    def test_stages_at_git_root_when_called_from_a_subdirectory(self):
        (self.source / "tool.ts").write_text("git root")
        repository = self.cwd / "repo root"
        nested = repository / "nested dir"
        nested.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        self.cwd = nested

        data = json.loads(self.run_tool("tool.ts").stdout)
        self.assertTrue(Path(data["entry"]).is_relative_to(repository / ".cstack/tools"))
        self.assertEqual(data["cwd"], str(nested))

    def test_uses_cwd_when_git_is_unavailable(self):
        (self.source / "tool.ts").write_text("no git")
        path = self.bin.parent / "runtime-only"
        path.mkdir()
        (path / "python3").symlink_to(Path(sys.executable))
        (path / "bun").symlink_to(self.bin / "bun")

        data = json.loads(self.run_tool("tool.ts", env=self.env | {"PATH": str(path)}).stdout)
        self.assertTrue(Path(data["entry"]).is_relative_to(self.cwd / ".cstack/tools"))

    def test_reports_a_missing_runtime(self):
        (self.source / "tool.ts").write_text("")
        path = self.bin.parent / "python-only"
        path.mkdir()
        (path / "python3").symlink_to(Path(sys.executable))
        result = self.run_tool("tool.ts", check=False, env=self.env | {"PATH": str(path)})
        self.assertEqual(result.returncode, 2)
        self.assertIn("required runtime not found: bun", result.stderr)

    def test_rejects_unsafe_or_missing_entrypoints(self):
        (self.source / "ok.ts").write_text("")
        outside = self.plugin / "outside.ts"
        outside.write_text("")
        (self.source / "escape.ts").symlink_to(outside)

        for entry in ("../outside.ts", str(outside), "escape.ts", "missing.ts"):
            with self.subTest(entry=entry):
                result = self.run_tool(entry, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())

    def test_rejects_cache_symlinks_that_escape_the_workspace(self):
        (self.source / "tool.ts").write_text("")
        outside = self.bin.parent / "outside-cache"
        outside.mkdir()
        state = self.cwd / ".cstack"
        state.symlink_to(outside, target_is_directory=True)
        result = self.run_tool("tool.ts", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("escapes workspace", result.stderr)
        self.assertFalse((outside / "tools").exists())

        state.unlink()
        state.mkdir()
        (state / "tools").symlink_to(outside, target_is_directory=True)
        result = self.run_tool("tool.ts", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("escapes workspace", result.stderr)

    def test_filesystem_errors_are_reported_without_a_traceback(self):
        (self.source / "tool.ts").write_text("")
        (self.cwd / ".cstack").write_text("not a directory")
        result = self.run_tool("tool.ts", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("run-tool:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_separate_stage_setup_allows_helpers_to_overlap(self):
        (self.source / "tool.ts").write_text("concurrent")
        (self.source / "package.json").write_text("{}")
        (self.source / "bun.lock").write_text("")
        (self.source / "bootstrap.ts").write_text("")
        barrier = self.bin.parent / "barrier"
        install_log = self.bin.parent / "installs"
        env = self.env | {
            "FAKE_BUN_BARRIER": str(barrier),
            "FAKE_BUN_INSTALL_LOG": str(install_log),
        }
        command = [BASH, str(self.plugin / "scripts/run-tool.sh"), "tool.ts"]
        processes = [subprocess.Popen(command, cwd=self.cwd, env=env, text=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for _ in range(2)]
        results = [process.communicate(timeout=5) + (process.returncode,) for process in processes]
        self.assertEqual([result[2] for result in results], [0, 0], results)
        entries = [Path(json.loads(result[0])["entry"]).parent for result in results]
        self.assertNotEqual(entries[0], entries[1])
        self.assertFalse(any(entry.exists() for entry in entries))
        self.assertEqual(install_log.read_text().splitlines(), ["install", "install"])


if __name__ == "__main__":
    unittest.main()
