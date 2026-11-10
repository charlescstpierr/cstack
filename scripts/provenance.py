"""Canonical, versioned fingerprints for scenario generation and verification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

TREE_HASH_ALGORITHM = "cstack-tree-sha256-v3"
IGNORED_DIRS = {".git", "__pycache__", "node_modules"}
GIT_OPERATIONS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer", "BISECT_START")


def git_snapshot(root: Path):
    marker = root / ".git"
    if marker.is_symlink():
        raise ValueError(f"métadonnées Git symboliques interdites: {marker}")
    if not marker.exists():
        return None
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_TERMINAL_PROMPT"] = "0"

    def git(*args, allowed=(0,)):
        result = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "-c", "core.fsmonitor=false", *args],
                                env=env, capture_output=True, check=False)
        if result.returncode not in allowed:
            raise ValueError(f"état Git illisible: {' '.join(args)}")
        return result

    git_dir = Path(os.fsdecode(git("rev-parse", "--absolute-git-dir").stdout.strip()))
    for operation in GIT_OPERATIONS:
        entry = git_dir / operation
        if entry.exists() or entry.is_symlink():
            raise ValueError(f"opération Git en cours non prise en charge: {operation}")
    head_ref = git("symbolic-ref", "-q", "HEAD", allowed=(0, 1)).stdout.strip()
    head = git("rev-parse", "--verify", "-q", "HEAD", allowed=(0, 1))
    if head.returncode and (not head_ref or git("show-ref", "--verify", "--quiet", os.fsdecode(head_ref), allowed=(0, 1)).returncode != 1):
        raise ValueError("HEAD Git illisible hors branche sans commit")
    # Plumbing reads logical values, avoiding index timestamps and object storage layout.
    return {
        "head_ref": os.fsdecode(head_ref) or None,
        "head_oid": os.fsdecode(head.stdout.strip()) or None,
        "refs": os.fsdecode(git("for-each-ref", "--sort=refname", "--format=%(refname)%00%(objectname)%00%(symref)").stdout),
        "index": os.fsdecode(git("ls-files", "--stage", "-z").stdout),
        "index_flags": os.fsdecode(git("ls-files", "-v", "-z").stdout),
        "config": os.fsdecode(git("config", "--local", "--null", "--list").stdout),
    }


def tree_hash(root, excluded=None):
    root = Path(root).resolve()
    excluded = Path(excluded).resolve() if excluded else None
    if excluded and root not in excluded.parents:
        excluded = None
    digest = hashlib.sha256((TREE_HASH_ALGORITHM + "\0").encode())
    files, total_bytes = 0, 0

    def record(kind, relative, mode, payload=b""):
        for value in (kind, os.fsencode(relative), mode.to_bytes(4, "big"), payload):
            digest.update(len(value).to_bytes(8, "big") + value)

    def file_content(path):
        nonlocal files, total_bytes
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"entrée non régulière non prise en charge: {path}")
        content = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                content.update(chunk)
                total_bytes += len(chunk)
        files += 1
        return info.st_mode, content.digest()

    def walk(directory):
        record(b"directory", directory.relative_to(root).as_posix(), stat.S_IMODE(directory.stat().st_mode))
        for entry in sorted(directory.iterdir(), key=lambda item: os.fsencode(item.name)):
            if entry == excluded:
                continue
            if entry.name == ".git":
                if directory != root:
                    raise ValueError(f"dépôt Git imbriqué non pris en charge: {entry}")
                continue
            if entry.name in IGNORED_DIRS and entry.is_dir():
                continue
            info = entry.lstat()
            relative = entry.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                target = entry.resolve(strict=True)
                if target.is_dir():
                    raise ValueError(f"dossier symbolique non pris en charge: {entry}")
                mode, content = file_content(target)
                if root not in target.parents:
                    raise ValueError(f"lien symbolique extérieur non pris en charge: {entry}")
                record(b"symlink", relative, stat.S_IMODE(info.st_mode), os.fsencode(os.readlink(entry)))
                record(b"target", relative, mode, content)
            elif stat.S_ISDIR(info.st_mode):
                walk(entry)
            elif stat.S_ISREG(info.st_mode):
                mode, content = file_content(entry)
                record(b"file", relative, mode, content)
            else:
                raise ValueError(f"entrée non régulière non prise en charge: {entry}")

    try:
        if not root.is_dir():
            raise ValueError(f"racine d’empreinte introuvable: {root}")
        snapshot = git_snapshot(root)
        git_bytes = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        record(b"git", ".", 0, git_bytes)
        walk(root)
    except OSError as error:
        raise ValueError(f"parcours d’empreinte incomplet: {error.filename or root}") from error
    return {"sha256": digest.hexdigest(), "algorithm": TREE_HASH_ALGORITHM, "files": files, "bytes": total_bytes,
            "git_sha256": hashlib.sha256(git_bytes).hexdigest() if snapshot is not None else None}


def case_configuration(case):
    return {"id": case["id"], "cwd": str(Path(case["cwd"]).expanduser().resolve()),
            "bundle": str(Path(case["bundle"]).expanduser().resolve()) if case.get("bundle") else None,
            "prompts": list(case["prompts"]) if "prompts" in case else [case["prompt"]],
            "sandbox": case.get("sandbox", "workspace-write"), "ephemeral": case.get("ephemeral", True)}


def case_hash(case):
    canonical = json.dumps(case_configuration(case), sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()
