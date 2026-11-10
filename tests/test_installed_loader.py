import importlib.util
import json
import os
import pwd
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('installed_loader', Path(__file__).resolve().parents[1]/'scripts/check-installed-loader.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class InstalledLoaderTests(unittest.TestCase):
    def test_real_execution_refuses_non_ci_before_any_command_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(P.os.environ, {'CI': '', 'GITHUB_ACTIONS': ''}), patch.object(P, 'command') as command:
                with self.assertRaisesRegex(P.Blocked, 'GitHub-hosted'):
                    P.execute(root, root/'codex', root/'output')
                command.assert_not_called()
                self.assertFalse((root/'output').exists())

    def test_clean_guard_rejects_preexisting_profile_home_override_and_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temporary = root/'temp'
            temporary.mkdir()
            account = root/'account'
            account.mkdir()
            repo = root/'repo'
            repo.mkdir()
            environ = dict(CI='true', GITHUB_ACTIONS='true', RUNNER_ENVIRONMENT='github-hosted',
                           HOME=str(account), GITHUB_WORKSPACE=str(repo), RUNNER_TEMP=str(temporary))
            self.assertEqual(P.clean_runner(repo, temporary/'codex', environ, account)[0], account/'.codex')
            for override in [dict(HOME=str(root/'other')), dict(CODEX_HOME=str(root/'other')), dict(CODEX_HOME=''),
                             dict(OPENAI_API_KEY='synthetic'), dict(CODEX_API_KEY='synthetic'),
                             dict(RUNNER_ENVIRONMENT='self-hosted')]:
                with self.subTest(override=tuple(override)), self.assertRaises(P.Blocked):
                    P.clean_runner(repo, temporary/'codex', dict(environ, **override), account)
            (account/'.codex').mkdir()
            with self.assertRaisesRegex(P.Blocked, 'preexisting'):
                P.clean_runner(repo, temporary/'codex', environ, account)

    def guard_fixture(self, root):
        repo = root / 'repo'
        repo.mkdir()
        binary = root / 'codex'
        binary.write_text('#!' + sys.executable + '\nprint("official CLI reached")\n')
        binary.chmod(0o755)
        output = root / 'evidence'
        with patch.object(P, 'clean_runner', return_value=(root / 'profile', root)), \
             patch.object(P, 'command', side_effect=P.Blocked('stop after guard creation')):
            self.assertFalse(P.execute(repo, binary, output))
        preflight = output / 'preflight-profiles'
        preflight.mkdir(mode=0o700, exist_ok=True)
        candidate = preflight / 'candidate'
        candidate.mkdir(mode=0o700)
        env = dict(os.environ, HOME=pwd.getpwuid(os.getuid()).pw_dir)
        env.pop('CODEX_HOME', None)
        return repo, output / 'codex-with-unchanged-profile', candidate, env

    def test_guard_accepts_private_preflight_adds_without_changing_the_default_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, guard, candidate, env = self.guard_fixture(Path(directory))
            for args in (['plugin', 'marketplace', 'add', str(repo)], ['plugin', 'add', P.PLUGIN]):
                result = subprocess.run([str(guard), *args], env=dict(env, CODEX_HOME=str(candidate)), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('official CLI reached', result.stdout)
            result = subprocess.run([str(guard), '--version'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_guard_rejects_external_profiles_and_preflight_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, guard, candidate, env = self.guard_fixture(root)
            outside = root / 'outside'
            outside.mkdir(mode=0o700)
            linked = candidate.parent / 'linked'
            linked.symlink_to(outside, target_is_directory=True)
            public = candidate.parent / 'public'
            public.mkdir(mode=0o755)
            for profile in ('', str(outside), str(linked), str(public)):
                result = subprocess.run([str(guard), 'plugin', 'add', P.PLUGIN], env=dict(env, CODEX_HOME=profile), capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, profile)
                self.assertNotIn('official CLI reached', result.stdout)
            for args in (['plugin', 'remove', P.PLUGIN], ['plugin', 'add', 'other'], ['plugin', 'marketplace', 'add', str(outside)]):
                result = subprocess.run([str(guard), *args], env=dict(env, CODEX_HOME=str(candidate)), capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, args)
                self.assertNotIn('official CLI reached', result.stdout)

    def reapply_fixture(self, root, replacement):
        repo, profile = root / 'repo', root / 'profile'
        repo.mkdir()
        profile.mkdir()
        config = profile / 'config.toml'
        config.write_text('[marketplaces.cstack]\nsource_type = "local"\n\n[plugins."cstack@cstack"]\nenabled = true\n')
        installs = 0
        def command(args, cwd, env):
            nonlocal installs
            if args[1:] == ['--version']:
                return 'codex-cli ' + P.VERSION
            if args[:2] == ['bash', str(repo / 'install.sh')]:
                if args[2:] == ['install', '--local']:
                    installs += 1
                    if installs == 2:
                        config.write_text(replacement)
                return ''
            return 'fixture'
        empty = ({'marketplaces': []}, {'data': []})
        installed = {'marketplaces': [{'plugins': [{'id': P.PLUGIN, 'installed': True}]}]}
        with patch.object(P, 'clean_runner', return_value=(profile, root)), \
             patch.object(P, 'command', side_effect=command), \
             patch.object(P, 'snapshot', side_effect=[empty, (installed, {}), (installed, {}), empty]), \
             patch.object(P, 'installed_evidence', return_value={'fixture': 'installed'}):
            result = P.execute(repo, root / 'codex', root / 'evidence')
        return result, json.loads((root / 'evidence/receipt.json').read_text())

    @unittest.skipIf(sys.version_info < (3, 11), 'TOML configuration checks require Python 3.11')
    def test_reapply_preserves_values_when_the_cli_reorders_toml_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            result, receipt = self.reapply_fixture(Path(directory),
                '\n[plugins."cstack@cstack"]\nenabled = true\n\n[marketplaces.cstack]\nsource_type = "local"\n')
            self.assertTrue(result, receipt)
            self.assertTrue(receipt['reapplyPreservedState'])

    @unittest.skipIf(sys.version_info < (3, 11), 'TOML configuration checks require Python 3.11')
    def test_reapply_rejects_changed_config_values_or_types(self):
        for value in ('false', '1', '"true"'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                result, receipt = self.reapply_fixture(Path(directory),
                    '[marketplaces.cstack]\nsource_type = "local"\n\n[plugins."cstack@cstack"]\nenabled = ' + value + '\n')
                self.assertFalse(result)
                self.assertEqual(receipt['status'], 'blocked')
                self.assertIn('reapply changed', receipt['error'])

    def fixture(self, root):
        repo, profile = root/'repo', root/'profile'
        manifest = repo/'plugins/cstack/.codex-plugin/plugin.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'version': 'fixture-version'}))
        source = repo/'plugins/cstack/skills/example/SKILL.md'
        source.parent.mkdir(parents=True)
        source.write_text('fixture skill')
        cached = profile/'plugins/cache/cstack/cstack/local/skills/example/SKILL.md'
        cached.parent.mkdir(parents=True)
        cached.write_bytes(source.read_bytes())
        cached_manifest = cached.parents[2]/'.codex-plugin/plugin.json'
        cached_manifest.parent.mkdir()
        cached_manifest.write_bytes(manifest.read_bytes())
        plugins = {'marketplaces': [{'name': 'cstack', 'plugins': [{'id': P.PLUGIN,
            'enabled': True, 'installed': True, 'localVersion': 'fixture-version'}]}]}
        skills = {'data': [{'cwd': '/fixture', 'errors': [], 'skills': [{'name': 'example',
            'pluginId': P.PLUGIN, 'enabled': True, 'path': str(cached)}]}]}
        return repo, profile, source, cached, plugins, skills

    def test_installed_discovery_requires_owner_cache_location_bytes_and_completeness(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, profile, source, cached, plugins, skills = self.fixture(Path(directory))
            self.assertEqual(P.installed_evidence(plugins, skills, repo, profile)['skillCount'], 1)
            skills['data'][0]['skills'][0]['path'] = str(source)
            with self.assertRaisesRegex(P.Blocked, 'installed cache'):
                P.installed_evidence(plugins, skills, repo, profile)
            skills['data'][0]['skills'][0]['path'] = str(cached)
            cached.write_text('changed')
            with self.assertRaises(P.Blocked):
                P.installed_evidence(plugins, skills, repo, profile)
            cached.write_bytes(source.read_bytes())
            skills['data'][0]['skills'][0]['pluginId'] = None
            with self.assertRaisesRegex(P.Blocked, 'incomplete'):
                P.installed_evidence(plugins, skills, repo, profile)

    def test_installed_executable_mode_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, profile, _, cached, plugins, skills = self.fixture(Path(directory))
            source_tool = repo/'plugins/cstack/scripts/tool.sh'
            source_tool.parent.mkdir()
            source_tool.write_text('#!/bin/sh\nexit 0\n')
            source_tool.chmod(0o755)
            cached_tool = cached.parents[2]/'scripts/tool.sh'
            cached_tool.parent.mkdir()
            cached_tool.write_bytes(source_tool.read_bytes())
            with self.assertRaises(P.Blocked):
                P.installed_evidence(plugins, skills, repo, profile)
            cached_tool.chmod(0o755)
            self.assertEqual(P.installed_evidence(plugins, skills, repo, profile)['sourceFileCount'], 3)

    def test_installed_discovery_rejects_disabled_plugin_and_wrong_version(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, profile, _, _, plugins, skills = self.fixture(Path(directory))
            row = plugins['marketplaces'][0]['plugins'][0]
            row['enabled'] = False
            with self.assertRaises(P.Blocked):
                P.installed_evidence(plugins, skills, repo, profile)
            row.update(enabled=True, localVersion='other')
            with self.assertRaisesRegex(P.Blocked, 'version'):
                P.installed_evidence(plugins, skills, repo, profile)


if __name__ == '__main__':
    unittest.main()
