#!/usr/bin/env python3
"""Prévisualiser et appliquer les fichiers fixes de configuration projet cstack."""

from __future__ import annotations

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

# Les comptes sont du texte de politique pour la prévisualisation de configuration, pas de la répartition automatique.
WORKFLOWS = {
    "clarify": {"count_rule": "0 par défaut; un explorateur par fait indépendant délégué", "roles": ["how explorer"]},
    "domain": {"count_rule": "0 par défaut; délégation factuelle optionnelle", "roles": ["how explorer", "documentation", "judgment and prose"]},
    "horizon": {"count_rule": "enfants de recherche variables; 1 synthèse optionnelle (judgment and prose)", "roles": ["how explorer", "judgment and prose"]},
    "audit-architecture": {"count_rule": "au plus 1 explorateur initial", "roles": ["how explorer"]},
}


class ProjectError(ValueError):
    pass


class InterruptedApply(Exception):
    def __init__(self, applied: list[str], skipped: list[str]) -> None:
        self.applied, self.skipped = applied, skipped
        super().__init__("application interrompue; le plan accepté peut reprendre")


def _models():
    path = Path(__file__).with_name("models.py")
    spec = importlib.util.spec_from_file_location("cstack_setup_models", path)
    if spec is None or spec.loader is None:
        raise ProjectError("impossible de charger le script d’aide models.py existant")
    module = importlib.util.module_from_spec(spec)
    # Lire le script d’aide de confiance sans écrire de bytecode dans le paquet installé.
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
        raise ProjectError("le contenu de l’instantané doit être du texte base64 ou null")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeError) as error:
        raise ProjectError("le contenu de l’instantané n’est pas du base64 valide") from error


def _path(workspace: Path, relative: str, *, write: bool = False) -> Path:
    allowed = TARGET_PATHS if write else ALLOWED_PATHS
    if relative not in allowed or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ProjectError(f"le chemin est hors de la liste d’autorisation de configuration projet: {relative}")
    return workspace / relative


def _workspace(path: Path) -> Path:
    """Accepter seulement un dossier existant dont les ancêtres restent dans le périmètre."""
    supplied = Path(path)
    absolute = Path(os.path.abspath(supplied))
    if supplied.is_symlink() or not supplied.exists() or not supplied.is_dir():
        raise ProjectError(f"l’espace de travail doit être un dossier régulier existant: {path}")
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ProjectError(f"un ancêtre de l’espace de travail est un lien symbolique: {current}")
        if current != absolute and not current.is_dir():
            raise ProjectError(f"un ancêtre de l’espace de travail n’est pas un dossier: {current}")
    return absolute


def _check(path: Path, workspace: Path) -> None:
    try:
        relative = path.relative_to(workspace)
    except ValueError as error:
        raise ProjectError(f"le chemin sort de l’espace de travail: {path}") from error
    current = workspace
    for part in relative.parts:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        if current.is_symlink():
            raise ProjectError(f"le chemin projet en lien symbolique n’est pas inscriptible: {current}")
        if current != path and not current.is_dir():
            raise ProjectError(f"le parent projet n’est pas un dossier: {current}")
    if (path.exists() or path.is_symlink()) and not path.is_file():
        raise ProjectError(f"la cible projet n’est pas un fichier régulier: {path}")


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
            raise ProjectError(f"enregistrement d’instantané observé invalide: {relative}")
        data = _unb64(record["content_b64"])
        if not isinstance(record["exists"], bool) or record["exists"] != (data is not None) or record["sha256"] != (None if data is None else _sha(data)):
            raise ProjectError(f"hash ou existence de l’instantané non concordant: {relative}")
        result[relative] = data
    return result


def _tracker(raw: Any) -> dict[str, str]:
    if raw is None:
        return {"mode": "keep"}
    if not isinstance(raw, dict) or set(raw) - TRACKER_KEYS or "mode" not in raw:
        raise ProjectError("le suivi doit contenir seulement mode, owner et repo")
    mode = raw["mode"]
    if mode not in TRACKER_MODES:
        raise ProjectError("le mode de suivi doit être keep, local ou github")
    if mode != "github" and set(raw) != {"mode"}:
        raise ProjectError(f"les clés de suivi ne sont pas valides pour le mode {mode}")
    if mode == "github":
        pattern = re.compile(r"^[A-Za-z0-9_.-]+$")
        if not all(isinstance(raw.get(key), str) and pattern.fullmatch(raw[key]) for key in ("owner", "repo")):
            raise ProjectError("owner et repo du suivi github sont invalides")
        return {"mode": mode, "owner": raw["owner"], "repo": raw["repo"]}
    return {"mode": mode}


def _options(raw: Any, models: Any, catalog: dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict) or set(raw) - {"model_choices", "tracker"}:
        raise ProjectError("options peut contenir seulement model_choices et tracker")
    choices = raw.get("model_choices", {})
    if not isinstance(choices, dict):
        raise ProjectError("model_choices doit être un objet")
    try:
        models.validate(choices)
        if choices:
            models.validate(choices, catalog, check_available=True)
    except (TypeError, ValueError) as error:
        raise ProjectError(f"model_choices invalide: {error}") from error
    return {"model_choices": choices, "tracker": _tracker(raw.get("tracker"))}


def _managed(payload: bytes) -> bytes:
    if START in payload or END in payload:
        raise ProjectError("le contenu généré ne peut pas contenir les marqueurs gérés cstack")
    return START + b"\n" + payload.rstrip(b"\r\n") + b"\n" + END


def _merge(old: bytes | None, payload: bytes, *, owned: bool) -> bytes:
    block = _managed(payload)
    if old is None:
        return block + b"\n"
    starts, ends = old.count(START), old.count(END)
    if starts or ends:
        if starts != 1 or ends != 1 or old.index(START) > old.index(END):
            raise ProjectError("les marqueurs gérés sont mal formés ou dupliqués")
        start, end = old.index(START), old.index(END) + len(END)
        return old[:start] + block + old[end:]
    if owned and old.strip():
        raise ProjectError("refus d’écraser un document généré non géré")
    if owned:
        return block + b"\n"
    separator = b"" if not old or old.endswith((b"\n", b"\r")) else b"\n"
    return old + separator + block + b"\n"


def _agent_payload(snapshots: dict[str, bytes | None]) -> bytes:
    lines = [
        "## cstack",
        "",
        "Les consignes cstack restent inactives pendant les tâches ordinaires.",
        "",
        "Quand l’utilisateur invoque explicitement une skill `$cstack:*` :",
        "",
        "1. Lire [docs/agents/cstack.md](docs/agents/cstack.md) pour la durée de cette tâche cstack.",
    ]
    if snapshots.get("CLAUDE.md") and snapshots["CLAUDE.md"].strip():
        lines.append("2. Lire [CLAUDE.md](CLAUDE.md) pour les conventions partagées qui s’appliquent, seulement pendant cette tâche cstack.")
    lines += ["", "Sans invocation cstack explicite, ne pas charger ni appliquer ces fichiers comme instructions. Une demande utilisateur peut toujours demander de les lire ou de les modifier comme fichiers ordinaires."]
    return ("\n".join(lines) + "\n").encode()


def _workflow_payload(tracker: dict[str, str]) -> bytes:
    rows = ["# Guide projet cstack", "", "Charger et appliquer ce fichier seulement quand l’utilisateur invoque explicitement `$cstack:*`.", "", "## Flux de travail", "", "`$cstack:cstack` possède la préparation automatique et le routage d’exécution; utiliser les commandes ci-dessous pour une demande de préparation ciblée.", "", "| Flux de travail | Invocation | Règle de nombre d’agents | Clés de rôles réutilisées |", "| --- | --- | --- | --- |"]
    for name, value in WORKFLOWS.items():
        rows.append(f"| `{name}` | `$cstack:{name}` | {value['count_rule']} | {', '.join(f'`{role}`' for role in value['roles'])} |")
    rows += ["", "## Enregistrements de domaine", "", "Utiliser le CONTEXT.md existant du projet et les conventions ADR quand ils existent. La configuration ne crée pas de CONTEXT.md ou de fichiers ADR vides.", "", "## État local", "", "Utiliser `.cstack/horizon` pour l’état Horizon. Garder `.cstack/models.json` comme source des choix de modèles et d’effort de raisonnement. La configuration n’effectue aucune configuration globale, aucun envoi distant (`push`), aucune étiquette et aucune action distante.", "", "## Limite des rôles", "", "Utiliser `hardest tasks` seulement pour l’architecture complexe explicite. La synthèse Horizon utilise `judgment and prose`.", "", "## Mode de suivi", "", f"Le mode de suivi configuré est `{tracker['mode']}`."]
    if tracker["mode"] == "github":
        rows.append(f"Référence distante: `https://github.com/{tracker['owner']}/{tracker['repo']}`. cstack n’effectue aucune action distante pendant la configuration.")
    return ("\n".join(rows) + "\n").encode()


def _tracker_payload(tracker: dict[str, str]) -> bytes:
    rows = ["# Suivi des tickets", "", f"Mode de suivi: `{tracker['mode']}`."]
    if tracker["mode"] == "local":
        rows += [
            "Utiliser `.cstack/horizon/<slug>/map.md` pour la carte, `.cstack/horizon/<slug>/tickets/<id>-<slug>.md` pour les tickets et `.cstack/horizon/<slug>/research/<id>.md` pour la recherche.",
            "Utiliser les statuts `ready`, `claimed`, `waiting`, `resolved` et `out-of-scope`. Garder `owner` stable, utiliser des IDs valides dans `blocked_by` et rendre un ticket éligible seulement quand ses dépendances sont `resolved`.",
            "Garder un seul rédacteur parent. Les artefacts enfants restent dans leurs propres fichiers. Enregistrer la réponse avant de mettre un ticket à `resolved`, puis ajouter le résumé de carte.",
            "Voir les modèles de documents `$cstack:horizon` pour les formes d’enregistrement détaillées. La configuration ne crée aucune étiquette ni aucun état distant.",
        ]
    elif tracker["mode"] == "github":
        rows += [
            f"Utiliser seulement le dépôt sélectionné `https://github.com/{tracker['owner']}/{tracker['repo']}`.",
            "Avant le travail, découvrir le schéma réel du `gh` authentifié ou du connecteur natif. Mapper la carte Horizon vers une issue parente et des issues enfants.",
            "Utiliser les liens de blocage natifs quand ils existent. Sinon mettre `Blocked by` dans le corps de l’issue. Garder les attributions sur un responsable stable. Enregistrer la réponse dans un commentaire et fermer seulement avec autorisation explicite. La configuration n’effectue aucune action API.",
        ]
    else:
        rows.append("Utiliser la documentation de suivi existante. La configuration ne crée pas de fichier de suivi vide.")
    return ("\n".join(rows) + "\n").encode()


def _models_content(old: bytes | None, choices: dict[str, Any], models: Any) -> bytes:
    if old is not None and not choices:
        return old
    try:
        config = {} if old is None else json.loads(old)
        models.validate(config)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ProjectError(f"models.json existant invalide: {error}") from error
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
        raise ProjectError(f"le fichier généré n’est pas en UTF-8: {relative}") from error
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


def _plan(workspace: Path, raw_options: Any, catalog: dict[str, Any] | None) -> dict[str, Any]:
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
        raise ProjectError("le plan contient des champs inconnus ou manquants")
    body = dict(plan)
    fingerprint = body.pop("plan_sha256")
    if not isinstance(fingerprint, str) or _sha(_canonical(body)) != fingerprint:
        raise ProjectError("l’empreinte du plan ne correspond pas à son contenu")
    paths: set[str] = set()
    for entry in plan["files"]:
        fields = {"action", "current_sha256", "new_content", "new_sha256", "original_content_b64", "path"}
        if not isinstance(entry, dict) or set(entry) != fields or entry["path"] in paths:
            raise ProjectError("une entrée de fichier du plan est invalide ou répétée")
        paths.add(entry["path"])
        if entry["path"] not in TARGET_PATHS or entry["action"] not in {"create", "update", "unchanged"}:
            raise ProjectError(f"chemin ou action de plan invalide: {entry['path']}")
        old = _unb64(entry["original_content_b64"])
        if entry["current_sha256"] != (None if old is None else _sha(old)) or not isinstance(entry["new_content"], str):
            raise ProjectError(f"ancien instantané du plan invalide: {entry['path']}")
        if entry["new_sha256"] != _sha(entry["new_content"].encode()):
            raise ProjectError(f"hash du nouveau contenu du plan invalide: {entry['path']}")
    _snapshots(plan["observed"])
    return plan


def _compare(expected: dict[str, Any], supplied: dict[str, Any]) -> None:
    left, right = dict(expected), dict(supplied)
    left.pop("plan_sha256", None)
    right.pop("plan_sha256", None)
    if left != right:
        raise ProjectError("le plan accepté ne correspond pas aux options et instantanés recalculés")


def _check_state(workspace: Path, plan: dict[str, Any]) -> None:
    observed, planned = _snapshots(plan["observed"]), {entry["path"]: entry for entry in plan["files"]}
    for relative, old in observed.items():
        current = _read(workspace, relative)
        current_hash, old_hash = None if current is None else _sha(current), None if old is None else _sha(old)
        if relative in planned:
            if current_hash not in {old_hash, planned[relative]["new_sha256"]}:
                raise ProjectError(f"fichier modifié depuis la prévisualisation: {relative}")
        elif current_hash != old_hash:
            raise ProjectError(f"fichier projet observé modifié depuis la prévisualisation: {relative}")
    for entry in plan["files"]:
        current = _read(workspace, entry["path"])
        if (None if current is None else _sha(current)) not in {entry["current_sha256"], entry["new_sha256"]}:
            raise ProjectError(f"fichier modifié depuis la prévisualisation: {entry['path']}")


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


def apply_plan(workspace: Path, supplied_plan: Any, raw_options: Any, catalog: dict[str, Any] | None, expected_plan_sha256: str | None = None) -> dict[str, Any]:
    workspace = _workspace(workspace)
    plan = _shape(supplied_plan)
    if expected_plan_sha256 is not None and expected_plan_sha256 != plan["plan_sha256"]:
        raise ProjectError("l’empreinte du plan accepté diffère de --expected-plan-sha256")
    models = _models()
    options = _options(raw_options, models, catalog)
    if options != plan["options"] or options["model_choices"] != plan["model_choices"]:
        raise ProjectError("les options d’application diffèrent de la prévisualisation acceptée")
    catalog_sha = None if catalog is None else _sha(_canonical(catalog))
    if plan["catalog_sha256"] != catalog_sha:
        raise ProjectError("le catalogue diffère de la prévisualisation acceptée")
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
            raise ProjectError(f"fichier modifié avant la préparation: {entry['path']}")
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
                raise ProjectError(f"fichier modifié pendant la préparation: {entry['path']}")
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
        raise ProjectError(f"impossible de lire le JSON {path}: {error}") from error


def _catalog(path: Path | None, raw_options: Any) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        return _models().read_catalog(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ProjectError(f"catalogue de modèles invalide: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser_class = _models().FrenchArgumentParser
    parser = parser_class(description=__doc__, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path)
    commands = parser.add_subparsers(dest="command", required=True, title="commandes", parser_class=parser_class)
    preview = commands.add_parser("preview", add_help=False)
    preview.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    preview.add_argument("--options", type=Path, required=True)
    apply = commands.add_parser("apply", add_help=False)
    apply.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
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
