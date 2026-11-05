import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location('comparison', Path(__file__).resolve().parents[1] / 'scripts/comparison-scenarios.py')
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def stuck(*args):
    os.setsid()
    time.sleep(30)


class ComparisonTests(unittest.TestCase):
    def test_balanced_order_and_repeatability(self):
        rows = C.order(3, 19)
        self.assertEqual(rows, C.order(3, 19))
        self.assertEqual(len(rows), 30)
        for i in range(0, 30, 5):
            self.assertEqual({r['arm'] for r in rows[i:i+5]}, set(C.ARMS))
            self.assertEqual(len({(r['task'], r['repetition']) for r in rows[i:i+5]}), 1)
        self.assertGreater(len({tuple(r['arm'] for r in rows[i:i+5]) for i in range(0, 30, 5)}), 3)

    def test_discovery_rejects_missing_unknown_and_enabled(self):
        for value in ({}, {'data': []}, {'data': [{'skills': [{'enabled': True}]}]},
                      {'data': [{'skills': [{}]}]}, {'data': [{'skills': [], 'errors': ['oops']}]}):
            self.assertFalse(C.clean_inventory(value))
        self.assertTrue(C.clean_inventory({'data': [{'skills': [{'enabled': False}]}]}))

    def test_source_snapshot_manifest_five_arms(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources = []
            for arm, entry in C.ENTRY.items():
                source = root / arm
                path = source / 'skills' / entry / 'SKILL.md'
                path.parent.mkdir(parents=True)
                path.write_text('source ' + arm)
                (source / 'LICENSE').write_text('MIT')
                sources.append(arm + '=' + str(source))
            args = SimpleNamespace(campaign=root/'campaign', source=sources, repetitions=1,
                                   seed=19, deadline=900, model='chosen-model', effort='high')
            C.prepare(args)
            manifest = json.loads((args.campaign/'private/manifest.json').read_text())
            self.assertEqual(manifest['arms'], list(C.ARMS))
            self.assertEqual(len(manifest['runs']), 10)
            for arm in C.ENTRY:
                snapshot = args.campaign/'sources'/arm
                self.assertEqual(C.inventory(snapshot), manifest['sources'][arm]['files'])
                self.assertTrue((snapshot/'LICENSE').exists())

            def candidate(case, output, command, model, effort, timeout):
                workspace = case['cwd']
                if (workspace/'src/duration.py').exists():
                    (workspace/'src/duration.py').write_text('import re\ndef parse_duration(text):\n if not re.fullmatch(r"(?:[0-9]+[hms])+", text): raise ValueError(text)\n return sum(int(n)*dict(h=3600,m=60,s=1)[u] for n,u in re.findall(r"([0-9]+)([hms])",text))\n')
                else:
                    (workspace/'review.json').write_text(json.dumps([
                        {'path':'README.md','missing':m,'evidence':'omitted'}
                        for m in ('field_order','malformed_exit')]))
                arm = case['id'].split('--')[1]
                commands = [] if arm == 'vanilla' else ['cat ' + str(args.campaign/'sources'/arm/'skills'/C.ENTRY[arm]/'SKILL.md')]
                return {'status':'completed', 'actual_commands':commands,
                        'after_turn_actual_metadata':[{'model':model,'reasoning_effort':effort}],
                        'native_child_thread_ids':[], 'child_metadata':[]}

            if os.geteuid() == 0:
                return  # run deliberately refuses root; snapshot assertions above still apply
            # Exercise prepare/run/resume and grading for all five arms, without a model call.
            with patch.object(C, 'preflight', return_value=[]), patch.object(C, 'bounded_run', candidate), contextlib.redirect_stdout(io.StringIO()):
                C.run(args)
                (args.campaign/'private').chmod(0)
                C.run(args)
                self.assertEqual((args.campaign/'private').stat().st_mode & 0o777, 0o700)
                with (args.campaign/'run.lock').open('a') as lock:
                    C.fcntl.flock(lock, C.fcntl.LOCK_EX | C.fcntl.LOCK_NB)
                    with self.assertRaises(C.Blocked):
                        C.run(args)
            rows = C.B.load_results(args.campaign/'private/results.jsonl')
            self.assertEqual(len(rows), 10)
            self.assertTrue(all(r['comparable'] and r['grade']['correct'] and r['grade']['scope_preserved'] for r in rows))

    def test_prepare_rejects_duplicate_sources_and_nonfinite_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            args = SimpleNamespace(campaign=Path(d)/'campaign', source=[a+'=/missing' for a in C.ENTRY], repetitions=1, seed=19, deadline=float('inf'), model='x', effort='high')
            with self.assertRaises(ValueError):
                C.prepare(args)
            self.assertFalse(args.campaign.exists())
            args.deadline = 900
            args.source.append('cstack=/other')
            with self.assertRaises(ValueError):
                C.prepare(args)
            self.assertFalse(args.campaign.exists())

    def test_deadline_is_outer_wall_budget(self):
        with tempfile.TemporaryDirectory() as d, patch.object(C, 'worker', stuck):
            start = time.monotonic()
            result = C.bounded_run({}, Path(d), [], 'x', 'high', .1)
            self.assertEqual(result['status'], 'timeout')
            self.assertLess(time.monotonic() - start, 3)

    @unittest.skipIf(os.geteuid() == 0, 'chmod does not protect against root')
    def test_private_directory_denies_reads_and_restores_mode(self):
        with tempfile.TemporaryDirectory() as d:
            private = Path(d)/'private'
            private.mkdir(mode=0o700)
            check = private/'check.py'
            check.write_text('private')
            with C.B.hidden_from_agent([private]):
                with self.assertRaises(PermissionError):
                    check.read_text()
            self.assertEqual(check.read_text(), 'private')
            self.assertEqual(private.stat().st_mode & 0o777, 0o700)

    def test_incomplete_and_excluded_results_do_not_win(self):
        manifest = {'runs': C.order(1, 19)}
        value = C.report(manifest, [])
        self.assertEqual(value['verdict'], 'INCONCLUSIVE')
        self.assertEqual(len(value['missing']), 10)
        rows = [{'id': r['id'], 'comparable': False} for r in manifest['runs']]
        value = C.report(manifest, rows)
        self.assertEqual(value['comparable'], 0)
        self.assertTrue(all(p['wins'] == 0 for p in value['pairs_vs_vanilla'].values()))
        with self.assertRaises(C.Blocked):
            C.report(manifest, [rows[0], rows[0]])

    def test_reconstructed_duration_checks_behavior(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            workspace = C.fixture('duration', root)
            baseline = root/'base'
            C.shutil.copytree(workspace, baseline)
            private = root/'private'
            private.mkdir()
            patchfile = root/'patch.diff'
            base = C.B.git(workspace, 'rev-parse', 'HEAD').strip()
            patchfile.write_text(C.B.capture_diff(workspace, base))
            self.assertFalse(C.grade('duration', workspace, baseline, patchfile, private)['correct'])
            (workspace/'src/duration.py').write_text('import re\ndef parse_duration(text):\n if not re.fullmatch(r"(?:[0-9]+[hms])+", text): raise ValueError(text)\n return sum(int(n)*dict(h=3600,m=60,s=1)[u] for n,u in re.findall(r"([0-9]+)([hms])",text))\n')
            patchfile.write_text(C.B.capture_diff(workspace, base))
            value = C.grade('duration', workspace, baseline, patchfile, private)
            self.assertTrue(value['correct'])
            self.assertTrue(value['scope_preserved'])
            self.assertEqual(len(value['check_sha256']), 64)
            (workspace/'README.md').write_text('oops')
            patchfile.write_text(C.B.capture_diff(workspace, base))
            self.assertFalse(C.grade('duration', workspace, baseline, patchfile, private)['scope_preserved'])

    def test_review_precision_and_dirty_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            workspace = C.fixture('review', root)
            original_index = C.B.git(workspace, 'diff', '--cached', '--binary')
            baseline = root/'base'
            C.shutil.copytree(workspace, baseline)
            C.B.git(baseline, 'add', '--all')
            C.B.git(baseline, *C.B.GIT_IDENTITY, 'commit', '-m', 'initial work')
            patchfile = root/'patch.diff'
            private = root/'private'
            private.mkdir()
            (workspace/'review.json').write_text(json.dumps([{'path':'README.md','missing':m,'evidence':'omitted from staged replacement'} for m in ('field_order','malformed_exit')]))
            # Build patch from the baseline commit including original dirty files.
            candidate = root/'candidate'
            C.shutil.copytree(baseline, candidate)
            C.shutil.copyfile(workspace/'review.json', candidate/'review.json')
            base = C.B.git(candidate,'rev-parse','HEAD').strip()
            patchfile.write_text(C.B.capture_diff(candidate,base))
            value = C.grade('review',workspace,baseline,patchfile,private,original_index)
            self.assertTrue(value['correct'])
            self.assertTrue(value['scope_preserved'])
            good = (candidate/'review.json').read_text()
            findings = json.loads(good)
            findings.append({'path':'src/feature.py','missing':'unsupported','evidence':'outside staged scope'})
            (candidate/'review.json').write_text(json.dumps(findings))
            patchfile.write_text(C.B.capture_diff(candidate,base))
            bad = C.grade('review',workspace,baseline,patchfile,private,original_index)
            self.assertFalse(bad['correct'])
            self.assertAlmostEqual(bad['precision'], 2/3)
            (candidate/'review.json').write_text(good)
            patchfile.write_text(C.B.capture_diff(candidate,base))
            C.B.git(workspace,'add','src/feature.py')
            self.assertFalse(C.grade('review',workspace,baseline,patchfile,private,original_index)['scope_preserved'])


if __name__ == '__main__':
    unittest.main()
