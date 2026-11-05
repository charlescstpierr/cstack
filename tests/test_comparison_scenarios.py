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
    def test_archive_under_an_unrelated_git_repository_has_no_git_commit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            C.B.git(root, 'init', '--quiet')
            (root/'anchor').write_text('parent repository')
            C.B.git(root, 'add', 'anchor')
            C.B.git(root, *C.B.GIT_IDENTITY, 'commit', '--quiet', '-m', 'parent')
            source = root/'.cstack/archive'
            skill = source/'skills/sol-loop/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('archive source')
            (source/'LICENSE').write_text('MIT')
            result = C.snapshot(source, root/'snapshot', 'tstack')
            self.assertIsNone(result['commit'])

    def test_balanced_order_and_repeatability(self):
        rows = C.order(3, 19)
        self.assertEqual(rows, C.order(3, 19))
        self.assertEqual(len(rows), 30)
        for i in range(0, 30, 5):
            self.assertEqual({r['arm'] for r in rows[i:i+5]}, set(C.ARMS))
            self.assertEqual(len({(r['task'], r['repetition']) for r in rows[i:i+5]}), 1)
        self.assertGreater(len({tuple(r['arm'] for r in rows[i:i+5]) for i in range(0, 30, 5)}), 3)

    def test_controls_seed_pairing_and_counterbalance(self):
        cases = C.case_specs('review-controls', 19)
        self.assertEqual(cases, C.case_specs('review-controls', 19))
        self.assertNotEqual(cases, C.case_specs('review-controls', 20))
        self.assertEqual(len({case.id for case in cases}), 5)
        reviews = [case for case in cases if case.kind == 'review']
        self.assertEqual({case.expected_findings for case in reviews}, {
            C.REVIEW_FINDINGS, frozenset({'field_order'}),
            frozenset({'malformed_exit'}), frozenset()})
        self.assertTrue(all(case.id.startswith('case-') for case in cases))
        self.assertEqual(len({C.prompt(case.kind, 'vanilla', Path('/campaign'))
                              for case in reviews}), 1)
        with self.assertRaises(AttributeError):
            cases[0].kind = 'changed'
        rows = C.order(10, 19, cases)
        self.assertEqual(rows, C.order(10, 19, cases))
        self.assertEqual(rows, C.order(10, 19, [case.id for case in cases]))
        positions = {(case.id, arm): [0] * 5 for case in cases for arm in C.ARMS}
        for start in range(0, len(rows), 5):
            block = rows[start:start+5]
            self.assertEqual({row['arm'] for row in block}, set(C.ARMS))
            self.assertEqual(len({(row['task'], row['repetition']) for row in block}), 1)
            for position, row in enumerate(block):
                positions[row['task'], row['arm']][position] += 1
        self.assertTrue(all(counts == [2] * 5 for counts in positions.values()))
        paired = C.report({'runs': rows}, [{**row, 'comparable': True,
            'grade': {'correct': True, 'scope_preserved': True}} for row in rows])
        self.assertTrue(all(count['ties'] == 50 and count['excluded'] == 0
                            for count in paired['cstack_vs'].values()))

    def review_result(self, root, expected, findings, change=None, stage_notes=False,
                      change_index=False):
        workspace = C.fixture('review', root, expected)
        if stage_notes:
            C.B.git(workspace, 'add', 'notes.md')
        original_index = C.B.git(workspace, 'diff', '--cached', '--binary')
        original = {name: (workspace/name).read_bytes()
                    for name in ('src/feature.py', 'notes.md')}
        baseline = root/'base'
        C.shutil.copytree(workspace, baseline)
        C.B.git(baseline, 'add', '--all')
        C.B.git(baseline, *C.B.GIT_IDENTITY, 'commit', '-m', 'initial work')
        candidate = root/'candidate'
        C.shutil.copytree(baseline, candidate)
        (candidate/'review.json').write_text(json.dumps(findings))
        if change:
            (candidate/change).write_text('unexpected modification')
        if change_index:
            C.B.git(workspace, 'add', 'src/feature.py')
        patchfile = root/'patch.diff'
        patchfile.write_text(C.B.capture_diff(candidate, C.B.git(candidate, 'rev-parse', 'HEAD').strip()))
        private = root/'private'
        private.mkdir()
        value = C.grade('review', workspace, baseline, patchfile, private,
                        original_index, expected=expected)
        self.assertEqual(original, {name: (workspace/name).read_bytes() for name in original})
        if not change_index:
            self.assertEqual(C.B.git(workspace, 'diff', '--cached', '--binary'), original_index)
        for name, content in original.items():
            if name != change:
                self.assertEqual((private/'grading'/name).read_bytes(), content)
        return value, workspace

    def test_all_review_controls_match_staged_content_and_grade(self):
        for case in C.case_specs('review-controls', 19):
            if case.kind != 'review':
                continue
            with self.subTest(expected=case.expected_findings), tempfile.TemporaryDirectory() as d:
                findings = [{'path': 'README.md', 'missing': label,
                             'evidence': 'Le diff retire ce comportement approuvé.'}
                            for label in sorted(case.expected_findings)]
                value, workspace = self.review_result(Path(d), case.expected_findings, findings)
                staged = C.B.git(workspace, 'show', ':README.md')
                self.assertEqual("--json préserve l'ordre des champs." in staged,
                                 'field_order' not in case.expected_findings)
                self.assertEqual('Une entrée mal formée entraîne un code de sortie non nul.' in staged,
                                 'malformed_exit' not in case.expected_findings)
                self.assertTrue(value['correct'])
                self.assertTrue(value['scope_preserved'])
                self.assertEqual(value['precision'], 1)
                self.assertEqual(value['recall'], 1)
                self.assertEqual(value['duplicates'], 0)
                self.assertEqual(value['false_positives'], 0)

    def test_clean_control_rejects_spurious_finding(self):
        with tempfile.TemporaryDirectory() as d:
            value, _ = self.review_result(Path(d), frozenset(), [
                {'path': 'README.md', 'missing': 'field_order', 'evidence': 'omitted'}])
            self.assertFalse(value['correct'])
            self.assertEqual(value['precision'], 0)
            self.assertEqual(value['recall'], 1)
            self.assertEqual(value['false_positives'], 1)

    def test_one_omission_rejects_hardcoded_two_findings(self):
        for expected in (frozenset({'field_order'}), frozenset({'malformed_exit'})):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as d:
                value, _ = self.review_result(Path(d), expected, [
                    {'path': 'README.md', 'missing': label, 'evidence': 'omitted'}
                    for label in sorted(C.REVIEW_FINDINGS)])
                self.assertFalse(value['correct'])
                self.assertEqual(value['precision'], .5)
                self.assertEqual(value['recall'], 1)
                self.assertEqual(value['false_positives'], 1)

    def test_malformed_report_and_duplicates_reduce_quality(self):
        good = {'path': 'README.md', 'missing': 'field_order', 'evidence': '理由'}
        for evidence in (None, True, 1, [], {}, '', '  '):
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory() as d:
                value, _ = self.review_result(Path(d), frozenset({'field_order'}),
                                             [{**good, 'evidence': evidence}])
                self.assertFalse(value['correct'])
                self.assertEqual(value['precision'], 0)
                self.assertEqual(value['false_positives'], 1)
        for malformed in ({'findings': [good]}, None, 'not an array'):
            with self.subTest(malformed=malformed), tempfile.TemporaryDirectory() as d:
                value, _ = self.review_result(Path(d), frozenset(), malformed)
                self.assertFalse(value['correct'])
                self.assertFalse(value['report_valid'])
                self.assertEqual(value['precision'], 0)
        with tempfile.TemporaryDirectory() as d:
            value, _ = self.review_result(Path(d), frozenset({'field_order'}), [good, good])
            self.assertFalse(value['correct'])
            self.assertEqual(value['precision'], .5)
            self.assertEqual(value['recall'], 1)
            self.assertEqual(value['duplicates'], 1)
            self.assertEqual(value['false_positives'], 0)

    def test_unreadable_json_and_missing_reports_fail_clean_control(self):
        for contents in ('[', None):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                self.review_result(root, frozenset(), [])
                report = root/'candidate/review.json'
                if contents is None:
                    report.unlink()
                else:
                    report.write_text(contents)
                patchfile = root/'patch.diff'
                candidate = root/'candidate'
                patchfile.write_text(C.B.capture_diff(candidate,
                    C.B.git(candidate, 'rev-parse', 'HEAD').strip()))
                workspace = root/'projects/task'
                value = C.grade('review', workspace, root/'base', patchfile, root/'private',
                    C.B.git(workspace, 'diff', '--cached', '--binary'), expected=frozenset())
                self.assertFalse(value['correct'])
                self.assertFalse(value['report_valid'])
                self.assertEqual(value['precision'], 0)
                self.assertEqual(value['recall'], 0)

    def test_controls_preserve_unrelated_files_and_initial_index(self):
        with tempfile.TemporaryDirectory() as d:
            value, _ = self.review_result(Path(d), frozenset(), [], stage_notes=True)
            self.assertTrue(value['scope_preserved'])
        with tempfile.TemporaryDirectory() as d:
            value, _ = self.review_result(Path(d), frozenset(), [], stage_notes=True,
                                         change_index=True)
            self.assertFalse(value['scope_preserved'])
        for name in ('src/feature.py', 'notes.md'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                value, _ = self.review_result(Path(d), frozenset(), [], change=name)
                self.assertTrue(value['correct'])
                self.assertFalse(value['scope_preserved'])

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
            self.assertFalse((args.campaign/'frozen-harness').exists())
            for filename, sha in manifest['harness'].items():
                self.assertEqual(C.digest(args.campaign/'private/frozen-harness'/filename), sha)
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

    def test_controls_campaign_uses_private_specs_and_runs_all_states(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources = []
            for arm, entry in C.ENTRY.items():
                source = root/arm
                path = source/'skills'/entry/'SKILL.md'
                path.parent.mkdir(parents=True)
                path.write_text('source ' + arm)
                (source/'LICENSE').write_text('MIT')
                sources.append(arm + '=' + str(source))
            args = SimpleNamespace(campaign=root/'campaign', source=sources, repetitions=1,
                seed=19, deadline=900, model='chosen-model', effort='high', suite='review-controls')
            with contextlib.redirect_stdout(io.StringIO()):
                C.prepare(args)
            manifest = json.loads((args.campaign/'private/manifest.json').read_text())
            self.assertEqual(manifest['suite'], 'review-controls')
            self.assertEqual(len(manifest['runs']), 25)
            self.assertEqual(len(manifest['cases']), 5)
            self.assertFalse((args.campaign/'manifest.json').exists())
            self.assertFalse((args.campaign/'frozen-harness').exists())
            self.assertTrue(any(case['kind'] == 'review' and case['expected_findings'] == []
                                for case in manifest['cases']))
            self.assertTrue(all('expected_findings' not in row for row in manifest['runs']))
            for filename, sha in manifest['harness'].items():
                self.assertEqual(C.digest(args.campaign/'private/frozen-harness'/filename), sha)
            prompts = []

            def candidate(case, output, command, model, effort, timeout):
                workspace = case['cwd']
                prompts.append(case['prompts'][0])
                if (workspace/'src/duration.py').exists():
                    (workspace/'src/duration.py').write_text('import re\ndef parse_duration(text):\n if not re.fullmatch(r"(?:[0-9]+[hms])+", text): raise ValueError(text)\n return sum(int(n)*dict(h=3600,m=60,s=1)[u] for n,u in re.findall(r"([0-9]+)([hms])",text))\n')
                else:
                    staged = C.B.git(workspace, 'show', ':README.md')
                    expected = []
                    if "--json préserve l'ordre des champs." not in staged:
                        expected.append('field_order')
                    if 'Une entrée mal formée entraîne un code de sortie non nul.' not in staged:
                        expected.append('malformed_exit')
                    (workspace/'review.json').write_text(json.dumps([
                        {'path': 'README.md', 'missing': label, 'evidence': 'extrait examiné'}
                        for label in expected]))
                arm = case['id'].split('--')[1]
                commands = [] if arm == 'vanilla' else ['cat ' + str(
                    args.campaign/'sources'/arm/'skills'/C.ENTRY[arm]/'SKILL.md')]
                return {'status': 'completed', 'actual_commands': commands,
                    'after_turn_actual_metadata': [{'model': model, 'reasoning_effort': effort}],
                    'native_child_thread_ids': [], 'child_metadata': []}

            if os.geteuid() == 0:
                return
            with patch.object(C, 'preflight', return_value=[]), patch.object(
                    C, 'bounded_run', candidate), contextlib.redirect_stdout(io.StringIO()):
                C.run(args)
                C.run(args)
            rows = C.B.load_results(args.campaign/'private/results.jsonl')
            self.assertEqual(len(rows), 25)
            self.assertEqual(len(prompts), 25)
            self.assertTrue(all(row['comparable'] and row['grade']['correct']
                                and row['grade']['scope_preserved'] for row in rows))
            for arm in C.ARMS:
                review_prompts = [text for text in prompts if 'Review only' in text
                    and (('Read and use ' not in text) if arm == 'vanilla'
                         else str(args.campaign/'sources'/arm/'skills') in text)]
                self.assertEqual(len(review_prompts), 4)
                self.assertEqual(len(set(review_prompts)), 1)
            for case in manifest['cases']:
                self.assertFalse(any(case['id'] in text for text in prompts))

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
