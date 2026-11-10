"""Pure T3 capture normalization and consistency checks. No discovery or attestation."""

from datetime import datetime, timezone
import hashlib
import json
import re

LIMIT = 1024 * 1024
DIRECT = 'cstack.t3-direct/1'
PROVIDER_LIMITS = ('enabled', 'canRunChildTask', 'canRunCrossProviderChildTask', 'constraints', 'runtimeModes')
SCOPE_KEYS = ('threadId', 'projectId', 'link', 'providerInstanceId', 'model', 'runtimeMode', 'interactionMode', 'options')


def fail(message):
    raise ValueError('BLOCKED: ' + message)


def timestamp(value):
    if not isinstance(value, str):
        fail('timestamp enveloppe/contexte absent')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError('timezone')
        return result
    except ValueError:
        fail('timestamp avec fuseau requis')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[\x21-\x7e]+', value) is not None


class DuplicateIdentity(ValueError):
    pass


def unique(rows, key):
    if not isinstance(rows, list):
        fail('liste attendue: ' + key)
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not identifier(row.get(key)):
            fail('identifiant invalide: ' + key)
        name = row[key]
        if name in result:
            raise DuplicateIdentity('BLOCKED: doublon: ' + key + '/' + name)
        result[name] = row
    return result


def options(rows):
    result = {}
    for name, row in unique(rows, 'id').items():
        values = row.get('values')
        if (not isinstance(values, list) or not values or type(values[0]) not in (str, bool)
                or any(type(v) is not type(values[0]) for v in values)
                or len({(type(v), v) for v in values}) != len(values)):
            fail('déclaration option mixed/malformed: ' + name)
        result[name] = {'type': 'string' if type(values[0]) is str else 'boolean', 'values': values}
        if row.get('default') is not None:
            if not any(type(row['default']) is type(v) and row['default'] == v for v in values):
                fail('default incohérent: ' + name)
            result[name]['default'] = row['default']
    return result


def parse(raw):
    if not isinstance(raw, bytes) or len(raw) > LIMIT:
        fail('capture trop grande: maximum 1 MiB')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail('doublon JSON: ' + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def envelope(raw, tool):
    data = parse(raw)
    if (not isinstance(data, dict) or data.get('toolName') != tool
            or not identifier(data.get('itemId')) or not isinstance(data.get('input'), dict)
            or not isinstance(data.get('output'), dict)):
        fail('enveloppe toolName/input/output/itemId requise: ' + tool)
    timestamp(data.get('observedAt'))
    return data, {'sha256': hashlib.sha256(raw).hexdigest(),
                  'itemId': data['itemId'], 'observedAt': data['observedAt'], 'toolName': tool}


def normalize(capabilities_raw, thread_raw):
    cap, cap_source = envelope(capabilities_raw, 't3-code.orchestrator_capabilities')
    thread, thread_source = envelope(thread_raw, 't3-code.t3_thread_read')
    caps = cap['output']
    identity = thread['output'].get('thread')
    if not isinstance(identity, dict):
        fail('output.thread requis')
    scope = {key: identity.get(key) for key in SCOPE_KEYS if key != 'options'}
    if not all(identifier(value) for value in scope.values()):
        fail('identité coordinator complète requise')
    if (thread['input'].get('threadId') != scope['threadId']
            or any(scope[key] != value for key, value in inherited_scope(caps).items())):
        fail('captures thread/provider/model/modes incohérentes')
    scope['options'] = inherited_options(caps)
    providers = catalog(caps)
    check_coordinator(scope, providers)
    body = {'schema': 'cstack.t3-snapshot/2', 'host': 't3', 'coordinator': scope,
            'sources': {'capabilities': cap_source, 'thread': thread_source}, 'providers': providers}
    return {**body, 'sha256': digest(body)}


def inherited_scope(caps):
    return {'threadId': caps.get('parentThreadId'), 'providerInstanceId': caps.get('inheritedProviderInstanceId'),
            'model': caps.get('inheritedModel'), 'runtimeMode': caps.get('runtimeMode'),
            'interactionMode': caps.get('interactionMode')}


def inherited_options(caps):
    result = {key: row.get('value') for key, row in unique(caps.get('inheritedOptions'), 'id').items()}
    if any(type(value) not in (str, bool) for value in result.values()):
        fail('inheritedOptions malformed')
    return result


def catalog(caps):
    providers = {}
    for name, provider in unique(caps.get('providers'), 'providerInstanceId').items():
        models = {}
        for model_id, model in unique(provider.get('models'), 'id').items():
            try:
                models[model_id] = {'options': options(model.get('options', []))}
            except DuplicateIdentity:
                raise
            except ValueError as error:
                models[model_id] = {'invalid': str(error)}
        normalized = {'models': models, 'modelsComplete': type(provider.get('omittedModels')) is int and provider['omittedModels'] == 0}
        for key in ('enabled', 'canRunChildTask', 'canRunCrossProviderChildTask'):
            if key in provider:
                if type(provider[key]) is not bool:
                    fail('metadata fournisseur incohérente: ' + key)
                normalized[key] = provider[key]
        constraints = provider.get('constraints')
        if not isinstance(constraints, list) or any(not isinstance(c, str) for c in constraints):
            fail('constraints fournisseur requises')
        normalized['constraints'] = constraints
        if 'omittedModels' in provider:
            if provider['omittedModels'] is not None and (type(provider['omittedModels']) is not int or provider['omittedModels'] < 0):
                fail('omittedModels incohérent')
            normalized['omittedModels'] = provider['omittedModels']
        if 'runtimeModes' in provider:
            if not isinstance(provider['runtimeModes'], list) or not all(identifier(v) for v in provider['runtimeModes']):
                fail('runtimeModes incohérents')
            normalized['runtimeModes'] = provider['runtimeModes']
        providers[name] = normalized
    return providers


def check_coordinator(scope, providers):
    coordinator_provider = providers.get(scope['providerInstanceId'])
    if not coordinator_provider:
        fail('fournisseur coordinator absent du catalogue')
    coordinator_model = coordinator_provider['models'].get(scope['model'])
    if coordinator_model is not None and 'options' in coordinator_model:
        for key, value in scope['options'].items():
            declaration = coordinator_model['options'].get(key)
            if declaration is None or not any(type(value) is type(v) and value == v for v in declaration['values']):
                fail('inheritedOptions incohérentes avec catalogue')


def capabilities(raw):
    """Lire la sortie de orchestrator_capabilities : brute, dans une enveloppe `output`, ou en texte dans un résultat MCP."""
    data = parse(raw)
    if isinstance(data, dict) and isinstance(data.get('output'), dict):
        data = data['output']
    elif isinstance(data, dict) and isinstance(data.get('content'), list):
        texts = [row.get('text') for row in data['content'] if isinstance(row, dict) and row.get('type') == 'text']
        if len(texts) != 1 or not isinstance(texts[0], str):
            fail('résultat MCP sans texte JSON unique')
        data = parse(texts[0].encode())
    if not isinstance(data, dict) or not isinstance(data.get('providers'), list):
        fail('sortie orchestrator_capabilities attendue')
    return data


def direct(raws):
    """Catalogue du chemin direct. Les captures suivantes, issues de `search`, ajoutent leurs modèles à la première."""
    scope, providers = None, {}
    for raw in raws:
        caps = capabilities(raw)
        current = inherited_scope(caps)
        if not all(identifier(value) for value in current.values()):
            fail('identité du fil absente de orchestrator_capabilities')
        current['options'] = inherited_options(caps)
        if scope not in (None, current):
            fail('captures de fils ou de réglages différents')
        scope = current
        for name, provider in catalog(caps).items():
            known = providers.get(name)
            if known is not None:
                if any(known.get(key) != provider.get(key) for key in PROVIDER_LIMITS):
                    fail('captures contradictoires pour le fournisseur ' + name)
                provider['models'] = {**known['models'], **provider['models']}
                provider['modelsComplete'] = known['modelsComplete'] and provider['modelsComplete']
                if known.get('omittedModels') != provider.get('omittedModels'):
                    provider.pop('omittedModels', None)
            providers[name] = provider
    if scope is None:
        fail('capture orchestrator_capabilities requise')
    check_coordinator(scope, providers)
    body = {'schema': DIRECT, 'host': 't3', 'coordinator': scope, 'providers': providers}
    return {**body, 'sha256': digest(body)}


def validate_context(catalog, context):
    if (not isinstance(catalog, dict) or catalog.get('schema') != 'cstack.t3-snapshot/2'
            or not isinstance(context, dict) or context.get('schema') != 'cstack.t3-context/2'):
        fail('migration explicite T3 v2 requise; recapturer les deux enveloppes, aucun fallback V1 environmentId/sessionId')
    if catalog.get('host') != 't3' or catalog.get('sha256') != digest({k: v for k, v in catalog.items() if k != 'sha256'}):
        fail('empreinte catalogue différente')
    scope = catalog.get('coordinator')
    if (not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS)
            or not all(identifier(scope[k]) for k in SCOPE_KEYS if k != 'options')
            or not isinstance(scope['options'], dict)
            or not all(identifier(k) and type(v) in (str, bool) for k, v in scope['options'].items())
            or digest(context.get('expectedCoordinator')) != digest(scope)):
        fail('expectedCoordinator absent ou étranger')
    if context.get('revalidated') is not True:
        fail('revalidation selon les règles T3 actives requise')
    if context.get('snapshotSha256') != catalog['sha256']:
        fail('empreinte snapshot contexte différente')
    sources = catalog.get('sources')
    if not isinstance(sources, dict) or set(sources) != {'capabilities', 'thread'}:
        fail('sources requises')
    revalidated = timestamp(context.get('revalidatedAt'))
    if not revalidated <= datetime.now(timezone.utc) < timestamp(context.get('expiresAt')):
        fail('contexte périmé/futur')
    for name, tool in (('capabilities', 't3-code.orchestrator_capabilities'), ('thread', 't3-code.t3_thread_read')):
        source = sources[name]
        if (not isinstance(source, dict) or source.get('toolName') != tool or not identifier(source.get('itemId'))
                or not isinstance(source.get('sha256'), str) or re.fullmatch('[a-f0-9]{64}', source['sha256']) is None
                or context.get(name + 'Sha256') != source['sha256']):
            fail('empreinte/source contexte différente: ' + name)
        if timestamp(source.get('observedAt')) > revalidated:
            fail('observation après revalidation')
    if not isinstance(catalog.get('providers'), dict):
        fail('fournisseurs non vérifiés')
    return catalog['providers']
