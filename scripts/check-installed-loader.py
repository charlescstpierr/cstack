#!/usr/bin/env python3
"""Exercise the installed Codex loader only in a fresh GitHub-hosted CI profile."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile

VERSION = '0.166.0'
PLUGIN = 'cstack@cstack'


class Blocked(RuntimeError):
    pass


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def within(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def clean_runner(repo, codex, environ, registered_home):
    if not (environ.get('CI') == 'true' and environ.get('GITHUB_ACTIONS') == 'true'
            and environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'):
        raise Blocked('requires a fresh GitHub-hosted runner')
    if environ.get('HOME') != str(registered_home) or 'CODEX_HOME' in environ:
        raise Blocked('requires the unchanged account home and no CODEX_HOME override')
    if any(environ.get(key) for key in ('OPENAI_API_KEY', 'CODEX_API_KEY')):
        raise Blocked('model credentials are not allowed for this loader check')
    if repo.resolve() != Path(environ.get('GITHUB_WORKSPACE', '/missing')).resolve():
        raise Blocked('repository must be the Actions checkout')
    temporary = Path(environ.get('RUNNER_TEMP', '/missing'))
    if not temporary.is_dir() or not within(codex, temporary):
        raise Blocked('Codex must be the pinned temporary package')
    profile = registered_home / '.codex'
    if profile.exists() or profile.is_symlink():
        raise Blocked('preexisting Codex profile; refusing installation')
    return profile, temporary


def command(args, cwd, env):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=90)
    if result.returncode:
        # Full output may contain account/configuration data. Keep it out of artifacts.
        raise Blocked('command failed with exit ' + str(result.returncode) + ': ' + args[0])
    return result.stdout


def snapshot(repo, codex, workspace, output):
    spec = importlib.util.spec_from_file_location('loader_existing_ipc', repo / 'scripts/verify-behavior.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    server = runner.AppServer([str(codex), 'app-server', '--stdio'], workspace,
                             Path(os.devnull), output / 'ipc.stderr')
    def notification(message):
        if isinstance(message, dict) and 'id' in message and 'method' in message:
            raise Blocked('IPC requires interaction; no authentication or approval attempted')
    try:
        server.request('initialize', {'clientInfo': {'name': 'cstack-installed-loader', 'version': '1'},
                       'capabilities': {'experimentalApi': True}}, 30, notification)
        server.notify('initialized')
        plugins = server.request('plugin/list', {'cwds': [str(workspace)], 'marketplaceKinds': ['local'],
                                  'forceRefetch': False}, 30, notification)
        skills = server.request('skills/list', {'cwds': [str(workspace)], 'forceReload': True}, 30, notification)
        return plugins, skills
    except (runner.HarnessError, runner.NeedsInput, TimeoutError):
        raise Blocked('non-model IPC unavailable without interaction') from None
    finally:
        server.close()


def plugin_rows(plugins):
    return [plugin for marketplace in plugins.get('marketplaces', [])
            for plugin in marketplace.get('plugins', []) if plugin.get('id') == PLUGIN]


def installed_evidence(plugins, skills, repo, profile):
    rows = plugin_rows(plugins)
    manifest = json.loads((repo / 'plugins/cstack/.codex-plugin/plugin.json').read_text())
    if len(rows) != 1 or not rows[0].get('installed') or not rows[0].get('enabled'):
        raise Blocked('installed and enabled plugin not established by plugin/list')
    if rows[0].get('localVersion') != manifest['version']:
        raise Blocked('installed manifest version is missing or different')
    expected = {path.parent.name: path for path in (repo / 'plugins/cstack/skills').glob('*/SKILL.md')}
    actual = {}
    cache_roots = set()
    for entry in skills.get('data', []):
        if entry.get('errors'):
            raise Blocked('skills/list returned discovery errors')
        for skill in entry.get('skills', []):
            if skill.get('pluginId') != PLUGIN:
                continue
            path = Path(skill['path'])
            if not skill.get('enabled') or not path.is_file() or not within(path, profile / 'plugins/cache'):
                raise Blocked('plugin skill is disabled or not loaded from the installed cache')
            name = path.parent.name
            if name not in expected or name in actual or digest(path) != digest(expected[name]):
                raise Blocked('installed skill is duplicate, foreign or differs from source')
            cache_roots.add(path.parents[2])
            actual[name] = {'name': skill['name'], 'path': str(path), 'sha256': digest(path)}
    if set(actual) != set(expected):
        raise Blocked('installed skill discovery is incomplete')
    if len(cache_roots) != 1:
        raise Blocked('skills do not belong to one installed package')
    cache_root = next(iter(cache_roots))
    source_root = repo / 'plugins/cstack'
    ignored = {'.git', '.cstack', '__pycache__', 'node_modules'}
    source_files = {path.relative_to(source_root).as_posix(): {'sha256': digest(path), 'executable': bool(path.stat().st_mode & 0o111)}
                    for path in source_root.rglob('*') if path.is_file()
                    and not set(path.relative_to(source_root).parts) & ignored}
    for relative, expected_file in source_files.items():
        cached = cache_root / relative
        if (not within(cached, cache_root) or digest(cached) != expected_file['sha256']
                or bool(cached.stat().st_mode & 0o111) != expected_file['executable']):
            raise Blocked('installed package file differs or is missing: ' + relative)
    inventory_sha = hashlib.sha256(json.dumps(source_files, sort_keys=True).encode()).hexdigest()
    return {'id': PLUGIN, 'version': manifest['version'], 'enabled': True,
            'sourceFileCount': len(source_files), 'packageInventorySha256': inventory_sha,
            'skillCount': len(actual), 'skills': actual}


def execute(repo, codex, output):
    registered_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    profile, temporary = clean_runner(repo, codex, os.environ, registered_home)
    if not within(output, temporary):
        raise Blocked('evidence output must stay under RUNNER_TEMP')
    output.mkdir(parents=True, exist_ok=False)
    evidence = {'status': 'unverified', 'phase': 'cli-version', 'modelTurnsRequested': 0, 'codexVersion': VERSION,
                'limits': ['Codex CLI installed discovery only; no T3 installation claim',
                           'No model turn or ordinary-task activation behavior tested']}
    wrapper = output / 'codex-with-unchanged-profile'
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\n'
        + 'if "CODEX_HOME" in os.environ or os.environ.get("HOME") != ' + repr(str(registered_home)) + ':\n'
        + '    raise SystemExit("BLOCKED: installer attempted a profile override")\n'
        + 'os.execv(' + repr(str(codex)) + ', [' + repr(str(codex)) + ', *sys.argv[1:]])\n')
    wrapper.chmod(0o755)
    env = dict(os.environ, CSTACK_CODEX=str(wrapper))
    installer = ['bash', str(repo / 'install.sh')]
    installed = False
    try:
        if command([str(codex), '--version'], repo, env).strip() != 'codex-cli ' + VERSION:
            raise Blocked('unexpected Codex CLI version')
        evidence['sourceHead'] = command(['git', 'rev-parse', 'HEAD'], repo, env).strip()
        evidence['sourceTree'] = command(['git', 'rev-parse', 'HEAD^{tree}'], repo, env).strip()
        evidence['cliLockSha256'] = digest(repo / 'ci/installed-loader/package-lock.json')
        evidence['nodeVersion'] = command(['node', '--version'], repo, env).strip()
        with tempfile.TemporaryDirectory(prefix='cstack-loader-cwd-', dir=temporary) as directory:
            workspace = Path(directory)
            evidence['phase'] = 'discovery-before-install'
            before_plugins, before_skills = snapshot(repo, codex, workspace, output)
            if (any(row.get('installed') for row in plugin_rows(before_plugins))
                    or any(skill.get('pluginId') == PLUGIN for entry in before_skills.get('data', [])
                           for skill in entry.get('skills', []))):
                raise Blocked('plugin already installed before the test')
            evidence['phase'] = 'install-local'
            installed = True
            command(installer + ['install', '--local'], repo, env)
            evidence['phase'] = 'doctor-installed'
            command(installer + ['doctor'], repo, env)
            sentinel = profile / 'loader-sentinel.txt'
            sentinel.write_text('owned CI sentinel\n')
            sentinel_sha = digest(sentinel)
            evidence['phase'] = 'installed-discovery'
            plugins, skills = snapshot(repo, codex, workspace, output)
            evidence['installed'] = installed_evidence(plugins, skills, repo, profile)
            config_sha = digest(profile / 'config.toml')
            evidence['phase'] = 'reapply-and-update'
            command(installer + ['install', '--local'], repo, env)
            command(installer + ['update'], repo, env)
            command(installer + ['doctor'], repo, env)
            plugins, skills = snapshot(repo, codex, workspace, output)
            repeated = installed_evidence(plugins, skills, repo, profile)
            if (repeated != evidence['installed'] or digest(profile / 'config.toml') != config_sha
                    or digest(sentinel) != sentinel_sha):
                raise Blocked('reapply changed configured state, skill bytes or the sentinel')
            evidence['reapplyPreservedState'] = True
            evidence['phase'] = 'uninstall'
            command(installer + ['uninstall'], repo, env)
            installed = False
            plugins, skills = snapshot(repo, codex, workspace, output)
            if (any(row.get('installed') for row in plugin_rows(plugins))
                    or any(skill.get('pluginId') == PLUGIN for entry in skills.get('data', [])
                           for skill in entry.get('skills', [])) or digest(sentinel) != sentinel_sha):
                raise Blocked('uninstall did not remove installed discovery or preserve the sentinel')
            evidence.update(status='verified', uninstallVerified=True)
    except (Blocked, OSError, ValueError, TimeoutError, subprocess.TimeoutExpired) as error:
        evidence.update(status='blocked', error=type(error).__name__ + ': ' + str(error))
    finally:
        if installed:
            try:
                command(installer + ['uninstall'], repo, env)
                evidence['cleanup'] = 'uninstalled'
            except (Blocked, OSError, TimeoutError, subprocess.TimeoutExpired):
                evidence['cleanup'] = 'failed; ephemeral runner must be discarded'
        (output / 'receipt.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence['status'] == 'verified'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--codex', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--guard-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.guard_only:
            clean_runner(args.repo.resolve(), args.codex.resolve(), os.environ, Path(pwd.getpwuid(os.getuid()).pw_dir))
            print(json.dumps({'profileGuard': 'passed'}))
            return 0
        passed = execute(args.repo.resolve(), args.codex.resolve(), args.output.resolve())
    except Blocked as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps({'verified': passed, 'receipt': str(args.output / 'receipt.json')}))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
