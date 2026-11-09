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

    def test_malformed_snapshot_runtime_modes_block_without_binding(self):
        for modes in ('full-access', {'full-access': True}, None, ['full-access', True]):
            with self.subTest(modes=modes):
                catalog, context, chosen = fixture()
                catalog['providers']['fixture-provider']['runtimeModes'] = modes
                seal(catalog)
                context['snapshotSha256'] = catalog['sha256']
                report = models.preflight({'judgment and prose': chosen}, ['judgment and prose'],
                                          catalog, 't3', context)
                row = report['positions']['judgment and prose'][0]
                self.assertEqual(row['status'], 'blocked')
                self.assertNotIn('binding', row)
                self.assertNotIn('judgment and prose', report['resolved'])

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
            for invalid_reason in ([], {}, None, False):
                malformed = copy.deepcopy(plan)
                malformed['preserved_agents']['.codex/agents/cstack-explorer.toml'] = invalid_reason
                malformed['plan_sha256'] = project._sha(project._canonical({k: v for k, v in malformed.items() if k != 'plan_sha256'}))
                with self.assertRaises(project.ProjectError):
                    project.apply_plan(root, malformed, {'native_agents': False}, None)
            result = project.apply_plan(root, plan, {'native_agents': False}, None)
            self.assertIn(result['status'], ('applied', 'noop'))
            self.assertEqual(result['preserved_agents'], plan['preserved_agents'])
            self.assertEqual(agent.read_text(), '# cstack:managed\nmodel="old"\n')

    def test_preview_reports_manual_agents_even_without_loading_saved_choices(self):
        project = models.project_helper()
        for mode, reason in [(None, 'manual-agent'), (False, 'manual-agent'), (True, 't3-role')]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / '.cstack').mkdir()
                (root / '.cstack/models.json').write_text(json.dumps({'how explorer': self.selected}))
                agent = root / '.codex/agents/cstack-explorer.toml'
                agent.parent.mkdir(parents=True)
                content = '# manual agent\nmodel="old"\n'
                agent.write_text(content)
                plan = project.preview_plan(root, {'native_agents': mode} if mode is not None else {}, None)
                self.assertEqual(plan['preserved_agents'], {'.codex/agents/cstack-explorer.toml': reason})
                result = project.apply_plan(root, plan, {'native_agents': mode} if mode is not None else {}, None)
                self.assertEqual(result['preserved_agents'], plan['preserved_agents'])
                self.assertEqual(agent.read_text(), content)

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

    def test_t3_preview_proposes_nothing_the_catalog_does_not_list(self):
        preview = models.preview({}, 'digest', self.catalog, host='t3', context=self.context)
        self.assertEqual(set(preview['recommendations']), set(models.T3_GROUPS))
        for group in preview['recommendations'].values():
            self.assertEqual(group['choices'], {})
            self.assertIn('absent du catalogue', group['unavailable'])
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

    def test_filtered_grok_discovery_blocks_only_unknown_inheritance(self):
        filtered = (self.base / 'capabilities-grok-filtered.json').read_bytes()
        catalog = self.helper.normalize(filtered, self.thread)
        context = self.context(catalog)
        context['revalidatedAt'] = json.loads(filtered)['observedAt']
        chosen = dict(runtime='t3', providerInstanceId='grok', model='grok-4.7',
                      options={'reasoningEffort': 'high'})
        report = models.preflight({'interrogate reviewers': ['inherit-parent', chosen]},
            ['interrogate reviewers'], catalog, 't3', context)
        rows = report['positions']['interrogate reviewers']
        self.assertEqual([r['status'] for r in rows], ['blocked', 'ready'])
        self.assertEqual(rows[1]['target'], {k: chosen[k] for k in ('providerInstanceId', 'model', 'options')})
        self.assertEqual(catalog['providers']['codex']['models'], {})
        self.assertFalse(catalog['providers']['codex']['modelsComplete'])
        single = models.preflight({'interrogate reviewers': [chosen]}, ['interrogate reviewers'],
            catalog, 't3', context)
        self.assertEqual(single['status'], 'ready')

    def test_coordinator_restrictions_block_cross_provider_without_model_list(self):
        for restriction in ({'enabled': False}, {'canRunChildTask': False},
                            {'constraints': ['blocked by host']},
                            {'runtimeModes': ['approval-required']}):
            with self.subTest(restriction=restriction):
                cap = json.loads((self.base / 'capabilities-grok-filtered.json').read_text())
                source = next(p for p in cap['output']['providers'] if p['providerInstanceId'] == 'codex')
                source.update(restriction)
                catalog = self.normalize(cap=cap)
                self.assertEqual(catalog['providers']['codex']['models'], {})
                context = self.context(catalog)
                context['revalidatedAt'] = cap['observedAt']
                chosen = dict(runtime='t3', providerInstanceId='grok', model='grok-4.7',
                              options={'reasoningEffort': 'high'})
                config = {'judgment and prose': chosen}
                report = models.preflight(config, ['judgment and prose'], catalog, 't3', context)
                row = report['positions']['judgment and prose'][0]
                self.assertEqual(row['status'], 'blocked')
                self.assertIn('codex', row['error'])
                self.assertNotIn('binding', row)
                self.assertNotIn('judgment and prose', report['resolved'])
                with self.assertRaisesRegex(ValueError, 'codex'):
                    models.resolve(config, 'judgment and prose', catalog, 't3', context)

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

    def test_nullable_host_default_is_unknown_and_not_an_invalid_option_value(self):
        cap = json.loads(self.cap)
        cap['output']['providers'][0]['models'][0]['options'][0]['default'] = None
        catalog = self.normalize(cap=cap)
        declaration = catalog['providers']['codex']['models']['gpt-6.1-sol']['options']['reasoningEffort']
        self.assertNotIn('default', declaration)
        self.assertEqual(models.t3_position({}, catalog, self.context(catalog))['dispatch'], 'delegate_task')

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
        cap = json.loads(self.cap)
        cap['output']['providers'][0]['omittedModels'] = None
        partial = self.normalize(cap=cap)['providers']['codex']
        self.assertIsNone(partial['omittedModels'])
        self.assertFalse(partial['modelsComplete'])
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


class T3DirectTests(unittest.TestCase):
    """Chemin direct : la sortie brute d'orchestrator_capabilities suffit, sans trace du fil ni contexte."""

    def setUp(self):
        base = Path(__file__).parent / 'fixtures/t3-normalizer'
        self.caps = json.loads((base / 'capabilities.json').read_text())['output']
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.script = Path(__file__).parents[1] / 'plugins/cstack/skills/setup-cstack/scripts/models.py'

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, caps=None, raw=None):
        path = self.root / 'capabilities.json'
        path.write_text(raw if raw is not None else json.dumps(self.caps if caps is None else caps))
        result = subprocess.run([sys.executable, str(self.script), '--host', 't3', '--capabilities', str(path),
                                 '--workspace', str(self.root), *args], capture_output=True, text=True, check=False)
        return result.returncode, (json.loads(result.stdout) if result.stdout.strip() else None), result.stderr

    def apply(self, choices, **kwargs):
        _, shown, _ = self.run_cli('show', **kwargs)
        path = self.root / 'choices.json'
        path.write_text(json.dumps(choices))
        return self.run_cli('apply', '--choices', str(path), '--expected-sha256', shown['sha256'], **kwargs)

    def test_show_proposes_a_sheet_checked_against_the_live_catalog(self):
        code, shown, error = self.run_cli('show')
        self.assertEqual(code, 0, error)
        groups = shown['recommendations']
        self.assertEqual(set(groups), {'everyday work', 'judgment', 'hard decisions', 'mixed panels'})
        self.assertTrue(all(group['unavailable'] is None for group in groups.values()), groups)
        self.assertEqual(groups['everyday work']['choices']['bug-fix'],
                         {'runtime': 't3', 'providerInstanceId': 'codex', 'model': 'gpt-6.1-sol',
                          'options': {'reasoningEffort': 'medium'}})
        self.assertEqual(groups['judgment']['choices']['judgment and prose'],
                         {'runtime': 't3', 'providerInstanceId': 'claudeAgent', 'model': 'claude-opus-5-5',
                          'options': {'effort': 'medium'}})
        reviewers = groups['mixed panels']['choices']['interrogate reviewers']
        self.assertEqual([(row['providerInstanceId'], row['model']) for row in reviewers],
                         [('codex', 'gpt-6.1-sol'), ('claudeAgent', 'claude-opus-5-5'), ('codex', 'gpt-6-astra')])
        self.assertEqual(shown['inheritance']['model'], 'gpt-6.1-sol')

    def test_accepted_sheet_resolves_to_delegate_targets_in_one_step(self):
        _, shown, _ = self.run_cli('show')
        choices = {}
        for group in shown['recommendations'].values():
            choices.update(group['choices'])
        code, applied, error = self.apply(choices)
        self.assertEqual(code, 0, error)
        self.assertEqual(applied['saved']['hardest tasks']['model'], 'gpt-6-astra')
        code, report, error = self.run_cli('preflight', 'interrogate reviewers', 'judgment and prose', 'simple edits')
        self.assertEqual((code, report['status']), (0, 'ready'), error)
        targets = [row['target'] for row in report['resolved']['interrogate reviewers']]
        self.assertEqual([row['dispatch'] for row in report['resolved']['interrogate reviewers']], ['delegate_task'] * 3)
        self.assertEqual(targets[1], {'providerInstanceId': 'claudeAgent', 'model': 'claude-opus-5-5',
                                      'options': {'effort': 'high'}})

    def test_raw_output_tool_result_and_envelope_are_all_accepted(self):
        wrapped = json.dumps({'content': [{'type': 'text', 'text': json.dumps(self.caps)}]})
        envelope = json.dumps({'toolName': 't3-code.orchestrator_capabilities', 'input': {}, 'output': self.caps})
        for raw in (json.dumps(self.caps), wrapped, envelope):
            code, shown, error = self.run_cli('show', raw=raw)
            self.assertEqual(code, 0, error)
            self.assertIn('gpt-6.1-sol', shown['supported']['codex'])

    def test_unavailable_provider_blocks_without_substitution(self):
        caps = copy.deepcopy(self.caps)
        claude = next(row for row in caps['providers'] if row['providerInstanceId'] == 'claudeAgent')
        selection = {'runtime': 't3', 'providerInstanceId': 'claudeAgent', 'model': 'claude-opus-5-5',
                     'options': {'effort': 'high'}}
        self.assertEqual(self.apply({'judgment and prose': selection})[0], 0)
        claude['canRunChildTask'] = False
        claude['constraints'] = ['Provider instance is disabled.']
        _, shown, _ = self.run_cli('show', caps=caps)
        self.assertIsNotNone(shown['recommendations']['judgment']['unavailable'])
        self.assertIsNone(shown['recommendations']['everyday work']['unavailable'])
        code, report, _ = self.run_cli('preflight', 'judgment and prose', 'bug-fix', caps=caps)
        self.assertEqual((code, report['status']), (2, 'blocked'))
        self.assertIn('judgment and prose', report['errors'])
        self.assertNotIn('bug-fix', report['errors'])

    def test_a_model_missing_from_the_short_list_is_unavailable_not_replaced(self):
        caps = copy.deepcopy(self.caps)
        codex = next(row for row in caps['providers'] if row['providerInstanceId'] == 'codex')
        codex['models'] = [row for row in codex['models'] if row['id'] != 'gpt-6-astra']
        _, shown, _ = self.run_cli('show', caps=caps)
        self.assertIn('gpt-6-astra', shown['recommendations']['hard decisions']['unavailable'])
        self.assertIsNone(shown['recommendations']['everyday work']['unavailable'])

    def test_a_new_model_replaces_a_tier_with_one_option(self):
        code, shown, error = self.run_cli('show', '--tier', 'work=gpt-6.1-terra@high', '--tier', 'judgment=claudeAgent/claude-sonnet-5-5')
        self.assertEqual(code, 0, error)
        groups = shown['recommendations']
        self.assertEqual(groups['everyday work']['choices']['feature, refactoring'],
                         {'runtime': 't3', 'providerInstanceId': 'codex', 'model': 'gpt-6.1-terra',
                          'options': {'reasoningEffort': 'high'}})
        self.assertEqual(groups['judgment']['choices']['judgment and prose']['model'], 'claude-sonnet-5-5')
        self.assertEqual(groups['mixed panels']['choices']['arena runners'][0]['model'], 'gpt-6.1-terra')
        _, shown, _ = self.run_cli('show', '--tier', 'work=modele-inconnu')
        self.assertIn('modele-inconnu', shown['recommendations']['everyday work']['unavailable'])
        code, _, error = self.run_cli('show', '--tier', 'vitesse=gpt-6.1-sol')
        self.assertEqual(code, 2)
        self.assertIn('vitesse', error)

    def test_a_search_capture_adds_a_model_outside_the_short_list(self):
        found = copy.deepcopy(self.caps)
        for provider in found['providers']:
            provider.pop('omittedModels', None)
            provider['models'] = []
        claude = next(row for row in found['providers'] if row['providerInstanceId'] == 'claudeAgent')
        claude['models'] = [{'id': 'claude-next-1', 'options': [{'id': 'effort', 'values': ['low', 'high']}]}]
        first, second = self.root / 'capabilities.json', self.root / 'search.json'
        first.write_text(json.dumps(self.caps))

        def show(*captures):
            command = [sys.executable, str(self.script), '--host', 't3', '--workspace', str(self.root)]
            for capture in captures:
                command += ['--capabilities', str(capture)]
            result = subprocess.run(command + ['show', '--tier', 'judgment=claude-next-1@high'],
                                    capture_output=True, text=True, check=False)
            return result.returncode, (json.loads(result.stdout) if result.stdout.strip() else None), result.stderr

        second.write_text(json.dumps(found))
        _, alone, _ = show(first)
        self.assertIn('claude-next-1', alone['recommendations']['judgment']['unavailable'])
        code, merged, error = show(first, second)
        self.assertEqual(code, 0, error)
        self.assertEqual(merged['recommendations']['judgment']['choices']['judgment and prose'],
                         {'runtime': 't3', 'providerInstanceId': 'claudeAgent', 'model': 'claude-next-1',
                          'options': {'effort': 'high'}})
        self.assertEqual(merged['recommendations']['everyday work']['choices']['bug-fix']['model'], 'gpt-6.1-sol')
        found['parentThreadId'] = 'another-thread'
        second.write_text(json.dumps(found))
        code, _, error = show(first, second)
        self.assertEqual(code, 2)
        self.assertIn('fils', error)

    def test_an_effort_no_option_offers_is_refused_when_asked_and_left_out_when_defaulted(self):
        _, shown, _ = self.run_cli('show', '--tier', 'work=gpt-6.1-sol@turbo')
        self.assertIn('turbo', shown['recommendations']['everyday work']['unavailable'])
        _, shown, _ = self.run_cli('show', '--tier', 'work=opencode/big-pickle')
        self.assertEqual(shown['recommendations']['everyday work']['choices']['bug-fix'],
                         {'runtime': 't3', 'providerInstanceId': 'opencode', 'model': 'opencode/big-pickle', 'options': {}})
        self.assertEqual(shown['tiers'], {'work': 'opencode/big-pickle', 'judgment': 'claude-opus-5-5', 'hard': 'gpt-6-astra'})

    def test_the_setup_reference_and_the_guide_name_the_proposed_models(self):
        plugin = Path(__file__).parents[1] / 'plugins/cstack'
        for page in ('skills/setup-cstack/references/models.md', 'docs/guide/12-t3-code.md'):
            text = (plugin / page).read_text()
            for tier, model in models.T3_TIERS.items():
                self.assertIn(f'| `{tier}` | `{model}` |', text, page)

    def test_direct_and_audited_inputs_do_not_mix(self):
        path = self.root / 'capabilities.json'
        path.write_text(json.dumps(self.caps))
        for extra in (['--catalog', str(path)], ['--host-context', str(path)]):
            result = subprocess.run([sys.executable, str(self.script), '--host', 't3', '--capabilities', str(path),
                                     *extra, '--workspace', str(self.root), 'show'], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2, result.stdout)
        result = subprocess.run([sys.executable, str(self.script), '--capabilities', str(path),
                                 '--workspace', str(self.root), 'show'], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2, result.stdout)
