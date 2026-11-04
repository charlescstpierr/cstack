import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from test_models import models, CATALOG


def seal(catalog):
    catalog.pop('sha256', None)
    catalog['sha256'] = hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return catalog


def fixture():
    context = dict(environmentId='synthetic-env', sessionId='synthetic-session',
                   capabilitiesSha256='a' * 64, traceSha256='b' * 64, revalidated=True)
    catalog = {k: v for k, v in context.items() if k != 'revalidated'}
    catalog.update(host='t3', observedAt='2026-01-01T00:00:00Z', expiresAt='2099-01-01T00:00:00Z',
                   providers={'fixture-provider': {'available': True, 'modelsComplete': False,
                       'models': {'fixture-model': {'options': {'effort': {'type': 'string',
                            'values': ['fixture-high'], 'secret': False}}}}}},
                   inheritance=dict(inheritedProviderInstanceId='fixture-provider', inheritedModel='fixture-model',
                                    inheritedOptions={'effort': 'fixture-high'}))
    selected = dict(runtime='t3', providerInstanceId='fixture-provider', model='fixture-model', options={'effort': 'fixture-high'})
    return seal(catalog), context, selected


class T3ModelsTests(unittest.TestCase):
    def setUp(self):
        self.catalog, self.context, self.selected = fixture()

    def report(self, value, host='t3', context=True):
        return models.preflight({'interrogate reviewers': value}, ['interrogate reviewers'], self.catalog,
                                host, self.context if context else None)

    def test_shared_selection_contract(self):
        path = Path(__file__).parent / 'fixtures/t3-selections.json'
        for row in json.loads(path.read_text()):
            with self.subTest(selection=row['selection']):
                if row['valid']:
                    self.assertEqual(models.selection(row['selection']), row['selection'])
                else:
                    with self.assertRaises(ValueError):
                        models.selection(row['selection'])

    def test_positions_preserve_order_and_cli_blocks_without_substitution(self):
        report = self.report([self.selected, {'runtime': 'claude-code'}, 'inherit-parent'])
        rows = report['positions']['interrogate reviewers']
        self.assertEqual([r['status'] for r in rows], ['ready', 'blocked', 'ready'])
        self.assertEqual([r['position'] for r in rows], [0, 1, 2])
        self.assertEqual(rows[0]['target'], {k: self.selected[k] for k in ('providerInstanceId', 'model', 'options')})
        self.assertEqual(rows[2]['target'], rows[0]['target'])
        self.assertNotIn('interrogate reviewers', report['resolved'])

    def test_outside_host_blocks_only_dependent_role_even_with_stale_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = root / '.codex/agents/cstack-explorer.toml'
            agent.parent.mkdir(parents=True)
            agent.write_text('# cstack:managed\nmodel = "stale"\n')
            config = {'how explorer': self.selected, 'documentation': 'inherit-parent'}
            report = models.preflight(config, list(config), CATALOG)
            self.assertEqual(report['status'], 'blocked')
            self.assertEqual(report['positions']['documentation'][0]['status'], 'ready')
            self.assertEqual(report['resolved']['documentation'], models.resolve(config, 'documentation', CATALOG))
            self.assertIn('hors hôte', report['errors']['how explorer'])
            models.project_helper().sync_agents(root, config)
            self.assertEqual(agent.read_text(), '# cstack:managed\nmodel = "stale"\n')

    def test_managed_and_manual_agents_untouched_even_explicit_enable_disable(self):
        project = models.project_helper()
        for content in (b'# cstack:managed\nmodel="old"\n', b'# manual\n'):
            for mode in (None, True, False):
                snapshots = {p: None for p in project.AGENT_PATHS.values()}
                snapshots[project.AGENT_PATHS['cstack-explorer']] = content
                changes = project._agent_changes(mode, snapshots, {'how explorer': self.selected}, models)
                self.assertNotIn(project.AGENT_PATHS['cstack-explorer'], changes)

    def test_global_shape_error_is_not_role_availability(self):
        with self.assertRaises(ValueError):
            models.preflight({'documentation': 'inherit-parent', 'how explorer': {**self.selected, 'reasoning_effort': 'high'}}, ['documentation'], CATALOG)
        models.validate({'how explorer': self.selected})
        self.assertNotIn('t3', models.RUNTIMES)

    def test_catalog_context_options_and_inheritance_fail_closed(self):
        mutations = [lambda c: c.update(environmentId='foreign'), lambda c: c.update(sessionId='foreign'),
                     lambda c: c.update(expiresAt='2020-01-01T00:00:00Z'),
                     lambda c: c['providers']['fixture-provider'].update(available=False),
                     lambda c: c['providers']['fixture-provider']['models'].clear(),
                     lambda c: c['providers']['fixture-provider']['models']['fixture-model']['options']['effort'].update(secret=True)]
        for mutate in mutations:
            self.catalog, self.context, self.selected = fixture()
            mutate(self.catalog)
            seal(self.catalog)
            with self.subTest(catalog=self.catalog):
                self.assertEqual(self.report([self.selected])['status'], 'blocked')
        self.catalog, self.context, self.selected = fixture()
        self.assertEqual(self.report([self.selected], context=False)['status'], 'blocked')
        self.context['revalidated'] = False
        self.assertEqual(self.report([self.selected])['status'], 'blocked')
        self.context['revalidated'] = True
        self.catalog['inheritance'].pop('inheritedOptions')
        seal(self.catalog)
        self.assertEqual(self.report(['inherit-parent'])['status'], 'blocked')

    def test_unknown_options_values_types_and_native_pairs_block(self):
        for options in ({'effort': 'wrong'}, {'reasoningEffort': 'fixture-high'}, {'effort': True}, {'token': 'secret'}):
            self.selected['options'] = options
            self.assertEqual(self.report([self.selected])['status'], 'blocked')
        for pair in ('fixture-model', {'model': 'fixture-model', 'reasoning_effort': 'high'}):
            self.assertEqual(self.report([pair])['status'], 'blocked')

    def test_t3_preview_and_explicit_apply_no_codex_recommendations(self):
        preview = models.preview({}, 'digest', self.catalog, host='t3', context=self.context)
        self.assertEqual(preview['recommendations'], {})
        self.assertIn('TOUT', preview['warning'])
        self.assertEqual(preview['supported']['fixture-provider']['fixture-model']['effort']['values'], ['fixture-high'])
        self.assertEqual(models.preview({}, 'digest', self.catalog, host='t3')['supported'], {})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, digest = models.read_config(root / '.cstack/models.json')
            project = models.project_helper()
            result = project.apply_model_choices(root, {'how explorer': self.selected}, digest, self.catalog, 't3', self.context)
            self.assertEqual(result['saved']['how explorer'], self.selected)
            self.assertFalse((root / '.codex/agents/cstack-explorer.toml').exists())

    def test_ready_preflight_matches_resolve(self):
        config = {'how explorer': self.selected}
        report = models.preflight(config, list(config), self.catalog, 't3', self.context)
        self.assertEqual(report['resolved']['how explorer'],
                         models.resolve(config, 'how explorer', self.catalog, 't3', self.context))
