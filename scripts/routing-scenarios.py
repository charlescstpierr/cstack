#!/usr/bin/env python3
"""Generate neutral routing-quality behavior fixtures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR_PATH = ROOT / "scripts" / "behavior-scenarios.py"
MODELS_PATH = ROOT / "plugins/cstack/skills/setup-cstack/scripts/models.py"
VARIANTS = (
    ("quartz", "shippedbaseline", "a"),
    ("cedar", "minimal_call_control", "b"),
    ("opal", "proposedriskaware", "c"),
)
DIRECT_POLICY = """## Local Routing Policy

Prefer direct execution for this temporary local bundle. Do not spawn native
subagents unless the user explicitly asks for parallel agents or delegation.
Keep normal safety checks and verification before reporting completion.
"""


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


behavior = load_module("behavior_scenarios", BEHAVIOR_PATH)
models = load_module("cstack_models", MODELS_PATH)


def read_role_models(path: Path | None, catalog: dict[str, list[str]] | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        choices = json.loads(path.read_text())
        models.validate(choices, catalog, check_available=True)
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"invalid --role-models: {error}") from error
    return choices


def validate_plugin_root(path: Path, name: str) -> None:
    if not path.is_dir() or not (path / "skills").is_dir():
        raise ValueError(f"{name} plugin root must contain a skills directory: {path}")


def role_metadata(role_models: dict[str, Any], roles: list[str], catalog: dict[str, list[str]] | None) -> dict[str, Any]:
    return {role: models.resolve(role_models, role, catalog) for role in roles}


def write_models(project: Path, role_models: dict[str, Any]) -> None:
    behavior.write_text(project, ".cstack/models.json", json.dumps(role_models, indent=2, ensure_ascii=False) + "\n")


def copy_catalog(catalog_path: Path | None, project: Path) -> None:
    if catalog_path is not None:
        destination = project / ".cstack/model-catalog.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(catalog_path, destination)


def create_project(output: Path, name: str, files: dict[str, str], role_models: dict[str, Any], catalog: Path | None) -> Path:
    project = output / "projects" / name
    project.mkdir(parents=True)
    for relative, content in files.items():
        behavior.write_text(project, relative, content)
    write_models(project, role_models)
    copy_catalog(catalog, project)
    return project


def git(project: Path, *args: str) -> None:
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-01-02T03:04:05Z", GIT_COMMITTER_DATE="2026-01-02T03:04:05Z")
    subprocess.run(
        ["git", *args], cwd=project, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def seed_git(project: Path) -> None:
    git(project, "init", "-b", "main")
    if not (project / ".gitignore").exists():
        behavior.write_text(project, ".gitignore", ".cstack/\n__pycache__/\n")
    git(project, "add", ".")
    git(project, "-c", f"user.name={behavior.GIT_NAME}", "-c", f"user.email={behavior.GIT_EMAIL}", "commit", "-m", "seed")


def commit_change(project: Path, message: str) -> None:
    git(project, "add", ".")
    git(project, "-c", f"user.name={behavior.GIT_NAME}", "-c", f"user.email={behavior.GIT_EMAIL}", "commit", "-m", message)


def copy_bundle(source: Path, output: Path, label: str, control: bool = False) -> Path:
    bundle = behavior.copy_bundle(source, output, label)
    if control:
        for skill in (bundle / "skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8")
            if text.startswith("---"):
                end = text.find("\n---", 3)
                if end < 0:
                    raise ValueError(f"invalid skill frontmatter: {skill}")
                insert = text.find("\n", end + 4)
                if insert < 0:
                    insert = len(text)
                text = text[:insert + 1] + "\n" + DIRECT_POLICY + "\n" + text[insert + 1:]
            else:
                text = DIRECT_POLICY + "\n" + text
            skill.write_text(text, encoding="utf-8")
    return bundle


def prompt(bundle: Path, skill: str, body: str) -> str:
    return behavior.prompt(bundle, skill, body, french=False)


def register(
    cases: list[dict[str, Any]],
    expectations: list[dict[str, Any]],
    *,
    case_id: str,
    variant_kind: str,
    fixture_class: str,
    project: Path,
    bundle: Path,
    skill: str,
    roles: list[str],
    role_models: dict[str, Any],
    catalog_map: dict[str, list[str]] | None,
    body: str,
    ground_truth: dict[str, Any],
    sandbox: str = "workspace-write",
) -> None:
    if not (project / ".git").exists():
        seed_git(project)
    case = {
        "id": case_id,
        "cwd": str(project),
        "sandbox": sandbox,
        "ephemeral": False,
        "prompt": prompt(bundle, skill, body),
    }
    cases.append(case)
    skill_path = bundle / "skills" / skill / "SKILL.md"
    expectations.append({
        "id": case_id,
        "variant": variant_kind,
        "fixture_class": fixture_class,
        "classification": ground_truth["classification"],
        "allowed_outputs": ground_truth["allowed_outputs"],
        "required_outputs": ground_truth["required_outputs"],
        "proof": ground_truth["proof"],
        "checks": ground_truth["checks"],
        "project_sha256": behavior.tree_hash(project),
        "source_sha256": {
            "bundle": behavior.tree_hash(bundle),
            "skill": hashlib.sha256(skill_path.read_bytes()).hexdigest(),
        },
        "role_metadata": role_metadata(role_models, roles, catalog_map),
        "independent_signal": ground_truth["independent_signal"],
    })


def fixture_specs() -> list[dict[str, Any]]:
    return [
        {
            "class": "triviallocalbug", "skill": "cstack", "roles": ["bug-fix"],
            "files": {
                "calc.py": "def total(items):\n    return sum(items[:-1])\n",
                "verify_calc.py": "from calc import total\n\nassert total([2, 3, 5]) == 10\nassert total([]) == 0\n",
            },
            "body": "Use $cstack:cstack. Fix calc.py so total includes every item. Add one runnable local check with assertions. Work in this project only; do not create commits or use external services.",
            "truth": {
                "classification": "direct_small_bugfix",
                "allowed_outputs": ["edit calc.py", "add or run a tiny local assertion check"],
                "required_outputs": ["total([2, 3, 5]) returns 10", "fresh local proof is reported"],
                "proof": ["assertion command or equivalent local check"],
                "checks": ["python calc check passes"],
                "independent_signal": ["stays direct unless inspection reveals wider risk"],
            },
        },
        {
            "class": "historydependentregression", "skill": "cstack", "roles": ["why investigators", "why synthesizer"],
            "history": True,
            "files": {"parser.py": "def parse_count(text):\n    return int(text)\n"},
            "after_seed": {"parser.py": "def parse_count(text):\n    return int(text.strip() or 0)\n"},
            "body": "Use $cstack:cstack. Explain why blank count strings now become zero. Inspect local git history and parser.py. Do not edit files. Return the commit-level cause, file path, symbol, and the behavior change.",
            "truth": {
                "classification": "read_only_history_cause",
                "allowed_outputs": ["read parser.py", "read local git history"],
                "required_outputs": ["identify parse_count", "identify the later commit as cause", "no project hash change"],
                "proof": ["git log or git show evidence"],
                "checks": ["read-only project hash remains unchanged"],
                "independent_signal": ["uses git history, not only current file contents"],
            },
            "sandbox": "read-only",
        },
        {
            "class": "smallmechanicalfeature", "skill": "cstack", "roles": ["simple edits"],
            "files": {
                "slug.py": "def slug(value):\n    return value.lower().replace(' ', '-')\n",
                "verify_slug.py": "from slug import slug\n\nassert slug('  A  B  ') == 'a-b'\nassert slug('Ready') == 'ready'\n",
            },
            "body": "Use $cstack:cstack. Extend slug.py so repeated spaces collapse to one dash and surrounding spaces are ignored. Add one runnable local check. Stay in this project and do not create commits.",
            "truth": {
                "classification": "direct_mechanical_feature",
                "allowed_outputs": ["edit slug.py", "add or run a small local check"],
                "required_outputs": ["slug('  A  B  ') == 'a-b'"],
                "proof": ["assertion command or equivalent local check"],
                "checks": ["slug normalization check passes"],
                "independent_signal": ["simple enough for parent implementation"],
            },
        },
        {
            "class": "statefulmoduleboundary", "skill": "cstack", "roles": ["bug-fix", "architect runners"],
            "files": {
                "inventory.py": "STOCK = {'sku-1': 2}\n\ndef take(sku, quantity):\n    if STOCK.get(sku, 0) < quantity:\n        raise ValueError('out of stock')\n    STOCK[sku] -= quantity\n",
                "reservations.py": "RESERVATIONS = {}\n\ndef remember(reservation_id, sku, quantity):\n    RESERVATIONS[reservation_id] = {'sku': sku, 'quantity': quantity}\n    return RESERVATIONS[reservation_id]\n",
                "api.py": "from inventory import take\nfrom reservations import remember\n\ndef reserve(reservation_id, sku, quantity):\n    take(sku, quantity)\n    return remember(reservation_id, sku, quantity)\n",
                "verify_reservations.py": "import inventory\nfrom api import reserve\n\nfirst = reserve('r1', 'sku-1', 1)\nsecond = reserve('r1', 'sku-1', 1)\nassert first == second\nassert inventory.STOCK['sku-1'] == 1\n",
            },
            "body": "Use $cstack:cstack. Fix duplicate reservations so calling reserve twice with the same reservation id is idempotent and stock is decremented only once. Keep the inventory and reservation modules separate. Run the reservation contract. Do not create commits.",
            "truth": {
                "classification": "stateful_cross_module_fix",
                "allowed_outputs": ["edit reservation/inventory boundary code", "preserve separate modules", "run local contract"],
                "required_outputs": ["duplicate reservation does not consume stock twice", "missing stock still errors"],
                "proof": ["verify_reservations.py passes or equivalent"],
                "checks": ["reservation contract passes"],
                "independent_signal": ["recognizes state invariant before patching one caller"],
            },
        },
        {
            "class": "contestedarchitecture", "skill": "cstack", "roles": ["architect runners", "interrogate reviewers"],
            "files": {
                "ADR.md": "# Export queue options\n\nOption A: sqlite table with status rows.\nOption B: append-only JSONL log with periodic compaction.\n\nConstraints: stdlib only, crash recovery, single-process CLI, operators sometimes inspect files by hand, expected volume under 500 jobs/day.\n",
                "queue.py": "def enqueue(job):\n    raise NotImplementedError\n",
            },
            "body": "Use $cstack:cstack. Compare the two viable export queue designs in ADR.md for this repository. Do not edit files. Grade the constraints and tradeoffs, then recommend one only if the local evidence supports it; otherwise name the tie and missing evidence.",
            "truth": {
                "classification": "contested_design_tradeoff",
                "allowed_outputs": ["read-only tradeoff analysis", "recommend sqlite, JSONL, or a tie with missing evidence"],
                "required_outputs": ["treat both options as viable", "grade crash recovery and operator inspection separately"],
                "proof": ["ADR.md and queue.py references"],
                "checks": ["read-only project hash remains unchanged"],
                "independent_signal": ["does not collapse to one invalid option"],
            },
            "sandbox": "read-only",
        },
        {
            "class": "broadreadonlyinvestigation", "skill": "cstack", "roles": ["how explorer"],
            "files": {
                "src/http.py": "from src.service import create_user\n\ndef post_user(payload):\n    return create_user(payload)['display_name']\n",
                "src/service.py": "from src.users import clean_name\nfrom src.audit import record\n\ndef create_user(payload):\n    user = {'name': payload['name'], 'display_name': clean_name(payload['name'])}\n    record(payload['name'])\n    return user\n",
                "src/users.py": "def clean_name(name):\n    return ' '.join(name.split()).title()\n",
                "src/audit.py": "EVENTS = []\n\ndef record(name):\n    EVENTS.append(name.strip().lower())\n",
                "src/report.py": "from src.audit import EVENTS\n\ndef latest_actor():\n    return EVENTS[-1] if EVENTS else None\n",
            },
            "body": "Use $cstack:cstack. Map the read-only path for user names from the HTTP entrypoint through service, normalization, audit, and report code. Identify the inconsistent display-name versus audit-name behavior. Do not edit files.",
            "truth": {
                "classification": "broad_read_only_mapping",
                "allowed_outputs": ["read-only cross-layer map", "bounded exploration when useful"],
                "required_outputs": ["include http.post_user", "include users.clean_name", "include audit.record", "identify audit lowercases while display names title-case"],
                "proof": ["path and symbol references"],
                "checks": ["read-only project hash remains unchanged"],
                "independent_signal": ["covers competing caller behavior across layers"],
            },
            "sandbox": "read-only",
        },
        {
            "class": "multisourcewhy", "skill": "cstack", "roles": ["why investigators", "why synthesizer"],
            "history": True,
            "files": {
                "docs/adr-001.md": "# Locale fallback\n\nDecision: empty locale should use account default, then en-US.\n",
                "locale.py": "def pick_locale(value, account_default):\n    return value or account_default or 'en-US'\n",
            },
            "after_seed": {"locale.py": "def pick_locale(value, account_default):\n    return value or 'en-US'\n"},
            "body": "Use $cstack:cstack. Explain why empty locale no longer uses the account default. Inspect local git history, docs/adr-001.md, and locale.py. Do not edit files.",
            "truth": {
                "classification": "multi_source_cause",
                "allowed_outputs": ["read git history", "read ADR", "read code"],
                "required_outputs": ["identify pick_locale change", "cite adr-001 account default decision", "no project hash change"],
                "proof": ["git and ADR evidence"],
                "checks": ["read-only project hash remains unchanged"],
                "independent_signal": ["combines git evidence with local ADR evidence"],
            },
            "sandbox": "read-only",
        },
        {
            "class": "independentmultifilesweep", "skill": "cstack", "roles": ["simple edits"],
            "files": {
                "prices.py": "def cents(dollars):\n    return int(dollars * 100)\n",
                "emails.py": "def normalized(email):\n    return email.strip()\n",
                "dates.py": "def iso_date(raw):\n    month, day, year = raw.split('/')\n    return f'{year}-{month}-{day}'\n",
                "verify_sweep.py": "from prices import cents\nfrom emails import normalized\nfrom dates import iso_date\n\nassert cents(10.29) == 1029\nassert normalized(' A@EXAMPLE.COM ') == 'a@example.com'\nassert iso_date('3/4/2026') == '2026-03-04'\n",
            },
            "body": "Use $cstack:cstack. Fix the three independent small defects covered by verify_sweep.py: exact cents conversion, lowercase trimmed emails, and zero-padded ISO dates. Keep the fixes local to the relevant modules, run the contract, and do not create commits.",
            "truth": {
                "classification": "independent_small_defect_sweep",
                "allowed_outputs": ["edit prices.py", "edit emails.py", "edit dates.py", "run one compact contract"],
                "required_outputs": ["cents avoids float truncation", "email is lowercase and trimmed", "date is zero-padded"],
                "proof": ["verify_sweep.py passes"],
                "checks": ["independent sweep contract passes"],
                "independent_signal": ["can split or sequence independent defects without mixing domains"],
            },
        },
        {
            "class": "generationbakeoff", "skill": "cstack", "roles": ["arena runners", "arena cross-judge pool"],
            "files": {
                "summary.py": "def summarize(records):\n    return []\n",
                "verify_summary.py": "from summary import summarize\n\nrecords = [\n    {'job': 'b', 'seq': 2, 'status': 'queued'},\n    {'job': 'a', 'seq': 1, 'status': 'old'},\n    {'job': 'a', 'seq': 3, 'status': 'done'},\n    {'job': 'b', 'seq': 2, 'status': 'running'},\n]\nassert summarize(records) == [\n    {'job': 'a', 'seq': 3, 'status': 'done'},\n    {'job': 'b', 'seq': 2, 'status': 'running'},\n]\nassert summarize({'job': str(i % 2), 'seq': i, 'status': str(i)} for i in range(4)) == [\n    {'job': '0', 'seq': 2, 'status': '2'},\n    {'job': '1', 'seq': 3, 'status': '3'},\n]\nassert summarize([]) == []\n",
            },
            "body": "Use $cstack:cstack. Produce two independent implementation proposals for summary.py, for example grouping versus incremental state. Compare them against correctness and memory constraints, apply the smallest correct one, and run verify_summary.py. Output must summarize event records by job using the largest sequence, let later input win equal sequence, sort by job, and support a single-pass iterable. Do not create commits.",
            "truth": {
                "classification": "alternative_generation_then_apply",
                "allowed_outputs": ["compare two implementation proposals", "edit summary.py", "run verify_summary.py"],
                "required_outputs": ["largest sequence wins per job", "later input wins equal sequence", "output sorted by job", "single-pass iterable works"],
                "proof": ["verify_summary.py passes", "proposal comparison covers correctness and memory"],
                "checks": ["summary contract passes"],
                "independent_signal": ["quality can improve through alternative comparison without answer leakage"],
            },
        },
        {
            "class": "multiphasemigration", "skill": "cstack", "roles": ["feature, refactoring", "how explorer"],
            "files": {
                "api.py": "from storage import load_invoice\n\ndef get_invoice(invoice_id):\n    invoice = load_invoice(invoice_id)\n    return {'id': invoice['id'], 'total': invoice['total']}\n",
                "storage.py": "DATA = {'inv-1': {'id': 'inv-1', 'total': 25}}\n\ndef load_invoice(invoice_id):\n    return DATA[invoice_id]\n",
                "report.py": "from storage import load_invoice\n\ndef report_line(invoice_id):\n    invoice = load_invoice(invoice_id)\n    return f\"{invoice['id']}={invoice['total']}\"\n",
                "client.py": "from api import get_invoice\n\ndef total_due(invoice_id):\n    return get_invoice(invoice_id)['total']\n",
                "verify_migration.py": "from api import get_invoice\nfrom client import total_due\nfrom report import report_line\n\ninvoice = get_invoice('inv-1')\nassert invoice['amount_cents'] == 2500\nassert invoice['total'] == 25\nassert total_due('inv-1') == 25\nassert report_line('inv-1') == 'inv-1=2500 cents'\n",
            },
            "body": "Use $cstack:cstack. Migrate the invoice data shape from total dollars to amount_cents across storage, API, report, and client callers. Keep API compatibility by preserving the old total field during this migration. Run verify_migration.py. Do not create commits.",
            "truth": {
                "classification": "multi_module_data_shape_migration",
                "allowed_outputs": ["edit storage.py", "edit api.py", "edit report.py", "preserve client compatibility", "run migration contract"],
                "required_outputs": ["amount_cents is canonical", "old total field remains available at API boundary", "report uses cents"],
                "proof": ["verify_migration.py passes"],
                "checks": ["migration contract passes"],
                "independent_signal": ["maps callers before changing shared data shape"],
            },
        },
    ]


def apply_history(project: Path, spec: dict[str, Any]) -> None:
    seed_git(project)
    for relative, content in spec.get("after_seed", {}).items():
        behavior.write_text(project, relative, content)
    if spec.get("after_seed"):
        commit_change(project, "change local behavior")


def build_cases(
    baseline: Path,
    proposed: Path,
    output: Path,
    role_models: dict[str, Any],
    catalog_path: Path | None,
    catalog_map: dict[str, list[str]] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bundles = {
        "shippedbaseline": copy_bundle(baseline, output, "quartz"),
        "minimal_call_control": copy_bundle(proposed, output, "cedar", control=True),
        "proposedriskaware": copy_bundle(proposed, output, "opal"),
    }
    cases: list[dict[str, Any]] = []
    expectations: list[dict[str, Any]] = []
    specs = fixture_specs()
    for index, spec in enumerate(specs, start=1):
        for variant_index, (_, variant_kind, short) in enumerate(VARIANTS, start=1):
            project_name = f"work-{index:02d}-{variant_index}"
            project = create_project(output, project_name, copy.deepcopy(spec["files"]), role_models, catalog_path)
            if spec.get("history"):
                apply_history(project, spec)
            register(
                cases, expectations,
                case_id=f"case_{index:02d}_{short}",
                variant_kind=variant_kind,
                fixture_class=spec["class"],
                project=project,
                bundle=bundles[variant_kind],
                skill=spec["skill"],
                roles=spec["roles"],
                role_models=role_models,
                catalog_map=catalog_map,
                body=spec["body"],
                ground_truth=spec["truth"],
                sandbox=spec.get("sandbox", "workspace-write"),
            )
    return cases, {
        "schema_version": 1,
        "variants": [
            {"key": kind, "resource_label": label, "description": description}
            for label, kind, description in VARIANTS
        ],
        "role_models": role_models,
        "cases": expectations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="trusted baseline plugin root")
    parser.add_argument("--proposed", type=Path, required=True, help="trusted proposed plugin root")
    parser.add_argument("--output", type=Path, required=True, help="new local root for projects, resources, and JSON")
    parser.add_argument("--role-models", type=Path, help="optional JSON map of cstack roles to explicit model choices")
    parser.add_argument("--catalog", type=Path,
                        help="optional live model catalog used to validate explicit role choices")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    baseline = args.baseline.expanduser().resolve()
    proposed = args.proposed.expanduser().resolve()
    catalog_path = args.catalog.expanduser().resolve() if args.catalog else None
    try:
        if output.exists() and any(output.iterdir()):
            parser.error("--output must be absent or empty; refusing to overwrite existing data")
        if any(output == root or output in root.parents or root in output.parents for root in (baseline, proposed)):
            parser.error("--output must be outside both plugin roots")
        validate_plugin_root(baseline, "--baseline")
        validate_plugin_root(proposed, "--proposed")
        if catalog_path is not None and not catalog_path.is_file():
            raise ValueError(f"--catalog must point to a regular file: {catalog_path}")
        catalog_map = models.read_catalog(catalog_path) if catalog_path and catalog_path.exists() else None
        role_models = read_role_models(args.role_models.expanduser().resolve() if args.role_models else None, catalog_map)
        output.mkdir(parents=True, exist_ok=True)
        cases, expectations = build_cases(baseline, proposed, output, role_models, catalog_path, catalog_map)
        (output / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "expectations.json").write_text(json.dumps(expectations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f"routing-scenarios: {error}\n")
    print(json.dumps({"output": str(output), "cases": len(cases), "expectations": len(expectations["cases"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
