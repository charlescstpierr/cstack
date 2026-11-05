#!/usr/bin/env python3
"""Small stdlib-only comparison pilot; never replaces the OSS Docker grader."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import random
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


B = module('comparison_outcome', ROOT / 'scripts/outcome-bench.py')
S = module('comparison_behavior', ROOT / 'scripts/behavior-scenarios.py')
ARMS = ('vanilla', 'cstack', 'pstack', 'superpowers', 'tstack')
TASKS = ('duration', 'review')
ENTRY = {'cstack': 'cstack', 'pstack': 'poteto-mode',
         'superpowers': 'using-superpowers', 'tstack': 'sol-loop'}
IGNORE = {'.git', 'node_modules', '__pycache__', '.cstack'}


class Blocked(RuntimeError):
    pass


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): {'sha256': digest(p), 'mode': stat.S_IMODE(p.stat().st_mode)} for p in sorted(root.rglob('*'))
            if p.is_file() and not set(p.relative_to(root).parts) & IGNORE}


def order(repetitions, seed):
    """Rotating blocks preserve task/rep pairing; reversal alternates drift direction."""
    if repetitions < 1:
        raise ValueError('repetitions must be positive')
    offset = random.Random(seed).randrange(len(ARMS))
    rows = []
    for rep in range(1, repetitions + 1):
        for index, task in enumerate(TASKS):
            shift = (offset + (rep - 1) * len(TASKS) + index) % len(ARMS)
            arms = list(ARMS[shift:] + ARMS[:shift])
            if (rep + index) % 2 == 0:
                arms.reverse()
            rows.extend({'id': f'{task}--{arm}--r{rep}', 'task': task,
                         'arm': arm, 'repetition': rep} for arm in arms)
    return rows


def snapshot(source, destination, arm):
    source = source.resolve()
    if not (source / 'skills' / ENTRY[arm] / 'SKILL.md').is_file():
        raise ValueError(f'{arm}: missing entry in {source}')
    shutil.copytree(source, destination, ignore=lambda _, names: set(names) & IGNORE,
                    symlinks=False)
    # A source can mutate during copying. Refuse a torn snapshot.
    if inventory(source) != inventory(destination):
        raise Blocked(f'{arm}: source changed during snapshot')
    if not any(p.name.lower().startswith('license') for p in destination.iterdir()):
        raise Blocked(f'{arm}: license missing from source')
    head = B.git(source, 'rev-parse', 'HEAD', check=False).strip() or None
    return {'origin': str(source), 'commit': head, 'files': inventory(destination),
            'entry': f'skills/{ENTRY[arm]}/SKILL.md',
            'activation': 'explicit source read', 'host': 'codex-cli',
            'variant': 'native-Sol fallback, not T3 native' if arm == 'tstack' else 'source'}


def prepare(args):
    campaign = args.campaign.resolve()
    sources = dict(item.split('=', 1) for item in args.source)
    if set(sources) != set(ENTRY) or len(args.source) != len(ENTRY):
        raise ValueError('--source required exactly once for cstack,pstack,superpowers,tstack')
    if not math.isfinite(args.deadline) or args.deadline <= 0:
        raise ValueError('deadline must be finite and positive')
    campaign.mkdir(parents=True, exist_ok=False)
    metadata = {arm: snapshot(Path(path), campaign / 'sources' / arm, arm)
                for arm, path in sources.items()}
    manifest = {'schema': 1, 'backend': 'local-stdlib-only', 'arms': list(ARMS),
                'sources': metadata, 'runs': order(args.repetitions, args.seed),
                'seed': args.seed, 'repetitions': args.repetitions,
                'requested': {'model': args.model, 'effort': args.effort},
                'policy': {'deadline_seconds': args.deadline, 'concurrency': 1,
                           'network': False, 'sandbox': 'workspace-write',
                           'route_trace': bool(shutil.which('strace'))},
                'harness': {p.name: digest(p) for p in (Path(__file__), B.RUNNER_PATH,
                            ROOT / 'scripts/outcome-bench.py', ROOT / 'scripts/behavior-scenarios.py')},
                'python': {'executable': sys.executable, 'version': platform.python_version(),
                           'sha256': digest(Path(sys.executable).resolve())},
                'machine': {'platform': platform.platform(), 'cpus': os.cpu_count(), 'load_average': list(os.getloadavg())},
                'future_metrics': ['recovery', 'installation'],
                'claim': 'Pilot only; no universal superiority or independent quality score.'}
    for filename in manifest['harness']:
        target = campaign / 'frozen-harness' / filename
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / 'scripts' / filename, target)
    private = campaign / 'private'
    private.mkdir(mode=0o700)
    write(private / 'manifest.json', manifest)
    (private / 'manifest.sha256').write_text(digest(private / 'manifest.json') + '\n', encoding='utf-8')
    print(campaign)


def initialize(server):
    server.request('initialize', {'clientInfo': {'name': 'cstack-comparison', 'version': '1'}}, 20, lambda _: None)
    server.notify('initialized')


def clean_inventory(value):
    data = value.get('data')
    return (isinstance(data, list) and bool(data)
            and all(not row.get('errors') and isinstance(row.get('skills'), list)
                    and all(s.get('enabled') is False for s in row['skills']) for row in data))


def preflight(cwd, receipt, model, effort):
    """Read only: original login remains in place; only process overrides change."""
    command = [shutil.which('codex') or 'codex', 'app-server', '--stdio',
               '-c', 'features.hooks=false', '-c', 'features.memories=false',
               '-c', 'developer_instructions=""', '-c', 'notify=[]']
    def probe(cmd):
        server = B.RUNNER.AppServer(cmd, cwd, Path(os.devnull), receipt / 'preflight.stderr')
        try:
            initialize(server)
            skills = server.request('skills/list', {'cwds': [str(cwd)], 'forceReload': True}, 20, lambda _: None)
            config = server.request('config/read', {'cwd': str(cwd), 'includeLayers': False}, 20, lambda _: None).get('config', {})
            models = []
            cursor = None
            while True:
                page = server.request('model/list', {'includeHidden': True, 'cursor': cursor}, 20, lambda _: None)
                models.extend(page.get('data', []))
                cursor = page.get('nextCursor')
                if not cursor:
                    break
            return skills, config, models
        finally:
            server.close()
    skills, initial_config, _ = probe(command)
    # Read the live schema through IPC, without TOML parsing or config writes.
    for table in ('plugins', 'mcp_servers'):
        for name in initial_config.get(table, {}):
            command += ['-c', f'{table}.{name}.enabled=false']
    paths = [s['path'] for row in skills.get('data', []) for s in row.get('skills', [])]
    disabled = '[' + ','.join('{path=' + json.dumps(p) + ',enabled=false}' for p in paths) + ']'
    command += ['-c', 'skills.config=' + disabled, '-c', 'project_doc_max_bytes=0',
                '-c', 'project_doc_fallback_filenames=[]',
                '-c', 'web_search="disabled"', '-c', 'include_apps_instructions=false',
                '-c', 'sandbox_workspace_write.network_access=false']
    skills, config, models = probe(command)
    # Never dump config values or auth. Keep only the allowlisted evidence.
    evidence = {'skills': skills, 'catalog': models, 'command': command,
                'project_doc_max_bytes': config.get('project_doc_max_bytes'),
                'instructions_present': bool(config.get('instructions')),
                'developer_instructions_present': bool(config.get('developer_instructions')),
                'model_instructions_file_present': bool(config.get('model_instructions_file'))}
    write(receipt / 'preflight.json', evidence)
    if not clean_inventory(skills):
        raise Blocked('clean-discovery inventory not empty/disabled')
    if config.get('project_doc_max_bytes') != 0 or config.get('instructions') or config.get('developer_instructions') or config.get('model_instructions_file'):
        raise Blocked('ancestor/global instructions not neutralized')
    if not any(m.get('model') == model and any(e.get('reasoningEffort') == effort
               for e in m.get('supportedReasoningEfforts', [])) for m in models):
        raise Blocked('requested model/effort absent from live CLI catalogue')
    return command


def fixture(task, root):
    if task == 'duration':
        project = S.arena_project(root, 'task', None)
        S.seed_git(project)
    else:
        project = S.interrogate_project(root, 'task', None)
    # The existing generator's example model selection is not part of this campaign.
    shutil.rmtree(project / '.cstack')
    return project


def prompt(task, arm, campaign):
    body = ('Implement parse_duration according to README.md. Run the relevant checks.' if task == 'duration' else
            'Review only the staged README.md change against the approved requirement: --json preserves field order and malformed input exits nonzero. '
            'The unstaged src/feature.py and untracked notes.md are existing unrelated work. Preserve all files and the index. '
            'Write review.json as a JSON array of findings, each with path, missing and evidence. '
            'Use missing="field_order" or "malformed_exit" for omitted requirements; use another value for any other finding. '
            'Report only supported findings.')
    body += '\nWork only in this repository. Do not commit, push or create a PR. '
    body += 'Use the same model and reasoning effort for any children; stop all children before finishing.'
    if arm != 'vanilla':
        body += '\nRead and use ' + str(campaign / 'sources' / arm / 'skills' / ENTRY[arm] / 'SKILL.md') + '.'
        if arm == 'superpowers':
            route = 'brainstorming' if task == 'duration' else 'requesting-code-review'
            body += ' Then read and apply the relevant workflow at ' + str(campaign / 'sources' / arm / 'skills' / route / 'SKILL.md') + '.'
    return body


DURATION_CHECK = '''import json,sys
from src.duration import parse_duration
checks=[]
for text,seconds in [('3m',180),('1h2m3s',3723),('0s',0),('17s',17),('12h',43200)]:
 try: checks.append(parse_duration(text)==seconds)
 except Exception: checks.append(False)
for text in ['', '7', '2x', '1hBAD', 'BAD1h']:
 try: parse_duration(text); checks.append(False)
 except ValueError: checks.append(True)
 except Exception: checks.append(False)
print(json.dumps(checks))
sys.exit(0 if all(checks) else 1)
'''


def grade(task, workspace, baseline, patch, private, initial_index=None):
    """Reconstruct from initial files plus captured patch after the candidate stops."""
    target = private / 'grading'
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(baseline, target)
    applied = subprocess.run(['git', 'apply', '--binary', str(patch)], cwd=target, capture_output=True)
    if applied.returncode and patch.stat().st_size:
        return {'correct': False, 'scope_preserved': False, 'patch_applied': False}
    original = inventory(baseline)
    current = inventory(target)
    allowed = {'src/duration.py', 'tests/test_duration.py'} if task == 'duration' else {'review.json'}
    changed = {p for p in original.keys() | current.keys() if original.get(p) != current.get(p)}
    scope = not changed - allowed
    if task == 'duration':
        check = private / 'duration-check.py'
        check.write_text(DURATION_CHECK, encoding='utf-8')
        # -c uses only reconstructed code; the check file never enters the candidate workspace.
        try:
            result = subprocess.run([sys.executable, '-B', '-c', DURATION_CHECK], cwd=target,
                                    capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return {'correct': False, 'scope_preserved': scope, 'check_sha256': digest(check),
                    'grading_timeout': True, 'patch_applied': True}
        return {'correct': result.returncode == 0, 'scope_preserved': scope,
                'check_sha256': digest(check), 'exit_code': result.returncode,
                'checks': result.stdout[-4000:], 'patch_applied': True}
    try:
        findings = json.loads((target / 'review.json').read_text(encoding='utf-8'))
        if not isinstance(findings, list):
            raise ValueError('review must be an array')
        hits = {f.get('missing') for f in findings if isinstance(f, dict)
                and f.get('path') == 'README.md' and f.get('evidence')
                and f.get('missing') in {'field_order', 'malformed_exit'}}
        precision = len(hits) / len(findings) if findings else 0
    except (OSError, ValueError, TypeError):
        hits, precision = set(), 0
    # Preserve index separately, as a full working-tree patch cannot encode stagedness.
    index_preserved = B.git(workspace, 'diff', '--cached', '--binary') == initial_index
    return {'correct': len(hits) == 2 and precision == 1, 'precision': precision,
            'recall': len(hits) / 2, 'scope_preserved': scope and index_preserved,
            'patch_applied': True}


def worker(case, output, command, model, effort, timeout, result):
    os.setsid()
    value = B.RUNNER.run_case(case, output, command, model, effort, timeout,
                                   trace_routes=case.get('trace_routes', False))
    write(result, value)


def bounded_run(case, output, command, model, effort, timeout):
    """One wall deadline covers startup, parent, children and metadata collection."""
    result = output / 'worker.json'
    process = multiprocessing.get_context('fork').Process(target=worker, args=(
        case, output, command, model, effort, timeout, result))
    started = time.monotonic()
    process.start()
    try:
        process.join(timeout)
        timed_out = process.is_alive()
    finally:
        # Also run on interruption; no child may survive the candidate turn.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.join(5)
    if timed_out or not result.exists():
        return {'status': 'timeout' if timed_out else 'infra_error',
                'wall_seconds': time.monotonic() - started}
    return json.loads(result.read_text(encoding='utf-8'))


def report(manifest, rows):
    expected = {r['id'] for r in manifest['runs']}
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows) or not set(by_id) <= expected:
        raise Blocked('duplicate or foreign result ids')
    valid = {key: row for key, row in by_id.items() if row.get('comparable')}
    pairs = {}
    for arm in ARMS[1:]:
        counts = {'wins': 0, 'ties': 0, 'losses': 0, 'excluded': 0}
        for run in manifest['runs']:
            if run['arm'] != arm:
                continue
            left = valid.get(run['id'])
            right = valid.get(f"{run['task']}--vanilla--r{run['repetition']}")
            if left is None or right is None:
                counts['excluded'] += 1
                continue
            a, b = (int(x['grade']['correct'] and x['grade']['scope_preserved']) for x in (left, right))
            counts['wins' if a > b else 'losses' if a < b else 'ties'] += 1
        pairs[arm] = counts
    against_cstack = {}
    for arm in ARMS:
        if arm == 'cstack':
            continue
        counts = {'wins': 0, 'ties': 0, 'losses': 0, 'excluded': 0}
        for run in manifest['runs']:
            if run['arm'] != arm:
                continue
            left = valid.get(f"{run['task']}--cstack--r{run['repetition']}")
            right = valid.get(run['id'])
            if left is None or right is None:
                counts['excluded'] += 1
                continue
            a, b = (int(x['grade']['correct'] and x['grade']['scope_preserved']) for x in (left, right))
            counts['wins' if a > b else 'losses' if a < b else 'ties'] += 1
        against_cstack[arm] = counts
    return {'verdict': 'INCONCLUSIVE', 'reason': 'small pilot; no independent quality rating',
            'expected': len(expected), 'recorded': len(rows), 'comparable': len(valid),
            'missing': sorted(expected - by_id.keys()), 'pairs_vs_vanilla': pairs,
            'cstack_vs': against_cstack,
            'excluded': [r['id'] for r in rows if not r.get('comparable')],
            'rows': rows}


def run(args):
    campaign = args.campaign.resolve()
    with (campaign / 'run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Blocked('another controller owns this campaign') from error
        private = campaign / 'private'
        if private.stat().st_uid != os.geteuid():
            raise Blocked('private directory belongs to another uid')
        # Recover permissions left by a killed controller only after acquiring its lock.
        if private.stat().st_mode & 0o777 == 0:
            private.chmod(0o700)
        execute_campaign(args)


def execute_campaign(args):
    campaign = args.campaign.resolve()
    private = campaign / 'private'
    if digest(private / 'manifest.json') != (private / 'manifest.sha256').read_text().strip():
        raise Blocked('manifest changed; prepare a new campaign')
    manifest = json.loads((private / 'manifest.json').read_text(encoding='utf-8'))
    for filename, sha in manifest['harness'].items():
        if digest(ROOT / 'scripts' / filename) != sha:
            raise Blocked('harness changed; prepare a new campaign')
    for arm, source in manifest['sources'].items():
        if inventory(campaign / 'sources' / arm) != source['files']:
            raise Blocked(f'{arm}: snapshot changed')
    if digest(Path(sys.executable).resolve()) != manifest['python']['sha256']:
        raise Blocked('Python interpreter changed')
    results = private / 'results.jsonl'
    rows = B.load_results(results, repair=True)
    report(manifest, rows)  # reject unknown or duplicate ids before execution
    if manifest['policy'].get('route_trace'):
        B.RUNNER.require_route_trace()
    if os.geteuid() == 0:
        raise Blocked('local private-test protection requires a non-root uid')
    done = {r['id'] for r in rows}
    for spec in manifest['runs']:
        if spec['id'] in done:
            continue
        with tempfile.TemporaryDirectory(prefix='cstack-comparison-') as temp:
            scratch = Path(temp)
            workspace = fixture(spec['task'], scratch)
            baseline = private / 'baseline'
            shutil.rmtree(baseline, ignore_errors=True)
            shutil.copytree(workspace, baseline)
            output = scratch / 'agent'
            output.mkdir()
            requested = manifest['requested']
            try:
                command = preflight(workspace, output, requested['model'], requested['effort'])
            except Exception:
                shutil.copytree(output, private / ('blocked-' + spec['id']), dirs_exist_ok=True)
                raise
            case = {'id': spec['id'], 'cwd': workspace, 'sandbox': 'workspace-write',
                    'ephemeral': False, 'prompts': [prompt(spec['task'], spec['arm'], campaign)],
                    'trace_routes': manifest['policy'].get('route_trace', False),
                    'bundle': campaign / 'sources' / spec['arm']}
            with B.hidden_from_agent([private]):
                agent = bounded_run(case, output, command, requested['model'], requested['effort'],
                                    manifest['policy']['deadline_seconds'])
            shutil.copytree(output, private / 'receipts' / spec['id'], dirs_exist_ok=True)
            patch = private / (spec['id'] + '.diff')
            # Capture dirty/untracked initial files as part of the base, not candidate edits.
            original_index = B.git(baseline, 'diff', '--cached', '--binary')
            B.git(baseline, 'add', '--all')
            B.git(baseline, *B.GIT_IDENTITY, 'commit', '--quiet', '--allow-empty', '-m', 'initial work')
            base = B.git(baseline, 'rev-parse', 'HEAD').strip()
            # Compare file snapshots through a temporary repository sharing the initial tree.
            grading_input = scratch / 'diff-input'
            shutil.copytree(baseline, grading_input)
            for child in list(grading_input.iterdir()):
                if child.name != '.git':
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
            for child in workspace.iterdir():
                if child.name in {'.git', '.cstack', '__pycache__'}:
                    continue
                if child.is_dir():
                    shutil.copytree(child, grading_input / child.name)
                else:
                    shutil.copy2(child, grading_input / child.name)
            patch.write_text(B.capture_diff(grading_input, base), encoding='utf-8')
            graded = grade(spec['task'], workspace, baseline, patch, private, original_index)
            settings = B.observed_settings(agent, requested['model'], requested['effort'])
            observed = settings['observed_settings']
            settings_ok = bool(observed) and all(x.get('model') == requested['model'] and
                          x.get('reasoning_effort') == requested['effort'] for x in observed)
            reads = B.RUNNER.explicit_route_reads(agent.get('actual_commands', []),
                       campaign / 'sources' / spec['arm'], workspace) if spec['arm'] != 'vanilla' else []
            opened = agent.get('route_observation', {}).get('opened', [])
            activation = spec['arm'] == 'vanilla' or ('skills/' + ENTRY[spec['arm']] + '/SKILL.md') in set(reads) | set(opened)
            child_gap = len(agent.get('native_child_thread_ids', [])) != len(agent.get('child_metadata', []))
            row = {**spec, 'agent_status': agent.get('status'), 'grade': graded,
                   'grading_backend': manifest['backend'],
                   'grader_sha256': manifest['harness']['comparison-scenarios.py'],
                   'interpreter_sha256': manifest['python']['sha256'],
                   'comparable': agent.get('status') == 'completed' and settings_ok and activation and not child_gap,
                   **settings, **B.token_metrics(agent), 'activation_observed': activation,
                   'route_reads': sorted(reads), 'route_opens': opened, 'wall_seconds': agent.get('wall_seconds'),
                   'questions_observed': len(agent['questions']) if 'questions' in agent else None,
                   'questions_unnecessary': None, 'patch_sha256': digest(patch),
                   'diff_bytes': patch.stat().st_size}
            B.append_result(results, row)
            rows.append(row)
            write(private / 'report.json', report(manifest, rows))
            print(json.dumps(row), flush=True)
    write(private / 'report.json', report(manifest, rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    prep = subs.add_parser('prepare')
    prep.add_argument('--campaign', type=Path, required=True)
    prep.add_argument('--source', action='append', default=[], metavar='ARM=PATH')
    prep.add_argument('--model', required=True)
    prep.add_argument('--effort', required=True)
    prep.add_argument('--seed', type=int, default=19)
    prep.add_argument('--repetitions', type=int, default=1)
    prep.add_argument('--deadline', type=float, default=900)
    launch = subs.add_parser('run')
    launch.add_argument('--campaign', type=Path, required=True)
    summary = subs.add_parser('report')
    summary.add_argument('--campaign', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            prepare(args)
        elif args.action == 'run':
            def interrupted(*_):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, interrupted)
            run(args)
        else:
            private = args.campaign / 'private'
            print(json.dumps(report(json.loads((private / 'manifest.json').read_text()),
                                    B.load_results(private / 'results.jsonl')), indent=2))
    except KeyboardInterrupt:
        print('Interrupted; completed rows retained. Resume with the same run command.', file=sys.stderr)
        return 130
    except (Blocked, OSError, ValueError, B.BenchError, B.RUNNER.HarnessError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
