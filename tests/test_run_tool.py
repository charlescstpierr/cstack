import contextlib
import importlib.util
import io
import json
import os
import shutil
import signal
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
STAGE_PREFIX = "cstack-run-"


class RunToolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name).resolve()
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
        self.home = (root / "home").resolve()
        self.home.mkdir()
        self.stage_tmp = self.home / ".cache/cstack/stages"
        self.stage_tmp.mkdir(mode=0o700, parents=True)
        bun = self.bin / "bun"
        bun.write_text("#!{}\n".format(sys.executable) + textwrap.dedent("""\
            import json, os, pathlib, signal, sys, time
            args = sys.argv[1:]
            if args == ["--help"]:
                print("Usage: bun [options]")
                if not os.environ.get("FAKE_BUN_NO_ENV_FILE_MISSING"):
                    print("  --no-env-file")
                raise SystemExit()
            config = None
            tsconfig_override = None
            no_env_file = False
            i = 0
            while i < len(args):
                arg = args[i]
                if arg == "--no-env-file":
                    no_env_file = True
                    i += 1
                    continue
                if arg.startswith("--config="):
                    config = arg.split("=", 1)[1]
                    i += 1
                    continue
                if arg == "--config":
                    config = args[i + 1]
                    i += 2
                    continue
                if arg.startswith("--tsconfig-override="):
                    tsconfig_override = arg.split("=", 1)[1]
                    i += 1
                    continue
                if arg == "--tsconfig-override":
                    tsconfig_override = args[i + 1]
                    i += 2
                    continue
                break
            args = args[i:]
            if args and args[0] == "-e":
                if name := os.environ.get("FAKE_BUN_SETUP_SIGNAL"):
                    os.kill(os.getpid(), getattr(signal, name))
                if code := os.environ.get("FAKE_BUN_SETUP_EXIT"):
                    raise SystemExit(int(code))
                marker = pathlib.Path.cwd() / "node_modules/.cstack-tools-install-key"
                if not marker.exists():
                    with open(os.environ["FAKE_BUN_INSTALL_LOG"], "a") as log:
                        log.write("install\\n")
                    time.sleep(0.1)
                    marker.parent.mkdir(exist_ok=True)
                    marker.write_text("ready")
                raise SystemExit()
            entry = pathlib.Path(args[0])
            stage = next((parent for parent in entry.parents if (parent / "package.json").exists()), entry.parent)
            if os.environ.get("FAKE_BUN_LOCK_STAGE"):
                locked = entry.parent / "locked"
                locked.mkdir()
                (locked / "x").write_text("x")
                locked.chmod(0o000)
                raise SystemExit(int(os.environ.get("FAKE_BUN_EXIT", "7")))
            if name := os.environ.get("FAKE_BUN_SIGNAL"):
                os.kill(os.getpid(), getattr(signal, name))
            if barrier := os.environ.get("FAKE_BUN_BARRIER"):
                barrier = pathlib.Path(barrier)
                barrier.mkdir(exist_ok=True)
                (barrier / str(os.getpid())).touch()
                deadline = time.monotonic() + 2
                while len(list(barrier.iterdir())) < 2 and time.monotonic() < deadline:
                    time.sleep(0.01)
                if len(list(barrier.iterdir())) < 2:
                    raise SystemExit("helpers did not overlap")
            tsconfig = tsconfig_override
            print(json.dumps({
                "argv": args[1:], "cwd": os.getcwd(),
                "entry": str(entry), "content": entry.read_text(),
                "node_modules": (stage / "node_modules").exists(),
                "ignored_module": (stage / "node_modules/ignored").exists(),
                "cache": (stage / "cache").exists(),
                "no_env_file": no_env_file,
                "config": config,
                "tsconfig": tsconfig,
            }))
            """))
        bun.chmod(0o755)
        self.env = os.environ | {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.home),
        }

    def tearDown(self):
        self._make_writable(Path(self.temp.name))
        self.temp.cleanup()

    @staticmethod
    def _make_writable(root):
        for dirpath, _directories, files in os.walk(root, topdown=True):
            current = Path(dirpath)
            try:
                if not current.is_symlink():
                    current.chmod(current.stat().st_mode | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRUSR)
            except OSError:
                continue
            for name in files:
                path = current / name
                if path.is_symlink():
                    continue
                try:
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)
                except OSError:
                    pass

    def run_tool(self, entry, *args, check=True, env=None):
        return subprocess.run(
            [BASH, str(self.plugin / "scripts/run-tool.sh"), str(entry), *args],
            cwd=self.cwd, env=env or self.env, text=True, capture_output=True,
            check=check,
        )

    def assert_under_stage_tmp(self, path):
        path = Path(path)
        self.assertTrue(path.is_relative_to(self.stage_tmp), path)
        self.assertTrue(
            any(parent.name.startswith(STAGE_PREFIX) for parent in [path, *path.parents]),
            path,
        )

    def leftover_stage_dirs(self, root):
        return [
            path for path in Path(root).rglob("*")
            if path.is_dir() and not path.is_symlink() and path.name.startswith(STAGE_PREFIX)
        ]

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
        self.assert_under_stage_tmp(data["entry"])
        self.assertFalse(Path(data["entry"]).is_relative_to(self.cwd))
        self.assertFalse(Path(data["entry"]).exists())
        self.assertEqual(self.leftover_stage_dirs(self.stage_tmp), [])
        self.assertEqual(self.leftover_stage_dirs(self.cwd), [])

    def test_source_change_is_reflected_in_a_new_stage(self):
        helper = self.source / "tool.ts"
        helper.write_text("one")
        first = json.loads(self.run_tool("tool.ts").stdout)
        helper.write_text("two")
        second = json.loads(self.run_tool("tool.ts").stdout)

        self.assertEqual(first["content"], "one")
        self.assertEqual(second["content"], "two")
        self.assert_under_stage_tmp(first["entry"])
        self.assert_under_stage_tmp(second["entry"])
        self.assertNotEqual(Path(first["entry"]).parent, Path(second["entry"]).parent)
        self.assertFalse(Path(first["entry"]).exists())
        self.assertFalse(Path(second["entry"]).exists())

    def test_ignores_preplanted_code_and_dependency_markers(self):
        (self.source / "tool.ts").write_text("trusted")
        (self.source / "package.json").write_text("{}")
        (self.source / "bun.lock").write_text("")
        (self.source / "bootstrap.ts").write_text("trusted bootstrap")
        planted = self.stage_tmp / f"{STAGE_PREFIX}planted"
        (planted / "node_modules").mkdir(parents=True)
        (planted / "tool.ts").write_text("tampered")
        (planted / "bootstrap.ts").write_text("tampered bootstrap")
        (planted / "node_modules/.cstack-tools-install-key").write_text("forged")
        install_log = self.bin.parent / "installs"
        env = self.env | {"FAKE_BUN_INSTALL_LOG": str(install_log)}
        data = json.loads(self.run_tool("tool.ts", env=env).stdout)

        self.assertEqual(data["content"], "trusted")
        self.assert_under_stage_tmp(data["entry"])
        self.assertNotEqual(Path(data["entry"]).parent, planted)
        self.assertEqual(install_log.read_text().splitlines(), ["install"])
        self.assertEqual([path for path in self.stage_tmp.iterdir() if path.name.startswith(STAGE_PREFIX)], [planted])

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
        self.assert_under_stage_tmp(data["entry"])
        self.assertFalse(Path(data["entry"]).is_relative_to(repository))
        self.assertEqual(data["cwd"], str(nested))
        self.assertTrue((repository / ".cstack/.gitignore").is_file())
        self.assertFalse((nested / ".cstack").exists())

    def test_uses_cwd_when_git_is_unavailable(self):
        (self.source / "tool.ts").write_text("no git")
        path = self.bin.parent / "runtime-only"
        path.mkdir()
        (path / "python3").symlink_to(Path(sys.executable))
        (path / "bun").symlink_to(self.bin / "bun")

        data = json.loads(self.run_tool("tool.ts", env=self.env | {"PATH": str(path)}).stdout)
        self.assert_under_stage_tmp(data["entry"])
        self.assertTrue((self.cwd / ".cstack/.gitignore").is_file())

    def test_reports_a_missing_runtime(self):
        (self.source / "tool.ts").write_text("")
        path = self.bin.parent / "python-only"
        path.mkdir()
        (path / "python3").symlink_to(Path(sys.executable))
        result = self.run_tool("tool.ts", check=False, env=self.env | {"PATH": str(path)})
        self.assertEqual(result.returncode, 2)
        self.assertIn("required runtime not found: bun", result.stderr)

    def test_rejects_bun_without_no_env_file_support(self):
        (self.source / "tool.ts").write_text("trusted")
        result = self.run_tool(
            "tool.ts",
            check=False,
            env=self.env | {"FAKE_BUN_NO_ENV_FILE_MISSING": "1"},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--no-env-file", result.stderr)
        self.assertFalse((self.cwd / ".cstack").exists())

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
        self.assertEqual(list(outside.iterdir()), [])

        state.unlink()
        state.mkdir()
        (state / "tools").symlink_to(outside, target_is_directory=True)
        result = self.run_tool("tool.ts")
        data = json.loads(result.stdout)
        self.assert_under_stage_tmp(data["entry"])
        self.assertFalse(Path(data["entry"]).is_relative_to(outside))
        self.assertEqual(list(outside.iterdir()), [])

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
        entries = [Path(json.loads(result[0])["entry"]) for result in results]
        for entry in entries:
            self.assert_under_stage_tmp(entry)
        self.assertNotEqual(entries[0].parent, entries[1].parent)
        self.assertFalse(any(entry.exists() for entry in entries))
        self.assertEqual(install_log.read_text().splitlines(), ["install", "install"])

    def test_signaled_helper_maps_to_128_plus_signal(self):
        helper = self.source / "die.sh"
        helper.write_text("kill -TERM $$\n")
        result = self.run_tool("die.sh", check=False)
        self.assertEqual(result.returncode, 128 + signal.SIGTERM)

    def test_signaled_dependency_setup_keeps_its_signal_status(self):
        (self.source / "tool.ts").write_text("trusted")
        (self.source / "package.json").write_text("{}")
        (self.source / "bun.lock").write_text("")
        (self.source / "bootstrap.ts").write_text("")
        result = self.run_tool(
            "tool.ts",
            check=False,
            env=self.env | {"FAKE_BUN_SETUP_SIGNAL": "SIGTERM"},
        )
        self.assertEqual(result.returncode, 128 + signal.SIGTERM)
        self.assertIn("dependency setup exited with status", result.stderr)

    def test_failed_dependency_setup_keeps_its_exit_code(self):
        (self.source / "tool.ts").write_text("trusted")
        (self.source / "package.json").write_text("{}")
        (self.source / "bun.lock").write_text("")
        (self.source / "bootstrap.ts").write_text("")
        result = self.run_tool(
            "tool.ts",
            check=False,
            env=self.env | {"FAKE_BUN_SETUP_EXIT": "5"},
        )
        self.assertEqual(result.returncode, 5)

    def test_out_of_range_owner_pid_does_not_abort_the_sweep(self):
        (self.source / "tool.ts").write_text("trusted")
        huge = self.stage_tmp / f"{STAGE_PREFIX}huge"
        huge.mkdir()
        (huge / "owner.pid").write_text("{}\n".format(2 ** 70))
        result = self.run_tool("tool.ts")
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(f"{STAGE_PREFIX}huge", {path.name for path in self.stage_tmp.iterdir()})

    def test_cleanup_failure_does_not_replace_helper_exit_code(self):
        (self.source / "tool.ts").write_text("trusted")
        result = self.run_tool(
            "tool.ts",
            check=False,
            env=self.env | {"FAKE_BUN_LOCK_STAGE": "1", "FAKE_BUN_EXIT": "7"},
        )
        self.assertEqual(result.returncode, 7)
        self.assertIn("failed to remove staged helper", result.stderr)

    def test_creates_cstack_gitignore_without_clobbering(self):
        (self.source / "tool.ts").write_text("trusted")
        self.run_tool("tool.ts")
        ignore = self.cwd / ".cstack/.gitignore"
        self.assertEqual(ignore.read_text(), "*\n")
        ignore.write_text("keep\n")
        self.run_tool("tool.ts")
        self.assertEqual(ignore.read_text(), "keep\n")

    def test_sweep_stale_run_stages_without_touching_other_state(self):
        (self.source / "tool.ts").write_text("trusted")
        keep = self.cwd / ".cstack/models.json"
        keep.parent.mkdir(parents=True)
        keep.write_text("keep")
        other = self.stage_tmp / "not-a-stage"
        other.mkdir()
        (other / "file").write_text("stay")
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        self.assertEqual(dead.wait(), 0)
        stale = self.stage_tmp / f"{STAGE_PREFIX}dead"
        stale.mkdir()
        (stale / "owner.pid").write_text("{}\n".format(dead.pid))
        live = self.stage_tmp / f"{STAGE_PREFIX}live"
        live.mkdir()
        (live / "owner.pid").write_text("{}\n".format(os.getpid()))
        (live / "marker").write_text("live")
        orphan = self.stage_tmp / f"{STAGE_PREFIX}orphan"
        orphan.mkdir()
        (orphan / "marker").write_text("no-pid")
        self.run_tool("tool.ts")
        names = {path.name for path in self.stage_tmp.iterdir()}
        self.assertNotIn(f"{STAGE_PREFIX}dead", names)
        self.assertIn(f"{STAGE_PREFIX}live", names)
        self.assertIn(f"{STAGE_PREFIX}orphan", names)
        self.assertIn("not-a-stage", names)
        self.assertEqual(keep.read_text(), "keep")

    def test_bun_uses_neutral_config_and_skips_project_env(self):
        (self.source / "tool.ts").write_text("trusted")
        (self.cwd / "bunfig.toml").write_text('preload = ["./evil.ts"]\n')
        (self.cwd / ".env").write_text("SECRET=1\n")
        data = json.loads(self.run_tool("tool.ts").stdout)
        self.assertTrue(data["no_env_file"])
        self.assertTrue(data["config"])
        self.assertTrue(data["config"].endswith("bunfig.toml"))
        self.assert_under_stage_tmp(data["config"])
        self.assertNotEqual(data["config"], str(self.cwd / "bunfig.toml"))

    def test_corrupt_owner_pid_does_not_abort_the_sweep(self):
        (self.source / "tool.ts").write_text("trusted")
        binary = self.stage_tmp / f"{STAGE_PREFIX}binary"
        binary.mkdir()
        (binary / "owner.pid").write_bytes(b"\xff\xfe\n")
        superscript = self.stage_tmp / f"{STAGE_PREFIX}superscript"
        superscript.mkdir()
        (superscript / "owner.pid").write_text("\u00b2\n", encoding="utf-8")
        result = self.run_tool("tool.ts")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        names = {path.name for path in self.stage_tmp.iterdir()}
        self.assertIn(f"{STAGE_PREFIX}binary", names)
        self.assertIn(f"{STAGE_PREFIX}superscript", names)

    def test_unreadable_stage_directory_does_not_abort_the_sweep(self):
        (self.source / "tool.ts").write_text("trusted")
        locked = self.stage_tmp / f"{STAGE_PREFIX}locked"
        locked.mkdir()
        (locked / "owner.pid").write_text("4000009\n")
        locked.chmod(0o000)
        try:
            result = self.run_tool("tool.ts")
        finally:
            locked.chmod(0o700)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Permission denied", result.stderr)
        self.assertIn(f"{STAGE_PREFIX}locked", {path.name for path in self.stage_tmp.iterdir()})

    def test_owner_pid_longer_than_a_pid_is_not_parsed(self):
        spec = importlib.util.spec_from_file_location("run_tool", PY_LAUNCHER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stage = self.cwd / "run-huge"
        stage.mkdir()
        (stage / "owner.pid").write_text("9" * 5000)
        self.assertFalse(module.stage_owner_dead(stage))

    def test_bun_receives_the_stage_tsconfig_as_an_override(self):
        (self.source / "tool.ts").write_text("trusted")
        (self.cwd / "tsconfig.json").write_text(
            '{"compilerOptions":{"baseUrl":".","paths":{"*":["./evil.ts"]}}}'
        )
        data = json.loads(self.run_tool("tool.ts").stdout)
        self.assertTrue(data["tsconfig"])
        self.assert_under_stage_tmp(data["tsconfig"])
        self.assertNotEqual(data["tsconfig"], str(self.cwd / "tsconfig.json"))

    @unittest.skipUnless(shutil.which("bun"), "bun resolves the entry path")
    def test_a_hostile_workspace_tsconfig_cannot_redirect_the_staged_entry(self):
        (self.source / "tool.ts").write_text('console.log("staged helper ran");\n')
        marker = Path(self.temp.name) / "hijacked"
        (self.cwd / "poison.ts").write_text(
            'import { writeFileSync } from "node:fs";\n'
            f"writeFileSync({json.dumps(str(marker))}, \"1\");\n"
        )
        (self.cwd / "tsconfig.json").write_text(
            '{"compilerOptions":{"baseUrl":".","paths":{"*":["./poison.ts"]}}}'
        )
        result = subprocess.run(
            [BASH, str(self.plugin / "scripts/run-tool.sh"), "tool.ts"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            env=os.environ | {"HOME": str(self.home)},
        )
        self.assertFalse(marker.exists(), result.stderr)
        self.assertIn("staged helper ran", result.stdout)

    def test_hostile_workspace_package_does_not_adopt_the_stage(self):
        (self.source / "tool.ts").write_text("trusted\n")
        (self.cwd / "package.json").write_text(json.dumps({
            "private": True,
            "workspaces": [".cstack/tools/*", f"{self.stage_tmp}/*"],
            "overrides": {"left-pad": "1.0.0"},
        }))
        data = json.loads(self.run_tool("tool.ts").stdout)
        entry = Path(data["entry"])
        self.assert_under_stage_tmp(entry)
        self.assertFalse(entry.is_relative_to(self.cwd))
        self.assertEqual(data["content"], "trusted\n")
        self.assertFalse((self.cwd / ".cstack" / "tools").exists())
        self.assertEqual(self.leftover_stage_dirs(self.cwd), [])

    def test_python_floor_rejects_versions_below_3_9(self):
        spec = importlib.util.spec_from_file_location("run_tool", PY_LAUNCHER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                module.require_python((3, 8, 19))
        self.assertEqual(caught.exception.code, 2)
        lines = stderr.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("run-tool:"))
        module.require_python((3, 9, 0))
        module.require_python((3, 12, 1))


if __name__ == "__main__":
    unittest.main()
