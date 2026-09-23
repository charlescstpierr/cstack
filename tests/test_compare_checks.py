"""Les comparaisons d'observations restent déterministes et ferment les inconnues."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/cstack/skills/cstack/scripts/compare-checks.py"
SPEC = importlib.util.spec_from_file_location("cstack_compare_checks", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
compare_checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare_checks)


COMMIT = "9d1d80fcb5defd81e32425dee7410cdad959d3fb"
HASH_A = "a" * 64
HASH_B = "b" * 64
PATCH_A = "1" * 64
PATCH_B = "2" * 64
MODEL_CHECK = "test_models.ModelSetupTests.test_customization_preserves_legacy_values_and_explicit_inheritance"
CRLF_CHECK = "test_project_setup.ProjectSetupTests.test_reapplying_the_same_plan_is_a_noop_and_gitignore_preserves_crlf"
MODEL_FAILURE = "AssertionError: Lists differ: [{}] != [{'model': 'gpt-6-astra'}]"
CRLF_FAILURE = "AssertionError: b'dist\\r\\n.cstack/\\n' != b'dist\\r\\n.cstack/\\r\\n'"
TEST_IDS = (MODEL_CHECK, CRLF_CHECK)
TEST_SOURCES = {
    MODEL_CHECK: Path("tests/test_models.py"),
    CRLF_CHECK: Path("tests/test_project_setup.py"),
}
COLLECTOR = r'''
import json
import sys
import traceback
import unittest


class RecordingResult(unittest.TestResult):
    def __init__(self, expected):
        super().__init__()
        self.expected = set(expected)
        self.observations = {}
        self.collection_errors = []

    def _record(self, test, outcome, error=""):
        test_id = test.id()
        self.observations.setdefault(test_id, []).append({
            "outcome": outcome,
            "evidence": error,
        })
        if test_id not in self.expected:
            self.collection_errors.append(test_id)

    @staticmethod
    def _error_text(error):
        return "".join(traceback.format_exception_only(error[0], error[1])).strip()

    def addSuccess(self, test):
        self._record(test, "pass")

    def addFailure(self, test, error):
        self._record(test, "fail", self._error_text(error))

    def addError(self, test, error):
        self._record(test, "error", self._error_text(error))

    def addSkip(self, test, reason):
        self._record(test, "skip", str(reason))

    def addUnexpectedSuccess(self, test):
        self._record(test, "error", "unexpected success")


requested = sys.argv[1:]
sys.path.insert(0, "tests")
loader = unittest.defaultTestLoader
suite = unittest.TestSuite()
for test_id in requested:
    suite.addTests(loader.loadTestsFromName(test_id))
result = RecordingResult(requested)
suite.run(result)
checks = []
for test_id in requested:
    checks.append({"id": test_id, "runs": result.observations.get(test_id, [])})
print(json.dumps({
    "inventory_complete": not result.collection_errors and all(
        test_id in result.observations for test_id in requested
    ),
    "checks": checks,
}, sort_keys=True))
'''


def run(outcome: str, evidence: str = "", count: int = 2):
    return [{"outcome": outcome, "evidence": evidence} for _ in range(count)]


def check(check_id: str, outcome: str, evidence: str = "", definition: Optional[str] = HASH_A, count: int = 2):
    return {
        "id": check_id,
        "definition_sha256": definition,
        "runs": run(outcome, evidence, count),
    }


def report(
    checks,
    *,
    patch_sha256=None,
    scope="unittest:target",
    environment="Python 3.14.4",
    inventory_complete=True,
):
    return {
        "version": 1,
        "revision": {"commit": COMMIT, "patch_sha256": patch_sha256},
        "scope": scope,
        "environment": environment,
        "inventory_complete": inventory_complete,
        "checks": checks,
    }


def report_for_observations(collected, definitions, patch_sha256):
    return report(
        [
            {
                "id": check_data["id"],
                "definition_sha256": definitions.get(check_data["id"]),
                "runs": check_data["runs"],
            }
            for check_data in collected["checks"]
        ],
        patch_sha256=patch_sha256,
        inventory_complete=collected["inventory_complete"],
    )


def by_id(result):
    return {item["id"]: item for item in result["checks"]}


class CompareChecksTests(unittest.TestCase):
    def test_recorded_green_to_red_mutation_is_a_regression(self):
        base = report([check(MODEL_CHECK, "pass")], patch_sha256=None)
        candidate = report([check(MODEL_CHECK, "fail", MODEL_FAILURE)], patch_sha256=PATCH_A)

        result = compare_checks.compare(base, candidate)

        self.assertEqual(result["status"], "regression")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "regression")
        self.assertEqual(
            by_id(result)[MODEL_CHECK]["candidate"]["runs"][0]["evidence"],
            MODEL_FAILURE,
        )

    def test_recorded_red_to_red_mutation_separates_new_failure_from_persistent_failure(self):
        base = report([
            check(MODEL_CHECK, "fail", MODEL_FAILURE),
            check(CRLF_CHECK, "pass"),
        ], patch_sha256=PATCH_A)
        candidate = report([
            check(CRLF_CHECK, "fail", CRLF_FAILURE),
            check(MODEL_CHECK, "fail", MODEL_FAILURE),
        ], patch_sha256=PATCH_B)

        result = compare_checks.compare(base, candidate)
        labels = by_id(result)

        self.assertEqual(result["status"], "regression")
        self.assertEqual(labels[MODEL_CHECK]["label"], "persistent_failure")
        self.assertEqual(labels[CRLF_CHECK]["label"], "regression")
        self.assertIn("ne prouve pas une cause préexistante", labels[MODEL_CHECK]["reasons"][0])

    def test_real_mutations_are_collected_by_fresh_subprocesses(self):
        clean = self._snapshot()
        mutant_a = self._snapshot(mutate_models=True)
        mutant_ab = self._snapshot(mutate_models=True, mutate_project=True)

        for test_id in TEST_IDS:
            self.assertEqual(
                by_id(clean)[test_id]["definition_sha256"],
                by_id(mutant_a)[test_id]["definition_sha256"],
            )
            self.assertEqual(
                by_id(clean)[test_id]["definition_sha256"],
                by_id(mutant_ab)[test_id]["definition_sha256"],
            )

        clean_to_a = compare_checks.compare(clean, mutant_a)
        a_to_ab = compare_checks.compare(mutant_a, mutant_ab)

        self.assertEqual(clean_to_a["status"], "regression")
        self.assertEqual(by_id(clean_to_a)[MODEL_CHECK]["label"], "regression")
        self.assertEqual(by_id(clean_to_a)[CRLF_CHECK]["label"], "no_difference_observed")
        self.assertEqual(a_to_ab["status"], "regression")
        self.assertEqual(by_id(a_to_ab)[MODEL_CHECK]["label"], "persistent_failure")
        self.assertEqual(by_id(a_to_ab)[CRLF_CHECK]["label"], "regression")
        self.assertEqual(
            by_id(a_to_ab)[CRLF_CHECK]["candidate"]["runs"][0]["evidence"],
            CRLF_FAILURE,
        )

    def test_failed_collection_cannot_become_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._copy_fixture(Path(directory))
            report = self._run_collector(fixture, TEST_IDS + ("tests.test_models.Missing",))
        self.assertFalse(report["inventory_complete"])
        self.assertEqual(report["checks"][-1]["runs"], [])
        snapshot = self._snapshot()
        invalid = report_for_observations(report, self._definition_hashes(), None)
        comparison = compare_checks.compare(snapshot, invalid)
        self.assertEqual(comparison["status"], "incomparable")

    def test_check_order_does_not_change_the_comparison(self):
        base = report([check(MODEL_CHECK, "pass"), check(CRLF_CHECK, "pass")])
        candidate = report([check(CRLF_CHECK, "pass"), check(MODEL_CHECK, "pass")])

        self.assertEqual(compare_checks.compare(base, candidate), compare_checks.compare(candidate, base))

    def test_hex_digest_case_does_not_change_a_comparison(self):
        base = report([check(MODEL_CHECK, "pass", definition=HASH_A)], patch_sha256=PATCH_A)
        candidate = report([check(MODEL_CHECK, "pass", definition=HASH_A.upper())], patch_sha256=PATCH_A.upper())
        candidate["revision"]["commit"] = COMMIT.upper()

        result = compare_checks.compare(base, candidate)

        self.assertEqual(result["status"], "no_difference_observed")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "no_difference_observed")
        self.assertTrue(any("la même révision est déclarée des deux côtés" in reason for reason in result["reasons"]))

    def test_changed_failure_evidence_is_not_preexisting(self):
        base = report([check(MODEL_CHECK, "fail", "AssertionError: old cause")])
        candidate = report([check(MODEL_CHECK, "fail", "AssertionError: new cause")], patch_sha256=PATCH_A)

        result = compare_checks.compare(base, candidate)

        self.assertEqual(result["status"], "changes_observed")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "failure_changed")

    def test_fixed_failure_still_needs_review(self):
        base = report([check(MODEL_CHECK, "fail", MODEL_FAILURE)])
        candidate = report([check(MODEL_CHECK, "pass")], patch_sha256=PATCH_A)

        result = compare_checks.compare(base, candidate)

        self.assertEqual(result["status"], "changes_observed")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "fixed_failure")

    def test_pass_duration_text_does_not_make_a_stable_pass_unstable(self):
        base = report([{
            "id": MODEL_CHECK,
            "definition_sha256": HASH_A,
            "runs": run("pass", "elapsed=0.10s") + run("pass", "elapsed=0.11s"),
        }])
        candidate = report([{
            "id": MODEL_CHECK,
            "definition_sha256": HASH_A,
            "runs": run("pass", "elapsed=0.20s") + run("pass", "elapsed=0.21s"),
        }], patch_sha256=PATCH_A)

        result = compare_checks.compare(base, candidate)

        self.assertEqual(result["status"], "no_difference_observed")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "no_difference_observed")
        self.assertFalse(any("la même révision est déclarée des deux côtés" in reason for reason in result["reasons"]))

    def test_inconsistent_repeated_failure_is_unstable(self):
        base = report([check(MODEL_CHECK, "pass")])
        candidate = report([{
            "id": MODEL_CHECK,
            "definition_sha256": HASH_A,
            "runs": [
                {"outcome": "fail", "evidence": "first cause"},
                {"outcome": "fail", "evidence": "second cause"},
            ],
        }], patch_sha256=PATCH_A)

        result = compare_checks.compare(base, candidate)

        self.assertEqual(result["status"], "unstable")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "unstable")

    def test_unknown_definition_and_single_pass_are_not_clean(self):
        unknown_base = report([check(MODEL_CHECK, "pass", definition=None)])
        unknown_candidate = report([check(MODEL_CHECK, "pass", definition=None)], patch_sha256=PATCH_A)
        unknown = compare_checks.compare(unknown_base, unknown_candidate)
        self.assertEqual(unknown["status"], "incomparable")
        self.assertEqual(by_id(unknown)[MODEL_CHECK]["label"], "definition_unknown")

        missing_base = report([check(MODEL_CHECK, "pass", definition=None)])
        missing_candidate = report([check(MODEL_CHECK, "pass", definition=HASH_A)], patch_sha256=PATCH_A)
        missing = compare_checks.compare(missing_base, missing_candidate)
        self.assertEqual(missing["status"], "incomparable")
        self.assertEqual(by_id(missing)[MODEL_CHECK]["label"], "definition_unknown")

        changed_base = report([check(MODEL_CHECK, "pass", definition=HASH_A)])
        changed_candidate = report([check(MODEL_CHECK, "pass", definition=HASH_B)], patch_sha256=PATCH_A)
        changed = compare_checks.compare(changed_base, changed_candidate)
        self.assertEqual(changed["status"], "changes_observed")
        self.assertEqual(by_id(changed)[MODEL_CHECK]["label"], "definition_changed")

        one_base = report([check(MODEL_CHECK, "pass", count=1)])
        one_candidate = report([check(MODEL_CHECK, "pass", count=1)], patch_sha256=PATCH_A)
        one = compare_checks.compare(one_base, one_candidate)
        self.assertEqual(one["status"], "incomparable")
        self.assertEqual(by_id(one)[MODEL_CHECK]["label"], "insufficient_observations")

    def test_added_and_removed_checks_are_conservative(self):
        base = report([check(MODEL_CHECK, "pass")])
        added_candidate = report([
            check(MODEL_CHECK, "pass"),
            check(CRLF_CHECK, "pass", definition=HASH_B),
        ], patch_sha256=PATCH_A)
        added = compare_checks.compare(base, added_candidate)
        self.assertEqual(added["status"], "changes_observed")
        self.assertEqual(by_id(added)[CRLF_CHECK]["label"], "added_check")

        removed_candidate = report([check(MODEL_CHECK, "pass")], patch_sha256=PATCH_A)
        removed_base = report([
            check(MODEL_CHECK, "pass"),
            check(CRLF_CHECK, "pass", definition=HASH_B),
        ])
        removed = compare_checks.compare(removed_base, removed_candidate)
        self.assertEqual(removed["status"], "incomparable")
        self.assertEqual(by_id(removed)[CRLF_CHECK]["label"], "removed_or_unobserved")

    def test_incomplete_inventory_and_metadata_mismatch_are_incomparable(self):
        base = report([check(MODEL_CHECK, "pass")], inventory_complete=False)
        candidate = report([check(MODEL_CHECK, "fail", MODEL_FAILURE)], patch_sha256=PATCH_A)
        incomplete = compare_checks.compare(base, candidate)
        self.assertEqual(incomplete["status"], "incomparable")
        self.assertEqual(by_id(incomplete)[MODEL_CHECK]["label"], "incomparable")

        mismatched = compare_checks.compare(
            report([check(MODEL_CHECK, "pass")]),
            report([check(MODEL_CHECK, "pass")], scope="unittest:other", patch_sha256=PATCH_A),
        )
        self.assertEqual(mismatched["status"], "incomparable")
        self.assertEqual(by_id(mismatched)[MODEL_CHECK]["label"], "incomparable")

    def test_skip_not_run_and_empty_inventory_are_not_empty_success(self):
        skipped = compare_checks.compare(
            report([check(MODEL_CHECK, "skip")]),
            report([check(MODEL_CHECK, "pass")], patch_sha256=PATCH_A),
        )
        self.assertEqual(skipped["status"], "incomparable")
        self.assertEqual(by_id(skipped)[MODEL_CHECK]["label"], "incomparable")

        empty = compare_checks.compare(report([]), report([], patch_sha256=PATCH_A))
        self.assertEqual(empty["status"], "incomparable")
        self.assertEqual(empty["checks"], [])

    def test_boundary_rejects_duplicates_unknown_outcomes_bad_hashes_and_extra_keys(self):
        valid = report([check(MODEL_CHECK, "pass")])
        malformed = dict(valid)
        malformed["version"] = True
        with self.assertRaises(compare_checks.ReportError):
            compare_checks.compare(malformed, valid)

        bad_run = report([check(MODEL_CHECK, "pass")])
        bad_run["checks"][0]["runs"][0]["outcome"] = "green"
        with self.assertRaises(compare_checks.ReportError):
            compare_checks.compare(bad_run, valid)

        extra = report([check(MODEL_CHECK, "pass")])
        extra["checks"][0]["extra"] = "reject"
        with self.assertRaises(compare_checks.ReportError):
            compare_checks.compare(extra, valid)

        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text(
                '{"version":1,"revision":{"commit":"%s","patch_sha256":null},'
                '"scope":"one","scope":"two","environment":"python",'
                '"inventory_complete":true,"checks":[]}' % COMMIT,
                encoding="utf-8",
            )
            with self.assertRaises(compare_checks.ReportError):
                compare_checks.load_report(duplicate)

    def test_cli_uses_fail_closed_exit_codes_and_does_not_follow_evidence_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_path = root / "base.json"
            candidate_path = root / "candidate.json"
            base_path.write_text(json.dumps(report([check(MODEL_CHECK, "pass")])), encoding="utf-8")
            candidate_path.write_text(
                json.dumps(report([check(MODEL_CHECK, "fail", "/tmp/must-not-be-read")], patch_sha256=PATCH_A)),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(base_path), str(candidate_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "regression")
            self.assertEqual(result.stderr, "")

            candidate_path.write_text(
                json.dumps(report([check(MODEL_CHECK, "pass")], patch_sha256=PATCH_A)),
                encoding="utf-8",
            )
            clean = subprocess.run(
                [sys.executable, str(SCRIPT), str(base_path), str(candidate_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(clean.returncode, 0)
            self.assertEqual(json.loads(clean.stdout)["status"], "no_difference_observed")
            self.assertEqual(clean.stderr, "")

            candidate_path.write_text("{", encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, str(SCRIPT), str(base_path), str(candidate_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(invalid.stdout, "")
            self.assertIn("entrée invalide", invalid.stderr)

    def test_json_with_surrogate_evidence_has_valid_output_on_strict_utf8_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "base.json"
            candidate = Path(directory) / "candidate.json"
            base.write_text(json.dumps(report([check(MODEL_CHECK, "pass")])), encoding="utf-8")
            candidate.write_text(json.dumps(report([check(MODEL_CHECK, "fail", chr(0xD800))],
                                                   patch_sha256=PATCH_A)), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(base), str(candidate)],
                                    capture_output=True, text=True,
                                    env={**os.environ, "PYTHONIOENCODING": "utf-8:strict"})
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, "")
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "regression")
            self.assertEqual(output["checks"][0]["candidate"]["runs"][0]["evidence"], chr(0xD800))

    def test_a_single_candidate_pass_does_not_claim_fixed_failure(self):
        result = compare_checks.compare(report([check(MODEL_CHECK, "fail", MODEL_FAILURE)]),
                                        report([check(MODEL_CHECK, "pass", count=1)], patch_sha256=PATCH_A))
        self.assertEqual(result["status"], "incomparable")
        self.assertEqual(by_id(result)[MODEL_CHECK]["label"], "insufficient_observations")

    def test_help_states_that_a_clean_comparison_is_not_delivery_authorization(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("jamais une autorisation de livraison", result.stdout)

    def _definition_hashes(self, root=ROOT):
        return {
            test_id: hashlib.sha256((root / source).read_bytes()).hexdigest()
            for test_id, source in TEST_SOURCES.items()
        }

    def _copy_fixture(self, destination):
        for relative in (
            Path("plugins/cstack/skills/setup-cstack/scripts/models.py"),
            Path("plugins/cstack/skills/setup-cstack/scripts/project.py"),
            Path("tests/test_models.py"),
            Path("tests/test_project_setup.py"),
        ):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        (destination / "tests" / "__init__.py").write_text("", encoding="utf-8")
        return destination

    def _run_collector(self, fixture, test_ids=TEST_IDS):
        result = subprocess.run(
            [sys.executable, "-B", "-c", COLLECTOR, *test_ids],
            cwd=fixture,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def _snapshot(self, *, mutate_models=False, mutate_project=False):
        observations = {test_id: [] for test_id in TEST_IDS}
        inventory_complete = True
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._copy_fixture(Path(directory))
            if mutate_models:
                path = fixture / "plugins/cstack/skills/setup-cstack/scripts/models.py"
                source = path.read_bytes()
                old = b"value = config.get(role, config.get(LEGACY_FALLBACKS.get(role), default))"
                new = b"value = config.get(role, default)"
                self.assertEqual(source.count(old), 1)
                path.write_bytes(source.replace(old, new))
            if mutate_project:
                path = fixture / "plugins/cstack/skills/setup-cstack/scripts/project.py"
                source = path.read_bytes()
                old = b'newline = b"\\r\\n" if old and b"\\r\\n" in old else b"\\n"'
                new = b'newline = b"\\n"'
                self.assertEqual(source.count(old), 1)
                path.write_bytes(source.replace(old, new))
            definitions = self._definition_hashes(fixture)
            for _ in range(2):
                collected = self._run_collector(fixture)
                inventory_complete = inventory_complete and collected["inventory_complete"]
                for check_data in collected["checks"]:
                    observations[check_data["id"]].extend(check_data["runs"])
        patch_label = "clean"
        if mutate_project:
            patch_label = "models-fallback-plus-project-newline"
        elif mutate_models:
            patch_label = "models-fallback"
        patch_sha256 = None if patch_label == "clean" else hashlib.sha256(patch_label.encode()).hexdigest()
        return {
            "version": 1,
            "revision": {"commit": COMMIT, "patch_sha256": patch_sha256},
            "scope": "unittest:%s,%s" % TEST_IDS,
            "environment": "Python %s" % sys.version.split()[0],
            "inventory_complete": inventory_complete,
            "checks": [
                {
                    "id": test_id,
                    "definition_sha256": definitions[test_id],
                    "runs": observations[test_id],
                }
                for test_id in TEST_IDS
            ],
        }


if __name__ == "__main__":
    unittest.main()
