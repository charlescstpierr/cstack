#!/usr/bin/env python3
"""Prévisualiser, enregistrer et résoudre les choix de modèles du projet; ne jamais lancer de modèle."""

import argparse
from datetime import datetime, timezone
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
# Panels de jugement mixtes proposés quand Claude Code est présent et connecté ; toujours un choix explicite.
# Trois entrées comme les panels par défaut : deux héritent du runtime natif, une passe par Claude Code.
MIXED_PANEL_ROLES = ("arena runners", "architect runners", "interrogate reviewers")
CODEX_NATIVE = "codex-native"


def mixed_panels():
    return {role: ["inherit-parent", {"runtime": "claude-code"}, "inherit-parent"] for role in MIXED_PANEL_ROLES}


def project_helper():
    """Charger project.py à la demande, pour les agents natifs gérés du projet."""
    import importlib.util
    path = Path(__file__).with_name("project.py")
    spec = importlib.util.spec_from_file_location("cstack_setup_project", path)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


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


def t3_identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[\x21-\x7e]+", value) is not None


def selection(value):
    if value == "inherit-parent":
        return {}
    if isinstance(value, str) and value.strip() == value and value:
        return {"model": value}
    if isinstance(value, dict) and value.get("runtime") == "t3":
        if (set(value) != {"runtime", "providerInstanceId", "model", "options"}
                or not all(t3_identifier(value.get(k))
                           and value[k] != "inherit-parent" for k in ("providerInstanceId", "model"))
                or not isinstance(value.get("options"), dict)
                or not all(t3_identifier(k) and type(v) in (str, bool)
                           for k, v in value["options"].items())):
            raise ValueError("t3 exige exactement runtime, providerInstanceId, model, options non secrets; clés CLI interdites")
        return dict(value)
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


def _t3_providers(catalog, host, context):
    """Validate coordinator-supplied evidence; this is consistency, not host attestation."""
    if host != "t3":
        raise ValueError("BLOCKED: sélection t3 hors hôte T3; aucun agent ou CLI de repli")
    if not isinstance(catalog, dict) or catalog.get("host") != "t3" or not isinstance(context, dict):
        raise ValueError("BLOCKED: preuve d’hôte non établie; catalogue et trace session requis")
    for key in ("environmentId", "sessionId", "capabilitiesSha256", "traceSha256"):
        if (not isinstance(context.get(key), str) or not context[key] or catalog.get(key) != context[key]
                or (key.endswith("Sha256") and re.fullmatch(r"[a-f0-9]{64}", context[key]) is None)):
            raise ValueError("BLOCKED: contexte catalogue/trace absent ou étranger: " + key)
    if context.get("revalidated") is not True:
        raise ValueError("BLOCKED: revalidation selon les règles T3 actives requise")
    try:
        if not all(isinstance(catalog.get(key), str) for key in ("observedAt", "expiresAt")):
            raise ValueError("dates ISO requises")
        observed = datetime.fromisoformat(catalog["observedAt"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(catalog["expiresAt"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if not observed <= now < expires:
            raise ValueError("catalogue périmé")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("BLOCKED: dates catalogue absentes ou périmées") from error
    body = {k: v for k, v in catalog.items() if k != "sha256"}
    if catalog.get("sha256") != hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest():
        raise ValueError("BLOCKED: empreinte catalogue différente")
    providers = catalog.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("BLOCKED: fournisseurs du catalogue non vérifiés")
    return providers


def _t3_options(model):
    declared = model.get("options")
    if not isinstance(declared, dict):
        raise ValueError("BLOCKED: options du modèle non vérifiées")
    types = {"string": str, "boolean": bool}
    for key, option in declared.items():
        if (not t3_identifier(key) or not isinstance(option, dict)
                or option.get("secret") is not False
                or not isinstance(option.get("type"), str) or option["type"] not in types
                or not isinstance(option.get("values"), list) or not option["values"]
                or any(type(value) is not types[option["type"]] for value in option["values"])
                or ("required" in option and type(option["required"]) is not bool)):
            raise ValueError("BLOCKED: déclaration d’option non vérifiée: " + str(key))
    return declared


def _t3_target(chosen, providers):
    provider = providers.get(chosen["providerInstanceId"])
    if not isinstance(provider, dict) or provider.get("available") is not True:
        raise ValueError("BLOCKED: providerInstanceId indisponible ou non vérifié")
    if type(provider.get("modelsComplete")) is not bool:
        raise ValueError("BLOCKED: complétude catalogue inconnue")
    models = provider.get("models")
    model = models.get(chosen["model"]) if isinstance(models, dict) else None
    if not isinstance(model, dict):
        raise ValueError("BLOCKED: modèle inconnu/non vérifié; absence d’une liste courte ne prouve pas son inexistence")
    declared = _t3_options(model)
    for key, value in chosen["options"].items():
        option = declared.get(key)
        if (option is None
                or not any(type(value) is type(v) and value == v for v in option["values"])):
            raise ValueError("BLOCKED: option non secrète, type ou valeur non vérifié: " + key)
    if any(opt.get("required") is True and key not in chosen["options"] for key, opt in declared.items() if isinstance(opt, dict)):
        raise ValueError("BLOCKED: option requise absente")
    return {k: chosen[k] for k in ("providerInstanceId", "model", "options")}


def t3_target(chosen, catalog, host="codex", context=None):
    return _t3_target(chosen, _t3_providers(catalog, host, context))


def t3_position(chosen, catalog, context):
    if chosen.get("runtime") in RUNTIMES:
        raise ValueError("BLOCKED: position CLI hors périmètre T3 V1; conserver Codex/CLI autonome ou convertir explicitement dans setup")
    if chosen.get("runtime") == "t3":
        return {"dispatch": "delegate_task", "target": t3_target(chosen, catalog, "t3", context)}
    if chosen:
        raise ValueError("BLOCKED: sélection native explicite non exprimable; aperçu de migration T3 requis")
    inherited = catalog.get("inheritance") if isinstance(catalog, dict) else None
    if not isinstance(inherited, dict) or set(inherited) != {"inheritedProviderInstanceId", "inheritedModel", "inheritedOptions"}:
        raise ValueError("BLOCKED: métadonnées inherited* absentes ou ambiguës")
    target = selection({"runtime": "t3", "providerInstanceId": inherited["inheritedProviderInstanceId"],
                        "model": inherited["inheritedModel"], "options": inherited["inheritedOptions"]})
    return {"dispatch": "delegate_task", "target": t3_target(target, catalog, "t3", context)}


def runtime_catalog(catalog, runtime):
    if catalog is None:
        return None
    if isinstance(catalog, dict) and catalog.get("host") == "t3":
        return None
    if isinstance(catalog, dict) and "runtimes" in catalog:
        runtimes = catalog["runtimes"]
        if isinstance(runtimes, dict):
            return runtimes.get(runtime)
        return None
    if runtime == CODEX_NATIVE:
        return catalog
    return None


def validate(config, catalog=None, check_available=False, host="codex", context=None):
    if not isinstance(config, dict):
        raise ValueError("models.json doit être un objet")
    for role, value in config.items():
        if role not in ROLES:
            raise ValueError(f"rôle inconnu: {role}")
        for entry in selections(role, value):
            try:
                chosen = selection(entry)
                if check_available and chosen.get("runtime") == "t3":
                    t3_target(chosen, catalog, host, context)
                    continue
                if check_available and host == "t3":
                    t3_position(chosen, catalog, context)
                    continue
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


def read_bounded_json(path, label):
    if path is None:
        return None
    with path.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError(label + " trop grand: maximum 1 MiB")
    return json.loads(raw)


def read_catalog(path):
    data = read_bounded_json(path, "catalogue")
    if path is None:
        return None
    if isinstance(data, dict) and data.get("host") == "t3":
        return data
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


def preview(config, digest, catalog, claude_ready=False, host="codex", context=None):
    if host == "t3":
        supported, unavailable = {}, {}
        try:
            providers = _t3_providers(catalog, host, context)
        except ValueError as error:
            providers = {}
            unavailable["catalog"] = str(error)
        if isinstance(providers, dict):
            for provider_id, provider in providers.items():
                models = provider.get("models", {}) if isinstance(provider, dict) else {}
                if not isinstance(models, dict):
                    continue
                for model_id, model in models.items():
                    label = f"{provider_id}/{model_id}"
                    try:
                        if not isinstance(model, dict):
                            raise ValueError("BLOCKED: modèle non vérifié")
                        options = _t3_options(model)
                        probe = {"runtime": "t3", "providerInstanceId": provider_id, "model": model_id,
                                 "options": {k: o["values"][0] for k, o in options.items()}}
                        _t3_target(selection(probe), providers)
                        supported.setdefault(provider_id, {})[model_id] = {
                            key: {k: v for k, v in option.items() if k in ("type", "values", "secret", "required")}
                            for key, option in options.items()}
                    except ValueError as error:
                        unavailable[label] = str(error)
        return {"saved": config, "sha256": digest, "recommendations": {},
                "supported": supported, "unavailable": unavailable,
                "inheritance": catalog.get("inheritance") if isinstance(catalog, dict) else None,
                "warning": "Entrée t3: TOUT le fichier illisible aux anciennes versions; rôle bloqué hors T3; providerInstanceId non portable. Aperçu seulement, sélection explicite requise.",
                "preflight": preflight(config, list(config) or ["how explorer"], catalog, host, context)}
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
    if claude_ready:
        recommendations["mixed review panels"] = {"choices": mixed_panels(), "unavailable": None}
    return {"recommendations": recommendations, "saved": config, "sha256": digest}


def role_value(config, role):
    default = ["inherit-parent"] * PANELS[role] if role in PANELS else "inherit-parent"
    value = config.get(role, config.get(LEGACY_FALLBACKS.get(role), default))
    return value


def resolve(config, role, catalog, host="codex", context=None):
    if role not in ROLES:
        raise ValueError(f"rôle inconnu: {role}")
    validate(config)
    value = role_value(config, role)
    validate({role: value}, catalog, check_available=True, host=host, context=context)
    if host == "t3":
        return [t3_position(selection(entry), catalog, context) for entry in selections(role, value)]
    return [selection(entry) for entry in selections(role, value)]


def preflight(config, roles, catalog, host="codex", context=None):
    validate(config)
    if not roles or any(role not in ROLES for role in roles):
        raise ValueError("le contrôle préalable exige des rôles connus")
    entries = {}
    for role in dict.fromkeys(roles):
        entries[role] = [selection(entry) for entry in selections(role, role_value(config, role))]
    if host == "t3" or any(chosen.get("runtime") == "t3" for panel in entries.values() for chosen in panel):
        positions, resolved, errors = {}, {}, {}
        for role, panel in entries.items():
            rows = []
            for index, chosen in enumerate(panel):
                try:
                    if host == "t3":
                        result = t3_position(chosen, catalog, context)
                    else:
                        if chosen.get("runtime") == "t3":
                            t3_target(chosen, catalog, host, context)
                        elif chosen and "model" in chosen:
                            scoped = runtime_catalog(catalog, chosen.get("runtime", CODEX_NATIVE))
                            if scoped is None or chosen["model"] not in scoped or ("reasoning_effort" in chosen and chosen["reasoning_effort"] not in scoped[chosen["model"]]):
                                raise ValueError("BLOCKED: modèle ou effort indisponible/non vérifié")
                        result = {"selection": chosen}
                    rows.append({"position": index, "status": "ready", **result})
                except ValueError as error:
                    rows.append({"position": index, "status": "blocked", "error": str(error)})
            positions[role] = rows
            if all(row["status"] == "ready" for row in rows):
                resolved[role] = ([{key: value for key, value in row.items()
                                   if key not in ("position", "status")} for row in rows]
                                  if host == "t3" else [row["selection"] for row in rows])
            else:
                errors[role] = "; ".join(row["error"] for row in rows if row["status"] == "blocked")
        return {"status": "blocked" if errors else "ready", "resolved": resolved, "errors": errors, "positions": positions}
    resolved, errors = {}, {}
    for role in dict.fromkeys(roles):
        try:
            resolved[role] = resolve(config, role, catalog)
        except ValueError as error:
            errors[role] = str(error)
    return {"status": "blocked" if errors else "ready", "resolved": resolved, "errors": errors}


def apply_choices(path, choices, expected_digest, catalog, host="codex", context=None):
    config, digest = read_config(path)
    if digest != expected_digest:
        raise ValueError("models.json a changé depuis la prévisualisation; le relire avant d’enregistrer")
    validate(choices, catalog, check_available=True, host=host, context=context)
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
    parser.add_argument("--host", choices=("codex", "t3"), default="codex")
    parser.add_argument("--host-context", type=Path)
    commands = parser.add_subparsers(dest="command", required=True, title="commandes", parser_class=FrenchArgumentParser)
    show = commands.add_parser("show", add_help=False)
    show.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    show.add_argument("--claude-ready", action="store_true",
                      help="Claude Code est détecté et connecté : proposer aussi les panels mixtes")
    resolver = commands.add_parser("resolve", add_help=False)
    resolver.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    resolver.add_argument("role", choices=sorted(ROLES))
    checker = commands.add_parser("preflight", add_help=False)
    checker.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    checker.add_argument("roles", nargs="+", choices=sorted(ROLES),
                         help="rôles nécessaires au workflow, vérifiés sans écriture ni génération")
    writer = commands.add_parser("apply", add_help=False)
    writer.add_argument("-h", "--help", action="help", help="afficher ce message d’aide et quitter")
    writer.add_argument("--choices", type=Path, required=True)
    writer.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    path = args.workspace / ".cstack" / "models.json"
    has_agents = (args.workspace / ".codex" / "agents").is_dir()
    try:
        catalog = read_catalog(args.catalog)
        context = read_bounded_json(args.host_context, "contexte")
        config, digest = read_config(path)
        if args.command == "show":
            result = preview(config, digest, catalog, args.claude_ready, args.host, context)
            # Les agents natifs gérés suivent models.json : l’aperçu dit lesquels seront alignés.
            result["managed_agents"] = project_helper().managed_agents(args.workspace) if has_agents else []
        elif args.command == "resolve":
            result = resolve(config, args.role, catalog, args.host, context)
        elif args.command == "preflight":
            result = preflight(config, args.roles, catalog, args.host, context)
        else:
            result = project_helper().apply_model_choices(args.workspace, json.loads(args.choices.read_text()),
                                                          args.expected_sha256, catalog, args.host, context)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"modèles cstack: {error}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if args.command == "preflight" and result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
