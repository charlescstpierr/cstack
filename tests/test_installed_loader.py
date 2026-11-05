import importlib.util
import json
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
