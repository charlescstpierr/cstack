"""Opt-in tests against a real agit CLI; no Hub or native runtime is exercised."""

import json
import os
import sqlite3
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "plugins/cstack/skills/cstack/scripts/session-bridge.sh"
AGIT_BINARY = os.environ.get("CSTACK_AGIT_BINARY")
SID = "aaaaaaaa-0000-4000-8000-000000000001"
TARGET = "fixture/qa@source"


@unittest.skipUnless(AGIT_BINARY, "set CSTACK_AGIT_BINARY to run real-CLI fixture tests")
class SessionBridgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.store = self.root / "agit"
        credentials = self.store / "credentials"
        credentials.mkdir(parents=True)
        # Same offline author fixture as upstream tests. This is not a Hub login.
        (credentials / "127.0.0.1_1.json").write_text(json.dumps({
            "username": "fixture", "email": None, "hub": "http://127.0.0.1:1",
            "access_token": "synthetic", "access_expires_at": "2099-01-01T00:00:00Z",
            "refresh_token": "synthetic", "refresh_expires_at": "2099-01-01T00:00:00Z",
        }))
        self.binary = Path(AGIT_BINARY).resolve()
        self.assertTrue(self.binary.is_file(), f"agit binary missing: {self.binary}")
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "agit").symlink_to(self.binary)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("AGIT_")}
        self.env.update({
            "PATH": f'{bin_dir}:{os.environ.get("PATH", "")}',
            "AGIT_HOME": str(self.store), "AGIT_HUB_URL": "http://127.0.0.1:1",
            "AGIT_USE_SYSTEM_GIT": "1", "AGIT_SECRETS_KEYSTORE": "file",
            "CODEX_HOME": str(self.root / "codex"),
            "CLAUDE_CONFIG_DIR": str(self.root / "claude"),
            "XDG_DATA_HOME": str(self.root / "xdg"),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0", "CI": "1", "AGIT_TUI": "0", "NO_COLOR": "1",
        })
        version = self.cli("--version").stdout.strip().split()[-1]
        (self.store / "cli-update.json").write_text(json.dumps({
            "checked_at": int(time.time()), "latest": version,
        }))
        self.cli("init", "qa", "--no-bind", "--auto-push=false")
        self.repo = self.store / "repos/fixture/qa"

    def run_command(self, command, success=True):
        result = subprocess.run(command, cwd=self.work, env=self.env,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def cli(self, *args):
        return self.run_command([str(self.binary), "--quiet", *args])

    def bridge(self, *args, success=True):
        return self.run_command(["bash", str(BRIDGE), *args], success=success)

    def git(self, *args):
        return self.run_command(["git", "-C", str(self.repo), *args]).stdout.strip()

    def write_source(self, runtime):
        if runtime == "claude-code":
            path = self.root / "claude/projects/fixture" / f"{SID}.jsonl"
            messages = [
                ("user", "u1", "BRIDGE-PROMPT"),
                ("assistant", "a1", [
                    {"type": "text", "text": "BRIDGE-ANSWER"},
                    {"type": "tool_use", "id": "call-1", "name": "exec_command",
                     "input": {"cmd": "printf BRIDGE-TOOL"}},
                ]),
                ("user", "u2", [{"type": "tool_result", "tool_use_id": "call-1",
                                    "content": "BRIDGE-TOOL-OUTPUT"}]),
                ("assistant", "a2", [{"type": "text", "text": "BRIDGE-DONE"}]),
            ]
            records = [{"type": role, "sessionId": SID, "cwd": str(self.work), "uuid": uid,
                        "message": {"role": role, "content": content}}
                       for role, uid, content in messages]
        else:
            path = self.root / "codex/sessions/2026/01/01" / f"rollout-2026-01-01T00-00-00-{SID}.jsonl"
            records = [{"type": "session_meta", "payload": {
                "id": SID, "cwd": str(self.work), "source": "cli", "originator": "codex_cli_rs",
            }}]
            payloads = [
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "BRIDGE-PROMPT"}]},
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "BRIDGE-ANSWER"}]},
                {"type": "function_call", "name": "exec_command", "call_id": "call-1",
                 "arguments": json.dumps({"cmd": "printf BRIDGE-TOOL"})},
                {"type": "function_call_output", "call_id": "call-1", "output": "BRIDGE-TOOL-OUTPUT"},
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "BRIDGE-DONE"}]},
            ]
            records.extend({"type": "response_item", "payload": payload} for payload in payloads)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        return path

    def adopt(self, runtime):
        source = self.write_source(runtime)
        original = source.read_bytes()
        self.bridge("lineage", runtime, SID, TARGET)
        self.assertEqual(self.git("branch", "--list", "source"), "")
        self.bridge("import", runtime, SID, TARGET, "independent")
        self.git("show-ref", "--verify", "refs/heads/source")
        exported = self.cli("export", TARGET, "--format", "jsonl").stdout
        self.assertEqual([json.loads(line) for line in exported.splitlines()],
                         [json.loads(line) for line in original.splitlines()])
        self.assertEqual(source.read_bytes(), original)
        return source

    def adopt_opencode(self):
        path = self.root / "xdg/opencode/opencode.db"
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path) as database:
            database.executescript("""
                CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT NOT NULL);
                CREATE TABLE session (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, parent_id TEXT,
                    directory TEXT NOT NULL, time_created INTEGER NOT NULL, time_updated INTEGER NOT NULL, version TEXT NOT NULL);
                CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, time_created INTEGER NOT NULL, data TEXT NOT NULL);
                CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT NOT NULL, session_id TEXT NOT NULL, time_created INTEGER NOT NULL, data TEXT NOT NULL);
            """)
            database.execute("INSERT INTO project VALUES (?, ?)", ("fixture", str(self.work)))
            database.execute("INSERT INTO session VALUES (?, ?, NULL, ?, 100, 190, ?)",
                             (SID, "fixture", str(self.work), "1.18.13"))
            for mid, role, created in [("u1", "user", 110), ("a1", "assistant", 120)]:
                data = {"role": role, "time": {"created": created}}
                if role == "assistant":
                    data.update(parentID="u1", finish="stop", time={"created": 120, "completed": 190})
                database.execute("INSERT INTO message VALUES (?, ?, ?, ?)", (mid, SID, created, json.dumps(data)))
            parts = [
                ("p1", "u1", 111, {"type": "text", "text": "BRIDGE-PROMPT"}),
                ("p2", "a1", 121, {"type": "text", "text": "BRIDGE-ANSWER"}),
                ("p3", "a1", 122, {"type": "tool", "tool": "exec_command", "callID": "call-1", "state": {
                    "status": "completed", "input": {"cmd": "printf BRIDGE-TOOL"},
                    "output": "BRIDGE-TOOL-OUTPUT", "metadata": {}, "time": {"start": 122, "end": 123},
                }}),
                ("p4", "a1", 124, {"type": "text", "text": "BRIDGE-DONE"}),
            ]
            for pid, mid, created, data in parts:
                database.execute("INSERT INTO part VALUES (?, ?, ?, ?, ?)", (pid, mid, SID, created, json.dumps(data)))
        original = path.read_bytes()
        self.bridge("lineage", "opencode", SID, TARGET)
        self.bridge("import", "opencode", SID, TARGET, "independent")
        self.git("show-ref", "--verify", "refs/heads/source")
        self.assertEqual(path.read_bytes(), original)
        return path

    def test_native_resume_and_historic_fork(self):
        source = self.adopt("claude-code")
        original = source.read_bytes()
        self.bridge("resume", TARGET, "--no-launch")
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(len(list((self.root / "claude").rglob("*.jsonl"))), 1)
        new_turn = [
            {"type": "user", "sessionId": SID, "cwd": str(self.work), "uuid": "u3",
             "message": {"role": "user", "content": "BRIDGE-NEXT-PROMPT"}},
            {"type": "assistant", "sessionId": SID, "cwd": str(self.work), "uuid": "a3",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "BRIDGE-NEXT-ANSWER"}]}},
        ]
        with source.open("a") as stream:
            stream.write("".join(json.dumps(record) + "\n" for record in new_turn))
        self.bridge("checkpoint", TARGET, "second fixture turn")
        self.assertIn("BRIDGE-NEXT-ANSWER", self.cli("export", TARGET).stdout)
        head = self.git("rev-parse", "refs/heads/source")
        self.bridge("fork", TARGET + "#1", "historic", "codex", "--accept-loss", "--no-launch")
        self.git("show-ref", "--verify", "refs/heads/historic")
        materialized = next((self.root / "codex").rglob("*.jsonl")).read_text()
        self.assertIn("BRIDGE-DONE", materialized)
        self.assertNotIn("BRIDGE-NEXT-ANSWER", materialized)
        self.assertEqual(self.git("rev-parse", "refs/heads/source"), head)

    def verify_conversion(self, runtime, destination):
        source = self.adopt_opencode() if runtime == "opencode" else self.adopt(runtime)
        original = source.read_bytes()
        self.bridge("resume", TARGET, destination, "--accept-loss", "--no-launch")
        paths = list((self.root / ("codex" if destination == "codex" else "claude")).rglob("*.jsonl"))
        self.assertEqual(len(paths), 1)
        materialized = paths[0].read_text()
        for marker in ["BRIDGE-PROMPT", "BRIDGE-ANSWER", "BRIDGE-DONE", "printf BRIDGE-TOOL", "BRIDGE-TOOL-OUTPUT"]:
            self.assertIn(marker, materialized)
        records = [json.loads(line) for line in materialized.splitlines()]
        if destination == "codex":
            calls = [record["payload"] for record in records if record.get("payload", {}).get("type") == "function_call"]
            outputs = [record["payload"] for record in records if record.get("payload", {}).get("type") == "function_call_output"]
            self.assertEqual(json.loads(calls[0]["arguments"]), {"cmd": "printf BRIDGE-TOOL"})
            self.assertEqual(outputs[0]["call_id"], calls[0]["call_id"])
            self.assertEqual(outputs[0]["output"], "BRIDGE-TOOL-OUTPUT")
        else:
            parts = [part for record in records for part in record.get("message", {}).get("content", []) if isinstance(part, dict)]
            calls = [part for part in parts if part.get("type") == "tool_use"]
            outputs = [part for part in parts if part.get("type") == "tool_result"]
            self.assertEqual(calls[0]["input"], {"cmd": "printf BRIDGE-TOOL"})
            self.assertEqual(outputs[0]["tool_use_id"], calls[0]["id"])
            self.assertEqual(outputs[0]["content"], "BRIDGE-TOOL-OUTPUT")
        self.assertEqual(source.read_bytes(), original)

    def test_claude_to_codex_preparation(self):
        self.verify_conversion("claude-code", "codex")

    def test_codex_to_claude_preparation(self):
        self.verify_conversion("codex", "claude-code")

    def test_opencode_to_codex_preparation(self):
        self.verify_conversion("opencode", "codex")

    def test_opencode_to_claude_preparation(self):
        self.verify_conversion("opencode", "claude-code")

    def test_auto_push_preference_blocks_real_import(self):
        self.write_source("claude-code")
        self.cli("config", "--repo", "fixture/qa", "push.auto", "true")
        head = self.git("rev-parse", "HEAD")
        refused = self.bridge("import", "claude-code", SID, TARGET, "independent", success=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("push.auto", refused.stderr)
        self.assertEqual(self.git("branch", "--list", "source"), "")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)


if __name__ == "__main__":
    unittest.main()
