import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "plugins/cstack/automations/intake/templates/github-intake.yml"


def workflow_script(step_name: str) -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    step = f"- name: {step_name}"
    for index, line in enumerate(lines):
        if line.strip() != step:
            continue
        for run_index in range(index + 1, len(lines)):
            if lines[run_index].strip() != "run: |":
                continue
            body = []
            for body_line in lines[run_index + 1:]:
                if body_line.startswith("          "):
                    body.append(body_line[10:])
                    continue
                if body_line.strip() == "":
                    body.append("")
                    continue
                break
            return "\n".join(body)
    raise AssertionError(f"missing workflow step: {step_name}")


def run_workflow_script(
    script: str,
    payload_path: Path,
    payload: dict,
    *,
    shims: bool = False,
) -> subprocess.CompletedProcess[str]:
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    script = script.replace("${{ steps.issue.outputs.number }}", "123")
    script = script.replace("${{ needs.triage.outputs.issue_number }}", "123")
    env = os.environ.copy()
    env["GITHUB_OUTPUT"] = str(payload_path.parent / "github-output")
    env["GITHUB_RUN_ID"] = "456"
    if shims:
        shim_dir = payload_path.parents[2] / "bin"
        shim_dir.mkdir()
        for command in ("git", "gh"):
            target = shim_dir / command
            target.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
            target.chmod(target.stat().st_mode | stat.S_IXUSR)
        env["PATH"] = f"{shim_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        ["bash", "-c", script],
        cwd=payload_path.parents[2],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def triage_payload(marker: str, body: str | None) -> dict:
    return {
        "classification": "bug",
        "marker": marker,
        "comment_body": body,
        "create_tracker": False,
        "tracker_title": "",
        "tracker_body": "",
        "tracker_labels": [],
        "tracker_url": "",
        "source_permalink": "",
        "stop_reason": "",
    }


def reproduce_payload(
    *,
    outcome: str = "reproduced",
    mode: str = "fix",
    verify: str = "not_applicable",
    patch: str = "diff --git a/a b/a\n",
    evidence: list[str] | None = None,
) -> dict:
    return {
        "outcome": outcome,
        "mode": mode,
        "status_label": "",
        "source_comment_body": "",
        "evidence_paths": evidence or [],
        "patch": patch,
        "commit_message": "fix: intake",
        "pr_title": "Fix intake",
        "pr_body": "Before and after evidence captured.",
        "verify_verdict": verify,
        "existing_fix_url": "",
        "stop_reason": "",
    }


class IntakeWorkflowTests(unittest.TestCase):
    def test_bug_and_performance_triage_requires_nonempty_matching_marker_comment(self) -> None:
        script = workflow_script("Publish triage outputs")
        failures = [
            (triage_payload("[intake:bug]", ""), "requires a verdict comment"),
            (triage_payload("[intake:performance]", None), "requires a verdict comment"),
            (triage_payload("[intake:bug]", "Seen. [intake:bug] [intake:other]"), "exactly one marker"),
            (triage_payload("[intake:bug]", "Seen.\n[intake:other]"), "does not match"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / ".cstack/intake/triage-output.json"
            for payload, expected in failures:
                with self.subTest(payload=payload):
                    result = run_workflow_script(script, output, payload)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(expected, result.stderr)

    def test_other_triage_may_fail_closed_without_comment(self) -> None:
        script = workflow_script("Publish triage outputs")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / ".cstack/intake/triage-output.json"
            result = run_workflow_script(script, output, triage_payload("[intake:other]", ""))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matching_bug_triage_comment_passes(self) -> None:
        script = workflow_script("Publish triage outputs")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / ".cstack/intake/triage-output.json"
            result = run_workflow_script(script, output, triage_payload("[intake:bug]", "Reproducing.\n[intake:bug]"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_draft_pull_request_requires_two_nonempty_evidence_paths_only_when_eligible(self) -> None:
        script = workflow_script("Open draft pull request")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / ".cstack/intake/reproduce-output.json"
            skipped = run_workflow_script(script, output, reproduce_payload(outcome="blocked", patch="", evidence=[]))
            self.assertEqual(skipped.returncode, 0, skipped.stdout + skipped.stderr)

            for evidence in ([], ["/tmp/before.png"], ["", "/tmp/after.png"]):
                with self.subTest(evidence=evidence):
                    result = run_workflow_script(script, output, reproduce_payload(evidence=evidence))
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("requires before-and-after evidence paths", result.stderr)

            passed = run_workflow_script(
                script,
                output,
                reproduce_payload(evidence=["/tmp/before.png", "/tmp/after.png"]),
                shims=True,
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)


if __name__ == "__main__":
    unittest.main()
