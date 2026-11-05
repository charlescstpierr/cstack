import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/t3-catalog-bench.py'
MODELS = ROOT / 'plugins/cstack/skills/setup-cstack/scripts/models.py'
SPEC = importlib.util.spec_from_file_location('catalog_bench', SCRIPT)
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)


class CatalogBenchTests(unittest.TestCase):
    def test_default_v2_workload_is_accepted_by_current_helper(self):
        helper = BENCH.load(MODELS, 'bench_models')
        catalog, context, values = BENCH.workload(4)
        self.assertEqual(catalog['schema'], 'cstack.t3-snapshot/2')
        self.assertEqual(context['schema'], 'cstack.t3-context/2')
        self.assertEqual(len(BENCH.check(BENCH.preview(helper, catalog, context), values)), 64)

    def test_v1_is_an_explicit_historical_format(self):
        catalog, context, _ = BENCH.workload(4, 'v1')
        self.assertIn('environmentId', catalog)
        self.assertIn('sessionId', context)
        with self.assertRaises(ValueError):
            BENCH.workload(4, 'unknown')

    def test_cli_explains_an_incompatible_helper_before_measuring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = root/'old_helper.py'
            before.write_text("def preview(*args, **kwargs): return {'supported': {}}\n")
            output = root/'result.json'
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--before', str(before),
                '--after', str(MODELS), '--values', '4', '--repetitions', '5', '--output', str(output)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertIn('BLOCKED: --before incompatible avec --format v2', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse(output.exists())

    def test_cli_exercises_complete_direct_and_subprocess_previews(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'result.json'
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--before', str(MODELS),
                '--after', str(MODELS), '--values', '4', '--repetitions', '5', '--output', str(output)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text())
            self.assertEqual(data['format'], 'v2')
            self.assertEqual(data['errors'], 0)
            self.assertEqual(data['complete_previews'], 20)
            self.assertTrue(data['sources_unchanged'])
            self.assertEqual(len({row['output_sha256'] for row in data['runs']}), 1)
            self.assertEqual(len({row['output_sha256'] for row in data['cli_runs']}), 1)


if __name__ == '__main__':
    unittest.main()
