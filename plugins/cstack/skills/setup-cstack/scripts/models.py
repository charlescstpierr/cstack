#!/usr/bin/env python3
"""Prévisualiser, enregistrer et résoudre les choix de modèles du projet; ne jamais lancer de modèle."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


# Les noms sont des recommandations de configuration, jamais des solutions de repli d’exécution automatiques.
GROUPS = {
    "exploration": ("gpt-5.6-luna", "max", [
        "how explorer", "how explainer", "why investigators", "why synthesizer"]),
    "simple changes": ("gpt-5.6-luna", "max", ["simple edits"]),
    "development": ("gpt-6-astra", "low", [
        "feature, refactoring", "perf-issue", "hillclimb",
        "swarm workers", "arena runners"]),
    "difficult debugging": ("gpt-6-astra", "medium", ["bug-fix"]),
    "code review": ("gpt-6-astra", "low", [
        "judgment and prose", "reflect tooling",
        "reflect judgment, divergent, synthesizer",
        "interrogate reviewers", "arena cross-judge pool"]),
    "complex architecture": ("gpt-6-astra", "xhigh", [
        "hardest tasks", "architect runners"]),
    "documentation": ("gpt-5.6-luna", "max", ["documentation"]),
}
PANELS = {"arena runners": 3, "arena cross-judge pool": 1,
          "architect runners": 3, "interrogate reviewers": 3}
ROLES = {role for _, _, roles in GROUPS.values() for role in roles}
LEGACY_FALLBACKS = {"simple edits": "feature, refactoring",
                    "documentation": "judgment and prose"}
RUNTIMES = {"codex-cli", "claude-code", "cursor-agent", "grok"}
CODEX_NATIVE = "codex-native"


class FrenchArgumentParser(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace("usage:", "utilisation:", 1)

    def format_help(self):
        return (super().format_help().replace("usage:", "utilisation:", 1)
                .replace("\npositional arguments:\n", "\narguments positionnels:\n"))

    @staticmethod
    def french_error(message):
        argument = re.fullmatch(r"argument (.+?): (.+)", message)
        if argument:
            return f"argument {argument[1]}: {FrenchArgumentParser.french_error(argument[2])}"
        for english, french in (
            (r"the following arguments are required: (.+)", "arguments requis: {}"),
            (r"unrecognized arguments: (.+)", "arguments non reconnus: {}"),
            (r"invalid choice: (.+) \(choose from (.+)\)", "choix invalide: {} (choisir parmi {})"),
            (r"ignored explicit argument (.+)", "argument explicite ignoré {}"),
            (r"ambiguous option: (.+) could match (.+)", "option ambiguë: {} peut correspondre à {}"),
        ):
            match = re.fullmatch(english, message, re.DOTALL)
            if match:
                return french.format(*match.groups())
        return "un argument attendu" if message == "expected one argument" else message

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: erreur: {self.french_error(message)}\n")


def ensure_cstack_gitignore(directory):
    if directory.name != ".cstack":
        return
    ignore = directory / ".gitignore"
    if ignore.exists() or ignore.is_symlink():
        return
    ignore.write_text("*\n")


def selections(role, value):
    if role in PANELS:
        minimum = 2 if role == "architect runners" else 1
        if not isinstance(value, list) or len(value) < minimum:
            raise ValueError(f"{role}: panneau attendu avec au moins {minimum} entrées")
        return value
    return [value]


def selection(value):
    if value == "inherit-parent":
        return {}
    if isinstance(value, str) and value.strip() == value and value:
        return {"model": value}
    if isinstance(value, dict) and set(value) == {"model", "reasoning_effort"}:
        model, effort = value["model"], value["reasoning_effort"]
        if (isinstance(model, str) and model and model.strip() == model
                and model != "inherit-parent" and isinstance(effort, str)
                and effort and effort.strip() == effort):
            return dict(value)
    if isinstance(value, dict) and set(value) in (
        {"runtime"}, {"runtime", "model"}, {"runtime", "model", "reasoning_effort"}
    ):
        runtime = value["runtime"]
        if not isinstance(runtime, str) or runtime not in RUNTIMES:
            raise ValueError(f"runtime attendu parmi {', '.join(sorted(RUNTIMES))}")
        if "model" not in value:
            return {"runtime": runtime}
        model = value["model"]
        if not (isinstance(model, str) and model and model.strip() == model
                and model != "inherit-parent"):
            raise ValueError("model explicite attendu pour un runtime externe")
        if "reasoning_effort" not in value:
            return {"runtime": runtime, "model": model}
        effort = value["reasoning_effort"]
        if not (isinstance(effort, str) and effort and effort.strip() == effort):
            raise ValueError("reasoning_effort non vide attendu")
        return {"runtime": runtime, "model": model, "reasoning_effort": effort}
    if isinstance(value, dict) and "reasoning_effort" in value and "model" not in value:
        raise ValueError("reasoning_effort exige model explicite")
    raise ValueError("chaîne de modèle, inherit-parent, {model, reasoning_effort} ou {runtime, model?, reasoning_effort?} attendu")


def runtime_catalog(catalog, runtime):
    if catalog is None:
        return None
    if isinstance(catalog, dict) and "runtimes" in catalog:
        runtimes = catalog["runtimes"]
        if isinstance(runtimes, dict):
            return runtimes.get(runtime)
        return None
    if runtime == CODEX_NATIVE:
        return catalog
    return None


def validate(config, catalog=None, check_available=False):
    if not isinstance(config, dict):
        raise ValueError("models.json doit être un objet")
    for role, value in config.items():
        if role not in ROLES:
            raise ValueError(f"rôle inconnu: {role}")
        for entry in selections(role, value):
            try:
                chosen = selection(entry)
                if check_available and chosen and "model" in chosen:
                    runtime = chosen.get("runtime", CODEX_NATIVE)
                    scoped = runtime_catalog(catalog, runtime)
                    model = chosen["model"]
                    if scoped is None or model not in scoped:
                        raise ValueError(f"modèle indisponible ou non vérifié pour {runtime}: {model}")
                    effort = chosen.get("reasoning_effort")
                    if effort is not None and effort not in scoped[model]:
                        raise ValueError(f"effort de raisonnement non pris en charge: {runtime} / {model} / {effort}")
            except ValueError as error:
                raise ValueError(f"{role}: {error}") from error


def read_catalog(path):
    if path is None:
        return None
    data = json.loads(path.read_text())
    # Accepter la sortie codex debug models ou un mapping transcrit depuis le schéma actuel.
    if isinstance(data, dict) and "models" in data:
        data = {row["slug"]: [level["effort"] for level in row["supported_reasoning_levels"]]
                for row in data["models"] if row.get("visibility", "list") == "list"}
    if isinstance(data, dict) and set(data) == {"runtimes"}:
        runtimes = data["runtimes"]
        if (isinstance(runtimes, dict) and set(runtimes) <= {CODEX_NATIVE, *RUNTIMES}
                and all(isinstance(name, str) and isinstance(mapping, dict)
                        and all(isinstance(model, str) and isinstance(levels, list)
                                and all(isinstance(level, str) for level in levels)
                                for model, levels in mapping.items())
                        for name, mapping in runtimes.items())):
            return data
        raise ValueError("le catalogue runtimes doit mapper chaque runtime pris en charge vers ses modèles et efforts")
    if not isinstance(data, dict) or not all(
        isinstance(name, str) and isinstance(levels, list)
        and all(isinstance(level, str) for level in levels)
        for name, levels in data.items()
    ):
        raise ValueError("le catalogue doit mapper les noms de modèles vers les listes d’efforts pris en charge")
    return data


def read_config(path):
    raw = path.read_bytes() if path.exists() else b""
    config = json.loads(raw) if raw or path.exists() else {}
    validate(config)
    return config, hashlib.sha256(raw).hexdigest()


def preview(config, digest, catalog):
    recommendations = {}
    for group, (model, effort, roles) in GROUPS.items():
        chosen = {"model": model, "reasoning_effort": effort}
        values = {role: [dict(chosen) for _ in range(PANELS[role])]
                  if role in PANELS else dict(chosen) for role in roles}
        try:
            validate(values, catalog, check_available=True)
            problem = None
        except ValueError as error:
            problem = str(error)
        recommendations[group] = {"choices": values, "unavailable": problem}
    return {"recommendations": recommendations, "saved": config, "sha256": digest}


def resolve(config, role, catalog):
    if role not in ROLES:
        raise ValueError(f"rôle inconnu: {role}")
    default = ["inherit-parent"] * PANELS[role] if role in PANELS else "inherit-parent"
    value = config.get(role, config.get(LEGACY_FALLBACKS.get(role), default))
    validate({role: value}, catalog, check_available=True)
    return [selection(entry) for entry in selections(role, value)]


def apply_choices(path, choices, expected_digest, catalog):
    config, digest = read_config(path)
    if digest != expected_digest:
        raise ValueError("models.json a changé depuis la prévisualisation; le relire avant d’enregistrer")
    validate(choices, catalog, check_available=True)
    config.update(choices)
    validate(config)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("models.json ou son dossier est un lien symbolique; le préserver et utiliser un état projet régulier")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.name == ".cstack":
        ensure_cstack_gitignore(path.parent)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(config, output, indent=2, ensure_ascii=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        # Détecter les edits faits pendant la préparation du remplacement; la configuration a un seul rédacteur.
        if read_config(path)[1] != expected_digest:
            raise ValueError("models.json a changé pendant l’enregistrement; aucun remplacement écrit")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return read_config(path)[0]


def main():
    parser = FrenchArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path)
    commands = parser.add_subparsers(dest="command", required=True, title="commandes", parser_class=FrenchArgumentParser)
    show = commands.add_parser("show", add_help=False)
    show.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    resolver = commands.add_parser("resolve", add_help=False)
    resolver.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    resolver.add_argument("role", choices=sorted(ROLES))
    writer = commands.add_parser("apply", add_help=False)
    writer.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    writer.add_argument("--choices", type=Path, required=True)
    writer.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    path = args.workspace / ".cstack" / "models.json"
    try:
        catalog = read_catalog(args.catalog)
        config, digest = read_config(path)
        if args.command == "show":
            result = preview(config, digest, catalog)
        elif args.command == "resolve":
            result = resolve(config, args.role, catalog)
        else:
            result = apply_choices(path, json.loads(args.choices.read_text()),
                                   args.expected_sha256, catalog)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"modèles cstack: {error}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
