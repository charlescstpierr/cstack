#!/usr/bin/env python3
"""Exécute des tours Codex natifs isolés et conserve les preuves pour une évaluation à l’aveugle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import sys
import tempfile
import time


DEFAULT_TURN_SECONDS = 300.0
MAX_TURN_SECONDS = 900.0
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Key-name policy: a dict key or assignment/flag/header name is secret when
# its normalized form contains a marker below or ends with "token". Markers
# are credential words, not bare "key" or "auth". "key" would redact
# identifier fields; "auth" would redact an auth mode and oauth_* names.
# "apikey" and "authorization" already cover the credential-bearing keys.
SECRET_KEY_MARKERS = (
    "password",
    "secret",
    "apikey",
    "authorization",
    "cookie",
    "privatekey",
    "credentials",
    "passwd",
    "pwd",
    "jwt",
    "bearer",
    "sshkey",
    "awsaccesskeyid",
)
GITHUB_TOKEN = re.compile(r"\b(?:github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]{36,})\b")
# The value after the scheme must look like a credential, so prose such as
# "the bearer of the ring" keeps its words.
BEARER_TOKEN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]{16,}")
BASIC_TOKEN = re.compile(r"(?i)(\bBasic\s+)[A-Za-z0-9+/=]{12,}")
QUERY_SECRET = re.compile(
    r"(?i)([?&](?:access[_-]token|refresh[_-]token|id[_-]token|session[_-]token|api[_-]key|private[_-]token|password|secret|authorization|token|jwt|bearer|credentials)=)[^&]*"
)
AWS_ACCESS_KEY_ID = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
SK_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")
SLACK_TOKEN = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")
JWT_TOKEN = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
URL_USERINFO = re.compile(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@")
NPM_TOKEN = re.compile(r"\bnpm_[A-Za-z0-9]{36,}\b")
GITLAB_TOKEN = re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")
GOOGLE_API_KEY = re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")
GOOGLE_OAUTH = re.compile(r"\bya29\.[A-Za-z0-9_-]+")
PEM_PRIVATE_KEY = re.compile(
    r"(-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----)\s*.*?\s*(-----END (?:[A-Z]+ )?PRIVATE KEY-----)",
    re.DOTALL,
)
ASSIGNMENT = re.compile(r"(?i)(\b(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)(=)([^\s&]*)")
FLAG = re.compile(r"(?i)(--[A-Za-z0-9_-]+|-p)(=|\s+)(\S+)")
HEADER = re.compile(r"(?i)(^|[\n\r])([A-Za-z][A-Za-z0-9-]*)(\s*:\s*)(.+)")
NEUTRAL_INSTRUCTIONS = (
    "Utilisez le paquet local sélectionné et les consignes du projet. Utilisez des rôles "
    "natifs génériques. Respectez la demande utilisateur et le périmètre actuel du projet. N’utilisez pas de "
    "plugins ou de processus sans rapport avec la tâche."
)


class HarnessError(RuntimeError):
    pass


class NeedsInput(HarnessError):
    pass


def secret_key(key):
    folded = normalized(key)
    return any(marker in folded for marker in SECRET_KEY_MARKERS) or folded.endswith("token")


def _password_short_flag(value):
    # -p is overloaded (password, port, pid, preserve). Treat it as a password
    # flag only when the value looks like a secret, not a path, port, or pid.
    if "/" in value or ":" in value or "." in value:
        return False
    if len(value) < 6:
        return False
    return any(char.isalpha() for char in value) and any(char.isdigit() for char in value)


def _scrub_assignment(match):
    prefix, name, eq, value = match.groups()
    if value and secret_key(name):
        return f"{prefix}{name}{eq}<REDACTED>"
    return match.group(0)


def _scrub_flag(match):
    flag, sep, value = match.groups()
    name = flag.lstrip("-")
    if name.lower() == "p":
        if not _password_short_flag(value):
            return match.group(0)
        return f"{flag}{sep}<REDACTED>"
    if secret_key(name):
        return f"{flag}{sep}<REDACTED>"
    return match.group(0)


def _scrub_header(match):
    lead, name, sep, rest = match.groups()
    if not secret_key(name):
        return match.group(0)
    auth = re.match(r"(?i)(Bearer|Basic)\s+(\S+)(.*)$", rest)
    if auth:
        return f"{lead}{name}{sep}{auth.group(1)} <REDACTED>{auth.group(3)}"
    return f"{lead}{name}{sep}<REDACTED>"


def scrub_text(text):
    text = PEM_PRIVATE_KEY.sub(r"\1\n<REDACTED>\n\2", text)
    text = GITHUB_TOKEN.sub("<REDACTED>", text)
    text = NPM_TOKEN.sub("<REDACTED>", text)
    text = GITLAB_TOKEN.sub("<REDACTED>", text)
    text = GOOGLE_API_KEY.sub("<REDACTED>", text)
    text = GOOGLE_OAUTH.sub("<REDACTED>", text)
    text = AWS_ACCESS_KEY_ID.sub("<REDACTED>", text)
    text = SLACK_TOKEN.sub("<REDACTED>", text)
    text = SK_TOKEN.sub("<REDACTED>", text)
    text = JWT_TOKEN.sub("<REDACTED>", text)
    text = BEARER_TOKEN.sub(r"\1<REDACTED>", text)
    text = BASIC_TOKEN.sub(r"\1<REDACTED>", text)
    text = URL_USERINFO.sub(r"\1<REDACTED>@", text)
    text = QUERY_SECRET.sub(r"\1<REDACTED>", text)
    text = FLAG.sub(_scrub_flag, text)
    text = ASSIGNMENT.sub(_scrub_assignment, text)
    text = HEADER.sub(_scrub_header, text)
    return text


def scrub(value):
    """Conserve des preuves utiles sans exposer de secrets dans summary.json."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if secret_key(key):
                result[key] = "<REDACTED>"
            else:
                result[key] = scrub(item)
        return result
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value


def dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from dicts(child)


def normalized(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def first(value, keys):
    if not isinstance(value, dict):
        return None
    for key in keys:
        if key in value:
            return value[key]
    return None


def found_values(value, wanted):
    wanted = {normalized(item) for item in wanted}
    found = []
    for item in dicts(value):
        for key, child in item.items():
            if normalized(key) in wanted:
                found.append(child)
    return found


def add_unique(items, value):
    if value is None:
        return
    if isinstance(value, (str, int)):
        value = str(value)
        if value and value not in items:
            items.append(value)
    elif isinstance(value, list):
        for child in value:
            add_unique(items, child)


def dispatch_record(item):
    return {
        "dispatch_id": item.get("id"),
        "tool": item.get("tool"),
        "dispatch_status": item.get("status"),
        "receiver_thread_ids": item.get("receiverThreadIds", item.get("receiver_thread_ids", [])),
        "requested_model": item.get("model"),
        "requested_reasoning_effort": item.get("reasoningEffort", item.get("reasoning_effort")),
        "agents_states": scrub(item.get("agentsStates", item.get("agents_states", {}))),
    }


def record_dispatch(state, item):
    record = dispatch_record(item)
    key = record["dispatch_id"] or json.dumps(record, sort_keys=True)
    if key in state["dispatch_indices"]:
        state["dispatch_metadata"][state["dispatch_indices"][key]].update(record)
    else:
        state["dispatch_indices"][key] = len(state["dispatch_metadata"])
        state["dispatch_metadata"].append(record)


def capture_thread_metadata(server, thread_id, timeout, state, parent_thread, kind):
    try:
        result = server.request(
            "thread/read", {"threadId": thread_id, "includeTurns": False}, timeout,
            lambda message: update_state(message, state, parent_thread),
        )
    except (NeedsInput, HarnessError, OSError, TimeoutError) as error:
        state["metadata_gaps"].append({
            "kind": kind,
            "thread_id": thread_id,
            "reason": "thread/read indisponible ; métadonnées non observées",
            "error": str(error),
        })
        return None
    return project_metadata(result)


def question_message(message):
    if not isinstance(message, dict) or "id" not in message or "method" not in message:
        return None
    return message


class AppServer:
    def __init__(self, command, cwd, raw_path, stderr_path):
        self.command = command
        self.raw = raw_path.open("wb")
        self.process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_path.open("wb"),
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b""
        self.next_id = 1

    def send(self, message):
        if self.process.stdin is None:
            raise HarnessError("l’entrée standard d’app-server est fermée")
        self.process.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())
        self.process.stdin.flush()

    def notify(self, method, params=None):
        message = {"method": method}
        if params is not None:
            message["params"] = params
        self.send(message)

    def read(self, deadline):
        while True:
            end = self.buffer.find(b"\n")
            if end >= 0:
                raw = self.buffer[: end + 1]
                self.buffer = self.buffer[end + 1 :]
                self.raw.write(raw)
                self.raw.flush()
                if not raw.strip():
                    continue
                try:
                    return json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise HarnessError(f"JSON d’app-server invalide: {error}") from error
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("délai de réponse d’app-server dépassé")
            if not self.selector.select(min(0.25, remaining)):
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise HarnessError(f"app-server fermé avec le code {self.process.poll()}")
            self.buffer += chunk

    def request(self, method, params, timeout, on_event):
        request_id = self.next_id
        self.next_id += 1
        self.send({"id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            message = self.read(deadline)
            if isinstance(message, dict) and "id" in message and "method" in message:
                on_event(message)
                raise NeedsInput(f"la requête native nécessite une réponse: {message.get('method')}")
            if isinstance(message, dict) and message.get("id") == request_id:
                if "error" in message:
                    raise HarnessError(f"échec de {method} : {scrub(message['error'])}")
                return message.get("result", {})
            on_event(message)

    def close(self):
        try:
            self.selector.close()
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            if self.process.stdin:
                self.process.stdin.close()
            if self.process.stdout:
                self.process.stdout.close()
            self.raw.close()


def update_state(message, state, parent_thread):
    if not isinstance(message, dict):
        return
    question = question_message(message)
    if question is not None:
        encoded = json.dumps(scrub(question), sort_keys=True)
        if encoded not in state["question_keys"]:
            state["question_keys"].add(encoded)
            state["questions"].append(scrub(question))
        raise NeedsInput(f"la requête native nécessite une réponse: {message.get('method', 'question')}")

    event_thread = first(message.get("params", {}), ("threadId", "thread_id"))
    for item in dicts(message):
        kind = normalized(item.get("type", ""))
        if kind in {"agentmessage", "agent_message"} and isinstance(item.get("text"), str):
            if event_thread in (None, parent_thread):
                item_id = item.get("id")
                if item_id is not None and item_id in state["message_indices"]:
                    state["messages"][state["message_indices"][item_id]] = item["text"]
                else:
                    if item_id is not None:
                        state["message_indices"][item_id] = len(state["messages"])
                    state["messages"].append(item["text"])
                async_questions = item.get("questions")
                if async_questions:
                    encoded = json.dumps(scrub(async_questions), sort_keys=True)
                    if encoded not in state["question_keys"]:
                        state["question_keys"].add(encoded)
                        state["questions"].append(scrub(async_questions))
        if kind in {"subagentactivity", "collabagenttoolcall", "collabtoolcall"}:
            record_dispatch(state, item)
            add_unique(state["child_ids"], first(item, ("agentThreadId", "agent_thread_id", "childThreadId", "child_thread_id")))
            add_unique(state["child_ids"], first(item, ("receiverThreadIds", "receiver_thread_ids", "receiverThreadId", "receiver_thread_id")))
        for key in ("command", "commandLine", "command_line", "cmd"):
            value = item.get(key)
            if isinstance(value, str):
                add_unique(state["actual_commands"], value)
            elif isinstance(value, list):
                add_unique(state["actual_commands"], " ".join(str(part) for part in value))
    for value in found_values(message, ("tokenUsage", "token_usage", "usage")):
        encoded = json.dumps(scrub(value), sort_keys=True)
        if encoded not in state["token_usage_keys"]:
            state["token_usage_keys"].add(encoded)
            state["token_usage"].append(scrub(value))
    if parent_thread is not None:
        state["child_ids"][:] = [thread_id for thread_id in state["child_ids"] if thread_id != str(parent_thread)]


def project_metadata(value):
    return {
        "model": next(iter(found_values(value, ("model",))), None),
        "reasoning_effort": next(iter(found_values(value, ("reasoningEffort", "reasoning_effort", "effort"))), None),
        "token_usage": [scrub(item) for item in found_values(value, ("tokenUsage", "token_usage", "usage"))],
        "metadata": scrub(value),
    }


def tree_hash(root, excluded):
    digest = hashlib.sha256()
    files = 0
    total_bytes = 0
    root = root.resolve()
    excluded = excluded.resolve() if excluded else None
    if excluded and root not in excluded.parents:
        excluded = None
    for directory, names, filenames in os.walk(root, topdown=True, followlinks=False):
        path = Path(directory)
        names[:] = sorted(name for name in names if name not in SKIP_DIRS and not (excluded and (path / name).resolve() == excluded))
        for filename in sorted(filenames):
            item = path / filename
            if item.is_symlink() or not item.is_file() or (excluded and (item == excluded or excluded in item.parents)):
                continue
            relative = item.relative_to(root).as_posix().encode()
            digest.update(relative + b"\0")
            with item.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
                    total_bytes += len(chunk)
            files += 1
    return {"sha256": digest.hexdigest(), "files": files, "bytes": total_bytes}


OPENED_PATH = re.compile(r'openat2?\([^\n]*?, "((?:[^"\\]|\\.)+)"[^\n]*?\)\s+=\s+(\d+)')


def observed_routes(trace_prefix, bundle):
    """Record successful filesystem opens; an open alone does not prove semantic use."""
    routes = set()
    ambiguous = False
    traces = sorted(trace_prefix.parent.glob(trace_prefix.name + ".*"))
    for trace in traces:
        for line in trace.read_text(errors="replace").splitlines():
            match = OPENED_PATH.search(line)
            if not match:
                continue
            try:
                path = Path(json.loads('"' + match.group(1) + '"')).resolve()
            except (json.JSONDecodeError, OSError):
                ambiguous = True
                continue
            try:
                relative = path.relative_to(bundle.resolve()).as_posix()
            except ValueError:
                continue
            if relative.startswith("skills/") and (
                relative.endswith("/SKILL.md")
                or "/playbooks/" in relative
                or "/principles/" in relative
            ):
                routes.add(relative)
    return {"opened": sorted(routes), "ambiguous_path": ambiguous, "trace_files": len(traces),
            "evidence": "successful filesystem open; bulk scans and transitive bundles may count"}


def score_routes(observed, expectation):
    gold = expectation.get("routing", {})
    expected, forbidden = set(gold.get("expected", [])), set(gold.get("forbidden", []))
    opened = set(observed["opened"])
    return {"true_positive": sorted(expected & opened), "false_negative": sorted(expected - opened),
            "false_positive": sorted(forbidden & opened),
            "known_true_negative": sorted(forbidden - opened),
            "unlabelled_opened": sorted(opened - expected - forbidden)}


def require_route_trace():
    if not shutil.which("strace"):
        raise HarnessError("--trace-routes exige strace sous Linux")
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run(
            ["strace", "-o", str(Path(directory) / "probe"), sys.executable, "-c", "pass"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    if result.returncode:
        raise HarnessError("--trace-routes exige l'autorisation ptrace de l'hôte: "
                           + result.stderr.strip()[:300])


def config_path():
    home = os.environ.get("CODEX_HOME")
    if home is None:
        return Path.home() / ".codex" / "config.toml"
    if home == "":
        raise HarnessError("CODEX_HOME est défini mais vide")
    return Path(home) / "config.toml"


def parse_toml(raw, path):
    try:
        import tomllib
    except ImportError as error:
        raise HarnessError(
            f"Python 3.11 ou ultérieur est requis pour lire {path} ; cet interpréteur utilise {sys.version.split()[0]}"
        ) from error
    try:
        return tomllib.loads(raw)
    except tomllib.TOMLDecodeError as error:
        raise HarnessError(f"impossible de lire la configuration Codex: {path}") from error


def config_names():
    path = config_path()
    try:
        raw = path.read_text()
    except OSError as error:
        raise HarnessError(f"impossible de lire la configuration Codex: {path}") from error
    config = parse_toml(raw, path)
    plugins = config.get("plugins", {})
    mcp_servers = config.get("mcp_servers", {})
    return (
        sorted(str(name) for name in plugins) if isinstance(plugins, dict) else [],
        sorted(str(name) for name in mcp_servers) if isinstance(mcp_servers, dict) else [],
    )


def build_command():
    executable = shutil.which("codex") or "codex"
    try:
        help_result = subprocess.run(
            [executable, "app-server", "--help"], capture_output=True, text=True, timeout=10, check=False
        )
        supports_ignore = "--ignore-user-config" in (help_result.stdout + help_result.stderr)
    except (OSError, subprocess.SubprocessError):
        supports_ignore = False
    command = [executable, "app-server", "--stdio"]
    plugins, mcp_servers = config_names()
    if supports_ignore:
        command.append("--ignore-user-config")
    else:
        for name in plugins:
            command += ["-c", f"plugins.{name}.enabled=false"]
        for name in mcp_servers:
            command += ["-c", f"mcp_servers.{name}.enabled=false"]
    command += [
        "-c", "features.hooks=false",
        "-c", "features.memories=false",
        "-c", 'developer_instructions=""',
        "-c", "notify=[]",
    ]
    return command


def read_cases(path):
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise HarnessError(f"impossible de lire le JSON des scénarios: {path}") from error
    if not isinstance(payload, list) or not payload:
        raise HarnessError("le JSON des scénarios doit être un tableau non vide")
    cases = []
    ids = set()
    for row in payload:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not SAFE_ID.fullmatch(row["id"]):
            raise HarnessError("chaque scénario nécessite un identifiant textuel sûr")
        case_id = row["id"]
        if case_id in ids:
            raise HarnessError(f"identifiant de scénario dupliqué: {case_id}")
        ids.add(case_id)
        cwd = Path(row.get("cwd", "")).expanduser().resolve()
        if not cwd.is_dir():
            raise HarnessError(f"le cwd du scénario n’est pas un dossier: {cwd}")
        has_prompt = isinstance(row.get("prompt"), str)
        has_prompts = isinstance(row.get("prompts"), list)
        if has_prompt == has_prompts:
            raise HarnessError(f"{case_id}: fournissez exactement un champ parmi prompt et prompts")
        prompts = [row["prompt"]] if has_prompt else row["prompts"]
        if not prompts or not all(isinstance(prompt, str) for prompt in prompts):
            raise HarnessError(f"{case_id}: prompts doit être un tableau non vide de chaînes")
        sandbox = row.get("sandbox", "workspace-write")
        if not isinstance(sandbox, str) or not sandbox:
            raise HarnessError(f"{case_id}: sandbox doit être une chaîne")
        ephemeral = row.get("ephemeral", True)
        if not isinstance(ephemeral, bool):
            raise HarnessError(f"{case_id}: ephemeral doit être un booléen")
        bundle = Path(row["bundle"]).expanduser().resolve() if row.get("bundle") else None
        if bundle is not None and not (bundle / "skills" / "cstack" / "SKILL.md").is_file():
            raise HarnessError(f"{case_id}: bundle de skills introuvable: {bundle}")
        cases.append({"id": case_id, "cwd": cwd, "prompts": prompts, "sandbox": sandbox,
                      "bundle": bundle, "ephemeral": ephemeral})
    return cases


def run_case(case, output, command, model, effort, timeout, trace_routes=False):
    case_dir = output / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    raw_path = case_dir / "raw.jsonl"
    stderr_path = case_dir / "stderr.log"
    state = {
        "child_ids": [], "messages": [], "questions": [], "question_keys": set(),
        "message_indices": {},
        "dispatch_metadata": [], "dispatch_indices": {}, "metadata_gaps": [],
        "actual_commands": [], "token_usage": [], "token_usage_keys": set(),
        "after_turn_actual_metadata": [], "turns": [], "current_turn": None,
    }
    before = tree_hash(case["cwd"], output)
    started = time.monotonic()
    server = None
    status = "completed"
    error = None
    parent_thread = None
    trace_prefix = case_dir / "route-open"
    actual_command = (["strace", "-ff", "-e", "trace=openat,openat2", "-s", "4096",
                       "-o", str(trace_prefix), *command] if trace_routes else command)
    try:
        server = AppServer(actual_command, case["cwd"], raw_path, stderr_path)
        server.request("initialize", {"clientInfo": {"name": "cstack-behavior-runner", "version": "0.1.0"}}, timeout, lambda message: update_state(message, state, parent_thread))
        server.notify("initialized")
        thread_params = {
            "cwd": str(case["cwd"]), "approvalPolicy": "never", "sandbox": case["sandbox"],
            "ephemeral": case.get("ephemeral", True), "developerInstructions": NEUTRAL_INSTRUCTIONS,
        }
        if model:
            thread_params["model"] = model
        thread_result = server.request("thread/start", thread_params, timeout, lambda message: update_state(message, state, parent_thread))
        parent_thread = first(thread_result, ("threadId", "thread_id")) or first(first(thread_result, ("thread",)) or {}, ("id",))
        if not parent_thread:
            raise HarnessError("thread/start n’a renvoyé aucun identifiant de conversation")
        state["child_ids"][:] = [thread_id for thread_id in state["child_ids"] if thread_id != str(parent_thread)]
        for index, prompt in enumerate(case["prompts"]):
            state["current_turn"] = {"index": index, "prompt": prompt, "messages": [], "status": None}
            state["messages"] = []
            state["message_indices"] = {}
            turn_params = {"threadId": parent_thread, "input": [{"type": "text", "text": prompt}]}
            if effort:
                turn_params["effort"] = effort
            turn_result = server.request("turn/start", turn_params, timeout, lambda message: update_state(message, state, parent_thread))
            turn_id = first(turn_result, ("turnId", "turn_id")) or first(first(turn_result, ("turn",)) or {}, ("id",))
            deadline = time.monotonic() + timeout
            turn_status = None
            while turn_status is None:
                message = server.read(deadline)
                update_state(message, state, parent_thread)
                if message.get("method") == "turn/completed":
                    params = message.get("params", {})
                    if first(params, ("threadId", "thread_id")) == parent_thread:
                        candidate = first(params, ("turn",)) or params
                        candidate_id = first(candidate, ("id", "turnId", "turn_id"))
                        if not turn_id or not candidate_id or str(candidate_id) == str(turn_id):
                            turn_status = first(candidate, ("status",)) or "unknown"
            current = state["current_turn"]
            current["status"] = turn_status
            current["final_text"] = "\n\n".join(state["messages"])
            current["after_turn_actual_metadata"] = capture_thread_metadata(
                server, parent_thread, timeout, state, parent_thread, "parent"
            )
            state["after_turn_actual_metadata"].append(current["after_turn_actual_metadata"])
            state["turns"].append({key: value for key, value in current.items() if key != "messages"})
            if turn_status != "completed":
                status = "failed_turn"
                break
        if status == "completed":
            for child_id in state["child_ids"]:
                child_metadata = capture_thread_metadata(
                    server, child_id, timeout, state, parent_thread, "child"
                )
                if child_metadata is not None:
                    state.setdefault("child_metadata", []).append({"thread_id": child_id, **child_metadata})
    except NeedsInput as exc:
        status = "needs_input"
        error = str(exc)
    except (HarnessError, OSError, TimeoutError, subprocess.SubprocessError) as exc:
        status = "failed_turn" if state["current_turn"] is not None and state["current_turn"].get("status") is None else "infra_error"
        error = str(exc)
    finally:
        if server is not None:
            server.close()
    after = tree_hash(case["cwd"], output)
    result = {
        "id": case["id"], "cwd": str(case["cwd"]), "sandbox": case["sandbox"],
        "input_prompts": case["prompts"], "status": status,
        "wall_seconds": round(time.monotonic() - started, 3),
        "before_project_hash": before, "after_project_hash": after,
        "project_hash_changed": before["sha256"] != after["sha256"],
        "hash_policy": {"excluded_directories": sorted(SKIP_DIRS), "included_cstack": True},
        "actual_commands": state["actual_commands"], "app_server_command": actual_command,
        "questions": state["questions"], "native_child_thread_ids": state["child_ids"],
        "dispatch_metadata": state["dispatch_metadata"], "child_metadata": state.get("child_metadata", []),
        "metadata_gaps": state["metadata_gaps"],
        "token_usage": state["token_usage"], "after_turn_actual_metadata": state["after_turn_actual_metadata"],
        "turns": state["turns"], "error": error,
        "raw_stream": str(raw_path.resolve()), "stderr": str(stderr_path.resolve()),
    }
    if trace_routes:
        result["route_observation"] = observed_routes(trace_prefix, case["bundle"])
    return result


def write_summary(output, results, selected_case_ids):
    summary = scrub({
        "cases": results,
        "selected_case_ids": selected_case_ids,
        "output": str(output),
    })
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Exécute des scénarios Codex natifs isolés pour vérifier le comportement.", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="affiche cette aide puis quitte")
    parser.add_argument("--cases", type=Path, required=True, help="tableau JSON de scénarios de confiance")
    parser.add_argument("--output", type=Path, required=True, help="dossier des artefacts situé hors du cwd de chaque scénario")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="exécute uniquement ce scénario ; option répétable")
    parser.add_argument("--model", help="modèle natif de remplacement facultatif")
    parser.add_argument("--effort", help="effort de raisonnement natif facultatif")
    parser.add_argument("--trace-routes", action="store_true", help="trace les ouvertures des skills avec strace Linux")
    parser.add_argument("--expectations", type=Path, help="expectations.json généré avec les scénarios")
    parser.add_argument("--repeats", type=int, default=1, help="nombre de passages indépendants par cas (1 à 10)")
    parser.add_argument("--turn-timeout", type=float, default=DEFAULT_TURN_SECONDS, help="délai maximal par tour en secondes, maximum 900")
    args = parser.parse_args(argv)
    if args.turn_timeout <= 0 or args.turn_timeout > MAX_TURN_SECONDS:
        parser.error("--turn-timeout doit être supérieur à 0 et inférieur ou égal à 900 secondes")
    if not 1 <= args.repeats <= 10:
        parser.error("--repeats doit être compris entre 1 et 10")
    if args.trace_routes:
        require_route_trace()
    cases = read_cases(args.cases)
    if args.trace_routes and any(case["bundle"] is None for case in cases):
        raise HarnessError("--trace-routes exige des scénarios générés avec bundle explicite")
    if args.expectations and not args.trace_routes:
        raise HarnessError("--expectations exige --trace-routes")
    expectations = {}
    if args.expectations:
        payload = json.loads(args.expectations.read_text())
        expectations = {row["id"]: row for row in payload["cases"]}
        missing = {case["id"] for case in cases} - set(expectations)
        if missing:
            raise HarnessError(f"attentes absentes pour: {', '.join(sorted(missing))}")
    if args.case_ids:
        wanted = set(args.case_ids)
        unknown = wanted - {case["id"] for case in cases}
        if unknown:
            raise HarnessError(f"identifiant de scénario inconnu: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in wanted]
    output = args.output.expanduser().resolve()
    for case in cases:
        if output == case["cwd"] or case["cwd"] in output.parents or output in case["cwd"].parents:
            raise HarnessError(f"la sortie doit être située hors du cwd du scénario: {case['id']}")
    if output.exists() and any(output.iterdir()):
        raise HarnessError("le dossier de sortie doit être absent ou vide ; refus d’écraser les preuves")
    output.mkdir(parents=True, exist_ok=True)
    command = build_command()
    results = []
    selected_case_ids = [case["id"] for case in cases]
    for case in cases:
        for repeat in range(1, args.repeats + 1):
            run = dict(case)
            if args.repeats > 1:
                run["id"] = f"{case['id']}__run_{repeat:02d}"
                run["cwd"] = output / "isolated-projects" / run["id"]
                shutil.copytree(case["cwd"], run["cwd"])
            print(f"[{run['id']}] démarrage", flush=True)
            try:
                result = run_case(run, output, command, args.model, args.effort,
                                  args.turn_timeout, args.trace_routes)
                if (result["status"] == "completed" and args.trace_routes
                        and result["route_observation"]["trace_files"] and case["id"] in expectations):
                    result["route_score"] = score_routes(result["route_observation"], expectations[case["id"]])
            except Exception as error:
                result = {"id": run["id"], "cwd": str(run["cwd"]), "status": "infra_error", "error": str(error)}
            results.append(result)
            print(f"[{run['id']}] {result['status']} ({result.get('wall_seconds', 0)}s)", flush=True)
            write_summary(output, results, selected_case_ids)
    write_summary(output, results, selected_case_ids)
    if any(result["status"] != "completed" for result in results):
        return 2 if any(result["status"] == "needs_input" for result in results) else 1
    print(f"résumé : {output / 'summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as error:
        print(f"verify-behavior: {error}", file=sys.stderr)
        raise SystemExit(1)
