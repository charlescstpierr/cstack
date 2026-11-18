"""Inject failures through external CLI processes and compare observable state."""
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(os.environ.get("CSTACK_INSTALL_SCRIPT", ROOT / "install.sh"))

CLI = r'''
import json, os, shutil, sys, time
from pathlib import Path
host = Path(sys.argv[0]).name
home = Path(os.environ['CODEX_HOME' if host == 'codex' else 'CLAUDE_CONFIG_DIR'])
home.mkdir(parents=True, exist_ok=True)
path = home / 'state.json'
root = home / 'marketplace'
state = json.loads(path.read_text()) if path.exists() else dict(source=None, installed=False, enabled=True, installed_version=None)
args = sys.argv[1:]
real = str(home) == os.environ['TEST_MAIN_PROFILE']
def save(): path.write_text(json.dumps(state))
def fault(stage):
    marker = Path(os.environ['TEST_FAULT_MARKER'])
    if stage == os.environ.get('TEST_FAULT') and not marker.exists():
        marker.touch()
        if stage == 'signal':
            Path(os.environ['TEST_READY']).touch()
            time.sleep(30)
        print('injected ' + stage, file=sys.stderr)
        sys.exit(1)
def source_entry():
    base, _, ref = state['source'].partition('#')
    if base.startswith('/'):
        return dict(name='cstack', source='directory', path=base, installLocation=str(root))
    return dict(name='cstack', source='github', repo=base, ref=ref, installLocation=str(root))
if args == ['--version']:
    print('test cli')
elif args[:3] == ['plugin', 'marketplace', 'list']:
    if host == 'codex':
        entry = dict(name='cstack', root=state['source'] if state['source'] and state['source'].startswith('/') else str(root), marketplaceSource=dict(sourceType='local' if state['source'] and state['source'].startswith('/') else 'git', source=state['source']))
        print(json.dumps(dict(marketplaces=[entry] if state['source'] else [])))
    else:
        print(json.dumps([source_entry()] if state['source'] else []))
elif args[:2] == ['plugin', 'list']:
    if os.environ.get('TEST_BAD_STATUS') == 'shape' and real:
        print('{}' if host == 'codex' else '{}')
    elif host == 'codex':
        entry = dict(pluginId='cstack@cstack', installed=state['installed'], enabled=state['enabled'], version=state['installed_version'])
        if real and os.environ.get('TEST_BAD_STATUS') == 'enabled': entry['enabled'] = 'false'
        if real and os.environ.get('TEST_BAD_STATUS') == 'version': entry['version'] = None
        print(json.dumps(dict(installed=[entry] if state['installed'] else [], available=[] if state['installed'] else [entry])))
    else:
        entry = dict(id='cstack@cstack', enabled=state['enabled'], version=state['installed_version'], installPath=str(home / 'plugins/cache/cstack/cstack' / str(state['installed_version'])))
        if real and os.environ.get('TEST_BAD_STATUS') == 'enabled': entry['enabled'] = 'false'
        if real and os.environ.get('TEST_BAD_STATUS') == 'version': entry['version'] = None
        print(json.dumps([entry] if state['installed'] else []))
elif args[:3] == ['plugin', 'marketplace', 'add']:
    source = ' '.join(args[3:])
    if state['source'] and state['source'] != source:
        sys.exit(1)
    if os.environ.get('TEST_ROLLBACK_FAIL') and 'install-rollback.' in source:
        print('injected rollback failure', file=sys.stderr)
        sys.exit(1)
    state['source'] = source
    if root.exists(): shutil.rmtree(root)
    if Path(args[3]).is_dir():
        shutil.copytree(args[3], root)
    else:
        (root / 'plugin').mkdir(parents=True)
        (root / 'plugin/version.txt').write_text('old' if 'oldsha' in source else 'new')
        for manifest, plugin_source in [('.agents/plugins/marketplace.json', dict(source='local', path='./plugin')), ('.claude-plugin/marketplace.json', './plugin')]:
            target = root / manifest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(dict(plugins=[dict(name='cstack', source=plugin_source)])))
    save()
    fault('real-add' if real else 'trial-add')
elif args[:3] == ['plugin', 'marketplace', 'remove']:
    state['source'] = None
    if root.exists(): shutil.rmtree(root)
    save()
    if real: fault('remove')
elif args[:2] in (['plugin', 'add'], ['plugin', 'install'], ['plugin', 'update']):
    state.update(installed=True, enabled=True, installed_version=(root / 'plugin/version.txt').read_text())
    cached_plugin = home / 'plugins/cache/cstack/cstack' / state['installed_version']
    shutil.copytree(root / 'plugin', cached_plugin, dirs_exist_ok=True)
    save()
    if real and os.environ.get('TEST_FAULT') == 'signal': fault('signal')
    fault('real-plugin' if real else 'trial-plugin')
elif args[:2] in (['plugin', 'remove'], ['plugin', 'uninstall']):
    state.update(installed=False, installed_version=None)
    save()
else:
    print('unexpected args: ' + repr(args), file=sys.stderr)
    sys.exit(2)
'''


class InstallTransactionTests(unittest.TestCase):
    def scenario(self, host, stage, initial, local=False, signal_case=False, bad_status=False, missing_snapshot=False, rollback_fails=False, missing_installed_cache=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / 'profile'
            profile.mkdir()
            cache = profile / 'marketplace'
            source = root / 'local-source'
            source.mkdir()
            self.source_tree(source, 'new')
            state = dict(source=(str(source) if local else 'owner/repo') if initial not in ('fresh', 'orphan') else None,
                         installed=initial in ('installed', 'disabled', 'orphan'), enabled=initial != 'disabled',
                         installed_version='old' if initial in ('installed', 'disabled', 'orphan') else None)
            if state['source']:
                cache.mkdir()
                self.source_tree(cache, 'old')
            installed_cache = profile / 'plugins/cache/cstack/cstack/old'
            if state['installed']:
                installed_cache.mkdir(parents=True)
                (installed_cache / 'version.txt').write_text('old')
            state_file = profile / 'state.json'
            state_file.write_text(json.dumps(state))
            if missing_snapshot:
                shutil.rmtree(cache)
            if missing_installed_cache:
                shutil.rmtree(installed_cache)
            before = self.observe(state_file, cache)
            tools = root / 'bin'
            tools.mkdir()
            tool = tools / host
            tool.write_text('#!' + sys.executable + '\n' + CLI)
            tool.chmod(0o755)
            git = tools / 'git'
            git.write_text('#!/bin/sh\nif [ "$1" = -C ]; then echo oldsha; fi\n')
            git.chmod(0o755)
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'],
                       CSTACK_CODEX=str(tool) if host == 'codex' else str(tools / 'absent'),
                       CSTACK_CLAUDE=str(tool) if host == 'claude' else str(tools / 'absent'),
                       CODEX_HOME=str(profile), CLAUDE_CONFIG_DIR=str(profile), XDG_STATE_HOME=str(root / 'state'),
                       TEST_MAIN_PROFILE=str(profile), TEST_FAULT=stage, TEST_FAULT_MARKER=str(root / 'fired'),
                       TEST_READY=str(root / 'ready'))
            if bad_status:
                env['TEST_BAD_STATUS'] = bad_status
            if rollback_fails:
                env['TEST_ROLLBACK_FAIL'] = '1'
            command = ['bash', str(SCRIPT), 'install', '--ref', 'new']
            if signal_case:
                process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    deadline = time.monotonic() + 8
                    while not (root / 'ready').exists():
                        if time.monotonic() > deadline or process.poll() is not None:
                            self.fail('installer did not reach signal barrier')
                        time.sleep(0.01)
                    os.killpg(process.pid, signal.SIGTERM)
                    stdout, stderr = process.communicate(timeout=10)
                    code = process.returncode
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.communicate()
                self.assertIn(code, (-signal.SIGTERM, 128 + signal.SIGTERM), stdout + stderr)
            else:
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
                code, stdout, stderr = result.returncode, result.stdout, result.stderr
                self.assertNotEqual(code, 0, stdout + stderr)
            after_observation = self.observe(state_file, cache)
            receipts = os.environ.get('CSTACK_INSTALL_RECEIPTS')
            if receipts:
                with open(receipts, 'a') as stream:
                    stream.write(json.dumps(dict(host=host, stage=stage, initial=initial, local=local,
                        bad_status=bad_status, missing_snapshot=missing_snapshot, rollback_fails=rollback_fails, missing_installed_cache=missing_installed_cache,
                        returncode=code, fault_reached=(root / 'fired').exists(), before=before, after=after_observation)) + '\n')
            if rollback_fails:
                self.assertIn('restauration impossible', stderr)
                snapshots = list((root / 'state/cstack').glob('install-rollback.*/source/plugin/version.txt'))
                self.assertEqual([p.read_text() for p in snapshots], ['old'])
                return
            self.assertEqual(self.observe(state_file, cache), before, stdout + stderr)
            if initial not in ('disabled', 'orphan') and not bad_status and not missing_snapshot and not missing_installed_cache:
                self.assertTrue((root / 'fired').exists(), 'fault injection was not reached: ' + stdout + stderr)
            else:
                self.assertFalse((root / 'fired').exists(), 'active profile was changed before rejecting the state')
            # A recovery source must survive after the transaction subprocess exits.
            after = json.loads(state_file.read_text())
            if after['source'] and after['source'].startswith('/') and after['source'] != str(source):
                self.assertEqual((Path(after['source']) / 'plugin/version.txt').read_text(), 'old')

    def source_tree(self, root, version):
        (root / 'plugin').mkdir(exist_ok=True)
        (root / 'plugin/version.txt').write_text(version)
        for manifest, source in [('.agents/plugins/marketplace.json', dict(source='local', path='./plugin')), ('.claude-plugin/marketplace.json', './plugin')]:
            target = root / manifest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(dict(plugins=[dict(name='cstack', source=source)])))

    def observe(self, path, cache):
        state = json.loads(path.read_text())
        return dict(present=bool(state['source']), installed=state['installed'], enabled=state['enabled'],
                    installed_version=state['installed_version'], snapshot=(cache / 'plugin/version.txt').read_text() if cache.exists() else None)

    def matrix(self, host):
        for initial in ('fresh', 'installed', 'uninstalled'):
            for stage in ('trial-add', 'trial-plugin', 'remove', 'real-add', 'real-plugin'):
                if initial == 'fresh' and stage == 'remove':
                    continue
                with self.subTest(host=host, initial=initial, stage=stage):
                    self.scenario(host, stage, initial)

    def test_codex_failure_matrix_4114031723(self):
        self.matrix('codex')

    def test_claude_failure_matrix(self):
        self.matrix('claude')

    def test_codex_local_snapshot_4114185309(self):
        self.scenario('codex', 'real-plugin', 'installed', local=True)

    def test_claude_local_snapshot(self):
        self.scenario('claude', 'real-plugin', 'installed', local=True)

    def test_codex_term_preserves_state(self):
        self.scenario('codex', 'signal', 'installed', signal_case=True)

    def test_claude_term_preserves_state(self):
        self.scenario('claude', 'signal', 'installed', signal_case=True)

    def test_missing_snapshot_never_mutates(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host):
                self.scenario(host, 'real-plugin', 'installed', missing_snapshot=True)
            with self.subTest(host=host, missing='installed-cache'):
                self.scenario(host, 'real-plugin', 'installed', missing_installed_cache=True)

    def test_failed_rollback_retains_recovery_snapshot(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host):
                self.scenario(host, 'real-plugin', 'installed', rollback_fails=True)

    def test_disabled_or_unknown_states_never_mutate(self):
        for host in ('codex', 'claude'):
            with self.subTest(host=host, state='disabled'):
                self.scenario(host, 'real-plugin', 'disabled')
            with self.subTest(host=host, state='orphan'):
                self.scenario(host, 'real-plugin', 'orphan')
            for shape in ('shape', 'enabled', 'version'):
                with self.subTest(host=host, state='unknown', shape=shape):
                    self.scenario(host, 'real-plugin', 'installed', bad_status=shape)


if __name__ == '__main__':
    unittest.main()
