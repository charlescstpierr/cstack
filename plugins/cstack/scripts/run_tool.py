#!/usr/bin/env python3
import errno
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePath


EXCLUDED = {"node_modules", "cache", ".cache", "__pycache__"}
OWNER_PID = "owner.pid"


def fail(message):
    print(f"run-tool: {message}", file=sys.stderr)
    raise SystemExit(2)


def exit_status(returncode):
    if returncode is None:
        return 1
    if returncode < 0:
        return 128 + (-returncode)
    return returncode


def validate_source(source):
    for root, directories, names in os.walk(source):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED)
        for name in directories:
            path = Path(root, name)
            if path.is_symlink():
                fail(f"source entry is not a regular directory: {path.relative_to(source)}")
        for name in sorted(names):
            path = Path(root, name)
            resolved = path.resolve()
            try:
                resolved.relative_to(source)
            except ValueError:
                fail(f"source symlink escapes helper directory: {path.relative_to(source)}")
            if not resolved.is_file():
                fail(f"source entry is not a regular file: {path.relative_to(source)}")


def workspace_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return Path.cwd()
    return Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()


def require_inside(path, root, label):
    try:
        path.resolve().relative_to(root)
    except ValueError:
        fail(f"{label} escapes workspace: {path}")


def ensure_cstack_gitignore(state):
    ignore = state / ".gitignore"
    if ignore.exists() or ignore.is_symlink():
        return
    ignore.write_text("*\n")


def stage_owner_dead(path):
    pid_file = path / OWNER_PID
    if pid_file.is_symlink() or not pid_file.is_file():
        return False
    try:
        raw = pid_file.read_text().strip()
    except OSError:
        return False
    if not raw.isdigit():
        return False
    pid = int(raw)
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OverflowError:
        return False
    except OSError as error:
        return getattr(error, "errno", None) == errno.ESRCH
    return False


def sweep_stale_stages(tools):
    try:
        entries = list(tools.iterdir())
    except OSError:
        return
    for path in entries:
        if not path.name.startswith("run-"):
            continue
        if path.is_symlink() or not path.is_dir():
            continue
        if not stage_owner_dead(path):
            continue
        try:
            shutil.rmtree(path)
        except OSError as error:
            print(f"run-tool: leftover stage {path.name}: {error}", file=sys.stderr)


def bun_command(bunfig, *args):
    return ["bun", "--no-env-file", f"--config={bunfig}", *args]


def main():
    if len(sys.argv) < 2:
        fail("usage: run-tool.sh <relative-helper> [args ...]")

    requested = PurePath(sys.argv[1])
    if requested.is_absolute() or ".." in requested.parts or not requested.parts:
        fail("helper must be a relative path within skills/cstack/scripts")

    source = (Path(__file__).resolve().parent.parent / "skills/cstack/scripts").resolve()
    entry = (source / requested).resolve()
    try:
        resolved_relative = entry.relative_to(source)
    except ValueError:
        fail("helper resolves outside skills/cstack/scripts")
    if EXCLUDED.intersection(requested.parts) or EXCLUDED.intersection(resolved_relative.parts):
        fail("helper is inside an excluded cache directory")
    if not entry.is_file():
        fail(f"helper is not a regular file: {sys.argv[1]}")

    suffix = entry.suffix
    if suffix == ".sh":
        runtime = "bash"
    elif suffix in {"", ".ts", ".js", ".mjs"}:
        runtime = "bun"
    else:
        fail(f"unsupported helper type: {suffix or '<none>'}")
    if shutil.which(runtime) is None:
        fail(f"required runtime not found: {runtime}")

    validate_source(source)
    workspace = workspace_root().resolve()
    state = workspace / ".cstack"
    if state.is_symlink():
        require_inside(state, workspace, ".cstack symlink")
    state.mkdir(exist_ok=True)
    require_inside(state, workspace, ".cstack directory")
    ensure_cstack_gitignore(state)
    tools = state / "tools"
    if tools.is_symlink():
        require_inside(tools, workspace, "tools symlink")
    tools.mkdir(exist_ok=True)
    require_inside(tools, workspace, "tools directory")
    sweep_stale_stages(tools)
    staged = Path(tempfile.mkdtemp(prefix="run-", dir=tools))
    (staged / OWNER_PID).write_text(f"{os.getpid()}\n")
    pending = {"child": None}

    def forward(signum, _frame):
        proc = pending["child"]
        if proc is not None:
            if proc.poll() is None:
                try:
                    proc.send_signal(signum)
                except OSError:
                    pass
            return
        raise SystemExit(128 + signum)

    def run_tracked(argv, **kwargs):
        proc = subprocess.Popen(argv, **kwargs)
        pending["child"] = proc
        try:
            return proc.wait()
        finally:
            pending["child"] = None

    previous_int = signal.signal(signal.SIGINT, forward)
    previous_term = signal.signal(signal.SIGTERM, forward)
    try:
        shutil.copytree(
            source,
            staged,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*EXCLUDED),
        )
        staged.chmod(0o700)
        for root, _, _ in os.walk(staged):
            Path(root).chmod(Path(root).stat().st_mode | stat.S_IWUSR | stat.S_IXUSR)
        bunfig = staged / "bunfig.toml"
        if not bunfig.is_file():
            bunfig.write_text("")
        bunfig = bunfig.resolve()
        if runtime == "bun" and all((staged / name).is_file() for name in ("bootstrap.ts", "package.json", "bun.lock")):
            environment = os.environ | {"CSTACK_BOOTSTRAP_ONLY": "1"}
            setup = run_tracked(
                bun_command(
                    bunfig,
                    "-e",
                    'import { ensureDependenciesInstalled } from "./bootstrap.ts"; ensureDependenciesInstalled()',
                ),
                cwd=str(staged),
                env=environment,
            )
            if setup:
                status = exit_status(setup)
                print(f"run-tool: dependency setup exited with status {status}", file=sys.stderr)
                raise SystemExit(status)

        staged_entry = (staged / requested).resolve()
        require_inside(staged_entry, staged.resolve(), "staged helper")
        if not staged_entry.is_file():
            fail(f"staged helper is not a regular file: {sys.argv[1]}")
        if runtime == "bun":
            command = bun_command(bunfig, str(staged_entry), *sys.argv[2:])
        else:
            command = [runtime, str(staged_entry), *sys.argv[2:]]
        raise SystemExit(exit_status(run_tracked(command)))
    finally:
        signal.signal(signal.SIGINT, previous_int)
        signal.signal(signal.SIGTERM, previous_term)
        try:
            shutil.rmtree(staged)
        except OSError as error:
            print(f"run-tool: failed to remove staged helper: {error}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        detail = f": {error.filename}" if error.filename else ""
        fail(f"{error.strerror or error}{detail}")
