#!/usr/bin/env python3
"""Preview, save and resolve project model choices; never launch a model."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


# Names are setup recommendations, never automatic runtime fallbacks.
GROUPS = {
    "exploration": ("gpt-5.6-luna", "max", [
        "how explorer", "how explainer", "why investigators", "why synthesizer"]),
    "simple changes": ("gpt-5.6-luna", "max", ["simple edits"]),
    "development": ("gpt-6-astra", "low", [
        "feature, refactoring", "bug-fix", "perf-issue", "hillclimb",
        "swarm workers", "arena runners"]),
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
            raise ValueError(f"{role}: expected a panel with at least {minimum} entries")
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
    raise ValueError("expected a model string, inherit-parent, or {model, reasoning_effort}")


def validate(config, catalog=None, check_available=False):
    if not isinstance(config, dict):
        raise ValueError("models.json must be an object")
    for role, value in config.items():
        if role not in ROLES:
            raise ValueError(f"unknown role: {role}")
        for entry in selections(role, value):
            try:
                chosen = selection(entry)
                if check_available and chosen:
                    model = chosen["model"]
                    if catalog is None or model not in catalog:
                        raise ValueError(f"model unavailable or unverified: {model}")
                    effort = chosen.get("reasoning_effort")
                    if effort is not None and effort not in catalog[model]:
                        raise ValueError(f"unsupported reasoning effort: {model} / {effort}")
            except ValueError as error:
                raise ValueError(f"{role}: {error}") from error


def read_catalog(path):
    if path is None:
        return None
    data = json.loads(path.read_text())
    # Accept codex debug models output or a mapping transcribed from the live schema.
    if isinstance(data, dict) and "models" in data:
        data = {row["slug"]: [level["effort"] for level in row["supported_reasoning_levels"]]
                for row in data["models"] if row.get("visibility", "list") == "list"}
    if not isinstance(data, dict) or not all(
        isinstance(name, str) and isinstance(levels, list)
        and all(isinstance(level, str) for level in levels)
        for name, levels in data.items()
    ):
        raise ValueError("catalog must map model names to supported effort lists")
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
    return {"saved": config, "sha256": digest, "recommendations": recommendations}


def resolve(config, role, catalog):
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    default = ["inherit-parent"] * PANELS[role] if role in PANELS else "inherit-parent"
    value = config.get(role, config.get(LEGACY_FALLBACKS.get(role), default))
    validate({role: value}, catalog, check_available=True)
    return [selection(entry) for entry in selections(role, value)]


def apply_choices(path, choices, expected_digest, catalog):
    config, digest = read_config(path)
    if digest != expected_digest:
        raise ValueError("models.json changed since preview; read it again before saving")
    validate(choices, catalog, check_available=True)
    config.update(choices)
    validate(config)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("models.json or its directory is a symlink; preserve it and use regular project state")
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
        # Catch edits made while preparing the replacement; setup has one writer.
        if read_config(path)[1] != expected_digest:
            raise ValueError("models.json changed while saving; no replacement written")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return read_config(path)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("show")
    resolver = commands.add_parser("resolve")
    resolver.add_argument("role", choices=sorted(ROLES))
    writer = commands.add_parser("apply")
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
        parser.exit(2, f"cstack models: {error}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
