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
STAGE_PREFIX = "cstack-run-"


def require_python(version):
    if tuple(version[:2]) < (3, 9):
        fail("Python 3.9 or newer is required")


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


def inside_stage(path, stage, label):
    try:
        path.resolve().relative_to(stage)
    except ValueError:
        fail(f"{label} escapes the stage: {path}")


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


def stage_root():
    home = Path.home()
    root = home / ".cache/cstack/stages"
    for path in (home / ".cache", home / ".cache/cstack", root):
        if path.is_symlink():
            fail(f"stage root is a symlink: {path}")
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as error:
        fail(f"{error.strerror or error}: {root}")
    if root.stat().st_uid != os.getuid():
        fail(f"stage root is not owned by this user: {root}")
    return root


def ensure_cstack_gitignore(state):
    ignore = state / ".gitignore"
    if ignore.exists() or ignore.is_symlink():
        return
    ignore.write_text("*\n")


def stage_owner_dead(path):
    pid_file = path / OWNER_PID
    try:
        if pid_file.is_symlink() or not pid_file.is_file():
            return False
        raw = pid_file.read_bytes()
    except OSError:
        return False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    text = text.strip()
    # CPython 3.9.14 and newer refuse int() on more than 4300 digits, so an
    # over-long run of digits is not a pid and must not reach int().
    if len(text) > 20 or not text.isascii() or not text.isdigit():
        return False
    pid = int(text)
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
        try:
            if not path.name.startswith(STAGE_PREFIX):
                continue
            if path.is_symlink() or not path.is_dir():
                continue
        except OSError:
            continue
        if not stage_owner_dead(path):
            continue
        try:
            shutil.rmtree(path)
        except OSError as error:
            print(f"run-tool: leftover stage {path.name}: {error}", file=sys.stderr)


def bun_command(bunfig, tsconfig, *args):
    # Bun resolves its TypeScript config from the process cwd, which for a
    # helper run is the inspected workspace, so a hostile `paths` mapping there
    # would redirect the staged entry. Pin the stage's neutral config instead.
    override = [f"--tsconfig-override={tsconfig}"] if tsconfig is not None else []
    return ["bun", "--no-env-file", f"--config={bunfig}", *override, *args]


def require_bun_no_env_file():
    result = subprocess.run(
        ["bun", "--help"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 or "--no-env-file" not in output:
        fail("Bun must support --no-env-file to isolate helper scripts")


def main():
    require_python(sys.version_info)
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
    if runtime == "bun":
        require_bun_no_env_file()

    validate_source(source)
    workspace = workspace_root().resolve()
    state = workspace / ".cstack"
    if state.is_symlink():
        require_inside(state, workspace, ".cstack symlink")
    state.mkdir(exist_ok=True)
    require_inside(state, workspace, ".cstack directory")
    ensure_cstack_gitignore(state)
    # The stage must sit outside the inspected workspace and outside a shared
    # temporary root: Bun adopts an ancestor package.json as its install root
    # and honours that tree's overrides, patches and .npmrc.
    stages = stage_root()
    sweep_stale_stages(stages)
    staged = Path(tempfile.mkdtemp(prefix=STAGE_PREFIX, dir=stages))
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
        tsconfig = staged / "tsconfig.json"
        if not tsconfig.is_file():
            tsconfig.write_text("{}\n")
        tsconfig = tsconfig.resolve()
        if runtime == "bun" and all((staged / name).is_file() for name in ("bootstrap.ts", "package.json", "bun.lock")):
            environment = os.environ | {"CSTACK_BOOTSTRAP_ONLY": "1"}
            # This run's cwd is the stage, so Bun already reads the stage's own
            # neutral tsconfig and needs no override.
            setup = run_tracked(
                bun_command(
                    bunfig,
                    None,
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
        inside_stage(staged_entry, staged.resolve(), "staged helper")
        if not staged_entry.is_file():
            fail(f"staged helper is not a regular file: {sys.argv[1]}")
        if runtime == "bun":
            command = bun_command(bunfig, tsconfig, str(staged_entry), *sys.argv[2:])
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
