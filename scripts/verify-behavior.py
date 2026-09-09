#!/usr/bin/env python3
"""Run isolated native Codex turns and preserve evidence for a blind judge."""

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
import time
import tomllib


DEFAULT_TURN_SECONDS = 300.0
MAX_TURN_SECONDS = 900.0
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
NEUTRAL_INSTRUCTIONS = (
    "Use the selected local bundle and project guidance. Use generic native agent "
    "roles. Follow the user prompt and current project scope. Do not use unrelated "
    "plugins or workflows."
)


class HarnessError(RuntimeError):
    pass


class NeedsInput(HarnessError):
    pass


def scrub(value):
    """Keep evidence useful while avoiding credentials in summary.json."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if (
                any(token in lowered for token in ("password", "secret", "api_key", "authorization", "cookie"))
                or lowered in {"token", "access_token", "refresh_token", "id_token", "session_token"}
            ):
                result[key] = "<REDACTED>"
            else:
                result[key] = scrub(item)
        return result
    if isinstance(value, list):
        return [scrub(item) for item in value]
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
            "reason": "thread/read unavailable; metadata not observed",
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
            raise HarnessError("app-server stdin is closed")
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
                    raise HarnessError(f"invalid app-server JSON: {error}") from error
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("app-server response timeout")
            if not self.selector.select(min(0.25, remaining)):
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise HarnessError(f"app-server closed with code {self.process.poll()}")
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
                raise NeedsInput(f"native request requires input: {message.get('method')}")
            if isinstance(message, dict) and message.get("id") == request_id:
                if "error" in message:
                    raise HarnessError(f"{method} failed: {scrub(message['error'])}")
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
        raise NeedsInput(f"native request requires input: {message.get('method', 'question')}")

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


def config_names():
    config_path = Path("/home/ubuntu/.codex/config.toml")
    if not config_path.exists():
        return [], []
    try:
        config = tomllib.loads(config_path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise HarnessError(f"cannot read Codex config: {config_path}") from error
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
        raise HarnessError(f"cannot read cases JSON: {path}") from error
    if not isinstance(payload, list) or not payload:
        raise HarnessError("cases JSON must be a non-empty array")
    cases = []
    ids = set()
    for row in payload:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not SAFE_ID.fullmatch(row["id"]):
            raise HarnessError("each case needs a safe string id")
        case_id = row["id"]
        if case_id in ids:
            raise HarnessError(f"duplicate case id: {case_id}")
        ids.add(case_id)
        cwd = Path(row.get("cwd", "")).expanduser().resolve()
        if not cwd.is_dir():
            raise HarnessError(f"case cwd is not a directory: {cwd}")
        has_prompt = isinstance(row.get("prompt"), str)
        has_prompts = isinstance(row.get("prompts"), list)
        if has_prompt == has_prompts:
            raise HarnessError(f"{case_id}: provide exactly one of prompt or prompts")
        prompts = [row["prompt"]] if has_prompt else row["prompts"]
        if not prompts or not all(isinstance(prompt, str) for prompt in prompts):
            raise HarnessError(f"{case_id}: prompts must be a non-empty string array")
        sandbox = row.get("sandbox", "workspace-write")
        if not isinstance(sandbox, str) or not sandbox:
            raise HarnessError(f"{case_id}: sandbox must be a string")
        cases.append({"id": case_id, "cwd": cwd, "prompts": prompts, "sandbox": sandbox})
    return cases


def run_case(case, output, command, model, effort, timeout):
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
    try:
        server = AppServer(command, case["cwd"], raw_path, stderr_path)
        server.request("initialize", {"clientInfo": {"name": "cstack-behavior-runner", "version": "0.1.0"}}, timeout, lambda message: update_state(message, state, parent_thread))
        server.notify("initialized")
        thread_params = {
            "cwd": str(case["cwd"]), "approvalPolicy": "never", "sandbox": case["sandbox"],
            "ephemeral": True, "developerInstructions": NEUTRAL_INSTRUCTIONS,
        }
        if model:
            thread_params["model"] = model
        thread_result = server.request("thread/start", thread_params, timeout, lambda message: update_state(message, state, parent_thread))
        parent_thread = first(thread_result, ("threadId", "thread_id")) or first(first(thread_result, ("thread",)) or {}, ("id",))
        if not parent_thread:
            raise HarnessError("thread/start returned no thread id")
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
    return {
        "id": case["id"], "cwd": str(case["cwd"]), "sandbox": case["sandbox"],
        "input_prompts": case["prompts"], "status": status,
        "wall_seconds": round(time.monotonic() - started, 3),
        "before_project_hash": before, "after_project_hash": after,
        "project_hash_changed": before["sha256"] != after["sha256"],
        "hash_policy": {"excluded_directories": sorted(SKIP_DIRS), "included_cstack": True},
        "actual_commands": state["actual_commands"], "app_server_command": command,
        "questions": state["questions"], "native_child_thread_ids": state["child_ids"],
        "dispatch_metadata": state["dispatch_metadata"], "child_metadata": state.get("child_metadata", []),
        "metadata_gaps": state["metadata_gaps"],
        "token_usage": state["token_usage"], "after_turn_actual_metadata": state["after_turn_actual_metadata"],
        "turns": state["turns"], "error": error,
        "raw_stream": str(raw_path.resolve()), "stderr": str(stderr_path.resolve()),
    }


def write_summary(output, results, selected_case_ids):
    summary = {"cases": results, "selected_case_ids": selected_case_ids, "output": str(output)}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run isolated native Codex behavior-proof cases.")
    parser.add_argument("--cases", type=Path, required=True, help="JSON array of trusted cases")
    parser.add_argument("--output", type=Path, required=True, help="artifact directory outside each case cwd")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="run only this case id; repeatable")
    parser.add_argument("--model", help="optional native model override")
    parser.add_argument("--effort", help="optional native reasoning effort")
    parser.add_argument("--turn-timeout", type=float, default=DEFAULT_TURN_SECONDS, help="turn timeout in seconds, max 900")
    args = parser.parse_args(argv)
    if args.turn_timeout <= 0 or args.turn_timeout > MAX_TURN_SECONDS:
        parser.error("--turn-timeout must be between 0 and 900 seconds")
    cases = read_cases(args.cases)
    if args.case_ids:
        wanted = set(args.case_ids)
        unknown = wanted - {case["id"] for case in cases}
        if unknown:
            raise HarnessError(f"unknown case id: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case["id"] in wanted]
    output = args.output.expanduser().resolve()
    for case in cases:
        if output == case["cwd"] or case["cwd"] in output.parents or output in case["cwd"].parents:
            raise HarnessError(f"output must be outside case cwd: {case['id']}")
    if output.exists() and any(output.iterdir()):
        raise HarnessError("output must be absent or empty; refusing to overwrite evidence")
    output.mkdir(parents=True, exist_ok=True)
    command = build_command()
    results = []
    selected_case_ids = [case["id"] for case in cases]
    for case in cases:
        print(f"[{case['id']}] start", flush=True)
        try:
            result = run_case(case, output, command, args.model, args.effort, args.turn_timeout)
        except Exception as error:
            result = {"id": case["id"], "cwd": str(case["cwd"]), "status": "infra_error", "error": str(error)}
        results.append(result)
        print(f"[{case['id']}] {result['status']} ({result.get('wall_seconds', 0)}s)", flush=True)
        write_summary(output, results, selected_case_ids)
    write_summary(output, results, selected_case_ids)
    if any(result["status"] != "completed" for result in results):
        return 2 if any(result["status"] == "needs_input" for result in results) else 1
    print(f"summary: {output / 'summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as error:
        print(f"verify-behavior: {error}", file=sys.stderr)
        raise SystemExit(1)
