import json, subprocess, sys, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="cstack-red-red-") as scratch:
    results = {}
    for name, second in [("baseline", "True"), ("changed", "False")]:
        path = Path(scratch) / (name + ".py")
        path.write_text("import unittest\nclass Checks(unittest.TestCase):\n def test_existing(self): self.assertTrue(False)\n def test_other(self): self.assertTrue(" + second + ")\nif __name__ == '__main__': unittest.main(verbosity=2)\n")
        run = subprocess.run([sys.executable, str(path)], capture_output=True, text=True)
        failures = [line.split(" (", 1)[0][6:] for line in run.stderr.splitlines() if line.startswith("FAIL: ")]
        results[name] = {"exit_code": run.returncode, "failed_tests": failures}
    assert results["baseline"]["exit_code"] == results["changed"]["exit_code"] == 1
    introduced = sorted(set(results["changed"]["failed_tests"]) - set(results["baseline"]["failed_tests"]))
    assert introduced == ["test_other"]
    results["new_failure_hidden_by_exit_code_only"] = introduced
    print(json.dumps(results, indent=2))
