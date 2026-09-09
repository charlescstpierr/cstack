#!/usr/bin/env python3
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePath


EXCLUDED = {"node_modules", "cache", ".cache", "__pycache__"}


def fail(message):
    print(f"run-tool: {message}", file=sys.stderr)
    raise SystemExit(2)


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
    tools = state / "tools"
    if tools.is_symlink():
        require_inside(tools, workspace, "tools symlink")
    tools.mkdir(exist_ok=True)
    require_inside(tools, workspace, "tools directory")
    staged = Path(tempfile.mkdtemp(prefix="run-", dir=tools))
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
        if runtime == "bun" and all((staged / name).is_file() for name in ("bootstrap.ts", "package.json", "bun.lock")):
            environment = os.environ | {"CSTACK_BOOTSTRAP_ONLY": "1"}
            setup = subprocess.run(
                ["bun", "-e", 'import { ensureDependenciesInstalled } from "./bootstrap.ts"; ensureDependenciesInstalled()'],
                cwd=staged,
                env=environment,
            )
            if setup.returncode:
                fail(f"dependency setup exited with status {setup.returncode}")

        staged_entry = (staged / requested).resolve()
        require_inside(staged_entry, staged.resolve(), "staged helper")
        if not staged_entry.is_file():
            fail(f"staged helper is not a regular file: {sys.argv[1]}")
        result = subprocess.run([runtime, str(staged_entry), *sys.argv[2:]])
        raise SystemExit(result.returncode)
    finally:
        shutil.rmtree(staged)


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        detail = f": {error.filename}" if error.filename else ""
        fail(f"{error.strerror or error}{detail}")
