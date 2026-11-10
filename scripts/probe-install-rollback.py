#!/usr/bin/env python3
"""Exercise official plugin CLIs in disposable profiles, without calling a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=('codex', 'claude', 'both'), default='both')
    parser.add_argument('--script', type=Path, default=ROOT / 'install.sh')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    receipts = []
    for host in (('codex', 'claude') if args.host == 'both' else (args.host,)):
        binary = shutil.which(host)
        if not binary:
            raise RuntimeError(f'{host} is not installed')
        cli_version = subprocess.check_output([binary, '--version'], text=True).strip()
        workspace = Path(tempfile.mkdtemp(prefix=f'cstack-native-{host}-'))
        profile = workspace / 'profile'
        profile.mkdir()
        sources = [workspace / 'previous', workspace / 'requested']
        for source in sources:
            for manifest in ('.agents/plugins/marketplace.json', '.claude-plugin/marketplace.json'):
                target = source / manifest
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / manifest, target)
            shutil.copytree(ROOT / 'plugins/cstack', source / 'plugins/cstack',
                            ignore=shutil.ignore_patterns('node_modules', '__pycache__'))
            shutil.copy2(args.script, source / 'install.sh')
        marker = sources[0] / 'plugins/cstack/rollback-probe.txt'
        marker.write_text('OLD')
        (sources[1] / 'plugins/cstack/rollback-probe.txt').write_text('TARGET')
        env = dict(os.environ, CODEX_HOME=str(profile), CLAUDE_CONFIG_DIR=str(profile),
                   XDG_STATE_HOME=str(workspace / 'state'),
                   CSTACK_CODEX=binary if host == 'codex' else str(workspace / 'absent'),
                   CSTACK_CLAUDE=binary if host == 'claude' else str(workspace / 'absent'))
        def run(script, environment, name):
            result = subprocess.run(['bash', str(script), 'install', '--local'], env=environment,
                                    text=True, capture_output=True, timeout=90)
            (args.output / f'{host}-{name}.log').write_text(result.stdout + result.stderr)
            return result
        initial = run(sources[0] / 'install.sh', env, 'initial')
        if initial.returncode:
            raise RuntimeError(f'{host} initial install failed; see output logs')
        version_file = '.codex-plugin/plugin.json' if host == 'codex' else '.claude-plugin/plugin.json'
        version = json.loads((sources[0] / 'plugins/cstack' / version_file).read_text())['version']
        cached = profile / 'plugins/cache/cstack/cstack' / version / 'rollback-probe.txt'
        def installed_state():
            command = [binary, 'plugin', 'list', '--json'] + (['--available'] if host == 'codex' else [])
            data = json.loads(subprocess.check_output(command, env=env, text=True))
            rows = data['installed'] if host == 'codex' else data
            entry = next(row for row in rows if row.get('pluginId' if host == 'codex' else 'id') == 'cstack@cstack')
            return dict(installed=entry['installed'] if host == 'codex' else True,
                        enabled=entry['enabled'], version=entry['version'])
        before = cached.read_text()
        state_before = installed_state()
        marker.write_text('NEW')
        fired = workspace / 'fault-fired'
        wrapper = workspace / 'fault-cli'
        install_verb = 'add' if host == 'codex' else 'install'
        profile_variable = 'CODEX_HOME' if host == 'codex' else 'CLAUDE_CONFIG_DIR'
        wrapper.write_text('#!' + sys.executable + '\n' + f'''
import os, subprocess, sys
from pathlib import Path
result = subprocess.run([{binary!r}, *sys.argv[1:]])
if (result.returncode == 0 and os.environ.get({profile_variable!r}) == {str(profile)!r}
        and sys.argv[1:3] == ['plugin', {install_verb!r}] and not Path({str(fired)!r}).exists()):
    Path({str(fired)!r}).touch()
    print('injected failure AFTER the real plugin install', file=sys.stderr)
    sys.exit(47)
sys.exit(result.returncode)
''')
        wrapper.chmod(0o755)
        failing_env = dict(env, **{'CSTACK_CODEX' if host == 'codex' else 'CSTACK_CLAUDE': str(wrapper)})
        result = run(sources[1] / 'install.sh', failing_env, 'rollback')
        after = cached.read_text() if cached.exists() else None
        state_after = installed_state()
        receipt = dict(host=host, cli_version=cli_version, plugin_state_before=state_before, plugin_state_after=state_after, workspace=str(workspace), cli=binary, before=before, after=after,
                       mutable_source=marker.read_text(), returncode=result.returncode, injected=fired.exists(),
                       installer_sha256=hashlib.sha256(args.script.read_bytes()).hexdigest())
        receipts.append(receipt)
        (args.output / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
        print(json.dumps(receipt), flush=True)
        if result.returncode == 0 or not fired.exists() or before != 'OLD' or after != before or state_after != state_before or not state_after['enabled'] or marker.read_text() != 'NEW':
            raise AssertionError(f'{host}: failed transaction changed the installed snapshot')
    return 0


if __name__ == '__main__':
    sys.exit(main())
