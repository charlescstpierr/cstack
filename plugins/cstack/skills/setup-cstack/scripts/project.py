#!/usr/bin/env python3
"""Preview and apply cstack's fixed project setup files."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any


START = b"<!-- cstack:managed:start -->"
END = b"<!-- cstack:managed:end -->"
PLAN_VERSION = 1
TARGET_PATHS = ("AGENTS.md", "docs/agents/cstack.md", "docs/agents/issue-tracker.md", ".gitignore", ".cstack/models.json")
ALLOWED_PATHS = TARGET_PATHS + ("CLAUDE.md",)
OBSERVED_PATHS = ("AGENTS.md", "CLAUDE.md", "docs/agents/cstack.md", "docs/agents/issue-tracker.md", ".gitignore", ".cstack/models.json")
TRACKER_MODES = {"keep", "local", "github"}
TRACKER_KEYS = {"mode", "owner", "repo"}

# Counts are policy text for the setup preview, not automatic dispatch.
WORKFLOWS = {
    "clarify": {"count_rule": "0 by default; one explorer per delegated independent fact", "roles": ["how explorer"]},
    "domain": {"count_rule": "0 by default; optional fact delegation", "roles": ["how explorer", "documentation", "judgment and prose"]},
    "horizon": {"count_rule": "variable research children; optional 1 synthesis (judgment and prose)", "roles": ["how explorer", "judgment and prose"]},
    "audit-architecture": {"count_rule": "at most 1 initial explorer", "roles": ["how explorer"]},
}


class ProjectError(ValueError):
    pass


class InterruptedApply(Exception):
    def __init__(self, applied: list[str], skipped: list[str]) -> None:
        self.applied, self.skipped = applied, skipped
        super().__init__("apply interrupted; the accepted plan is resumable")


def _models():
    path = Path(__file__).with_name("models.py")
    spec = importlib.util.spec_from_file_location("cstack_setup_models", path)
    if spec is None or spec.loader is None:
        raise ProjectError("cannot load the existing models.py helper")
    module = importlib.util.module_from_spec(spec)
    # Read the trusted helper without writing bytecode into the installed bundle.
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _b64(data: bytes | None) -> str | None:
    return None if data is None else base64.b64encode(data).decode("ascii")


def _unb64(value: Any) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProjectError("snapshot content must be base64 text or null")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeError) as error:
        raise ProjectError("snapshot content is not valid base64") from error


def _path(workspace: Path, relative: str, *, write: bool = False) -> Path:
    allowed = TARGET_PATHS if write else ALLOWED_PATHS
    if relative not in allowed or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ProjectError(f"path is outside the project setup allowlist: {relative}")
    return workspace / relative


def _workspace(path: Path) -> Path:
    """Accept only an existing directory whose ancestors stay in scope."""
    supplied = Path(path)
    absolute = Path(os.path.abspath(supplied))
    if supplied.is_symlink() or not supplied.exists() or not supplied.is_dir():
        raise ProjectError(f"workspace must be an existing regular directory: {path}")
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ProjectError(f"workspace ancestor is a symlink: {current}")
        if current != absolute and not current.is_dir():
            raise ProjectError(f"workspace ancestor is not a directory: {current}")
    return absolute


def _check(path: Path, workspace: Path) -> None:
    try:
        relative = path.relative_to(workspace)
    except ValueError as error:
        raise ProjectError(f"path escapes workspace: {path}") from error
    current = workspace
    for part in relative.parts:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        if current.is_symlink():
            raise ProjectError(f"symlinked project path is not writable: {current}")
        if current != path and not current.is_dir():
            raise ProjectError(f"project parent is not a directory: {current}")
    if (path.exists() or path.is_symlink()) and not path.is_file():
        raise ProjectError(f"project target is not a regular file: {path}")


def _read(workspace: Path, relative: str) -> bytes | None:
    path = _path(workspace, relative)
    _check(path, workspace)
    return path.read_bytes() if path.exists() else None


def _record(data: bytes | None) -> dict[str, Any]:
    return {"exists": data is not None, "sha256": None if data is None else _sha(data), "content_b64": _b64(data)}


def _snapshots(records: dict[str, Any]) -> dict[str, bytes | None]:
    result: dict[str, bytes | None] = {}
    for relative, record in records.items():
        if relative not in ALLOWED_PATHS or not isinstance(record, dict) or set(record) != {"content_b64", "exists", "sha256"}:
            raise ProjectError(f"invalid observed snapshot record: {relative}")
        data = _unb64(record["content_b64"])
        if not isinstance(record["exists"], bool) or record["exists"] != (data is not None) or record["sha256"] != (None if data is None else _sha(data)):
            raise ProjectError(f"snapshot hash or existence does not match: {relative}")
        result[relative] = data
    return result


def _tracker(raw: Any) -> dict[str, str]:
    if raw is None:
        return {"mode": "keep"}
    if not isinstance(raw, dict) or set(raw) - TRACKER_KEYS or "mode" not in raw:
        raise ProjectError("tracker must contain only mode, owner, and repo")
    mode = raw["mode"]
    if mode not in TRACKER_MODES:
        raise ProjectError("tracker mode must be keep, local, or github")
    if mode != "github" and set(raw) != {"mode"}:
        raise ProjectError(f"tracker keys are not valid for mode {mode}")
    if mode == "github":
        pattern = re.compile(r"^[A-Za-z0-9_.-]+$")
        if not all(isinstance(raw.get(key), str) and pattern.fullmatch(raw[key]) for key in ("owner", "repo")):
            raise ProjectError("github tracker owner and repo are invalid")
        return {"mode": mode, "owner": raw["owner"], "repo": raw["repo"]}
    return {"mode": mode}


def _options(raw: Any, models: Any, catalog: dict[str, list[str]] | None) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict) or set(raw) - {"model_choices", "tracker"}:
        raise ProjectError("options may contain only model_choices and tracker")
    choices = raw.get("model_choices", {})
    if not isinstance(choices, dict):
        raise ProjectError("model_choices must be an object")
    try:
        models.validate(choices)
        if choices:
            if catalog is None:
                raise ProjectError("a live catalog is required for explicit model choices")
            models.validate(choices, catalog, check_available=True)
    except (TypeError, ValueError) as error:
        raise ProjectError(f"invalid model_choices: {error}") from error
    return {"model_choices": choices, "tracker": _tracker(raw.get("tracker"))}


def _managed(payload: bytes) -> bytes:
    if START in payload or END in payload:
        raise ProjectError("generated content cannot contain cstack managed markers")
    return START + b"\n" + payload.rstrip(b"\r\n") + b"\n" + END


def _merge(old: bytes | None, payload: bytes, *, owned: bool) -> bytes:
    block = _managed(payload)
    if old is None:
        return block + b"\n"
    starts, ends = old.count(START), old.count(END)
    if starts or ends:
        if starts != 1 or ends != 1 or old.index(START) > old.index(END):
            raise ProjectError("managed markers are malformed or duplicated")
        start, end = old.index(START), old.index(END) + len(END)
        return old[:start] + block + old[end:]
    if owned and old.strip():
        raise ProjectError("refusing to overwrite an unmanaged generated document")
    if owned:
        return block + b"\n"
    separator = b"" if not old or old.endswith((b"\n", b"\r")) else b"\n"
    return old + separator + block + b"\n"


def _agent_payload(snapshots: dict[str, bytes | None]) -> bytes:
    lines = ["## cstack", "", "Read [docs/agents/cstack.md](docs/agents/cstack.md) only after the user explicitly invokes a cstack skill."]
    if snapshots.get("CLAUDE.md") and snapshots["CLAUDE.md"].strip():
        lines += ["", "Read [CLAUDE.md](CLAUDE.md) for existing project rules when they apply. Do not copy them here."]
    return ("\n".join(lines) + "\n").encode()


def _workflow_payload(tracker: dict[str, str]) -> bytes:
    rows = ["# cstack project guidance", "", "Read this file only after the user explicitly invokes a cstack skill.", "", "## Workflows", "", "`$cstack:cstack` owns automatic preparation and execution routing; use the commands below for a focused preparation request.", "", "| Workflow | Invocation | Agent count rule | Reused role keys |", "| --- | --- | --- | --- |"]
    for name, value in WORKFLOWS.items():
        rows.append(f"| `{name}` | `$cstack:{name}` | {value['count_rule']} | {', '.join(f'`{role}`' for role in value['roles'])} |")
    rows += ["", "## Domain records", "", "Use the project's existing CONTEXT.md and ADR conventions when present. Setup does not create blank CONTEXT.md or ADR files.", "", "## Local state", "", "Use `.cstack/horizon` for Horizon state. Keep `.cstack/models.json` as the source for model and reasoning-effort choices. Setup performs no global setup, push, label, or remote action.", "", "## Role boundary", "", "Use `hardest tasks` only for explicit complex architecture. Horizon synthesis uses `judgment and prose`.", "", "## Tracker mode", "", f"The configured tracker mode is `{tracker['mode']}`."]
    if tracker["mode"] == "github":
        rows.append(f"Remote reference: `https://github.com/{tracker['owner']}/{tracker['repo']}`. cstack performs no remote action during setup.")
    return ("\n".join(rows) + "\n").encode()


def _tracker_payload(tracker: dict[str, str]) -> bytes:
    rows = ["# Issue tracker", "", f"Tracker mode: `{tracker['mode']}`."]
    if tracker["mode"] == "local":
        rows += [
            "Use `.cstack/horizon/<slug>/map.md` for the map, `.cstack/horizon/<slug>/tickets/<id>-<slug>.md` for tickets, and `.cstack/horizon/<slug>/research/<id>.md` for research.",
            "Use statuses `ready`, `claimed`, `waiting`, `resolved`, and `out-of-scope`. Keep `owner` stable, use valid IDs in `blocked_by`, and make a ticket eligible only when its dependencies are `resolved`.",
            "Keep one parent writer. Child artifacts stay in their own files. Record the answer before setting a ticket to `resolved`, then add the map gist.",
            "See `$cstack:horizon` templates for the detailed record shapes. Setup creates no labels or remote state.",
        ]
    elif tracker["mode"] == "github":
        rows += [
            f"Use the selected repository `https://github.com/{tracker['owner']}/{tracker['repo']}` only.",
            "Before work, discover the actual authenticated `gh` or native connector schema. Map the horizon map to one parent issue and child issues.",
            "Use native blocking links when available. Otherwise put `Blocked by` in the issue body. Keep claims on a stable assignee. Record the answer in a comment and close only with explicit authorization. Setup performs no API action.",
        ]
    else:
        rows.append("Use the existing tracker documentation. Setup does not create a blank tracker file.")
    return ("\n".join(rows) + "\n").encode()


def _models_content(old: bytes | None, choices: dict[str, Any], models: Any) -> bytes:
    if old is not None and not choices:
        return old
    try:
        config = {} if old is None else json.loads(old)
        models.validate(config)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ProjectError(f"existing models.json is invalid: {error}") from error
    config.update(choices)
    models.validate(config)
    return (json.dumps(config, indent=2, ensure_ascii=False) + "\n").encode()


def _ignore_content(old: bytes | None) -> bytes:
    newline = b"\r\n" if old and b"\r\n" in old else b"\n"
    if old is None:
        return b".cstack/" + newline
    if b".cstack/" in old.replace(b"\r\n", b"\n").split(b"\n"):
        return old
    separator = b"" if old.endswith((b"\n", b"\r")) else newline
    return old + separator + b".cstack/" + newline


def _entry(relative: str, old: bytes | None, new: bytes) -> dict[str, Any]:
    try:
        text = new.decode()
    except UnicodeDecodeError as error:
        raise ProjectError(f"generated file is not UTF-8: {relative}") from error
    return {"action": "create" if old is None else ("unchanged" if old == new else "update"), "current_sha256": None if old is None else _sha(old), "new_content": text, "new_sha256": _sha(new), "original_content_b64": _b64(old), "path": relative}


def _payload(options: dict[str, Any], snapshots: dict[str, bytes | None], models: Any) -> dict[str, Any]:
    tracker = options["tracker"]
    files = [
        _entry("AGENTS.md", snapshots["AGENTS.md"], _merge(snapshots["AGENTS.md"], _agent_payload(snapshots), owned=False)),
        _entry("docs/agents/cstack.md", snapshots["docs/agents/cstack.md"], _merge(snapshots["docs/agents/cstack.md"], _workflow_payload(tracker), owned=True)),
        _entry(".gitignore", snapshots[".gitignore"], _ignore_content(snapshots[".gitignore"])),
    ]
    tracker_old = snapshots["docs/agents/issue-tracker.md"]
    if tracker["mode"] != "keep":
        files.append(_entry("docs/agents/issue-tracker.md", tracker_old, _merge(tracker_old, _tracker_payload(tracker), owned=True)))
    elif tracker_old is not None:
        files.append(_entry("docs/agents/issue-tracker.md", tracker_old, tracker_old))
    old_models = snapshots[".cstack/models.json"]
    if old_models is not None or options["model_choices"]:
        files.append(_entry(".cstack/models.json", old_models, _models_content(old_models, options["model_choices"], models)))
    return {"files": files, "observed": {path: _record(snapshots[path]) for path in OBSERVED_PATHS}}


def _plan(workspace: Path, raw_options: Any, catalog: dict[str, list[str]] | None) -> dict[str, Any]:
    workspace = _workspace(workspace)
    models = _models()
    options = _options(raw_options, models, catalog)
    snapshots = {path: _read(workspace, path) for path in OBSERVED_PATHS}
    payload = _payload(options, snapshots, models)
    payload["files"].sort(key=lambda entry: TARGET_PATHS.index(entry["path"]))
    payload.update({"catalog_sha256": None if catalog is None else _sha(_canonical(catalog)), "model_choices": options["model_choices"], "options": options, "status": "preview", "version": PLAN_VERSION, "workflows": WORKFLOWS})
    payload["plan_sha256"] = _sha(_canonical(payload))
    return payload


def _shape(plan: Any) -> dict[str, Any]:
    required = {"catalog_sha256", "files", "model_choices", "observed", "options", "plan_sha256", "status", "version", "workflows"}
    if not isinstance(plan, dict) or set(plan) != required or plan["version"] != PLAN_VERSION or plan["status"] != "preview":
        raise ProjectError("plan has unknown or missing fields")
    body = dict(plan)
    fingerprint = body.pop("plan_sha256")
    if not isinstance(fingerprint, str) or _sha(_canonical(body)) != fingerprint:
        raise ProjectError("plan fingerprint does not match its contents")
    paths: set[str] = set()
    for entry in plan["files"]:
        fields = {"action", "current_sha256", "new_content", "new_sha256", "original_content_b64", "path"}
        if not isinstance(entry, dict) or set(entry) != fields or entry["path"] in paths:
            raise ProjectError("plan file entry is invalid or repeated")
        paths.add(entry["path"])
        if entry["path"] not in TARGET_PATHS or entry["action"] not in {"create", "update", "unchanged"}:
            raise ProjectError(f"plan path or action is invalid: {entry['path']}")
        old = _unb64(entry["original_content_b64"])
        if entry["current_sha256"] != (None if old is None else _sha(old)) or not isinstance(entry["new_content"], str):
            raise ProjectError(f"plan old snapshot is invalid: {entry['path']}")
        if entry["new_sha256"] != _sha(entry["new_content"].encode()):
            raise ProjectError(f"plan new content hash is invalid: {entry['path']}")
    _snapshots(plan["observed"])
    return plan


def _compare(expected: dict[str, Any], supplied: dict[str, Any]) -> None:
    left, right = dict(expected), dict(supplied)
    left.pop("plan_sha256", None)
    right.pop("plan_sha256", None)
    if left != right:
        raise ProjectError("accepted plan does not match recomputed options and snapshots")


def _check_state(workspace: Path, plan: dict[str, Any]) -> None:
    observed, planned = _snapshots(plan["observed"]), {entry["path"]: entry for entry in plan["files"]}
    for relative, old in observed.items():
        current = _read(workspace, relative)
        current_hash, old_hash = None if current is None else _sha(current), None if old is None else _sha(old)
        if relative in planned:
            if current_hash not in {old_hash, planned[relative]["new_sha256"]}:
                raise ProjectError(f"file changed since preview: {relative}")
        elif current_hash != old_hash:
            raise ProjectError(f"observed project file changed since preview: {relative}")
    for entry in plan["files"]:
        current = _read(workspace, entry["path"])
        if (None if current is None else _sha(current)) not in {entry["current_sha256"], entry["new_sha256"]}:
            raise ProjectError(f"file changed since preview: {entry['path']}")


def _missing_ancestors(path: Path) -> list[Path]:
    missing: list[Path] = []
    cursor = path
    while not cursor.exists():
        missing.append(cursor)
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent
    return missing


def _remove_empty_dirs(created: list[Path]) -> None:
    for directory in created:
        try:
            if directory.is_symlink() or not directory.is_dir():
                continue
            directory.rmdir()
        except OSError:
            continue


def _temp(parent: Path, data: bytes, mode: int) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", dir=parent, delete=False) as output:
        path = Path(output.name)
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(path, mode)
    return path


def _restore(path: Path, old: bytes | None, new_hash: str) -> bool:
    try:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            return False
        current = path.read_bytes() if path.exists() else None
        if (None if current is None else _sha(current)) != new_hash:
            return False
        if old is None:
            path.unlink(missing_ok=True)
            return True
        temp = _temp(path.parent, old, stat.S_IMODE(path.stat().st_mode))
        try:
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def apply_plan(workspace: Path, supplied_plan: Any, raw_options: Any, catalog: dict[str, list[str]] | None, expected_plan_sha256: str | None = None) -> dict[str, Any]:
    workspace = _workspace(workspace)
    plan = _shape(supplied_plan)
    if expected_plan_sha256 is not None and expected_plan_sha256 != plan["plan_sha256"]:
        raise ProjectError("accepted plan fingerprint differs from --expected-plan-sha256")
    models = _models()
    options = _options(raw_options, models, catalog)
    if options != plan["options"] or options["model_choices"] != plan["model_choices"]:
        raise ProjectError("apply options differ from the accepted preview")
    catalog_sha = None if catalog is None else _sha(_canonical(catalog))
    if plan["catalog_sha256"] != catalog_sha:
        raise ProjectError("catalog differs from the accepted preview")
    snapshots = _snapshots(plan["observed"])
    expected = _payload(options, snapshots, models)
    expected["files"].sort(key=lambda entry: TARGET_PATHS.index(entry["path"]))
    expected.update({"catalog_sha256": plan["catalog_sha256"], "model_choices": options["model_choices"], "options": options, "status": "preview", "version": PLAN_VERSION, "workflows": WORKFLOWS})
    _compare(expected, plan)
    _check_state(workspace, plan)
    changes = []
    for entry in plan["files"]:
        if entry["action"] == "unchanged":
            continue
        current = _read(workspace, entry["path"])
        current_hash = None if current is None else _sha(current)
        if current_hash == entry["new_sha256"]:
            continue
        if current_hash != entry["current_sha256"]:
            raise ProjectError(f"file changed before staging: {entry['path']}")
        changes.append(entry)
    if not changes:
        return {"status": "noop", "changed": [], "plan_sha256": plan["plan_sha256"]}
    staged: list[tuple[dict[str, Any], Path, bytes | None]] = []
    replaced: list[tuple[dict[str, Any], bytes | None]] = []
    created_dirs: list[Path] = []
    try:
        for entry in changes:
            target = _path(workspace, entry["path"], write=True)
            _check(target, workspace)
            old = _unb64(entry["original_content_b64"])
            mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
            created_dirs.extend(_missing_ancestors(target.parent))
            staged.append((entry, _temp(target.parent, entry["new_content"].encode(), mode), old))
        for entry, temp, old in staged:
            current = _read(workspace, entry["path"])
            current_hash = None if current is None else _sha(current)
            if current_hash == entry["new_sha256"]:
                continue
            if current_hash != entry["current_sha256"]:
                raise ProjectError(f"file changed during staging: {entry['path']}")
            os.replace(temp, _path(workspace, entry["path"], write=True))
            replaced.append((entry, old))
        return {"status": "applied", "changed": [entry["path"] for entry, _ in replaced], "plan_sha256": plan["plan_sha256"]}
    except InterruptedApply:
        raise
    except KeyboardInterrupt as error:
        done = [entry["path"] for entry, _ in replaced]
        skipped = [entry["path"] for entry in changes if entry["path"] not in done]
        raise InterruptedApply(done, skipped) from error
    except Exception as error:
        rolled_back, conflicts = [], []
        for entry, old in reversed(replaced):
            (rolled_back if _restore(_path(workspace, entry["path"], write=True), old, entry["new_sha256"]) else conflicts).append(entry["path"])
        return {"status": "rolled_back" if not conflicts else "partial", "error": str(error), "rolled_back": rolled_back, "rollback_conflicts": conflicts, "plan_sha256": plan["plan_sha256"]}
    finally:
        for _, temp, _ in staged:
            temp.unlink(missing_ok=True)
        _remove_empty_dirs(created_dirs)


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProjectError(f"cannot read JSON {path}: {error}") from error


def _catalog(path: Path | None, raw_options: Any) -> dict[str, list[str]] | None:
    if path is None:
        if isinstance(raw_options, dict) and raw_options.get("model_choices"):
            raise ProjectError("--catalog is required for explicit model choices")
        return None
    try:
        return _models().read_catalog(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ProjectError(f"invalid model catalog: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("preview")
    preview.add_argument("--options", type=Path, required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--plan", type=Path, required=True)
    apply.add_argument("--options", type=Path, required=True)
    apply.add_argument("--expected-plan-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        raw_options = _json(args.options)
        catalog = _catalog(args.catalog, raw_options)
        if args.command == "preview":
            result = _plan(args.workspace, raw_options, catalog)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        result = apply_plan(args.workspace, _json(args.plan), raw_options, catalog, args.expected_plan_sha256)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] in {"applied", "noop"} else 2
    except InterruptedApply as error:
        print(json.dumps({"status": "partial", "error": str(error), "applied": error.applied, "skipped": error.skipped}))
        return 3
    except (OSError, ProjectError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "rejected", "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
