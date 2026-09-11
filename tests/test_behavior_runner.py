import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "verify-behavior.py"
SPEC = importlib.util.spec_from_file_location("verify_behavior", MODULE_PATH)
verify_behavior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_behavior)


def state():
    return {
        "child_ids": [],
        "messages": [],
        "message_indices": {},
        "questions": [],
        "question_keys": set(),
        "dispatch_metadata": [],
        "dispatch_indices": {},
        "metadata_gaps": [],
        "actual_commands": [],
        "token_usage": [],
        "token_usage_keys": set(),
    }


class BehaviorRunnerTests(unittest.TestCase):
    def test_rejects_overlapping_or_nonempty_output_before_native_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Read only."}]))
            evidence = root / "evidence"
            evidence.mkdir()
            saved = evidence / "summary.json"
            saved.write_text("preserve previous evidence")
            with patch.object(verify_behavior, "build_command") as build:
                for output in (project, project / "results", root, evidence):
                    with self.subTest(output=output), self.assertRaises(verify_behavior.HarnessError):
                        verify_behavior.main(["--cases", str(cases), "--output", str(output)])
                build.assert_not_called()
            self.assertEqual(saved.read_text(), "preserve previous evidence")

    def test_dispatch_metadata_is_recorded_separately_from_effective_metadata(self):
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "parent",
                    "item": {
                        "type": "collabAgentToolCall",
                        "id": "dispatch-1",
                        "tool": "spawnAgent",
                        "status": "completed",
                        "receiverThreadIds": ["closed-child"],
                        "model": "model-requested",
                        "reasoningEffort": "max",
                    },
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["child_ids"], ["closed-child"])
        self.assertEqual(current["dispatch_metadata"][0]["requested_model"], "model-requested")
        self.assertNotIn("effective_model", current["dispatch_metadata"][0])

    def test_closed_child_thread_is_a_metadata_gap_not_case_failure(self):
        class ClosedChildServer:
            def request(self, *args, **kwargs):
                raise verify_behavior.HarnessError("thread not loaded: child")

        current = state()
        metadata = verify_behavior.capture_thread_metadata(
            ClosedChildServer(), "child", 1, current, "parent", "child"
        )
        self.assertIsNone(metadata)
        self.assertEqual(current["metadata_gaps"][0]["thread_id"], "child")
        self.assertIn("thread/read unavailable", current["metadata_gaps"][0]["reason"])

    def test_agent_message_with_null_questions_is_not_input(self):
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/started",
                "params": {
                    "threadId": "parent",
                    "item": {"type": "agentMessage", "id": "m1", "text": "", "questions": None},
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["questions"], [])

    def test_case_ephemeral_defaults_true_and_allows_opt_in_false(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            cases.write_text(json.dumps([
                {"id": "default", "cwd": str(project), "prompt": "Read only."},
                {"id": "persisted", "cwd": str(project), "prompt": "Spawn once.", "ephemeral": False},
            ]))
            parsed = verify_behavior.read_cases(cases)
            self.assertTrue(parsed[0]["ephemeral"])
            self.assertFalse(parsed[1]["ephemeral"])

    def test_case_ephemeral_must_be_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            cases.write_text(json.dumps([{
                "id": "bad",
                "cwd": str(project),
                "prompt": "Read only.",
                "ephemeral": "false",
            }]))
            with self.assertRaises(verify_behavior.HarnessError):
                verify_behavior.read_cases(cases)

    def test_persisted_case_archives_harness_thread_after_metadata(self):
        class FakeServer:
            requests = []

            def __init__(self, *args):
                self.reads = 0

            def request(self, method, params, timeout, on_event):
                self.requests.append((method, params.copy()))
                if method == "thread/start":
                    return {"threadId": "parent"}
                if method == "turn/start":
                    return {"turnId": "turn"}
                if method == "thread/read":
                    return {"thread": {"id": params["threadId"], "model": "model"}}
                return {}

            def notify(self, *args):
                pass

            def read(self, deadline):
                self.reads += 1
                return {
                    "method": "turn/completed",
                    "params": {"threadId": "parent", "turn": {"id": "turn", "status": "completed"}},
                }

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            output = root / "output"
            case = {"id": "persisted", "cwd": project, "prompts": ["Read only."], "sandbox": "read-only", "ephemeral": False}
            with patch.object(verify_behavior, "AppServer", FakeServer):
                result = verify_behavior.run_case(case, output, ["codex"], None, None, 1)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["archived_thread_ids"], ["parent"])
            self.assertIn(("thread/archive", {"threadId": "parent"}), FakeServer.requests)
            self.assertIn(("thread/start", {
                "cwd": str(project),
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": False,
                "developerInstructions": verify_behavior.NEUTRAL_INSTRUCTIONS,
            }), FakeServer.requests)

    def test_persisted_case_archives_parent_after_needs_input(self):
        class NeedsInputServer:
            requests = []

            def __init__(self, *args):
                pass

            def request(self, method, params, timeout, on_event):
                self.requests.append((method, params.copy()))
                if method == "thread/start":
                    return {"threadId": "parent"}
                if method == "turn/start":
                    raise verify_behavior.NeedsInput("native request requires input: item/requestUserInput")
                return {}

            def notify(self, *args):
                pass

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            output = root / "output"
            case = {"id": "persisted", "cwd": project, "prompts": ["Read only."], "sandbox": "read-only", "ephemeral": False}
            with patch.object(verify_behavior, "AppServer", NeedsInputServer):
                result = verify_behavior.run_case(case, output, ["codex"], None, None, 1)
            self.assertEqual(result["status"], "needs_input")
            self.assertEqual(result["error"], "native request requires input: item/requestUserInput")
            self.assertEqual(result["archived_thread_ids"], ["parent"])
            self.assertEqual(result["cleanup_errors"], [])
            self.assertIn(("thread/archive", {"threadId": "parent"}), NeedsInputServer.requests)

    def test_archive_failure_is_reported_without_hiding_turn_failure(self):
        class ArchiveFailureServer:
            requests = []

            def __init__(self, *args):
                pass

            def request(self, method, params, timeout, on_event):
                self.requests.append((method, params.copy()))
                if method == "thread/start":
                    return {"threadId": "parent"}
                if method == "turn/start":
                    raise verify_behavior.NeedsInput("native request requires input: item/requestUserInput")
                if method == "thread/archive":
                    raise verify_behavior.HarnessError("archive denied")
                return {}

            def notify(self, *args):
                pass

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            output = root / "output"
            case = {"id": "persisted", "cwd": project, "prompts": ["Read only."], "sandbox": "read-only", "ephemeral": False}
            with patch.object(verify_behavior, "AppServer", ArchiveFailureServer):
                result = verify_behavior.run_case(case, output, ["codex"], None, None, 1)
            self.assertEqual(result["status"], "needs_input")
            self.assertEqual(result["error"], "native request requires input: item/requestUserInput")
            self.assertEqual(result["archived_thread_ids"], [])
            self.assertEqual(result["cleanup_errors"], [{
                "operation": "thread/archive",
                "thread_id": "parent",
                "error": "archive denied",
            }])

    def test_timeout_interrupts_active_turn_before_archive(self):
        class TimeoutServer:
            requests = []

            def __init__(self, *args):
                self.reads = 0

            def request(self, method, params, timeout, on_event):
                self.requests.append((method, params.copy(), timeout))
                if method == "thread/start":
                    return {"threadId": "parent"}
                if method == "turn/start":
                    return {"turnId": "turn"}
                if method == "turn/interrupt":
                    on_event({
                        "method": "turn/completed",
                        "params": {"threadId": "parent", "turn": {"id": "turn", "status": "interrupted"}},
                    })
                    return {}
                return {}

            def notify(self, *args):
                pass

            def read(self, deadline):
                self.reads += 1
                if self.reads == 1:
                    raise TimeoutError("app-server response timeout")
                raise AssertionError("turn completion was already received during turn/interrupt")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            output = root / "output"
            case = {"id": "persisted", "cwd": project, "prompts": ["Read only."], "sandbox": "read-only", "ephemeral": False}
            with patch.object(verify_behavior, "AppServer", TimeoutServer):
                result = verify_behavior.run_case(case, output, ["codex"], None, None, 90)
            self.assertEqual(result["status"], "failed_turn")
            self.assertEqual(result["error"], "app-server response timeout")
            request_names = [request[0] for request in TimeoutServer.requests]
            self.assertLess(request_names.index("turn/interrupt"), request_names.index("thread/archive"))
            self.assertIn(("turn/interrupt", {"threadId": "parent", "turnId": "turn"}, 15), TimeoutServer.requests)
            self.assertEqual(result["archived_thread_ids"], ["parent"])

    def test_keyboard_interrupt_during_archive_still_closes_server(self):
        class KeyboardInterruptServer:
            closed = False

            def __init__(self, *args):
                pass

            def request(self, method, params, timeout, on_event):
                if method == "thread/start":
                    return {"threadId": "parent"}
                if method == "turn/start":
                    return {"turnId": "turn"}
                if method == "thread/read":
                    return {"thread": {"id": params["threadId"], "model": "model"}}
                if method == "thread/archive":
                    raise KeyboardInterrupt()
                return {}

            def notify(self, *args):
                pass

            def read(self, deadline):
                return {
                    "method": "turn/completed",
                    "params": {"threadId": "parent", "turn": {"id": "turn", "status": "completed"}},
                }

            def close(self):
                self.__class__.closed = True

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            output = root / "output"
            case = {"id": "persisted", "cwd": project, "prompts": ["Read only."], "sandbox": "read-only", "ephemeral": False}
            with patch.object(verify_behavior, "AppServer", KeyboardInterruptServer):
                with self.assertRaises(KeyboardInterrupt):
                    verify_behavior.run_case(case, output, ["codex"], None, None, 1)
            self.assertTrue(KeyboardInterruptServer.closed)

    def test_main_fails_completed_case_with_cleanup_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            cases = root / "cases.json"
            output = root / "output"
            cases.write_text(json.dumps([{"id": "one", "cwd": str(project), "prompt": "Read only."}]))
            result = {
                "id": "one",
                "cwd": str(project),
                "status": "completed",
                "error": None,
                "cleanup_errors": [{"operation": "thread/archive", "thread_id": "parent", "error": "archive denied"}],
            }
            with patch.object(verify_behavior, "build_command", return_value=["codex"]):
                with patch.object(verify_behavior, "run_case", return_value=result):
                    exit_code = verify_behavior.main(["--cases", str(cases), "--output", str(output)])
            self.assertEqual(exit_code, 1)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["cases"][0]["status"], "completed")
            self.assertIsNone(summary["cases"][0]["error"])
            self.assertEqual(summary["cases"][0]["cleanup_errors"], result["cleanup_errors"])

    def test_native_user_input_rpc_stops_without_answer(self):
        current = state()
        with self.assertRaises(verify_behavior.NeedsInput):
            verify_behavior.update_state(
                {
                    "id": 42,
                    "method": "item/requestUserInput",
                    "params": {"questions": [{"id": "choice"}]},
                },
                current,
                "parent",
            )
        self.assertEqual(current["questions"][0]["method"], "item/requestUserInput")

    def test_nonempty_async_questions_are_recorded_without_stopping(self):
        current = state()
        verify_behavior.update_state(
            {
                "method": "item/started",
                "params": {
                    "threadId": "parent",
                    "item": {
                        "type": "agentMessage",
                        "id": "m1",
                        "text": "question pending",
                        "questions": [{"id": "choice", "text": "Which policy?"}],
                    },
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["questions"][0][0]["id"], "choice")
        self.assertEqual(current["messages"], ["question pending"])
        verify_behavior.update_state(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "parent",
                    "item": {"type": "agentMessage", "id": "m1", "text": "final answer", "questions": []},
                },
            },
            current,
            "parent",
        )
        self.assertEqual(current["messages"], ["final answer"])


if __name__ == "__main__":
    unittest.main()
