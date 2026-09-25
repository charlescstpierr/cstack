#!/usr/bin/env python3
"""Compare Codex seul, cstack et pstack sur des correctifs open source réels, notés par des tests cachés."""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import random
import re
import shutil
import statistics
import stat
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = Path(__file__).resolve().parent / "verify-behavior.py"
DEFAULT_TASKS = ROOT / "evals" / "outcome"
DEFAULT_PLUGIN = ROOT / "plugins" / "cstack"
ARMS = ("vanilla", "cstack", "pstack")
DEFAULT_ARMS = ("vanilla", "cstack")
MODELS_HELPER = ROOT / "plugins" / "cstack" / "skills" / "setup-cstack" / "scripts" / "models.py"
NETWORK_FLAG = ["-c", "sandbox_workspace_write.network_access=true"]
CLI_RUNTIMES = ("codex-cli", "claude-code", "cursor-agent", "grok")
# Signaux d’une récupération possible du correctif amont pendant un run avec réseau.
LEAK_COMMAND = re.compile(r"\bgit\s+(?:fetch|clone|pull|ls-remote)\b|\b(?:curl|wget)\b[^\n]*github", re.IGNORECASE)
UPSTREAM_INVENTORY = ROOT / "UPSTREAM.json"
# Point d’entrée de chaque paquet évalué. pstack reste la source amont épinglée, non traduite.
ARM_SKILLS = {"cstack": "cstack", "pstack": "poteto-mode"}
PSTACK_PREAMBLE = "Use poteto mode for this task. Delegate independent work to native subagents in parallel."
KINDS = {"bug", "regression", "feature", "refactor"}
SHA = re.compile(r"^[0-9a-f]{40}$")
# Les consignes restent celles d’un ticket : aucun libellé ne signale une mesure.
FORBIDDEN_PROMPT_LABELS = re.compile(r"\b(?:benchmark|eval(?:uation)?|judge|hidden tests?|tests? cachés?)\b", re.IGNORECASE)
SCOPE_NOTE = "Travaille uniquement dans ce dépôt local. Ne crée ni commit, ni push, ni PR."
SOURCE_NOTE = "La version source n’est pas installée. Lis directement ce fichier de compétence avant d’agir : {path}"
EXCLUDED_FROM_DIFF = (".cstack",)
# Le fichier info/exclude des checkouts ignore déjà .cstack ; la pathspec couvre aussi un `git add -f`.
DIFF_PATHSPEC = ("--", ".", *(f":(exclude){name}" for name in EXCLUDED_FROM_DIFF))


class BenchError(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Le runner natif fournit aussi les primitives partagées : identifiants sûrs, empreintes d’arbre, recherche de clés.
RUNNER = load_module("verify_behavior", RUNNER_PATH)
SAFE_ID = RUNNER.SAFE_ID


def load_runner():
    return RUNNER


def parse_arms(text: str) -> list[dict[str, Any]]:
    """Lit `nom` ou `nom=base[:models.json]` ; seule une base cstack accepte une config de modèles."""
    arms = []
    for item in (part.strip() for part in text.split(",")):
        if not item:
            continue
        name, _, spec = item.partition("=")
        base, _, models = (spec or name).partition(":")
        if not SAFE_ID.fullmatch(name) or base not in ARMS:
            raise BenchError(f"bras invalide: {item!r} ; base parmi {', '.join(ARMS)}")
        if models and base != "cstack":
            raise BenchError(f"{name}: seule une base cstack lit .cstack/models.json")
        arms.append({"name": name, "base": base, "models": Path(models) if models else None})
    names = [arm["name"] for arm in arms]
    if len(arms) < 2 or len(set(names)) != len(names):
        raise BenchError("--arms exige au moins deux bras de noms distincts")
    return arms


def load_arm_models(arms: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    helper = load_module("cstack_models", MODELS_HELPER)
    configs = {}
    for arm in arms:
        if arm["models"] is None:
            continue
        path = arm["models"].expanduser().resolve()
        try:
            config, _ = helper.read_config(path)
        except (OSError, ValueError) as error:
            raise BenchError(f"{arm['name']}: config de modèles invalide {path}: {error}") from error
        if not config:
            raise BenchError(f"{arm['name']}: config de modèles vide ou absente {path}")
        configs[arm["name"]] = config
    return configs


def private_paths(work: Path, output: Path) -> list[Path]:
    """Chemins que l’agent ne doit pas lire : miroirs et reçus, patches, état et résultats des autres runs."""
    return [work, output / "patches", output / "state", output / "results.jsonl"]


def possible_leak(task: dict[str, Any], commands: list[str], private: list[Path] = ()) -> bool:
    """Signale un run qui a pu lire le correctif : dépôt distant, miroir de notation ou autres runs."""
    markers = [task["repo"].split("://", 1)[1].removesuffix(".git").lower(), task["fix_sha"], task["fix_sha"][:12]]
    markers += [str(path).lower() for path in private]
    return any(LEAK_COMMAND.search(command) or any(marker in command.lower() for marker in markers)
               for command in commands)


class hidden_from_agent:
    """Retire la lecture des miroirs et des autres runs pendant le tour de l’agent (sans effet sous root)."""

    def __init__(self, paths: list[Path]):
        self.paths = [path for path in paths if path.exists()]
        self.modes: dict[Path, int] = {}

    def __enter__(self):
        for path in self.paths:
            self.modes[path] = stat.S_IMODE(path.stat().st_mode)
            path.chmod(0)
        return self

    def __exit__(self, *_):
        for path, mode in self.modes.items():
            path.chmod(mode)
        return False


def threads(agent: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Métadonnées du fil parent (une par tour) puis des enfants natifs, telles que les relève le runner."""
    seen = [("parent", item) for item in agent.get("after_turn_actual_metadata", []) if isinstance(item, dict)]
    return seen + [("child", item) for item in agent.get("child_metadata", []) if isinstance(item, dict)]


def observed_settings(agent: dict[str, Any], model: str | None, effort: str | None) -> dict[str, Any]:
    """Compare le modèle et l’effort réellement exposés par l’hôte à ceux du manifeste."""
    rows = [{"thread": kind, "model": item.get("model"), "reasoning_effort": item.get("reasoning_effort")}
            for kind, item in threads(agent)]
    mismatch = any(
        (model and row["model"] and row["model"] != model)
        or (effort and row["reasoning_effort"] and row["reasoning_effort"] != effort)
        for row in rows
    )
    observed = bool(rows) and all(row["model"] for row in rows)
    return {"observed_settings": rows, "settings_observed": observed, "settings_mismatch": mismatch}


def git(cwd: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise BenchError(f"git {' '.join(args)} a échoué dans {cwd}: {result.stderr.strip()}")
    return result.stdout


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    return RUNNER.tree_hash(root, None)["sha256"]


def parse_time(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise BenchError(f"{label}: date ISO 8601 invalide: {value!r}") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BenchError(f"impossible de lire le JSON: {path}") from error


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_commands(task_id: str, key: str, value: Any, required: bool) -> None:
    if not isinstance(value, list) or (required and not value):
        raise BenchError(f"{task_id}: {key} doit être une liste{' non vide' if required else ''}")
    seen = set()
    for row in value:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("command"), str):
            raise BenchError(f"{task_id}: chaque entrée de {key} exige id et command textuels")
        if row["id"] in seen:
            raise BenchError(f"{task_id}: identifiant dupliqué dans {key}: {row['id']}")
        seen.add(row["id"])


def load_task(directory: Path, merged_after: datetime) -> dict[str, Any]:
    task = read_json(directory / "task.json")
    if not isinstance(task, dict):
        raise BenchError(f"{directory}: task.json doit être un objet")
    task_id = task.get("id")
    if not isinstance(task_id, str) or not SAFE_ID.fullmatch(task_id) or task_id != directory.name:
        raise BenchError(f"{directory}: id doit être sûr et égal au nom du dossier")
    for key in ("repo", "source", "language", "prompt"):
        if not isinstance(task.get(key), str) or not task[key].strip():
            raise BenchError(f"{task_id}: {key} doit être une chaîne non vide")
    if not task["repo"].startswith(("https://", "file://")):
        raise BenchError(f"{task_id}: repo doit être une URL https ou file")
    for key in ("base_sha", "fix_sha"):
        if not isinstance(task.get(key), str) or not SHA.fullmatch(task[key]):
            raise BenchError(f"{task_id}: {key} doit être un SHA complet en minuscules")
    if task.get("kind") not in KINDS:
        raise BenchError(f"{task_id}: kind doit être parmi {sorted(KINDS)}")
    if parse_time(task.get("merged_at", ""), f"{task_id}.merged_at") < merged_after:
        raise BenchError(f"{task_id}: correctif fusionné avant la date plancher de la suite")
    if FORBIDDEN_PROMPT_LABELS.search(task["prompt"]):
        raise BenchError(f"{task_id}: la consigne contient un libellé de mesure")
    hidden = task.get("hidden_paths")
    if not isinstance(hidden, list) or not hidden or not all(isinstance(path, str) and path for path in hidden):
        raise BenchError(f"{task_id}: hidden_paths doit être une liste non vide de chemins")
    for path in hidden:
        if path.startswith("/") or ".." in Path(path).parts:
            raise BenchError(f"{task_id}: chemin caché hors du dépôt: {path}")
    task.setdefault("pass_to_pass", [])
    check_commands(task_id, "fail_to_pass", task.get("fail_to_pass"), True)
    check_commands(task_id, "pass_to_pass", task["pass_to_pass"], False)
    timeout = task.get("test_timeout", 600)
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
        raise BenchError(f"{task_id}: test_timeout doit être compris entre 0 et 3600 secondes")
    if not (directory / "Dockerfile").is_file():
        raise BenchError(f"{task_id}: Dockerfile absent")
    task["test_timeout"] = timeout
    task["dir"] = directory
    task["digest"] = tree_digest(directory)
    return task


def load_suite(root: Path, wanted: list[str] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suite = read_json(root / "suite.json")
    if not isinstance(suite, dict) or not isinstance(suite.get("tasks"), list) or not suite["tasks"]:
        raise BenchError("suite.json doit contenir une liste tasks non vide")
    merged_after = parse_time(suite.get("merged_after", ""), "suite.merged_after")
    ids = suite["tasks"]
    if len(set(ids)) != len(ids):
        raise BenchError("suite.json contient des tâches dupliquées")
    if wanted:
        unknown = set(wanted) - set(ids)
        if unknown:
            raise BenchError(f"tâche inconnue: {', '.join(sorted(unknown))}")
        ids = [task_id for task_id in ids if task_id in wanted]
    return suite, [load_task(root / "tasks" / task_id, merged_after) for task_id in ids]


def mirror(task: dict[str, Any], work: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", task["repo"].split("://", 1)[1])
    path = work / "mirrors" / f"{slug}.git"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        git(path.parent, "clone", "--mirror", "--quiet", task["repo"], str(path))
    for sha in (task["base_sha"], task["fix_sha"]):
        if git(path, "cat-file", "-t", sha, check=False).strip() != "commit":
            git(path, "fetch", "--quiet", "origin", sha)
    if subprocess.run(["git", "merge-base", "--is-ancestor", task["base_sha"], task["fix_sha"]], cwd=path).returncode:
        raise BenchError(f"{task['id']}: base_sha n’est pas un ancêtre de fix_sha")
    return path


def checkout(mirror_path: Path, sha: str, destination: Path, history: bool) -> Path:
    """Crée un checkout ; avec history, seul l’historique de sha est copié, jamais le correctif."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if history:
        branch = f"outcome-{sha[:12]}"
        git(mirror_path, "branch", "--force", branch, sha)
        git(destination.parent, "clone", "--quiet", "--no-tags", "--single-branch", "--branch", branch,
            mirror_path.resolve().as_uri(), str(destination))
        git(destination, "remote", "remove", "origin")
        git(destination, "branch", "-m", branch, "main")
    else:
        git(destination.parent, "clone", "--quiet", "--no-checkout", str(mirror_path), str(destination))
        git(destination, "checkout", "--quiet", "--detach", sha)
    exclude = destination / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as stream:
        stream.write("".join(f"/{name}/\n" for name in EXCLUDED_FROM_DIFF))
    return destination


def image_tag(task: dict[str, Any]) -> str:
    return f"cstack-outcome/{task['id'].lower()}:{task['digest'][:12]}"


def build_image(task: dict[str, Any]) -> str:
    tag = image_tag(task)
    if subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode != 0:
        result = subprocess.run(["docker", "build", "--quiet", "-t", tag, str(task["dir"])], capture_output=True, text=True)
        if result.returncode != 0:
            raise BenchError(f"{task['id']}: construction de l’image impossible: {result.stderr.strip()[-2000:]}")
    return tag


def image_id(reference: str) -> str:
    """Identité immuable d’une image ; un tag peut être reconstruit entre validate et run."""
    result = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", reference],
                            capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise BenchError(f"image introuvable: {reference}")
    return result.stdout.strip()


def docker_run(image: str, workdir: Path, *command: str) -> list[str]:
    return ["docker", "run", "--rm", "--network", "none", "-v", f"{workdir.resolve()}:/work", "-w", "/work",
            image, *command]


def release_workdir(image: str, workdir: Path) -> None:
    """Rend /work à l’utilisateur hôte après les tests, pour que le nettoyage reste possible hors root."""
    if os.getuid() != 0:
        subprocess.run(docker_run(image, workdir, "chown", "-R", f"{os.getuid()}:{os.getgid()}", "/work"),
                       capture_output=True)


def run_test(image: str, workdir: Path, command: str, timeout: float) -> dict[str, Any]:
    argv = docker_run(image, workdir, "sh", "-c", command)
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"passed": False, "exit_code": None, "timed_out": True, "tail": ""}
    if result.returncode == 125:
        # Docker réserve 125 à ses propres échecs : ce n’est pas un test rouge.
        raise BenchError(f"docker run a échoué avant le test: {result.stderr.strip()[-1000:]}")
    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "timed_out": False,
        "tail": (result.stdout + result.stderr)[-4000:],
    }


def run_tests(task: dict[str, Any], image: str, workdir: Path) -> dict[str, dict[str, Any]]:
    results = {}
    try:
        for key in ("fail_to_pass", "pass_to_pass"):
            for row in task[key]:
                results[f"{key}:{row['id']}"] = run_test(image, workdir, row["command"], task["test_timeout"])
    finally:
        release_workdir(image, workdir)
    return results


def overlay_hidden(task: dict[str, Any], workdir: Path) -> None:
    git(workdir, "checkout", "--quiet", task["fix_sha"], "--", *task["hidden_paths"])


def all_pass(results: dict[str, dict[str, Any]], prefix: str) -> bool:
    return all(value["passed"] for key, value in results.items() if key.startswith(prefix))


def validate_task(task: dict[str, Any], work: Path) -> dict[str, Any]:
    source = mirror(task, work)
    image = image_id(build_image(task))
    scratch = work / "validation-checkouts" / task["id"]
    base = checkout(source, task["base_sha"], scratch / "base", history=False)
    overlay_hidden(task, base)
    before = run_tests(task, image, base)
    fixed = checkout(source, task["fix_sha"], scratch / "fix", history=False)
    after = run_tests(task, image, fixed)
    problems = []
    for key, value in before.items():
        if key.startswith("fail_to_pass:") and value["passed"]:
            problems.append(f"{key} passe déjà sur la base")
        if key.startswith("pass_to_pass:") and not value["passed"]:
            problems.append(f"{key} échoue sur la base")
    problems += [f"{key} échoue avec le correctif" for key, value in after.items() if not value["passed"]]
    shutil.rmtree(scratch, ignore_errors=True)
    return {
        "task_id": task["id"], "task_digest": task["digest"], "image": image, "image_tag": image_tag(task),
        "valid": not problems, "problems": problems,
        "base": before, "fix": after,
        "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@functools.lru_cache(maxsize=None)
def default_prompt(plugin: Path) -> str:
    text = (plugin / "skills" / "cstack" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    match = re.search(r'^\s*default_prompt:\s*"(.*)"\s*$', text, re.MULTILINE)
    if not match:
        raise BenchError("default_prompt de cstack introuvable")
    return match.group(1)


def arm_prompt(task: dict[str, Any], arm: str, bundles: dict[str, Path]) -> str:
    """Même demande pour tous les bras ; chaque paquet ajoute son entrée et sa demande de délégation."""
    body = task["prompt"].strip() + "\n\n" + SCOPE_NOTE
    if arm == "vanilla":
        return body
    bundle = bundles[arm]
    preamble = default_prompt(bundle) if arm == "cstack" else PSTACK_PREAMBLE
    skill = bundle / "skills" / ARM_SKILLS[arm] / "SKILL.md"
    return "\n\n".join([preamble, body, SOURCE_NOTE.format(path=skill)])


def plan_runs(tasks: list[dict[str, Any]], repetitions: int, seed: int, arms=DEFAULT_ARMS) -> list[dict[str, Any]]:
    """`arms` contient des noms de bras ; chaque nom apparaît autant de fois par tâche."""
    runs = [
        {"run_id": f"{task['id']}--{arm}--r{rep}", "task_id": task["id"], "arm": arm, "repetition": rep}
        for task in tasks for arm in arms for rep in range(1, repetitions + 1)
    ]
    random.Random(seed).shuffle(runs)
    return runs


def staged_diff(workspace: Path, base_sha: str, *flags: str) -> str:
    return git(workspace, "diff", "--cached", *flags, base_sha, *DIFF_PATHSPEC)


def capture_diff(workspace: Path, base_sha: str) -> str:
    """Indexe tout le travail de l’agent, commits compris, puis renvoie le patch depuis la base."""
    git(workspace, "add", "--all")
    return staged_diff(workspace, base_sha, "--binary")


def diff_stats(workspace: Path, base_sha: str, reference: set[str], hidden: set[str]) -> dict[str, Any]:
    """Suppose l’index préparé par capture_diff."""
    added = removed = 0
    files = []
    for line in staged_diff(workspace, base_sha, "--numstat").splitlines():
        plus, minus, path = line.split("\t", 2)
        added += int(plus) if plus.isdigit() else 0
        removed += int(minus) if minus.isdigit() else 0
        files.append(path)
    return {
        "files_changed": len(files), "lines_added": added, "lines_removed": removed,
        "files_outside_reference": sorted(set(files) - reference),
        "hidden_paths_touched": sorted(set(files) & hidden),
    }


def total_tokens(value: Any) -> int | None:
    found = [item for item in RUNNER.found_values(value, ("totalTokens",)) if isinstance(item, int)]
    return max(found) if found else None


def token_metrics(result: dict[str, Any]) -> dict[str, Any]:
    """Maximum cumulé par fil ; un fil sans métadonnées rend le total inconnu."""
    seen = threads(result)
    per_thread = [total_tokens([item for kind, item in seen if kind == "parent"])]
    per_thread += [total_tokens(item.get("token_usage", [])) for kind, item in seen if kind == "child"]
    missing = len(result.get("native_child_thread_ids", [])) - len(result.get("child_metadata", []))
    if all(value is not None for value in per_thread) and missing <= 0:
        return {"tokens": sum(per_thread), "tokens_source": "per_thread"}
    fallback = total_tokens(result.get("token_usage", []))
    return {"tokens": fallback, "tokens_source": "stream_max" if fallback is not None else "unknown"}


def grade(task: dict[str, Any], image: str, source: Path, patch: Path, work: Path) -> dict[str, Any]:
    grading = checkout(source, task["base_sha"], work / "grading" / task["id"], history=False)
    try:
        if patch.stat().st_size:
            applied = subprocess.run(["git", "apply", "--binary", str(patch)], cwd=grading, capture_output=True, text=True)
            if applied.returncode != 0:
                return {"resolved": False, "patch_applied": False, "error": applied.stderr.strip(), "tests": {}}
        overlay_hidden(task, grading)
        tests = run_tests(task, image, grading)
    finally:
        shutil.rmtree(grading, ignore_errors=True)
    return {
        "resolved": all_pass(tests, "fail_to_pass:") and all_pass(tests, "pass_to_pass:"),
        "patch_applied": True, "tests": tests,
    }


def execute_run(run: dict[str, Any], task: dict[str, Any], image: str, context: dict[str, Any]) -> dict[str, Any]:
    output: Path = context["output"]
    work: Path = context["work"]
    source = mirror(task, work)
    # Le workspace vit hors du dossier de travail, loin du miroir qui contient le correctif.
    workspace = checkout(source, task["base_sha"],
                         Path(tempfile.mkdtemp(prefix="cstack-outcome-")) / "repo", history=True)
    base = context["arm_bases"][run["arm"]]
    models = context["arm_models"].get(run["arm"])
    if models is not None:
        write_json(workspace / ".cstack" / "models.json", models)
    case = {"id": run["run_id"], "cwd": workspace, "sandbox": "workspace-write", "ephemeral": False,
            "prompts": [arm_prompt(task, base, context["bundles"])]}
    private = private_paths(work, output)
    with hidden_from_agent(private):
        agent = context["runner"].run_case(case, output / "agent", context["command"], context["model"],
                                           context["effort"], context["turn_timeout"])
    patch = output / "patches" / f"{run['run_id']}.diff"
    patch.parent.mkdir(parents=True, exist_ok=True)
    patch.write_text(capture_diff(workspace, task["base_sha"]), encoding="utf-8")
    reference = set(git(source, "diff", "--name-only", task["base_sha"], task["fix_sha"]).split())
    stats = diff_stats(workspace, task["base_sha"], reference, set(task["hidden_paths"]))
    # L’état cstack (reçus de workers, points de reprise) reste une preuve de la campagne.
    state = output / "state" / run["run_id"]
    if (workspace / ".cstack").is_dir():
        shutil.copytree(workspace / ".cstack", state, dirs_exist_ok=True)
    shutil.rmtree(workspace.parent, ignore_errors=True)
    commands = agent.get("actual_commands", [])
    graded = grade(task, image, source, patch, work)
    return {
        **run,
        "base": base,
        "possible_leak": possible_leak(task, commands, private),
        **observed_settings(agent, context["model"], context["effort"]),
        "cli_runtimes_seen": [name for name in CLI_RUNTIMES if any(name in command for command in commands)],
        "state_dir": str(state) if state.exists() else None,
        "agent_status": agent.get("status"),
        "agent_error": agent.get("error"),
        "wall_seconds": agent.get("wall_seconds"),
        **token_metrics(agent),
        "questions": len(agent.get("questions", [])),
        "children": len(agent.get("native_child_thread_ids", [])),
        "diff": stats,
        "patch": str(patch),
        "patch_sha256": sha256_file(patch),
        **graded,
    }


def load_results(path: Path, repair: bool = False) -> list[dict[str, Any]]:
    """Ignore un dernier enregistrement tronqué par une interruption ; `repair` le retire du fichier."""
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            if index != len(lines) - 1:
                raise BenchError(f"{path}: enregistrement {index + 1} illisible au milieu du fichier") from error
            if repair:
                path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return rows


def append_result(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def expected_runs(manifest: dict[str, Any]) -> set[str]:
    names = [arm["name"] for arm in manifest["arms"]]
    tasks = [{"id": task_id} for task_id in manifest["tasks"]]
    return {run["run_id"] for run in plan_runs(tasks, manifest["repetitions"], manifest["seed"], names)}


def summarize(results: list[dict[str, Any]], expected: set[str] | None = None) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    by_arm: dict[str, list[dict[str, Any]]] = {}
    counted_by_arm: dict[str, list[dict[str, Any]]] = {}
    by_task: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in results:
        by_arm.setdefault(row["arm"], []).append(row)
        if row.get("agent_status") != "infra_error" and not row.get("possible_leak") and not row.get("settings_mismatch"):
            counted_by_arm.setdefault(row["arm"], []).append(row)
            by_task.setdefault((row["task_id"], row["arm"]), []).append(row)
    order = {base: index for index, base in enumerate(ARMS)}
    present = sorted(by_arm, key=lambda name: (order.get(name, len(ARMS)), name))
    for arm in present:
        rows = counted_by_arm.get(arm, [])
        everything = by_arm[arm]
        resolved = [row for row in rows if row.get("resolved")]
        tokens = [row["tokens"] for row in rows if isinstance(row.get("tokens"), int)]
        walls = [row["wall_seconds"] for row in rows if isinstance(row.get("wall_seconds"), (int, float))]
        arms[arm] = {
            "runs": len(rows),
            "resolved": len(resolved),
            "resolved_rate": round(len(resolved) / len(rows), 3) if rows else None,
            "infra_errors": sum(1 for row in everything if row.get("agent_status") == "infra_error"),
            "possible_leaks": sum(1 for row in everything if row.get("possible_leak")),
            "settings_mismatches": sum(1 for row in everything if row.get("settings_mismatch")),
            "settings_unobserved": sum(1 for row in rows if not row.get("settings_observed")),
            "needs_input": sum(1 for row in rows if row.get("agent_status") == "needs_input"),
            "median_tokens": statistics.median(tokens) if tokens else None,
            "tokens_known": len(tokens),
            "tokens_per_resolved": round(sum(tokens) / len(resolved)) if resolved and len(tokens) == len(rows) else None,
            "median_wall_seconds": statistics.median(walls) if walls else None,
            "mean_children": round(statistics.mean(row.get("children", 0) for row in rows), 2) if rows else None,
            "questions": sum(row.get("questions", 0) for row in rows),
            "median_lines_changed": statistics.median(
                row["diff"]["lines_added"] + row["diff"]["lines_removed"] for row in rows
            ) if rows else None,
            "runs_touching_hidden_paths": sum(1 for row in rows if row["diff"]["hidden_paths_touched"]),
        }
    per_task = {}
    for task_id in sorted({task_id for task_id, _ in by_task}):
        rates = {}
        for arm in present:
            rows = by_task.get((task_id, arm), [])
            rates[arm] = round(sum(1 for row in rows if row.get("resolved")) / len(rows), 3) if rows else None
        per_task[task_id] = rates
    paired = {}
    for index, left in enumerate(present):
        for right in present[index + 1:]:
            both = [rates for rates in per_task.values() if rates.get(left) is not None and rates.get(right) is not None]
            paired[f"{right}_vs_{left}"] = {
                "tasks": len(both),
                f"{right}_better": sum(1 for rates in both if rates[right] > rates[left]),
                f"{left}_better": sum(1 for rates in both if rates[left] > rates[right]),
                "ties": sum(1 for rates in both if rates[left] == rates[right]),
            }
    missing = sorted(expected - {row["run_id"] for row in results}) if expected is not None else None
    return {
        "complete": expected is not None and not missing,
        "missing_runs": missing,
        "arms": arms,
        "per_task": per_task,
        "paired": paired,
        "limits": [
            "Échantillon petit : l’écart doit être large et cohérent entre tâches pour être interprété.",
            "infra_error, possible_leak et settings_mismatch sont exclus des dénominateurs et comptés à part.",
            "Les tokens viennent des métadonnées natives ; tokens_known indique leur couverture.",
        ],
    }


def command_validate(args: argparse.Namespace) -> int:
    _, tasks = load_suite(args.tasks, args.task_ids)
    failures = 0
    for task in tasks:
        print(f"[{task['id']}] validation", flush=True)
        try:
            receipt = validate_task(task, args.work)
        except BenchError as error:
            receipt = {"task_id": task["id"], "task_digest": task["digest"], "valid": False, "problems": [str(error)]}
        write_json(args.work / "validation" / f"{task['id']}.json", receipt)
        failures += not receipt["valid"]
        print(f"[{task['id']}] {'valide' if receipt['valid'] else 'refusée : ' + '; '.join(receipt['problems'])}", flush=True)
    return 1 if failures else 0


def require_receipt(task: dict[str, Any], work: Path) -> str:
    path = work / "validation" / f"{task['id']}.json"
    receipt = read_json(path) if path.exists() else None
    if not receipt or not receipt.get("valid") or receipt.get("task_digest") != task["digest"]:
        raise BenchError(f"{task['id']}: aucune validation courante ; lancez d’abord la commande validate")
    if not str(receipt.get("image", "")).startswith("sha256:"):
        raise BenchError(f"{task['id']}: reçu sans identité d’image ; relancez validate")
    return receipt["image"]


def upstream_pin() -> dict[str, Any]:
    inventory = read_json(UPSTREAM_INVENTORY)
    return {
        "repository": inventory["repository"], "commit": inventory["commit"],
        "subdirectory": inventory["subdirectory"],
        "blobs": {row["path"]: row["git_blob"] for row in inventory["files"]},
    }


def default_pstack(work: Path) -> Path:
    pin = upstream_pin()
    return work / "upstream" / pin["commit"] / pin["subdirectory"]


def fetch_pstack(work: Path) -> Path:
    """Récupère pstack au commit épinglé de UPSTREAM.json et vérifie chaque blob de l’inventaire."""
    pin = upstream_pin()
    checkout_root = work / "upstream" / pin["commit"]
    if not (checkout_root / ".git").exists():
        checkout_root.mkdir(parents=True, exist_ok=True)
        git(checkout_root, "init", "--quiet")
        git(checkout_root, "remote", "add", "origin", pin["repository"])
        git(checkout_root, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", pin["commit"])
        git(checkout_root, "sparse-checkout", "set", pin["subdirectory"])
        git(checkout_root, "checkout", "--quiet", "--detach", pin["commit"])
    tree = {}
    for line in git(checkout_root, "ls-tree", "-r", "HEAD", "--", pin["subdirectory"]).splitlines():
        meta, path = line.split("\t", 1)
        tree[path] = meta.split()[2]
    if tree != pin["blobs"]:
        raise BenchError("le checkout pstack ne correspond pas à l’inventaire de UPSTREAM.json")
    return checkout_root / pin["subdirectory"]


def arm_roots(args: argparse.Namespace) -> dict[str, Path]:
    roots = {}
    bases = {arm["base"] for arm in args.arms}
    if "cstack" in bases:
        roots["cstack"] = args.plugin.expanduser().resolve()
    if "pstack" in bases:
        roots["pstack"] = (args.pstack or default_pstack(args.work)).expanduser().resolve()
    for arm, root in roots.items():
        if not (root / "skills" / ARM_SKILLS[arm] / "SKILL.md").is_file():
            hint = " ; lancez d’abord fetch-pstack" if arm == "pstack" else ""
            raise BenchError(f"{arm}: point d’entrée absent sous {root}{hint}")
    return roots


def command_fetch_pstack(args: argparse.Namespace) -> int:
    print(fetch_pstack(args.work))
    return 0


def command_run(args: argparse.Namespace) -> int:
    suite, tasks = load_suite(args.tasks, args.task_ids)
    output = args.output.expanduser().resolve()
    manifest_path = output / "manifest.json"
    if output == args.work or args.work in output.parents:
        raise BenchError("--output doit être hors de --work, masqué pendant le tour de l’agent")
    roots = arm_roots(args)
    arm_models = load_arm_models(args.arms)
    manifest = {
        "schema_version": 3, "suite_digest": tree_digest(args.tasks), "merged_after": suite["merged_after"],
        "tasks": [task["id"] for task in tasks], "task_digests": {task["id"]: task["digest"] for task in tasks},
        "arms": [
            {"name": arm["name"], "base": arm["base"],
             "models_sha256": hashlib.sha256(json.dumps(arm_models[arm["name"]], sort_keys=True).encode()).hexdigest()
             if arm["name"] in arm_models else None}
            for arm in args.arms
        ],
        "bundle_digests": {base: tree_digest(root) for base, root in roots.items()},
        "network": args.network, "repetitions": args.repetitions, "seed": args.seed,
        "model": args.model, "effort": args.effort, "turn_timeout": args.turn_timeout,
    }
    if manifest_path.exists():
        previous = read_json(manifest_path)
        if {key: value for key, value in previous.items() if key != "started_at"} != manifest:
            raise BenchError("la sortie existe avec un autre manifeste ; refus de mélanger deux campagnes")
    elif output.exists() and any(output.iterdir()):
        raise BenchError("le dossier de sortie doit être absent, vide ou une campagne identique à reprendre")
    images = {task["id"]: require_receipt(task, args.work) for task in tasks}
    output.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        write_json(manifest_path, {**manifest, "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    bundles = {}
    for arm, root in roots.items():
        bundles[arm] = output / "resources" / arm
        if not bundles[arm].exists():
            shutil.copytree(root, bundles[arm], ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".git"))
    runner = load_runner()
    command = runner.build_command() + (NETWORK_FLAG if args.network else [])
    context = {
        "output": output, "work": args.work, "bundles": bundles, "runner": runner, "command": command,
        "arm_bases": {arm["name"]: arm["base"] for arm in args.arms}, "arm_models": arm_models,
        "model": args.model, "effort": args.effort, "turn_timeout": args.turn_timeout,
    }
    results_path = output / "results.jsonl"
    done = {row["run_id"] for row in load_results(results_path, repair=True)}
    by_id = {task["id"]: task for task in tasks}
    for run in plan_runs(tasks, args.repetitions, args.seed, [arm["name"] for arm in args.arms]):
        if run["run_id"] in done:
            continue
        print(f"[{run['run_id']}] démarrage", flush=True)
        try:
            row = execute_run(run, by_id[run["task_id"]], images[run["task_id"]], context)
        except (BenchError, OSError, subprocess.SubprocessError) as error:
            row = {**run, "agent_status": "infra_error", "agent_error": str(error), "resolved": False}
        append_result(results_path, runner.scrub(row))
        print(f"[{run['run_id']}] {row['agent_status']} résolu={row.get('resolved')}", flush=True)
    write_json(output / "summary.json", summarize(load_results(results_path), expected_runs(manifest)))
    print(f"résumé : {output / 'summary.json'}", flush=True)
    return 0


def command_report(args: argparse.Namespace) -> int:
    output = args.output.expanduser().resolve()
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        raise BenchError(f"aucune campagne sous {output} : manifest.json absent")
    summary = summarize(load_results(output / "results.jsonl"), expected_runs(read_json(manifest_path)))
    if not summary["complete"]:
        print(f"outcome-bench: campagne incomplète, {len(summary['missing_runs'])} run(s) manquant(s)", file=sys.stderr)
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("-h", "--help", action="help", help="affiche cette aide puis quitte")
    commands = parser.add_subparsers(dest="command", required=True)

    def resolved_path(value: str) -> Path:
        return Path(value).expanduser().resolve()

    def work_option(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--work", type=resolved_path, default=resolved_path(str(ROOT / ".cstack" / "outcome-bench")),
                         help="caches, miroirs et reçus locaux")

    def task_options(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--tasks", type=resolved_path, default=DEFAULT_TASKS, help="racine contenant suite.json et tasks/")
        sub.add_argument("--task-id", action="append", dest="task_ids", help="limite à cette tâche ; option répétable")
        work_option(sub)

    validate = commands.add_parser("validate", help="vérifie chaque tâche sans modèle")
    task_options(validate)
    validate.set_defaults(handler=command_validate)
    fetch = commands.add_parser("fetch-pstack", help="récupère pstack au commit épinglé et vérifie ses blobs")
    work_option(fetch)
    fetch.set_defaults(handler=command_fetch_pstack)
    run = commands.add_parser("run", help="exécute les bras choisis puis note les diffs")
    task_options(run)
    run.set_defaults(handler=command_run)
    run.add_argument("--output", type=Path, required=True, help="dossier de campagne ; une campagne identique reprend")
    run.add_argument("--plugin", type=Path, default=DEFAULT_PLUGIN, help="racine du plugin cstack évalué")
    run.add_argument("--pstack", type=Path, help="racine pstack ; par défaut le checkout épinglé de fetch-pstack")
    run.add_argument("--arms", default=",".join(DEFAULT_ARMS),
                     help=f"bras `nom` ou `nom=base[:models.json]` séparés par des virgules ; bases : {', '.join(ARMS)}")
    run.add_argument("--network", action="store_true", help="autorise le réseau du sandbox pour tous les bras")
    run.add_argument("--repetitions", type=int, default=3)
    run.add_argument("--seed", type=int, required=True, help="graine de l’ordre entrelacé, enregistrée")
    run.add_argument("--model", help="modèle natif commun à tous les bras")
    run.add_argument("--effort", help="effort commun à tous les bras")
    run.add_argument("--turn-timeout", type=float, default=900.0)
    report = commands.add_parser("report", help="recalcule summary.json depuis results.jsonl")
    report.add_argument("--output", type=Path, required=True)
    report.set_defaults(handler=command_report)
    args = parser.parse_args(argv)
    if args.command == "run":
        try:
            args.arms = parse_arms(args.arms)
        except BenchError as error:
            parser.error(str(error))
        if not 1 <= args.repetitions <= 10:
            parser.error("--repetitions doit être compris entre 1 et 10")
        if not 0 < args.turn_timeout <= 900:
            parser.error("--turn-timeout doit être supérieur à 0 et inférieur ou égal à 900 secondes")
    return args.handler(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BenchError as error:
        print(f"outcome-bench: {error}", file=sys.stderr)
        raise SystemExit(1)
