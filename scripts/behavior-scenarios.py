#!/usr/bin/env python3
"""Génère des projets isolés et des scénarios de comportement Codex natifs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


MODEL = {"model": "gpt-5.6-luna", "reasoning_effort": "max"}
IGNORED_DIRS = {".git", "__pycache__", "node_modules"}
FORBIDDEN_PROMPT_LABELS = re.compile(r"\b(?:eval|test|judge|candidate|benchmark)\b", re.IGNORECASE)
PANEL_LENGTHS = {"interrogate reviewers": 3, "arena runners": 3, "arena cross-judge pool": 1}
GIT_NAME = "scénario cstack"
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
        raise ValueError(f"la racine du plugin doit contenir un dossier skills: {source}")
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
        "commit", "-m", "initialiser le scénario",
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
        f"La version source n’est pas installée. Lis directement ce fichier de compétence avant d’agir : {skill_path}"
    )
    value = body.strip() + "\n\n" + note
    if FORBIDDEN_PROMPT_LABELS.search(value):
        raise ValueError(f"libellé d’évaluation interdit dans la consigne de {skill}")
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
    expected_children: int | None = 0,
    min_children: int | None = None,
    expected_artifacts: list[str] | None = None,
    expected_routes: list[str] | None = None,
    forbidden_routes: list[str] | None = None,
    outcome_checks: list[dict[str, Any]] | None = None,
) -> None:
    if not (project / ".git").exists():
        seed_git(project)
    discovered = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=project, text=True).strip()
    if Path(discovered).resolve() != project.resolve():
        raise ValueError(f"le scénario a hérité d’un autre dépôt: {project}")
    if (body is None) == (bodies is None):
        raise ValueError(f"{case_id}: fournissez body ou bodies")
    texts = bodies if bodies is not None else [body]
    prompts = [prompt(bundle, skill, text, french) for text in texts if text is not None]
    case: dict[str, Any] = {"id": case_id, "cwd": str(project), "sandbox": sandbox,
                            "ephemeral": False, "bundle": str(bundle.resolve())}
    case["prompts" if bodies is not None else "prompt"] = prompts if bodies is not None else prompts[0]
    cases.append(case)
    skill_path = bundle / "skills" / skill / "SKILL.md"
    expectation: dict[str, Any] = {
        "id": case_id,
        "project_sha256": tree_hash(project),
        "source_sha256": {
            "bundle": tree_hash(bundle),
            "skill": hashlib.sha256(skill_path.read_bytes()).hexdigest(),
        },
        "role_metadata": model_config(roles),
    }
    if expected_children is not None and min_children is not None:
        raise ValueError(f"{case_id}: expected_children et min_children s’excluent")
    if expected_children is not None:
        expectation["expected_children"] = expected_children
    if min_children is not None:
        expectation["min_children"] = min_children
    if expected_artifacts is not None:
        expectation["expected_artifacts"] = expected_artifacts
    if outcome_checks is not None:
        expectation["outcome_checks"] = outcome_checks
    if expected_routes is not None or forbidden_routes is not None:
        expected = sorted(expected_routes or [])
        forbidden = sorted(forbidden_routes or [])
        overlap = set(expected) & set(forbidden)
        if overlap:
            raise ValueError(f"{case_id}: route présente dans expected et forbidden: {sorted(overlap)}")
        for route in expected + forbidden:
            if not (bundle / route).is_file():
                raise ValueError(f"{case_id}: route absente du bundle: {route}")
        expectation["routing"] = {"expected": expected, "forbidden": forbidden}
    expectations.append(expectation)


def interrogate_project(output: Path, name: str, catalog: Path | None) -> Path:
    project = create_project(output, name, {
        "README.md": """# Service d’événements Cedar

## Comportement approuvé

La commande accepte --json.
Le README doit expliquer que --json préserve l’ordre des champs et qu’une entrée mal formée entraîne un code de sortie non nul.
""",
        "src/feature.py": """def normalize_owner(value):
    return value.strip()
""",
    }, ["interrogate reviewers"], catalog)
    seed_git(project, "feature/review")
    write_text(project, "README.md", """# Service d’événements Cedar

## Sortie

Utilisez cedar --json pour des enregistrements lisibles par une machine.
""")
    git(project, "add", "README.md")
    write_text(project, "src/feature.py", """def normalize_owner(value):
    return " ".join(value.split()).title()
""")
    write_text(project, "notes.md", "Note de travail existante ; elle est hors du périmètre de revue demandé.\n")
    return project


def partial_set_project(output: Path, name: str, catalog: Path | None) -> Path:
    project = create_project(output, name, {
        "README.md": """# Facturation Cedar

## Comportement approuvé

Chaque statut de commande (pending, paid, refunded, disputed) a son propre libellé français.
Une commande en litige (disputed) ne doit jamais apparaître comme réglée.
""",
        "src/status.py": 'STATUSES = ("pending", "paid", "refunded", "disputed")\n',
        "src/billing.py": """def label(status):
    return status


def legacy_total(items):
    return sum(items)
""",
        "src/reports.py": """from .billing import legacy_total


def report(items):
    return legacy_total(items)
""",
    }, ["interrogate reviewers"], catalog)
    seed_git(project, "feature/labels")
    write_text(project, "src/billing.py", """def label(status):
    if status == "pending":
        return "En attente"
    if status == "refunded":
        return "Remboursée"
    return "Réglée"
""")
    git(project, "add", "src/billing.py")
    return project


def arena_project(output: Path, name: str, catalog: Path | None) -> Path:
    return create_project(output, name, {
        "README.md": """# Durées Cedar

parse_duration convertit une durée écrite en secondes : "90s" vaut 90, "2h" vaut 7200, "1h30m" vaut 5400 et "0m" vaut 0.
Une chaîne vide, une unité inconnue ("10x") ou un nombre sans unité ("15") lève ValueError.
""",
        "src/__init__.py": "",
        "src/duration.py": """def parse_duration(text):
    raise NotImplementedError
""",
        "tests/__init__.py": "",
        "tests/test_duration.py": """import unittest

from src.duration import parse_duration


class ParseDuration(unittest.TestCase):
    def test_values(self):
        for text, seconds in (("90s", 90), ("2h", 7200), ("1h30m", 5400), ("0m", 0)):
            self.assertEqual(parse_duration(text), seconds)

    def test_rejects(self):
        for text in ("", "10x", "15"):
            with self.assertRaises(ValueError):
                parse_duration(text)


if __name__ == "__main__":
    unittest.main()
""",
    }, ["arena runners", "arena cross-judge pool"], catalog)


def setup_project(output: Path, name: str, catalog: Path | None) -> Path:
    project = create_project(output, name, {}, [], catalog)
    (project / "AGENTS.md").write_bytes("# Règles manuelles du projet\r\n\r\nConserver cette ligne exacte.\r\n".encode("utf-8"))
    (project / "CLAUDE.md").write_bytes("# Règles manuelles Claude\r\n\r\nConserver aussi cette ligne exacte.\r\n".encode("utf-8"))
    (project / ".gitignore").write_bytes(b"# Exclusions manuelles\r\nbuild/\r\n")
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
    correction = """Utilise $cstack:cstack pour cette petite correction Python. Dans events.py, rends la borne inférieure inclusive et rejette les événements postérieurs à aujourd’hui. Ajoute verify_events.py avec des assertions directes pour la borne de début et les événements futurs. Travaille directement dans ce projet. Ne crée aucun sous-agent ni commit et ne modifie aucun fichier sans rapport avec la tâche."""
    explanation = """Utilise $cstack:how pour expliquer comment events.py filtre les événements et où ses bornes sont définies. Réponds avec les chemins et les symboles utiles. Ne modifie aucun fichier, ne délègue pas et ne crée aucun commit."""
    review = """Utilise $cstack:interrogate pour une revue en lecture seule du travail actuel. Examine la modification indexée de README.md selon cette exigence approuvée : expliquer que --json préserve l’ordre des champs et qu’une entrée mal formée entraîne un code de sortie non nul. Examine la branche et l’arbre de travail pour comprendre le contexte. La modification non indexée de src/feature.py et le fichier non suivi notes.md existaient déjà ; ne les modifie pas, ne les commite pas et ne les inclus pas dans le périmètre de revue. Utilise le panel de réviseurs configuré et ne rapporte que des constats étayés."""

    for case_id, name, bundle in (
        ("clear_python_correction_baseline", "alder", old),
        ("clear_python_correction_proposed", "cedar", new),
    ):
        register(cases, expectations, case_id=case_id,
                 project=create_project(output, name, event_files, ["bug-fix"], catalog),
                 bundle=bundle, skill="cstack", roles=["bug-fix"],
                 body=correction, expected_children=0,
                 outcome_checks=[{"id": "event-boundaries", "argv": [sys.executable, "-c",
                     "import json; from events import filter_events; events = [{'date': n} for n in (0, 1, 2, 3)]; "
                     "print(json.dumps(filter_events(events, 1, 2)))"],
                     "expected_json": [{"date": 1}, {"date": 2}]}])

    archive_files = {
        "storage.py": "def save_record(record, existing):\n    if record[\"id\"] not in existing:\n        raise KeyError(record[\"id\"])\n    return record\n",
    }
    ambiguous_archive = """Utilise $cstack:cstack pour ajouter archive_completed à storage.py. Les entrées terminées doivent être archivées, mais personne n'a défini si elles quittent la liste active ou reçoivent un statut archived, ni si l'objet actuel est modifié ou copié. Examine le dépôt, puis fais ce qui est demandé. Ne crée aucun sous-agent ni commit."""
    for case_id, name, bundle in (
        ("ambiguous_archive_baseline", "juniper", old),
        ("ambiguous_archive_proposed", "larch", new),
    ):
        register(cases, expectations, case_id=case_id,
                 project=create_project(output, name, archive_files, ["bug-fix"], catalog),
                 bundle=bundle, skill="cstack", roles=["bug-fix"],
                 body=ambiguous_archive, french=True, sandbox="read-only")
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

    partial_review = """Utilise $cstack:interrogate sur le travail courant indexé (git diff --cached) avec le panel configuré. Intention : afficher un libellé français pour chaque statut de commande. Le README contient le comportement approuvé. Ne modifie aucun fichier et ne crée ni commit ni PR."""
    for case_id, name, bundle in (
        ("interrogate_partial_set_baseline", "aspen", old),
        ("interrogate_partial_set_proposed", "poplar", new),
    ):
        register(cases, expectations, case_id=case_id,
                 project=partial_set_project(output, name, catalog), bundle=bundle,
                 skill="interrogate", roles=["interrogate reviewers"],
                 body=partial_review, french=True, sandbox="read-only", expected_children=3)

    arena_task = """Utilise $cstack:arena pour implémenter parse_duration dans src/duration.py selon le README, avec le panel configuré de trois implémentations concurrentes. La vérification du projet est python3 -m unittest discover -s tests. Ne crée ni commit, ni PR, ni objectif natif."""
    register(cases, expectations, case_id="arena_verified_selection",
             project=arena_project(output, "yew", catalog), bundle=new,
             skill="arena", roles=["arena runners", "arena cross-judge pool"],
             body=arena_task, french=True, expected_children=5)

    verification_files = {
        "README.md": """# Notes Cedar

`python3 notes.py add <texte>` ajoute une note à notes.txt et affiche son numéro.
`python3 notes.py list` affiche les notes numérotées.
`python3 notes.py sync` envoie les notes au service distant défini par NOTES_TOKEN.
""",
        "notes.py": """import os
import sys

STORE = "notes.txt"


def main(argv):
    if argv[:1] == ["add"] and len(argv) > 1:
        with open(STORE, "a", encoding="utf-8") as handle:
            handle.write(" ".join(argv[1:]) + "\\n")
        with open(STORE, encoding="utf-8") as handle:
            print(sum(1 for _ in handle))
        return 0
    if argv[:1] == ["list"]:
        if os.path.exists(STORE):
            with open(STORE, encoding="utf-8") as handle:
                for index, line in enumerate(handle, 1):
                    print(f"{index}. {line.rstrip()}")
        return 0
    if argv[:1] == ["sync"]:
        if not os.environ.get("NOTES_TOKEN"):
            print("NOTES_TOKEN manquant", file=sys.stderr)
            return 2
        print("synchronisé")
        return 0
    print("usage: notes.py add|list|sync", file=sys.stderr)
    return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
""",
    }
    verification = """Utilise $cstack:create-verification-skill pour ce dépôt. J'autorise l'écriture de la skill générée sous .agents/skills/ et l'exécution de notes.py dans ce dépôt. Pour la preuve de la skill générée, pilote la fonctionnalité sync, sans NOTES_TOKEN : aucun jeton n'est disponible et aucun service distant ne doit être contacté. Ne modifie pas notes.py et ne crée ni commit ni PR."""
    register(cases, expectations, case_id="create_verification_cli_verdicts",
             project=create_project(output, "hornbeam", verification_files, [], catalog),
             bundle=new, skill="create-verification-skill", roles=[], body=verification,
             french=True, expected_children=None)

    storage = archive_files
    overwrite = """Utilise $cstack:clarify pour préparer une décision sur storage.py. Lorsqu'un enregistrement existant serait écrasé, le produit n'a pas encore choisi entre remplacer, conserver l'ancien ou refuser. Inspecte les faits du dépôt, puis pose les questions de frontière nécessaires avec des recommandations. Ne choisis pas pour moi, ne modifie aucun fichier et n'écris aucun document."""
    complete = """Utilise $cstack:clarify uniquement pour examiner cette demande entièrement définie. save_record doit remplacer un enregistrement existant, renvoyer le nouvel enregistrement et conserver l’erreur existante pour un identifiant absent. S’il ne reste aucune ambiguïté importante, indique-le et termine sans inventer de question. Ne modifie aucun fichier, ne crée aucun document et n’implémente rien."""
    register(cases, expectations, case_id="clarify_overwrite",
             project=create_project(output, "spruce", storage, [], catalog),
             bundle=new, skill="clarify", roles=[], body=overwrite, french=True, sandbox="read-only")
    register(cases, expectations, case_id="clarify_complete",
             project=create_project(output, "willow", storage, [], catalog),
             bundle=new, skill="clarify", roles=[], body=complete, sandbox="read-only")

    setup_first = """Utilise $cstack:setup-cstack dans ce projet. J’autorise une configuration avec ces choix exacts : ajouter le bloc passif cstack à AGENTS.md, ajouter les consignes du projet dans docs/agents/cstack.md et configurer le suivi local Markdown dans docs/agents/issue-tracker.md. Préserve les octets manuels d’AGENTS.md et CLAUDE.md hors du contenu géré, y compris les fins de ligne CRLF. Préserve les entrées existantes de .gitignore et ajoute uniquement l’entrée d’exclusion nécessaire à la configuration. Conserve .cstack/models.json strictement à l’identique ; ne choisis aucun modèle. Utilise uniquement l’utilitaire de confiance project.py pour cette configuration ; n’invoque pas models.py. Ne crée aucun sous-agent, fichier global, objectif, commit ou PR et n’accède à aucun service distant. Applique la configuration locale du projet et indique les chemins modifiés."""
    setup_second = """Utilise à nouveau $cstack:setup-cstack avec exactement les mêmes choix : bloc passif AGENTS.md, consignes du projet et suivi local Markdown, sans choix de modèles. Relis l’état actuel du projet et applique la configuration ; aucune modification n’est attendue. Préserve les fichiers manuels en CRLF, les entrées .gitignore et .cstack/models.json. Utilise uniquement l’utilitaire de confiance project.py ; n’invoque pas models.py. Ne crée aucun sous-agent, fichier global, objectif, commit ou PR et n’accède à aucun service distant."""
    register(cases, expectations, case_id="setup_project_twice",
             project=setup_project(output, "hazel", catalog), bundle=new,
             skill="setup-cstack", roles=[], bodies=[setup_first, setup_second])

    domain_files = {
        "CONTEXT.md": "# Termes Cedar\n\nLigne manuelle : conserver cette phrase exacte.\n",
        "members.py": 'def member_label(row):\n    return row["name"]\n',
    }
    domain_readonly = """Utilise $cstack:domain. Lis members.py et CONTEXT.md, puis propose dans la conversation une entrée pour le terme ambigu « member ». Le choix métier reste humain. Ne modifie aucun fichier et ne crée aucun document."""
    domain_write = """Utilise $cstack:domain. J’autorise explicitement cette tâche à mettre à jour CONTEXT.md pour le terme défini Member ; préserve toutes les séquences d’octets manuelles existantes, ajoute uniquement l’entrée de glossaire approuvée et ne modifie pas le code. Dans ce dépôt, un Member est une personne ayant accès à un espace de travail. Rédige l’entrée selon les conventions existantes du document sans créer d’ADR pour ce terme. Ne redemande pas d’autorisation après celle-ci."""
    register(cases, expectations, case_id="domain_readonly",
             project=create_project(output, "ash", domain_files, ["documentation"], catalog),
             bundle=new, skill="domain", roles=["documentation"],
             body=domain_readonly, french=True, sandbox="read-only")
    register(cases, expectations, case_id="domain_authorized_write",
             project=create_project(output, "beech", domain_files, ["documentation"], catalog),
             bundle=new, skill="domain", roles=["documentation"], body=domain_write)

    horizon_readme = """# Migration des archives

## Faits principaux

- Les événements sont stockés dans data/archive.jsonl.
- La durée de conservation actuelle est de 90 jours.
- Les instantanés nocturnes sont conservés pendant 30 jours.
- La migration doit conserver l’ordre des événements et permettre un retour arrière pendant 14 jours.

## Questions de recherche

1. Quel fait détermine la durée de conservation et la fréquence des sauvegardes ?
2. Quel fait détermine la procédure de retour arrière ?
"""
    horizon_first = """Utilise $cstack:horizon pour organiser ce travail sur plusieurs sessions. La destination est déjà définie : migrer les archives d’événements vers un stockage en ajout seul, sans perte de données et avec un retour arrière possible pendant 14 jours. J’autorise l’écriture des documents de planification Horizon dans .cstack/horizon/, mais ne modifie pas le code du produit et ne crée ni PR ni objectif natif. Le README fourni est la source principale pour deux questions de recherche en lecture seule. Crée exactement ces tickets : 001 recherche les faits de conservation et sauvegarde dans le README ; 002 recherche les faits de retour arrière dans le README ; 003 est une décision humaine de politique bloquée par 001 et 002 ; 004 est une décision humaine de politique bloquée par 003. Pour chaque ticket de recherche prêt, affecte exactement deux enfants natifs de recherche sur deux angles distincts en utilisant le rôle how explorer configuré; conserve un handle et un artefact par angle et attends les quatre résultats avant de résoudre 001 ou 002. Lors de cette invocation, résous uniquement 001 et 002 ; laisse 003 et 004 ouverts. Ne réponds pas à la place d’un humain."""
    horizon_second = """Utilise $cstack:horizon pour reprendre depuis l’état Horizon existant. Résous uniquement le ticket 003 avec cette décision utilisateur : conserver les événements source pendant 90 jours, garder les instantanés nocturnes pendant 30 jours et exiger un retour arrière possible pendant 14 jours. Le ticket 004 doit rester ouvert, car il dépend de 003 et n’a aucune réponse humaine. L’écriture des documents du plan reste autorisée ; ne modifie pas le code du produit et ne crée ni PR ni objectif natif. Vérifie les documents de recherche de 001 et 002 avant d’enregistrer 003 et ne réponds pas à 004."""
    register(cases, expectations, case_id="horizon_two_research_then_policy",
             project=create_project(output, "fir", {"README.md": horizon_readme}, ["how explorer"], catalog),
             bundle=new, skill="horizon", roles=["how explorer"],
             bodies=[horizon_first, horizon_second], expected_children=4)

    audit_files = {
        "src/users.py": 'def username(user):\n    return user["name"].strip().lower()\n',
        "src/orders.py": 'def owner_name(order):\n    return order["owner"].strip().lower()\n',
        "src/reports.py": 'def actor_name(report):\n    return report["actor"].strip().lower()\n',
    }
    audit = """Utilise $cstack:audit-architecture sur le périmètre src/. Lis directement la compétence indiquée, puis dresse une enquête d'architecture en lecture seule sur le point chaud de normalisation des noms d'utilisateur dans ces trois modules. Utilise exactement deux explorateurs bornés sur deux angles distincts; conserve les builders et reviewers hors de ce panel. Ne modifie aucun fichier. Rapporte les chemins, symboles, appelants, preuves et la profondeur d'interface observée; toute forme proposée doit rester explicitement non vérifiée."""
    register(cases, expectations, case_id="audit_architecture_username_scope",
             project=create_project(output, "rowan", audit_files, ["how explorer"], catalog),
             bundle=new, skill="audit-architecture", roles=["how explorer"],
             body=audit, french=True, sandbox="read-only", expected_children=2)

    trivial = """Use $cstack:cstack. src/errors.py prints "could not proccess invoice" to users. The word should be "process". Correct it."""
    register(cases, expectations, case_id="routing_one_word_user_string",
             project=create_project(output, "linden", {
                 "src/errors.py": 'def fail(code):\n    return f"Error: could not proccess invoice {code}"\n',
             }, [], catalog),
             bundle=new, skill="cstack", roles=[], body=trivial,
             expected_children=None,
             expected_routes=["skills/cstack/playbooks/bug-fix.md"],
             forbidden_routes=[
                 "skills/cstack/references/principles/laziness-protocol.md",
             ], outcome_checks=[{"id": "invoice-message", "argv": [sys.executable, "-c",
                 "import json; from src.errors import fail; print(json.dumps(fail('demo')))"],
                 "expected_json": "Error: could not process invoice demo"}])

    typed_boundary = """Use $cstack:cstack. Operators hand-edit config.yaml and the service reads it at startup. Give the configuration a typed shape and write the loader that produces it. Operators regularly ship a missing key, a quoted number where an integer belongs, or an endpoint with no scheme."""
    register(cases, expectations, case_id="routing_typed_external_boundary",
             project=create_project(output, "sorrel", {
                 "config.yaml": "retries: 3\ntimeout_ms: 500\nendpoint: https://x.example\n",
                 "src/config.py": "def load(path):\n    raise NotImplementedError\n",
             }, [], catalog),
             bundle=new, skill="cstack", roles=[], body=typed_boundary,
             expected_children=None,
             expected_routes=[
                 "skills/cstack/references/principles/boundary-discipline.md",
                 "skills/cstack/references/principles/foundational-thinking.md",
                 "skills/cstack/references/principles/type-system-discipline.md",
             ])

    migration = """Use $cstack:cstack. src/auth.py still exposes legacy_auth(), and src/session.py and src/api.py both call it. verify() replaces it. Move every caller across and retire the old entry point."""
    register(cases, expectations, case_id="routing_internal_api_replacement",
             project=create_project(output, "hemlock", {
                 "src/auth.py": 'def legacy_auth(token):\n    return bool(token)\n\n\ndef verify(token):\n    return bool(token)\n',
                 "src/session.py": 'from .auth import legacy_auth\n\n\ndef open_session(token):\n    return legacy_auth(token)\n',
                 "src/api.py": 'from .auth import legacy_auth\n\n\ndef handle(token):\n    return legacy_auth(token)\n',
             }, [], catalog),
             bundle=new, skill="cstack", roles=[], body=migration,
             expected_children=None,
             expected_routes=[
                 "skills/cstack/playbooks/refactoring.md",
                 "skills/cstack/references/principles/migrate-callers-then-delete-legacy-apis.md",
             ])

    live_process = """Use $cstack:cstack. The queue worker pegs one core and stops draining its queue after roughly an hour of uptime. It is running right now and reproduces on demand. No capture has been taken. Diagnose the cause."""
    register(cases, expectations, case_id="routing_live_process_diagnosis",
             project=create_project(output, "tamarack", {
                 "src/worker.py": 'def drain(queue):\n    while True:\n        if not queue:\n            continue\n        queue.pop()\n',
             }, [], catalog),
             bundle=new, skill="cstack", roles=[], body=live_process,
             expected_children=None,
             expected_routes=["skills/cstack/playbooks/runtime-forensics.md"],
             forbidden_routes=["skills/cstack/playbooks/trace-forensics.md"])

    changelog_rule = """Utilise $cstack:cstack. Dans ce dépôt, les agents oublient le numéro de PR dans CHANGELOG.md dès qu'on leur dit que la publication est urgente. Ajoute à la compétence .agents/skills/changelog/SKILL.md la règle qui l'empêche, et montre qu'elle change leur choix sous cette pression. Ne crée ni commit ni PR."""
    register(cases, expectations, case_id="authoring_rule_baseline_first",
             project=create_project(output, "buckeye", {
                 ".agents/skills/changelog/SKILL.md": "---\nname: changelog\ndescription: Ajoute une entrée à CHANGELOG.md pour chaque changement livré.\n---\n\n# Changelog\n\nAjoute une ligne sous « Non publié » qui dit ce qui change pour l'utilisateur.\n",
                 "CHANGELOG.md": "# Changelog\n\n## Non publié\n\n- Export CSV des factures (#41)\n- Correction du fuseau horaire des rappels\n",
             }, [], catalog),
             bundle=new, skill="cstack", roles=[], body=changelog_rule, french=True,
             expected_children=None, min_children=2,
             expected_artifacts=[
                 ".cstack/tasks/*/pressure/base.md",
                 ".cstack/tasks/*/pressure/regle-1.md",
             ],
             expected_routes=[
                 "skills/cstack/playbooks/authoring-a-skill.md",
                 "skills/cstack/references/rule-pressure-tests.md",
             ])
    route_specs = [
        ("simple_feature", "Add an optional greeting suffix to greet() without changing its callers.",
         "feature", ["how/SKILL.md"], ["arena/SKILL.md", "interrogate/SKILL.md"]),
        ("stateful_feature", "Add a pending-to-complete transition to the job record and persist it across restart.",
         "feature", ["cstack/references/principles/model-the-domain.md", "architect/SKILL.md"],
         ["interrogate/SKILL.md"]),
        ("cross_module_feature", "Add a token expiry check in src/auth.py and update the shared contract used by src/api.py and src/session.py.",
         "feature", ["architect/SKILL.md", "blast-radius/SKILL.md"], ["arena/SKILL.md"]),
        ("competing_feature_shapes", "Implement a retry policy. A queue-based and a scheduled design are both feasible; compare their failure behavior before choosing.",
         "feature", ["arena/SKILL.md", "architect/SKILL.md"], ["interrogate/SKILL.md"]),
        ("contested_design", "The team disputes whether retries belong to the API or worker. Settle the architecture using independent critical review before implementation.",
         "feature", ["interrogate/SKILL.md", "architect/SKILL.md"], []),
        ("read_only_why", "Why did the service keep two retry counters? Inspect the history and answer with evidence; change nothing.",
         "investigation", ["how/SKILL.md", "why/SKILL.md"], ["architect/SKILL.md"]),
        ("one_off_performance", "The request takes 900 ms. Diagnose the bottleneck and improve it against a measured baseline.",
         "perf-issue", [], ["cstack/playbooks/hillclimb.md"]),
        ("iterative_metric", "Increase requests per second to 500 through repeated measured iterations; keep only improvements.",
         "hillclimb", [], ["cstack/playbooks/perf-issue.md"]),
        ("captured_trace", "Diagnose the CPU bottleneck from the captured trace.json. The process is no longer running. Report a finding only.",
         "trace-forensics", [], ["cstack/playbooks/runtime-forensics.md"]),
        ("throwaway_prototype", "Build a disposable sketch to compare two pagination layouts, observe the result, then recommend one.",
         "prototype", [], ["cstack/playbooks/feature.md"]),
        ("skill_authoring", "Create a small SKILL.md for inspecting the service health endpoint.",
         "authoring-a-skill", [], ["cstack/playbooks/feature.md"]),
        ("typescript_boundary", "Add typed parsing of an untrusted JSON config in src/config.ts and a function that uses the parsed settings.",
         "feature", ["typescript-best-practices/SKILL.md", "cstack/references/principles/boundary-discipline.md",
                     "cstack/references/principles/type-system-discipline.md"], []),
        ("shared_writers", "Two independent workers write the same checkpoint file. Change the design so concurrent writes cannot corrupt state.",
         "bug-fix", ["cstack/references/principles/separate-before-serializing-shared-state.md"], []),
    ]
    for index, (name, body, primary, required, forbidden) in enumerate(route_specs):
        project = create_project(output, f"route-{index:02d}", {
            "src/service.py": "import time\n\ndef greet(name):\n    return 'Hello ' + name\n\ndef request(name):\n    time.sleep(0.9)\n    return greet(name)\n",
            "src/auth.py": "def verify(token):\n    return bool(token)\n",
            "src/api.py": "from .auth import verify\n\ndef handle(token):\n    return verify(token)\n",
            "src/session.py": "from .auth import verify\n\ndef open_session(token):\n    return verify(token)\n",
            "src/job.py": "class Job:\n    def __init__(self):\n        self.status = 'pending'\n",
            "src/worker.py": "from pathlib import Path\n\ndef checkpoint(value):\n    Path('checkpoint.json').write_text(value)\n",
            "src/retry.py": "api_retries = 0\nworker_retries = 0\n",
            "src/config.ts": "export const settings = JSON.parse('{}');\n",
            "trace.json": '{"sampled_cpu_ms": 800, "function": "greet"}\n',
        }, [], catalog)
        register(cases, expectations, case_id="routing_" + name,
                 project=project, bundle=new, skill="cstack", roles=[],
                 body="Use $cstack:cstack. " + body, expected_children=None,
                 expected_routes=["skills/cstack/playbooks/" + primary + ".md"]
                                 + ["skills/" + route for route in required],
                 forbidden_routes=["skills/" + route for route in forbidden])
    return cases, expectations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="affiche cette aide puis quitte")
    parser.add_argument("--baseline", type=Path, required=True, help="racine de confiance du plugin de référence")
    parser.add_argument("--proposed", type=Path, required=True, help="racine de confiance du plugin proposé")
    parser.add_argument("--output", type=Path, required=True, help="nouvelle racine locale des projets, ressources et fichiers JSON")
    parser.add_argument("--catalog", type=Path, help="catalogue actuel facultatif des modèles, copié dans les projets générés")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("--output doit être absent ou vide ; refus d’écraser les données existantes")
    baseline = args.baseline.expanduser().resolve()
    proposed = args.proposed.expanduser().resolve()
    catalog = args.catalog.expanduser().resolve() if args.catalog else None
    if catalog is not None and not catalog.is_file():
        parser.error("--catalog doit pointer vers un fichier ordinaire")
    if any(output == root or output in root.parents or root in output.parents for root in (baseline, proposed)):
        parser.error("--output doit être situé hors des deux racines de plugins")
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
