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
