#!/usr/bin/env python3
"""Exécute des tours Codex natifs isolés et conserve les preuves pour une évaluation à l’aveugle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time


DEFAULT_TURN_SECONDS = 300.0
MAX_TURN_SECONDS = 900.0
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
TREE_HASH_ALGORITHM = "cstack-tree-sha256-v2"
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
    def unreadable(error):
        raise HarnessError(f"parcours d’empreinte incomplet: {error.filename}") from error

    digest = hashlib.sha256((TREE_HASH_ALGORITHM + "\0").encode())
    files = 0
    total_bytes = 0
    root = root.resolve()
    excluded = excluded.resolve() if excluded else None
    if excluded and root not in excluded.parents:
        excluded = None
    for directory, names, filenames in os.walk(root, topdown=True, followlinks=False, onerror=unreadable):
        path = Path(directory)
        names[:] = sorted(name for name in names if name not in SKIP_DIRS and not (excluded and (path / name).resolve() == excluded))
        for name in names:
            if (path / name).is_symlink():
                raise HarnessError(f"empreinte non prise en charge pour un dossier symbolique: {path / name}")
        for filename in sorted(filenames):
            item = path / filename
            if excluded and (item == excluded or excluded in item.parents):
                continue
            try:
                mode = item.stat().st_mode
            except OSError as error:
                raise HarnessError(f"entrée non régulière ou inaccessible: {item}") from error
            if not stat.S_ISREG(mode):
                raise HarnessError(f"entrée non régulière non prise en charge: {item}")
            relative = item.relative_to(root).as_posix().encode()
            effective_mode = stat.S_IFMT(mode) | stat.S_IMODE(mode)
            digest.update(effective_mode.to_bytes(2, "big") + len(relative).to_bytes(8, "big") + relative)
            content_digest = hashlib.sha256()
            with item.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    content_digest.update(chunk)
                    total_bytes += len(chunk)
            digest.update(content_digest.digest())
            files += 1
    return {"sha256": digest.hexdigest(), "algorithm": TREE_HASH_ALGORITHM, "files": files, "bytes": total_bytes}


def case_configuration(case):
    return {"id": case["id"], "cwd": str(Path(case["cwd"]).expanduser().resolve()),
            "bundle": str(Path(case["bundle"]).expanduser().resolve()) if case.get("bundle") else None,
            "prompts": list(case["prompts"]) if "prompts" in case else [case["prompt"]],
            "sandbox": case.get("sandbox", "workspace-write"), "ephemeral": case.get("ephemeral", True)}


def case_hash(case):
    canonical = json.dumps(case_configuration(case), sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


OPENED_PATH = re.compile(r'openat2?\([^\n]*?, "((?:[^"\\]|\\.)+)"[^\n]*?\)\s+=\s+(\d+)')


def explicit_route_reads(commands, bundle, cwd):
    """Accept only simple direct file reads; complex shell commands remain unclassified."""
    direct = set()
    for command in commands:
        if any(operator in command for operator in ("|", ";", "&&", ">", "<", "$", "`")):
            continue
        try:
            words = shlex.split(command)
        except ValueError:
            continue
        if not words or Path(words[0]).name not in {"cat", "sed", "head", "tail"}:
            continue
        if Path(words[0]).name == "sed" and any(word == "-i" or word.startswith("--in-place")
                                                  for word in words[1:]):
            continue
        for word in words[1:]:
            if word.startswith("-"):
                continue
            path = Path(word)
            if not path.is_absolute():
                path = cwd / path
            try:
                relative = path.resolve().relative_to(bundle.resolve()).as_posix()
            except ValueError:
                continue
            if relative.startswith("skills/") and (
                relative.endswith("/SKILL.md") or "/playbooks/" in relative
                or "/principles/" in relative
            ):
                direct.add(relative)
    return direct


def observed_routes(trace_prefix, bundle, commands=(), cwd=None):
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
                path = Path(json.loads('"' + match.group(1) + '"'))
                # Relative opens use the traced process's cwd or dirfd, neither
                # of which this trace records (a child may have called chdir).
                if not path.is_absolute():
                    ambiguous = True
                    continue
                path = path.resolve()
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
    direct = routes & explicit_route_reads(commands, bundle, cwd or bundle)
    return {"opened": sorted(routes), "direct_reads": sorted(direct),
            "unattributed_opens": sorted(routes - direct),
            "ambiguous_path": ambiguous, "trace_files": len(traces),
            "evidence": "direct_reads require a simple read command and a successful filesystem open; other opens are unresolved"}


def score_routes(observed, expectation):
    gold = expectation.get("routing", {})
    expected, forbidden = set(gold.get("expected", [])), set(gold.get("forbidden", []))
    opened = set(observed["opened"])
    direct = set(observed["direct_reads"])
    incomplete = observed["ambiguous_path"]
    return {"true_positive": sorted(expected & direct),
            "false_negative": sorted(expected - opened) if not incomplete else [],
            "unknown_expected": sorted((expected & opened) - direct | (expected - opened if incomplete else set())),
            "false_positive": sorted(forbidden & direct),
            "unknown_forbidden": sorted((forbidden & opened) - direct | (forbidden - opened if incomplete else set())),
            "known_true_negative": sorted(forbidden - opened) if not incomplete else [],
            "unlabelled_opened": sorted(opened - expected - forbidden)}


def read_expectations(path):
    payload = json.loads(path.read_text())
    if (not isinstance(payload, dict) or type(payload.get("schema_version")) is not int
            or payload["schema_version"] != 1 or not isinstance(payload.get("cases"), list)
            or set(payload) - {"schema_version", "cases"}):
        raise HarnessError("expectations.json doit contenir schema_version: 1 et un tableau cases")
    expectations = {}
    for row in payload["cases"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in expectations:
            raise HarnessError("identifiant d’attente absent ou dupliqué")
        case_id = row["id"]
        if set(row) - {"id", "expected_children", "min_children", "routing", "expected_artifacts",
                       "outcome_checks", "project_sha256", "source_sha256", "skill_path", "role_metadata", "hash_algorithm", "case_sha256"}:
            raise HarnessError(f"{case_id}: champs d’attente inconnus")
        hashes = row.get("source_sha256", {})
        if not isinstance(hashes, dict) or set(hashes) - {"bundle", "skill"}:
            raise HarnessError(f"{case_id}: source_sha256 invalide")
        if (row.get("hash_algorithm", TREE_HASH_ALGORITHM) != TREE_HASH_ALGORITHM
                or (("project_sha256" in row or hashes) and "hash_algorithm" not in row)):
            raise HarnessError(f"{case_id}: algorithme d’empreinte ancien ou absent ; régénérer les attentes")
        if ("project_sha256" in row or hashes) and "case_sha256" not in row:
            raise HarnessError(f"{case_id}: empreinte de configuration de cas absente ; régénérer les attentes")
        for digest in list(hashes.values()) + [row[key] for key in ("project_sha256", "case_sha256") if key in row]:
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise HarnessError(f"{case_id}: empreinte SHA-256 invalide")
        if "skill_path" in row:
            relative = row["skill_path"]
            if (not isinstance(relative, str) or len(Path(relative).parts) != 3
                    or Path(relative).parts[0] != "skills" or Path(relative).parts[-1] != "SKILL.md"
                    or Path(relative).is_absolute() or ".." in Path(relative).parts):
                raise HarnessError(f"{case_id}: skill_path doit désigner skills/<skill>/SKILL.md")
        roles = row.get("role_metadata", {})
        if not isinstance(roles, dict):
            raise HarnessError(f"{case_id}: role_metadata doit être un objet")
        for role, entries in roles.items():
            entries = entries if isinstance(entries, list) else [entries]
            if (not role or not entries or any(
                    not isinstance(entry, dict) or set(entry) != {"model", "reasoning_effort"}
                    or any(not isinstance(value, str) or not value for value in entry.values())
                    for entry in entries)):
                raise HarnessError(f"{case_id}: métadonnées de modèle invalides")
        for key in ("expected_children", "min_children"):
            if key in row and (type(row[key]) is not int or row[key] < 0):
                raise HarnessError(f"{case_id}: {key} doit être un entier positif ou nul")
        if "expected_children" in row and "min_children" in row:
            raise HarnessError(f"{case_id}: expected_children et min_children s’excluent")
        routing = row.get("routing", {})
        if not isinstance(routing, dict) or set(routing) - {"expected", "forbidden"}:
            raise HarnessError(f"{case_id}: attentes de routage invalides")
        for key in ("expected", "forbidden"):
            values = routing.get(key, [])
            if not isinstance(values, list) or any(not isinstance(p, str) or not p for p in values):
                raise HarnessError(f"{case_id}: routes {key} invalides")
        if set(routing.get("expected", [])) & set(routing.get("forbidden", [])):
            raise HarnessError(f"{case_id}: route à la fois requise et interdite")
        artifacts = row.get("expected_artifacts", [])
        if not isinstance(artifacts, list) or any(
                not isinstance(p, str) or not p or Path(p).is_absolute() or ".." in Path(p).parts
                for p in artifacts):
            raise HarnessError(f"{case_id}: les artefacts doivent rester dans le projet")
        checks = row.get("outcome_checks", [])
        if not isinstance(checks, list):
            raise HarnessError(f"{case_id}: outcome_checks doit être un tableau")
        ids = set()
        for check in checks:
            if (not isinstance(check, dict) or set(check) - {"id", "argv", "timeout", "expected_json"}
                    or not isinstance(check.get("id"), str) or not check["id"] or check["id"] in ids
                    or not isinstance(check.get("argv"), list) or not check["argv"]
                    or any(not isinstance(arg, str) or "\0" in arg for arg in check["argv"])
                    or not check["argv"][0]):
                raise HarnessError(f"{case_id}: vérificateur de résultat invalide")
            timeout = check.get("timeout", 30)
            if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 300:
                raise HarnessError(f"{case_id}: délai de vérification invalide, maximum 300 secondes")
            ids.add(check["id"])
        expectations[case_id] = row
    return expectations


def verify_provenance(case, expectation, execution_case=None):
    """Check generator digests against the inputs before launching the native turn."""
    def matches(label, actual, expected):
        if actual != expected:
            raise HarnessError(f"{case['id']}: empreinte {label} différente des attentes")

    source = expectation.get("source_sha256", {})
    if ("project_sha256" in expectation or source) and expectation.get("hash_algorithm") != TREE_HASH_ALGORITHM:
        raise HarnessError(f"{case['id']}: algorithme d’empreinte ancien ou absent ; régénérer les attentes")
    if ("project_sha256" in expectation or source) and "case_sha256" not in expectation:
        raise HarnessError(f"{case['id']}: empreinte de configuration de cas absente ; régénérer les attentes")
    if "case_sha256" in expectation:
        matches("configuration de cas", case_hash(execution_case or case), expectation["case_sha256"])
    try:
        project_hash = tree_hash(case["cwd"], None)["sha256"]
        if "project_sha256" in expectation:
            matches("projet", project_hash, expectation["project_sha256"])
        bundle = case.get("bundle")
        if bundle is None and not source:
            return
        if bundle is None:
            raise HarnessError(f"{case['id']}: empreintes source exigent un bundle explicite")
        bundle_hash = tree_hash(bundle, None)["sha256"]
        if "bundle" in source:
            matches("bundle", bundle_hash, source["bundle"])
        if "skill" in source:
            relative = expectation.get("skill_path")
            if relative is None:
                # Older generated prompts name the source file explicitly.
                paths = [path for path in bundle.glob("skills/*/SKILL.md")
                         if any(str(path) in prompt for prompt in case["prompts"])]
                if len(paths) != 1:
                    raise HarnessError(f"{case['id']}: empreinte skill exige skill_path non ambigu")
                skill = paths[0]
            else:
                skill = bundle / relative
            if not skill.resolve().is_relative_to(bundle.resolve()):
                raise HarnessError(f"{case['id']}: skill_path sort du bundle")
            matches("skill", hashlib.sha256(skill.read_bytes()).hexdigest(), source["skill"])
    except OSError as error:
        raise HarnessError(f"{case['id']}: impossible de vérifier les empreintes source/projet") from error


def check_verdict(checks):
    states = {check["status"] for check in checks}
    return {"status": "fail" if "fail" in states else "pass" if states == {"pass"} else "unverified",
            "checks": checks}


def evaluate_case(result, expectation, verify_outcomes=False):
    workflow, outcome = [], []
    if result["status"] != "completed":
        return {"turn": result["status"], "workflow": check_verdict([]), "outcome": check_verdict([])}
    if "routing" in expectation:
        score = result.get("route_score")
        if score is None:
            status = "unverified"
        elif score["false_negative"] or score["false_positive"]:
            status = "fail"
        else:
            status = "unverified" if score["unknown_expected"] or score["unknown_forbidden"] else "pass"
        workflow.append({"id": "routing", "status": status})
    if "expected_children" in expectation or "min_children" in expectation:
        children = result.get("native_child_thread_ids")
        if children is None:
            status = "unverified"
        else:
            count = len(set(children))
            matches = (count == expectation["expected_children"] if "expected_children" in expectation
                       else count >= expectation["min_children"])
            status = "pass" if matches else "fail"
        workflow.append({"id": "delegation", "status": status})
    for pattern in expectation.get("expected_artifacts", []):
        exists = any(p.is_file() for p in Path(result["cwd"]).glob(pattern))
        workflow.append({"id": "artifact:" + pattern, "status": "pass" if exists else "fail"})
    if verify_outcomes:
        for check in expectation.get("outcome_checks", []):
            record = {"id": check["id"]}
            try:
                process = subprocess.run(check["argv"], cwd=result["cwd"], stdin=subprocess.DEVNULL,
                                         capture_output=True, text=True, errors="replace",
                                         timeout=check.get("timeout", 30), check=False)
                passed = process.returncode == 0
                if "expected_json" in check:
                    try:
                        # Canonical JSON preserves scalar types: Python equality
                        # would accept true in place of 1, even inside objects.
                        passed = passed and (
                            json.dumps(json.loads(process.stdout), sort_keys=True, allow_nan=False)
                            == json.dumps(check["expected_json"], sort_keys=True, allow_nan=False))
                    except (ValueError, RecursionError):
                        passed = False
                record.update(status="pass" if passed else "fail", returncode=process.returncode,
                              stdout=scrub_text(process.stdout)[-4096:], stderr=scrub_text(process.stderr)[-4096:])
            except (OSError, subprocess.TimeoutExpired) as error:
                record.update(status="unverified", error=scrub_text(str(error)))
            outcome.append(record)
    return {"turn": result["status"], "workflow": check_verdict(workflow), "outcome": check_verdict(outcome)}


def require_route_trace():
    if not shutil.which("strace"):
        raise HarnessError("--trace-routes exige strace sous Linux")
    options = subprocess.run(["strace", "--help"], capture_output=True, text=True,
                             timeout=10, check=False)
    if "--kill-on-exit" not in options.stdout:
        raise HarnessError("--trace-routes exige strace avec --kill-on-exit")
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
        if set(row) - {"id", "cwd", "prompt", "prompts", "sandbox", "bundle", "ephemeral"}:
            raise HarnessError(f"{case_id}: champs de scénario inconnus")
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
    actual_command = (["strace", "-ff", "--kill-on-exit", "-e", "trace=openat,openat2", "-s", "4096",
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
        result["route_observation"] = observed_routes(
            trace_prefix, case["bundle"], state["actual_commands"], case["cwd"]
        )
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
    parser.add_argument("--verify-outcomes", action="store_true",
                        help="autorise les commandes outcome_checks du fichier d’attentes de confiance")
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
    if args.verify_outcomes and not args.expectations:
        raise HarnessError("--verify-outcomes exige --expectations")
    expectations = {}
    if args.expectations:
        expectations = read_expectations(args.expectations)
    if args.case_ids:
        wanted = set(args.case_ids)
        unknown = wanted - {case["id"] for case in cases}
        if unknown:
            raise HarnessError(f"identifiant de scénario inconnu: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in wanted]
    if args.expectations:
        missing = {case["id"] for case in cases} - set(expectations)
        if missing:
            raise HarnessError(f"attentes absentes pour: {', '.join(sorted(missing))}")
    output = args.output.expanduser().resolve()
    for case in cases:
        for label, source_root in (("cwd", case["cwd"]), ("bundle", case["bundle"])):
            if source_root is not None and (
                    output == source_root or source_root in output.parents or output in source_root.parents):
                raise HarnessError(f"la sortie doit être située hors du {label} du scénario: {case['id']}")
        verify_provenance(case, expectations.get(case["id"], {}))
        if args.repeats > 1:
            if not (case["cwd"] / ".git").exists():
                for parent in case["cwd"].parents:
                    git_path = parent / ".git"
                    if git_path.is_file() or git_path.is_symlink() or (git_path / "HEAD").is_file():
                        raise HarnessError(f"répétitions non prises en charge pour un sous-dossier de dépôt Git: {case['cwd']}")
            for directory, names, files in os.walk(case["cwd"]):
                git_path = Path(directory) / ".git"
                if ".git" in files or git_path.is_symlink():
                    raise HarnessError(f"répétitions non prises en charge pour un dépôt Git lié: {git_path}")
                for name in names:
                    if (Path(directory) / name).is_symlink():
                        raise HarnessError(f"répétitions non prises en charge pour un dossier symbolique: {Path(directory) / name}")
                names[:] = [name for name in names if name != ".git"]
    if output.exists() and any(output.iterdir()):
        raise HarnessError("le dossier de sortie doit être absent ou vide ; refus d’écraser les preuves")
    output.mkdir(parents=True, exist_ok=True)
    command = build_command()
    results = []
    unverified_requested = False
    selected_case_ids = [case["id"] for case in cases]
    for case in cases:
        expectation = expectations.get(case["id"], {})
        workflow_requested = any(key in expectation for key in
                                 ("routing", "expected_children", "min_children", "expected_artifacts"))
        for repeat in range(1, args.repeats + 1):
            run = dict(case)
            if args.repeats > 1:
                run["id"] = f"{case['id']}__run_{repeat:02d}"
                run["cwd"] = output / "isolated-projects" / run["id"]
                shutil.copytree(case["cwd"], run["cwd"])
            verify_provenance(run, expectation, execution_case=case)
            source_case_digest = case_hash(case)
            effective_config = case_configuration(run)
            effective_case_digest = case_hash(effective_config)
            print(f"[{run['id']}] démarrage", flush=True)
            try:
                result = run_case(run, output, command, args.model, args.effort,
                                  args.turn_timeout, args.trace_routes)
                if (result["status"] == "completed" and args.trace_routes
                        and result["route_observation"]["trace_files"] and case["id"] in expectations):
                    result["route_score"] = score_routes(result["route_observation"], expectations[case["id"]])
            except Exception as error:
                result = {"id": run["id"], "cwd": str(run["cwd"]), "status": "infra_error", "error": str(error)}
            result.update(source_case_id=case["id"], case_sha256=source_case_digest,
                          case_hash_verified="case_sha256" in expectation,
                          effective_case_sha256=effective_case_digest, effective_case=effective_config,
                          requested_runtime_config={"model": args.model, "effort": args.effort,
                                                    "turn_timeout": args.turn_timeout, "trace_routes": args.trace_routes})
            result["verdicts"] = evaluate_case(result, expectation, args.verify_outcomes)
            if ((workflow_requested and result["verdicts"]["workflow"]["status"] == "unverified")
                    or (args.verify_outcomes and result["verdicts"]["outcome"]["status"] == "unverified")):
                unverified_requested = True
            if expectation:
                result["expectation_sha256"] = hashlib.sha256(
                    json.dumps(expectation, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            results.append(result)
            verdicts = result["verdicts"]
            print(f"[{run['id']}] tour={verdicts['turn']} workflow={verdicts['workflow']['status']} "
                  f"résultat={verdicts['outcome']['status']} ({result.get('wall_seconds', 0)}s)", flush=True)
            write_summary(output, results, selected_case_ids)
    write_summary(output, results, selected_case_ids)
    if any(result["status"] != "completed" for result in results):
        return 2 if any(result["status"] == "needs_input" for result in results) else 1
    if any(result["verdicts"][stage]["status"] == "fail"
           for result in results for stage in ("workflow", "outcome")):
        return 1
    if unverified_requested:
        return 2
    print(f"résumé : {output / 'summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as error:
        print(f"verify-behavior: {error}", file=sys.stderr)
        raise SystemExit(1)
