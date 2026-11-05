import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from test_models import models, CATALOG


def seal(catalog):
    catalog.pop('sha256', None)
    catalog['sha256'] = hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return catalog


def fixture():
    scope = dict(threadId='synthetic-thread', projectId='synthetic-project', link='opaque-link',
                 providerInstanceId='fixture-provider', model='fixture-model', runtimeMode='full-access',
                 interactionMode='default', options={'effort': 'fixture-high'})
    catalog = dict(schema='cstack.t3-snapshot/2', host='t3', coordinator=scope,
                   sources={name: dict(sha256=digest * 64, itemId=name, observedAt='2026-01-01T00:00:00Z', toolName=tool)
                            for name, digest, tool in [('capabilities', 'a', 't3-code.orchestrator_capabilities'),
                                                     ('thread', 'b', 't3-code.t3_thread_read')]},
                   providers={'fixture-provider': {'canRunChildTask': True, 'canRunCrossProviderChildTask': True,
                       'constraints': [], 'modelsComplete': False,
                       'models': {'fixture-model': {'options': {'effort': {'type': 'string',
                            'values': ['fixture-high']}}}}}})
    seal(catalog)
    context = dict(schema='cstack.t3-context/2', expectedCoordinator=copy.deepcopy(scope),
                   capabilitiesSha256='a' * 64, threadSha256='b' * 64, snapshotSha256=catalog['sha256'],
                   revalidated=True, revalidatedAt='2026-01-01T00:00:00Z', expiresAt='2099-01-01T00:00:00Z')
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
        malformed = {'documentation': 'inherit-parent', 'how explorer': {'model': 3}}
        with self.assertRaises(ValueError):
            models.resolve(malformed, 'documentation', CATALOG)
        with self.assertRaises(ValueError):
            models.preflight({'documentation': 'inherit-parent', 'how explorer': {**self.selected, 'reasoning_effort': 'high'}}, ['documentation'], CATALOG)
        models.validate({'how explorer': self.selected})
        self.assertNotIn('t3', models.RUNTIMES)

    def test_public_setup_disable_preserves_saved_t3_agent(self):
        project = models.project_helper()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.cstack').mkdir()
            (root / '.cstack/models.json').write_text(json.dumps({'how explorer': self.selected}))
            agent = root / '.codex/agents/cstack-explorer.toml'
            agent.parent.mkdir(parents=True)
            agent.write_text('# cstack:managed\nmodel="old"\n')
            plan = project.preview_plan(root, {'native_agents': False}, None)
            self.assertFalse(any(row['path'] == '.codex/agents/cstack-explorer.toml'
                                 for row in plan['files']))
            self.assertEqual(plan['preserved_agents'], {'.codex/agents/cstack-explorer.toml': 't3-role'})
            tampered = copy.deepcopy(plan)
            tampered['preserved_agents']['.codex/agents/cstack-worker.toml'] = 't3-role'
            tampered['plan_sha256'] = project._sha(project._canonical({k: v for k, v in tampered.items() if k != 'plan_sha256'}))
            with self.assertRaisesRegex(project.ProjectError, 'recalculés'):
                project.apply_plan(root, tampered, {'native_agents': False}, None)
            result = project.apply_plan(root, plan, {'native_agents': False}, None)
            self.assertIn(result['status'], ('applied', 'noop'))
            self.assertEqual(result['preserved_agents'], plan['preserved_agents'])
            self.assertEqual(agent.read_text(), '# cstack:managed\nmodel="old"\n')

    def test_disable_with_invalid_models_preserves_files_and_requires_repair(self):
        project = models.project_helper()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / '.cstack/models.json'
            config.parent.mkdir()
            config.write_text('{"how explorer":{"model":3}}')
            agent = root / '.codex/agents/cstack-explorer.toml'
            agent.parent.mkdir(parents=True)
            agent.write_text('# cstack:managed\nmodel="old"\n')
            before = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
            with self.assertRaisesRegex(project.ProjectError, 'models.json existant invalide'):
                project.preview_plan(root, {'native_agents': False}, None)
            self.assertEqual(before, {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()})

    def test_malformed_option_blocks_only_its_position(self):
        for malformed in ([], {}, None):
            with self.subTest(type=malformed):
                catalog = copy.deepcopy(self.catalog)
                models_in_catalog = catalog['providers']['fixture-provider']['models']
                models_in_catalog['valid-model'] = copy.deepcopy(models_in_catalog['fixture-model'])
                models_in_catalog['fixture-model']['options']['effort']['type'] = malformed
                seal(catalog)
                self.context["snapshotSha256"] = catalog["sha256"]
                config = {'interrogate reviewers': [self.selected, {**self.selected, 'model': 'valid-model'}]}
                report = models.preflight(config, list(config), catalog, 't3', self.context)
                self.assertEqual([row['status'] for row in report['positions']['interrogate reviewers']],
                                 ['blocked', 'ready'])

    def test_catalog_context_options_and_inheritance_fail_closed(self):
        mutations = [lambda c: c['coordinator'].update(threadId='foreign'),
                     lambda c: c['coordinator'].update(link='foreign'),
                     lambda c: c['providers']['fixture-provider'].update(enabled=False),
                     lambda c: c['providers']['fixture-provider'].update(canRunChildTask=False),
                     lambda c: c['providers']['fixture-provider']['models'].clear()]
        for mutate in mutations:
            self.catalog, self.context, self.selected = fixture()
            mutate(self.catalog)
            seal(self.catalog)
            self.context['snapshotSha256'] = self.catalog['sha256']
            self.assertEqual(self.report([self.selected])['status'], 'blocked')
        for change in [dict(revalidated=False), dict(expiresAt='2020-01-01T00:00:00Z'),
                       dict(revalidatedAt='2099-01-01T00:00:00Z'), dict(revalidatedAt=None),
                       dict(revalidatedAt='2025-01-01T00:00:00Z'), dict(threadSha256='f' * 64)]:
            self.catalog, self.context, self.selected = fixture()
            self.context.update(change)
            self.assertEqual(self.report([self.selected])['status'], 'blocked')
        self.assertEqual(self.report([self.selected], context=False)['status'], 'blocked')

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

    def test_t3_catalog_is_not_a_native_model_mapping(self):
        report = models.preflight({'documentation': 'providers'}, ['documentation'], self.catalog)
        self.assertEqual(report['status'], 'blocked')

    def test_host_context_file_is_bounded_before_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = root / 'context.json'
            context.write_text(json.dumps({'padding': 'x' * (1024 * 1024)}))
            result = subprocess.run([sys.executable, str(Path(models.__file__)), '--workspace', str(root),
                                     '--host', 't3', '--host-context', str(context), 'show'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn('maximum', result.stderr)

    def test_preview_lists_large_options_and_rejects_mixed_types(self):
        values = ['level-' + str(index) for index in range(256)]
        option = self.catalog['providers']['fixture-provider']['models']['fixture-model']['options']['effort']
        option['values'] = values
        seal(self.catalog)
        self.context["snapshotSha256"] = self.catalog["sha256"]
        report = models.preview({}, 'digest', self.catalog, host='t3', context=self.context)
        self.assertEqual(report['supported']['fixture-provider']['fixture-model']['effort']['values'], values)
        option['values'] = [values[0], True]
        seal(self.catalog)
        self.context["snapshotSha256"] = self.catalog["sha256"]
        report = models.preview({}, 'digest', self.catalog, host='t3', context=self.context)
        self.assertNotIn('fixture-provider', report['supported'])


class T3NormalizerTests(unittest.TestCase):
    def setUp(self):
        self.helper = models.t3_catalog_helper()
        self.base = Path(__file__).parent / 'fixtures/t3-normalizer'
        self.cap = (self.base / 'capabilities.json').read_bytes()
        self.thread = (self.base / 'thread.json').read_bytes()

    def normalize(self, cap=None, thread=None):
        return self.helper.normalize(self.cap if cap is None else json.dumps(cap).encode(),
                                     self.thread if thread is None else json.dumps(thread).encode())

    def test_golden_determinism_bytes_and_old_observations(self):
        expected = json.loads((self.base / 'snapshot.json').read_text())
        self.assertEqual(self.normalize(), expected)
        self.assertEqual(self.normalize(), self.normalize())
        self.assertEqual(expected['sources']['capabilities']['sha256'], hashlib.sha256(self.cap).hexdigest())
        self.assertEqual(expected['sources']['thread']['observedAt'], json.loads(self.thread)['observedAt'])
        self.assertFalse(expected['providers']['codex']['modelsComplete'])
        self.assertNotIn('enabled', expected['providers']['codex'])
        self.assertNotIn('secret', expected['providers']['codex']['models']['gpt-6.1-sol']['options']['reasoningEffort'])

    def test_capture_envelopes_identity_and_timestamps(self):
        for key in ('threadId', 'providerInstanceId', 'model', 'runtimeMode', 'interactionMode'):
            thread = json.loads(self.thread)
            thread['output']['thread'][key] = 'foreign'
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.normalize(thread=thread)
        for name in ('cap', 'thread'):
            data = json.loads(self.cap if name == 'cap' else self.thread)
            for field in ('observedAt', 'itemId', 'toolName'):
                modified = copy.deepcopy(data)
                modified.pop(field)
                with self.assertRaises(ValueError):
                    self.normalize(**{name: modified})
        with self.assertRaises(ValueError):
            self.normalize(thread=json.loads(self.thread)['output'])
        with self.assertRaises(ValueError):
            self.helper.normalize(b' ' * (1024 * 1024 + 1), self.thread)

    def test_duplicates_and_metadata(self):
        for kind in ('provider', 'model', 'option', 'inherited'):
            cap = json.loads(self.cap)
            provider = cap['output']['providers'][0]
            rows = {'provider': cap['output']['providers'], 'model': provider['models'],
                    'option': provider['models'][0]['options'], 'inherited': cap['output']['inheritedOptions']}[kind]
            rows.append(copy.deepcopy(rows[0]))
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'doublon'):
                self.normalize(cap=cap)
        cap = json.loads(self.cap)
        cap['output']['providers'][0]['canRunChildTask'] = 'true'
        with self.assertRaises(ValueError):
            self.normalize(cap=cap)
        with self.assertRaisesRegex(ValueError, 'doublon JSON'):
            self.helper.normalize(b'{"a":1,"a":2}', self.thread)

    def context(self, catalog):
        return dict(schema='cstack.t3-context/2', expectedCoordinator=copy.deepcopy(catalog['coordinator']),
                    snapshotSha256=catalog['sha256'], revalidated=True, revalidatedAt='2026-11-05T00:36:23.734Z',
                    expiresAt='2099-01-01T00:00:00Z',
                    **{name + 'Sha256': value['sha256'] for name, value in catalog['sources'].items()})

    def test_malformed_model_only_blocks_its_position(self):
        for values in (['high', True], [], [None], {'high': True}):
            cap = json.loads(self.cap)
            provider = cap['output']['providers'][0]
            provider['models'][1]['options'][0]['values'] = values
            catalog = self.normalize(cap=cap)
            chosen = dict(runtime='t3', providerInstanceId='codex', model=provider['models'][1]['id'], options={})
            report = models.preflight({'interrogate reviewers': [chosen, 'inherit-parent']},
                                     ['interrogate reviewers'], catalog, 't3', self.context(catalog))
            self.assertEqual([r['status'] for r in report['positions']['interrogate reviewers']], ['blocked', 'ready'])

    def test_malformed_option_container_blocks_only_affected_model(self):
        cap = json.loads(self.cap)
        cap['output']['providers'][0]['models'][1]['options'] = None
        catalog = self.normalize(cap=cap)
        self.assertIn('invalid', catalog['providers']['codex']['models']['gpt-6-astra'])
        self.assertEqual(models.t3_position({}, catalog, self.context(catalog))['dispatch'], 'delegate_task')

    def test_partial_inactive_cross_provider_and_binding(self):
        for omitted, complete in [(None, False), (0, True), (2, False)]:
            cap = json.loads(self.cap)
            provider = cap['output']['providers'][0]
            provider.pop('omittedModels', None)
            if omitted is not None:
                provider['omittedModels'] = omitted
            self.assertEqual(self.normalize(cap=cap)['providers']['codex']['modelsComplete'], complete)
        catalog = self.normalize()
        context = self.context(catalog)
        selected = dict(runtime='t3', providerInstanceId='claudeAgent', model='claude-opus-5-5', options={'effort': 'high'})
        result = models.t3_position(selected, catalog, context)
        self.assertEqual(result['binding']['target'], result['target'])
        self.assertEqual(result['binding']['coordinatorScope'], context['expectedCoordinator'])
        for name in ('codex', 'claudeAgent'):
            changed = copy.deepcopy(catalog)
            changed['providers'][name]['canRunCrossProviderChildTask'] = False
            seal(changed)
            with self.assertRaisesRegex(ValueError, 'cross-provider'):
                models.t3_position(selected, changed, self.context(changed))
        context['expectedCoordinator']['threadId'] = 'other'
        with self.assertRaisesRegex(ValueError, 'étranger'):
            models.t3_position(selected, catalog, context)
        with self.assertRaisesRegex(ValueError, 'migration explicite T3 v2'):
            models.t3_position(selected, {'host': 't3', 'environmentId': 'old'}, {})

    def test_pure_normalizer_and_cli_ignores_invalid_models_file(self):
        from unittest.mock import patch
        with patch('builtins.open', side_effect=AssertionError('disk')), patch('subprocess.run', side_effect=AssertionError('process')):
            self.normalize()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.cstack').mkdir()
            (root / '.cstack/models.json').write_text('INVALID')
            before = sorted(str(p.relative_to(root)) for p in root.rglob('*'))
            result = subprocess.run([sys.executable, str(Path(models.__file__)), '--workspace', str(root), 'normalize',
                                     '--capabilities-trace', str(self.base / 'capabilities.json'),
                                     '--thread-trace', str(self.base / 'thread.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), self.normalize())
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob('*')))
