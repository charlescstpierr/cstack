#!/usr/bin/env python3
"""Create/check local post-merge worktree cleanup fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

GIT_NAME = "cstack cleanup fixture"
GIT_EMAIL = "cstack-cleanup@example.invalid"


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def git(cwd: Path, *args: str) -> str:
    return sh(cwd, "git", *args)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, msg: str) -> str:
    git(repo, "-c", f"user.name={GIT_NAME}", "-c", f"user.email={GIT_EMAIL}", "add", ".")
    git(repo, "-c", f"user.name={GIT_NAME}", "-c", f"user.email={GIT_EMAIL}", "commit", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_file() and not path.is_symlink():
                rel = path.relative_to(root).as_posix()
                digest.update(rel.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def main_hash(repo: Path) -> str:
    digest = hashlib.sha256()
    files = git(repo, "ls-files", "-z").split("\0")
    for rel in sorted(x for x in files if x and not x.startswith(".cstack/")):
        digest.update(rel.encode() + b"\0" + (repo / rel).read_bytes() + b"\0")
    return digest.hexdigest()


def refs(repo: Path) -> dict[str, str]:
    lines = git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads")
    return dict(line.split(" ", 1) for line in lines.splitlines() if line)


def prefixed_refs(repo: Path, namespace: str) -> dict[str, str]:
    lines = git(repo, "for-each-ref", "--format=%(refname) %(objectname)", namespace)
    return dict(line.split(" ", 1) for line in lines.splitlines() if line)


def seed_repo(root: Path) -> Path:
    repo = root / "workspace"
    repo.mkdir(parents=True)
    git(repo, "init", "-b", "main")
    write(repo / ".gitignore", ".cstack/\n.env\nbuild-cache/\n")
    write(repo / "README.md", "# Cleanup fixture\n")
    write(repo / "src/app.txt", "main data v1\n")
    commit(repo, "initial")
    git(root, "init", "--bare", str(root / "origin.git"))
    git(repo, "remote", "add", "origin", str(root / "origin.git"))
    git(repo, "push", "-u", "origin", "main")
    return repo


def branch(repo: Path, name: str, body: str) -> str:
    git(repo, "switch", "main")
    git(repo, "switch", "-c", name)
    write(repo / "changes" / f"{name.replace('/', '_')}.txt", body + "\n")
    head = commit(repo, f"{name} change")
    git(repo, "switch", "main")
    return head


def noff(repo: Path, name: str) -> str:
    git(repo, "switch", "main")
    git(repo, "-c", f"user.name={GIT_NAME}", "-c", f"user.email={GIT_EMAIL}", "merge", "--no-ff", name, "-m", f"merge {name}")
    return git(repo, "rev-parse", "HEAD")


def squash(repo: Path, name: str) -> str:
    git(repo, "switch", "main")
    git(repo, "-c", f"user.name={GIT_NAME}", "-c", f"user.email={GIT_EMAIL}", "merge", "--squash", name)
    return commit(repo, f"squash {name}")


def worktree(repo: Path, root: Path, name: str, dirname: str) -> Path:
    path = root / "worktrees" / dirname
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", str(path), name)
    return path


def detached_worktree(repo: Path, root: Path, commit: str, dirname: str) -> Path:
    path = root / "worktrees" / dirname
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "--detach", str(path), commit)
    return path


def gh_stub(root: Path, prs: dict) -> Path:
    state = root / "gh-prs.json"
    write(state, json.dumps(prs, indent=2, sort_keys=True) + "\n")
    stub = root / "bin/gh"
    write(stub, f"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
if args[:2] != ["pr", "view"]:
    raise SystemExit("stub supports only: gh pr view <number-or-branch> --json ...")
prs = json.loads(Path({str(state)!r}).read_text())
key = args[2]
record = prs.get(key) or next((pr for pr in prs.values() if str(pr["number"]) == key), None)
if record is None:
    raise SystemExit("unknown fixture PR")
print(json.dumps(record))
""")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def prompt(root: Path, repo: Path, stub: Path) -> None:
    skill = Path(__file__).resolve().parents[1] / "plugins/cstack/skills/cstack/SKILL.md"
    write(root / "ACTOR_PROMPT.md", f"""Use $cstack:cstack to finish the already-authorized delivery recorded in the local checkpoint.

The source cstack bundle is not installed. Read this skill file directly before acting:
{skill}

Main workspace:
{repo}

Use this local GitHub CLI stub first on PATH:
{stub}

Use the checkpoint and local Git evidence as the source of truth. The local stub supplies forge responses; Git operations use a local bare origin. Treat this as completion of the delivered units, not a request to take on pending units. All writes must stay in this fixture at {root}; outside it, only read the selected skill bundle. Do not read evaluation files outside the workspace/worktrees except this prompt and the gh stub. Do not use the network, change branch refs or run Codex CLI.
""")


def create(root: Path) -> None:
    if root.exists():
        raise SystemExit(f"refusing to overwrite existing fixture root: {root}")
    root.mkdir(parents=True)
    repo, cases, prs = seed_repo(root), [], {}

    def add(name: str, dirname: str, owner: str, expected: str, merge: str = "merge", locked: bool = False) -> Path:
        head = branch(repo, name, dirname)
        merge_commit = {"merge": noff, "squash": squash}.get(merge, lambda *_: None)(repo, name)
        if merge == "advance":
            merge_commit = noff(repo, name)
            git(repo, "switch", name)
            write(repo / "changes" / f"{name.replace('/', '_')}-after.txt", "advanced after delivery\n")
            commit(repo, f"advance {name}")
            git(repo, "switch", "main")
        if merge == "detached" or merge == "detached-tag":
            merge_commit = squash(repo, name)
            if merge == "detached-tag":
                git(repo, "tag", f"keep/{dirname}", head)
            git(repo, "branch", "-D", name)
            path = detached_worktree(repo, root, head, dirname)
        else:
            path = worktree(repo, root, name, dirname)
        if locked:
            git(repo, "worktree", "lock", "--reason", "active delivery session", str(path))
        cases.append({"branch": name, "path": str(path), "owner": owner, "expected": expected, "head": head})
        prs[name] = {
            "number": len(cases),
            "headRefName": name,
            "state": "OPEN" if merge == "none" else "MERGED",
            "mergedAt": None if merge == "none" else "2026-09-11T12:00:00Z",
            "headRefOid": head,
            "baseRefName": "main",
            "mergeCommit": {"oid": merge_commit} if merge_commit else None,
        }
        return path

    trail = add("task/alpha", "alpha", "released", "removed") / ".cstack/tasks/alpha/decisions.tsv"
    write(trail, "decision\tevidence\nship alpha\tverified current head on real artifact\n")
    write(add("task/bravo", "bravo", "released", "removed", "squash") / "build-cache/artifact.bin", "ignored disposable build output\n")
    add("team/charlie", "charlie", "unrelated", "kept")
    add("task/delta", "delta", "active", "kept")
    add("task/echo", "echo", "released", "kept", locked=True)
    write(add("task/foxtrot", "foxtrot", "released", "kept") / "changes/task_foxtrot.txt", "dirty local edit\n")
    write(add("task/golf", "golf", "released", "kept") / "local-note.txt", "local scratch\n")
    write(add("task/hotel", "hotel", "released", "kept") / ".env", "SECRET=keep-me\n")
    add("task/india", "india", "released", "kept", "none")
    add("task/juliet", "juliet", "released", "kept", "advance")
    add("task/kilo", "kilo", "released", "kept", "detached")
    add("task/lima", "lima", "released", "removed", "detached-tag")

    git(repo, "switch", "main")
    git(repo, "push", "--all", "origin")
    git(repo, "push", "--tags", "origin")
    git(repo, "fetch", "--prune", "origin")
    checkpoint = repo / ".cstack/post-merge-cleanup.json"
    write(checkpoint, json.dumps({
        "schema": 1,
        "task": "post-merge-cleanup",
        "authorizedActions": ["deliver verified units through merge", "finish delivery"],
        "verification": "Delivered units checked against main; no product work remains for those units.",
        "worktrees": {
            c["branch"]: {
                "path": c["path"],
                "owner": "post-merge-cleanup",
                "ownerState": c["owner"],
                "taskCreatedPaths": [c["path"]],
                "disposableOutputs": ["build-cache"] if c["branch"] == "task/bravo" else [],
                "artifacts": [str(trail)] if c["branch"] == "task/alpha" else [],
                "release": {"releasedAt": "2026-09-11T12:30:00Z", "writersReleased": True, "verifiersReleased": True, "descendantsReleased": True, "processesStopped": True, "dependentUnits": []} if c["owner"] == "released" else None,
                "pr": {
                    "number": index,
                    "baseRefName": "main",
                    "originalHeadRefOid": c["head"],
                    "currentHeadRefOid": prs[c["branch"]]["headRefOid"],
                    "state": prs[c["branch"]]["state"],
                    "mergedAt": prs[c["branch"]]["mergedAt"],
                    "mergeCommitOid": (prs[c["branch"]]["mergeCommit"] or {}).get("oid"),
                },
            }
            for index, c in enumerate(cases, 1)
            if c["owner"] in {"released", "active"}
        },
        "prs": prs,
    }, indent=2, sort_keys=True) + "\n")
    stub = gh_stub(root, prs)
    prompt(root, repo, stub)
    write(root / "expected/manifest.json", json.dumps({
        "repo": str(repo),
        "gh_stub": str(stub),
        "removed": [c["path"] for c in cases if c["expected"] == "removed"],
        "kept": {c["path"]: tree_hash(Path(c["path"])) for c in cases if c["expected"] == "kept"},
        "branch_refs": refs(repo),
        "local_tags": prefixed_refs(repo, "refs/tags"),
        "remote_tracking_refs": prefixed_refs(repo, "refs/remotes"),
        "origin_heads": prefixed_refs(root / "origin.git", "refs/heads"),
        "origin_tags": prefixed_refs(root / "origin.git", "refs/tags"),
        "main_working_hash": main_hash(repo),
        "checkpoint": str(checkpoint),
        "preserved_artifact_sha256": hashlib.sha256(trail.read_bytes()).hexdigest(),
    }, indent=2, sort_keys=True) + "\n")


def listed_worktrees(repo: Path) -> set[str]:
    return {line[9:] for line in git(repo, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")}


def check(root: Path) -> int:
    manifest = json.loads((root / "expected/manifest.json").read_text(encoding="utf-8"))
    repo, failures = Path(manifest["repo"]), []
    listed = listed_worktrees(repo)
    for item in manifest["removed"]:
        if Path(item).exists():
            failures.append(f"should be removed: {item}")
        if item in listed:
            failures.append(f"should be deregistered: {item}")
    for item, expected in manifest["kept"].items():
        path = Path(item)
        if not path.exists():
            failures.append(f"should be kept: {item}")
        elif tree_hash(path) != expected:
            failures.append(f"protected tree changed: {item}")
        if item not in listed:
            failures.append(f"kept worktree deregistered: {item}")
    if refs(repo) != manifest["branch_refs"]:
        failures.append("branch refs changed")
    if "local_tags" in manifest and prefixed_refs(repo, "refs/tags") != manifest["local_tags"]:
        failures.append("local tags changed")
    if "remote_tracking_refs" in manifest and prefixed_refs(repo, "refs/remotes") != manifest["remote_tracking_refs"]:
        failures.append("remote-tracking refs changed")
    origin = root / "origin.git"
    if "origin_heads" in manifest and prefixed_refs(origin, "refs/heads") != manifest["origin_heads"]:
        failures.append("bare-origin heads changed")
    if "origin_tags" in manifest and prefixed_refs(origin, "refs/tags") != manifest["origin_tags"]:
        failures.append("bare-origin tags changed")
    if main_hash(repo) != manifest["main_working_hash"]:
        failures.append("main tracked data changed outside .cstack")
    if not any(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == manifest["preserved_artifact_sha256"] for p in (repo / ".cstack").rglob("*")):
        failures.append("task evidence was not preserved in the surviving workspace")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"ok: {root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create", "check"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        create(args.root.resolve())
        print(args.root.resolve())
        return 0
    return check(args.root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
