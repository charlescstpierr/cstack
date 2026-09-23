from __future__ import annotations

import json
import os
import re
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
    env["GITHUB_RUN_ATTEMPT"] = "2"
    env["GITHUB_REPOSITORY"] = "example-org/example-repo"
    env["GITHUB_SERVER_URL"] = "https://github.com"
    if shims:
        shim_dir = payload_path.parents[2] / "bin"
        shim_dir.mkdir(exist_ok=True)
        for command in ("git", "gh"):
            target = shim_dir / command
            target.write_text(
                f"#!/usr/bin/env sh\nprintf '%s\\n' \"$0 $*\" >> {payload_path.parents[2] / 'shim.log'}\nexit 0\n",
                encoding="utf-8",
            )
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

            for evidence in ([], ["/tmp/before.png"], ["", "/tmp/after.png"], [" ", "\t"]):
                with self.subTest(evidence=evidence):
                    result = run_workflow_script(script, output, reproduce_payload(evidence=evidence))
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("requires before-and-after evidence paths", result.stderr)

            (output.parent / "durable-reproduce").mkdir(exist_ok=True)
            (output.parent / "durable-reproduce/manifest.json").write_text("{}", encoding="utf-8")
            passed = run_workflow_script(
                script,
                output,
                reproduce_payload(evidence=["/tmp/before.png", "/tmp/after.png"]),
                shims=True,
            )
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            shim_log = (Path(directory) / "shim.log").read_text(encoding="utf-8")
            self.assertIn("checkout -b intake/issue-123-456-2", shim_log)

    def test_reproduce_evidence_is_staged_before_comments_or_draft_pr(self) -> None:
        script = workflow_script("Stage reproduce evidence")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / ".cstack/intake/reproduce-output.json"
            output.parent.mkdir(parents=True)
            for name in ("run-context.json", "source-issue.json", "tracker-issues-all.json", "prs-all.json"):
                (output.parent / name).write_text("{}", encoding="utf-8")
            (output.parent / "commits.txt").write_text("abc123 fix\n", encoding="utf-8")
            before = root / "before.png"
            after = root / "after.png"
            before.write_text("before", encoding="utf-8")
            after.write_text("after", encoding="utf-8")

            result = run_workflow_script(
                script,
                output,
                reproduce_payload(
                    evidence=[str(before), str(after), "https://github.com/example-org/example-repo/actions/runs/456"],
                ),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            staged = output.parent / "durable-reproduce"
            self.assertTrue((staged / "manifest.json").is_file())
            self.assertTrue((staged / "files/evidence-1-before.png").is_file())
            self.assertTrue((staged / "files/evidence-2-after.png").is_file())
            self.assertIn("actions/runs/456", (staged / "evidence-urls.txt").read_text(encoding="utf-8"))

    def test_reproduce_evidence_staging_fails_closed_for_missing_local_file(self) -> None:
        script = workflow_script("Stage reproduce evidence")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / ".cstack/intake/reproduce-output.json"
            output.parent.mkdir(parents=True)
            for name in ("run-context.json", "source-issue.json", "tracker-issues-all.json", "prs-all.json"):
                (output.parent / name).write_text("{}", encoding="utf-8")
            (output.parent / "commits.txt").write_text("abc123 fix\n", encoding="utf-8")

            result = run_workflow_script(
                script,
                output,
                reproduce_payload(evidence=[str(root / "missing.png"), "https://example.test/after.png"]),
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("evidence path is not a file", result.stderr)

    def test_workflow_snapshots_all_state_issue_pr_and_commit_signals(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("gh issue list --limit 1000 --state all", workflow)
        self.assertIn("> .cstack/intake/tracker-issues-all.json", workflow)
        self.assertIn("gh pr list --limit 1000 --state all", workflow)
        self.assertIn("> .cstack/intake/prs-all.json", workflow)
        self.assertIn("git log --oneline --decorate -n 200 > .cstack/intake/commits.txt", workflow)

    def test_snapshot_source_issue_requires_github_repository_slug_match(self) -> None:
        script = workflow_script("Snapshot source issue")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / ".cstack/intake/unused.json"
            config = root / ".github/cstack/intake/configuration.yaml"
            config.parent.mkdir(parents=True)
            config.write_text('source:\n  repository: "other-org/example-repo"\n', encoding="utf-8")

            failed = run_workflow_script(script, output, {}, shims=True)
            self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
            self.assertIn("source.repository must match GITHUB_REPOSITORY", failed.stderr)

            config.write_text('source:\n  repository: "example-org/example-repo"\n', encoding="utf-8")
            passed = run_workflow_script(script, output, {}, shims=True)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertTrue((output.parent / "run-context.json").is_file())

    def test_installed_intake_files_are_committed_outside_ignored_cstack(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        required_files = re.findall(r"^            (\.github/cstack/intake/[^\s]+)", workflow, flags=re.MULTILINE)
        self.assertIn(".github/cstack/intake/configuration.yaml", required_files)
        self.assertIn(".github/cstack/intake/prompts/triage.md", required_files)
        self.assertIn(".github/cstack/intake/prompts/reproduce.md", required_files)
        self.assertTrue(all(not path.startswith(".cstack/") for path in required_files))

    def test_example_configuration_uses_github_repository_slug_format(self) -> None:
        config = ROOT / "plugins/cstack/automations/intake/templates/configuration.example.yaml"
        text = config.read_text(encoding="utf-8")

        self.assertIn('repository: "example-org/example-repo"', text)
        self.assertNotIn('source:\n  repository: "https://github.com/example-org/example-repo"', text)


if __name__ == "__main__":
    unittest.main()
