#!/usr/bin/env python3
"""Generate isolated projects and native Codex behavior cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


MODEL = {"model": "gpt-5.6-luna", "reasoning_effort": "max"}
IGNORED_DIRS = {".git", "__pycache__", "node_modules"}
FORBIDDEN_PROMPT_LABELS = re.compile(r"\b(?:eval|test|judge|candidate|benchmark)\b", re.IGNORECASE)
PANEL_LENGTHS = {"interrogate reviewers": 3}
GIT_NAME = "cstack scenario fixture"
GIT_EMAIL = "cstack-scenario@example.invalid"


def model_config(roles: list[str]) -> dict[str, Any]:
    return {
        role: [dict(MODEL) for _ in range(PANEL_LENGTHS[role])]
        if role in PANEL_LENGTHS else dict(MODEL)
        for role in roles
    }


def write_text(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for directory, names, filenames in os.walk(root, topdown=True):
        path = Path(directory)
        names[:] = sorted(name for name in names if name not in IGNORED_DIRS)
        for filename in sorted(filenames):
            item = path / filename
            if item.is_symlink() or not item.is_file():
                continue
            digest.update(item.relative_to(root).as_posix().encode() + b"\0")
            digest.update(item.read_bytes())
    return digest.hexdigest()


def copy_bundle(source: Path, output: Path, label: str) -> Path:
    source = source.expanduser().resolve()
    if not source.is_dir() or not (source / "skills").is_dir():
        raise ValueError(f"plugin root must contain a skills directory: {source}")
    destination = output / "resources" / label
    shutil.copytree(source, destination, ignore=lambda _, names: set(names) & IGNORED_DIRS)
    return destination


def git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=project, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def seed_git(project: Path, branch: str | None = None) -> None:
    git(project, "init", "-b", "main")
    if not (project / ".gitignore").exists():
        write_text(project, ".gitignore", ".cstack/\n__pycache__/\n")
    git(project, "add", ".")
    git(
        project, "-c", f"user.name={GIT_NAME}", "-c", f"user.email={GIT_EMAIL}",
        "commit", "-m", "seed scenario",
    )
    if branch:
        git(project, "switch", "-c", branch)


def create_project(
    output: Path, name: str, files: dict[str, str], roles: list[str], catalog: Path | None = None
) -> Path:
    project = output / "projects" / name
    project.mkdir(parents=True)
    for relative, content in files.items():
        write_text(project, relative, content)
    write_text(project, ".cstack/models.json", json.dumps(model_config(roles), indent=2) + "\n")
    if catalog is not None:
        shutil.copyfile(catalog, project / ".cstack/model-catalog.json")
    return project


def prompt(bundle: Path, skill: str, body: str, french: bool = False) -> str:
    skill_path = bundle / "skills" / skill / "SKILL.md"
    note = (
        f"La version source n'est pas installée. Lis directement ce fichier de compétence avant d'agir : {skill_path}"
        if french else
        f"The source version is not installed. Read this skill file directly before acting: {skill_path}"
    )
    value = body.strip() + "\n\n" + note
    if FORBIDDEN_PROMPT_LABELS.search(value):
        raise ValueError(f"forbidden evaluation label in prompt for {skill}")
    return value


def register(
    cases: list[dict[str, Any]],
    expectations: list[dict[str, Any]],
    *,
    case_id: str,
    project: Path,
    bundle: Path,
    skill: str,
    roles: list[str],
    body: str | None = None,
    bodies: list[str] | None = None,
    french: bool = False,
    sandbox: str = "workspace-write",
    expected_children: int = 0,
) -> None:
    if not (project / ".git").exists():
        seed_git(project)
    discovered = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=project, text=True).strip()
    if Path(discovered).resolve() != project.resolve():
        raise ValueError(f"fixture inherited a different repository: {project}")
    if (body is None) == (bodies is None):
        raise ValueError(f"{case_id}: provide body or bodies")
    texts = bodies if bodies is not None else [body]
    prompts = [prompt(bundle, skill, text, french) for text in texts if text is not None]
    case: dict[str, Any] = {"id": case_id, "cwd": str(project), "sandbox": sandbox}
    case["prompts" if bodies is not None else "prompt"] = prompts if bodies is not None else prompts[0]
    cases.append(case)
    skill_path = bundle / "skills" / skill / "SKILL.md"
    expectations.append({
        "id": case_id,
        "project_sha256": tree_hash(project),
        "source_sha256": {
            "bundle": tree_hash(bundle),
            "skill": hashlib.sha256(skill_path.read_bytes()).hexdigest(),
        },
        "expected_children": expected_children,
        "role_metadata": model_config(roles),
    })


def interrogate_project(output: Path, name: str, catalog: Path | None) -> Path:
    project = create_project(output, name, {
        "README.md": """# Cedar event service

## Approved behavior

The command accepts --json.
The README must explain that --json preserves field order and malformed input exits nonzero.
""",
        "src/feature.py": """def normalize_owner(value):
    return value.strip()
""",
    }, ["interrogate reviewers"], catalog)
    seed_git(project, "feature/review")
    write_text(project, "README.md", """# Cedar event service

## Output

Use cedar --json for machine-readable records.
""")
    git(project, "add", "README.md")
    write_text(project, "src/feature.py", """def normalize_owner(value):
    return " ".join(value.split()).title()
""")
    write_text(project, "notes.md", "Existing working note; it is outside the requested review scope.\n")
    return project


def setup_project(output: Path, name: str, catalog: Path | None) -> Path:
    project = create_project(output, name, {}, [], catalog)
    (project / "AGENTS.md").write_bytes(b"# Manual project rules\r\n\r\nKeep this exact line.\r\n")
    (project / "CLAUDE.md").write_bytes(b"# Manual Claude rules\r\n\r\nKeep this exact line too.\r\n")
    (project / ".gitignore").write_bytes(b"# Manual ignore\r\nbuild/\r\n")
    (project / ".cstack/models.json").write_bytes(
        b'{\n  "documentation": {\n    "model": "gpt-5.6-luna",\n    "reasoning_effort": "max"\n  }\n}\n'
    )
    seed_git(project)
    return project


def build_cases(
    baseline: Path, proposed: Path, output: Path, catalog: Path | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    old = copy_bundle(baseline, output, "quartz")
    new = copy_bundle(proposed, output, "opal")
    cases: list[dict[str, Any]] = []
    expectations: list[dict[str, Any]] = []

    event_files = {
        "events.py": """from __future__ import annotations


def filter_events(events, start, today):
    return [event for event in events if start < event["date"] <= today]
""",
    }
    correction = """Use $cstack:cstack for this small Python correction. In events.py, make the lower bound inclusive and reject events after today. Add verify_events.py with direct assertions for the start boundary and future events. Work directly in this project. Do not spawn subagents, create commits, or change unrelated files."""
    explanation = """Utilise $cstack:how pour expliquer comment events.py filtre les événements et où ses bornes sont définies. Réponds avec les chemins et les symboles utiles. Ne modifie aucun fichier, ne délègue pas et ne crée aucun commit."""
    review = """Use $cstack:interrogate for a read-only review of the current work. Review the staged change in README.md against this approved requirement: explain that --json preserves field order and malformed input exits nonzero. Inspect the branch and working tree for context. The unstaged change in src/feature.py and untracked notes.md are pre-existing context; do not edit, commit, or include them in the review scope. Use the configured reviewer panel and return only evidence-backed findings."""

    for case_id, name, bundle in (
        ("clear_python_correction_baseline", "alder", old),
        ("clear_python_correction_proposed", "cedar", new),
    ):
        register(cases, expectations, case_id=case_id,
                 project=create_project(output, name, event_files, ["bug-fix"], catalog),
                 bundle=bundle, skill="cstack", roles=["bug-fix"],
                 body=correction, expected_children=0)
    for case_id, name, bundle in (
        ("readonly_explanation_baseline", "maple", old),
        ("readonly_explanation_proposed", "birch", new),
    ):
        register(cases, expectations, case_id=case_id,
                 project=create_project(output, name, event_files, ["how explainer"], catalog),
                 bundle=bundle, skill="how", roles=["how explainer"],
                 body=explanation, french=True, sandbox="read-only")
    for case_id, name, bundle in (
        ("interrogate_current_work_baseline", "elm", old),
        ("interrogate_current_work_proposed", "pine", new),
    ):
        register(cases, expectations, case_id=case_id,
                 project=interrogate_project(output, name, catalog), bundle=bundle,
                 skill="interrogate", roles=["interrogate reviewers"],
                 body=review, sandbox="read-only", expected_children=3)

    storage = {"storage.py": "def save_record(record, existing):\n    if record[\"id\"] not in existing:\n        raise KeyError(record[\"id\"])\n    return record\n"}
    overwrite = """Utilise $cstack:clarify pour préparer une décision sur storage.py. Lorsqu'un enregistrement existant serait écrasé, le produit n'a pas encore choisi entre remplacer, conserver l'ancien ou refuser. Inspecte les faits du dépôt, puis pose les questions de frontière nécessaires avec des recommandations. Ne choisis pas pour moi, ne modifie aucun fichier et n'écris aucun document."""
    complete = """Use $cstack:clarify only to inspect this fully specified request. save_record must replace an existing record, return the new record, and preserve the existing error for a missing id. If no material ambiguity remains, say so and finish without inventing a question. Do not edit files, create documents, or implement anything."""
    register(cases, expectations, case_id="clarify_overwrite",
             project=create_project(output, "spruce", storage, [], catalog),
             bundle=new, skill="clarify", roles=[], body=overwrite, french=True, sandbox="read-only")
    register(cases, expectations, case_id="clarify_complete",
             project=create_project(output, "willow", storage, [], catalog),
             bundle=new, skill="clarify", roles=[], body=complete, sandbox="read-only")

    setup_first = """Use $cstack:setup-cstack in this project. I authorize one setup pass with these exact choices: add the passive cstack block to AGENTS.md, add project guidance under docs/agents/cstack.md, and configure the local markdown tracker under docs/agents/issue-tracker.md. Preserve manual AGENTS.md and CLAUDE.md bytes outside managed content, including CRLF line endings. Preserve existing .gitignore entries and append only the required setup ignore entry. Keep the existing .cstack/models.json byte-for-byte unchanged; make no model choices. Use only the trusted project.py helper for this project setup; do not invoke models.py. Do not spawn subagents, write global files, access remote services, create a goal, commit, or open a PR. Apply the local project setup and report the paths changed."""
    setup_second = """Use $cstack:setup-cstack again with exactly the same choices: the passive AGENTS.md block, project guidance, and local markdown tracker, with no model choices. Re-read the current project state and apply the setup; the expected result is a no-op. Preserve the manual CRLF files, .gitignore entries, and existing .cstack/models.json. Use only the trusted project.py helper; do not invoke models.py. Do not spawn subagents, write global files, access remote services, create a goal, commit, or open a PR."""
    register(cases, expectations, case_id="setup_project_twice",
             project=setup_project(output, "hazel", catalog), bundle=new,
             skill="setup-cstack", roles=[], bodies=[setup_first, setup_second])

    domain_files = {
        "CONTEXT.md": "# Cedar terms\n\nManual line: preserve this exact sentence.\n",
        "members.py": 'def member_label(row):\n    return row["name"]\n',
    }
    domain_readonly = """Utilise $cstack:domain. Lis members.py et CONTEXT.md, puis propose dans la conversation une entrée pour le terme ambigu « member ». Le choix métier reste humain. Ne modifie aucun fichier et ne crée aucun document."""
    domain_write = """Use $cstack:domain. I explicitly authorize this task to update CONTEXT.md for the resolved term Member; preserve every existing manual byte sequence, append only the approved glossary entry, and do not edit code. In this repository, a Member is a person with access to a workspace. Write the glossary entry under the existing document conventions without creating an ADR for this vocabulary entry. Do not ask for approval again after this authorization."""
    register(cases, expectations, case_id="domain_readonly",
             project=create_project(output, "ash", domain_files, ["documentation"], catalog),
             bundle=new, skill="domain", roles=["documentation"],
             body=domain_readonly, french=True, sandbox="read-only")
    register(cases, expectations, case_id="domain_authorized_write",
             project=create_project(output, "beech", domain_files, ["documentation"], catalog),
             bundle=new, skill="domain", roles=["documentation"], body=domain_write)

    horizon_readme = """# Archive migration

## Primary facts

- Events are stored in data/archive.jsonl.
- The current retention period is 90 days.
- Nightly snapshots are retained for 30 days.
- The migration must preserve event order and allow rollback for 14 days.

## Research questions

1. Which fact determines the retention and backup schedule?
2. Which fact determines the rollback procedure?
"""
    horizon_first = """Use $cstack:horizon to chart this multi-session effort. The destination is already defined: migrate the event archive to append-only storage with zero data loss and a 14-day rollback window. I authorize writes to Horizon planning artifacts under .cstack/horizon/, but do not edit product code, create a PR, or create a native goal. The provided README is the primary source for two read-only research questions. Create exactly these tickets: 001 research the retention and backup facts from the README; 002 research the rollback facts from the README; 003 is a human policy decision blocked by 001 and 002; 004 is a human policy decision blocked by 003. Dispatch one native research child for each ready research ticket using the configured how explorer role. On this invocation, resolve only 001 and 002; leave 003 and 004 open. Do not answer for a human."""
    horizon_second = """Use $cstack:horizon to continue from the existing Horizon state. Resolve only ticket 003 with this user decision: retain source events for 90 days, keep nightly snapshots for 30 days, and require a 14-day rollback window. Ticket 004 must remain open because it depends on 003 and has no human answer. Plan artifact writes remain authorized; do not edit product code, create a PR, or create a native goal. Verify the research artifacts for 001 and 002 before recording 003, and do not answer 004."""
    register(cases, expectations, case_id="horizon_two_research_then_policy",
             project=create_project(output, "fir", {"README.md": horizon_readme}, ["how explorer"], catalog),
             bundle=new, skill="horizon", roles=["how explorer"],
             bodies=[horizon_first, horizon_second], expected_children=2)

    audit_files = {
        "src/users.py": 'def username(user):\n    return user["name"].strip().lower()\n',
        "src/orders.py": 'def owner_name(order):\n    return order["owner"].strip().lower()\n',
        "src/reports.py": 'def actor_name(report):\n    return report["actor"].strip().lower()\n',
    }
    audit = """Utilise $cstack:audit-architecture sur le périmètre src/. Lis directement la compétence indiquée, puis dresse une enquête d'architecture en lecture seule sur le point chaud de normalisation des noms d'utilisateur dans ces trois modules. Utilise au plus un explorateur borné si la délégation native est disponible. Ne modifie aucun fichier. Rapporte les chemins, symboles, appelants, preuves et la profondeur d'interface observée; toute forme proposée doit rester explicitement non vérifiée."""
    register(cases, expectations, case_id="audit_architecture_username_scope",
             project=create_project(output, "rowan", audit_files, ["how explorer"], catalog),
             bundle=new, skill="audit-architecture", roles=["how explorer"],
             body=audit, french=True, sandbox="read-only", expected_children=1)
    return cases, expectations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="trusted baseline plugin root")
    parser.add_argument("--proposed", type=Path, required=True, help="trusted proposed plugin root")
    parser.add_argument("--output", type=Path, required=True, help="new local root for projects, resources, and JSON")
    parser.add_argument("--catalog", type=Path, help="optional live model catalog copied into generated projects")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("--output must be absent or empty; refusing to overwrite existing data")
    baseline = args.baseline.expanduser().resolve()
    proposed = args.proposed.expanduser().resolve()
    catalog = args.catalog.expanduser().resolve() if args.catalog else None
    if catalog is not None and not catalog.is_file():
        parser.error("--catalog must point to a regular file")
    if any(output == root or output in root.parents or root in output.parents for root in (baseline, proposed)):
        parser.error("--output must be outside both plugin roots")
    output.mkdir(parents=True, exist_ok=True)
    cases, expectations = build_cases(baseline, proposed, output, catalog)
    (output / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "expectations.json").write_text(
        json.dumps({"schema_version": 1, "cases": expectations}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "cases": len(cases), "expectations": len(expectations)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
