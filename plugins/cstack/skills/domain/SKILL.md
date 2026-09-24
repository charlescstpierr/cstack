---
name: domain
description: "Utiliser quand $cstack:domain est sélectionne explicitement ou route pendant une tâche cstack explicite afin de trancher le vocabulaire du projet et consigner les entrées de glossaire ou ADR epars autorisés."
---

# Domaine

Contrat d’exécution : [`../cstack/references/codex-runtime.md`](../cstack/references/codex-runtime.md).

Utilise cette skill quand l'utilisateur sélectionne explicitement `$cstack:domain`, ou quand le coordinateur `$cstack:cstack` actif ou ses skills de préparation routent ici une décision terminologique matérielle. Elle sert au travail de domaine actif : résoudre le vocabulaire, vérifier les frontières de modèle et consigner un petit nombre de décisions durables. Lire simplement un glossaire n'est pas cette skill.

Lis `docs/agents/cstack.md` si le projet l'a; il peut définir des conventions locales, mais son absence est acceptable. N'exige pas setup, les skills Matt Pocock, des skills globales ou un autre plugin.

## Localiser les artefacts

Inspecte le dépôt avant de choisir chemins ou formats.

- Si la racine contient `CONTEXT-MAP.md`, utilise le contexte qu'il mappe pour le sujet.
- Sinon, utilise le `CONTEXT.md` racine quand il existe.
- Si aucun des deux n'existe, propose un `CONTEXT.md` racine seulement quand un terme est vraiment résolu et qu'une écriture documentaire est autorisée. Ne l'echafaude jamais spéculativement.
- Inspecte les emplacements ADR existants, la numérotation, le frontmatter et les templates. Suis ces conventions. S'il n'en existe aucun, un ADR epars peut utiliser `docs/adr/NNNN-slug.md` avec une à trois phrases.

## Affuter le langage

Pour chaque terme dispute ou surcharge :

1. Trouve ses usages réels dans le code et les documents de domaine existants, en réutilisant [`$cstack:how`](../how/SKILL.md) quand le flux ou la responsabilité est large. Utilise le code observé comme preuve, pas comme substitut à la décision produit de l'utilisateur.
2. Signale les définitions ou synonymes conflictuels et propose un terme canonique précis.
3. Teste la frontière avec un scénario concret. Demande à l'utilisateur de choisir quand le sens affecte les règles métier, la responsabilité où le comportement visible de l'extérieur. N'infère jamais une décision métier matérielle.
4. Redige une entrée de glossaire qui définit ce que la chose **est**, en une ou deux phrases, et liste les synonymes rejetés sous `_Avoid_`. Garde les détails d'implémentation, specs et notes scratch hors de `CONTEXT.md`.

Écris une entrée résolue en place quand la tâche courante autorise déjà les écritures documentaires. Sinon, retourne l'entrée proposée dans le chat. Ne redemande pas d'approbation pour chaque entrée une fois l'autorité d'écriture établie. En mode Plan ou travail en lecture seule, retourne toujours les brouillons et n'écris pas de fichiers.

## Consigner les décisions avec parcimonie

Propose un ADR seulement quand les trois conditions tiennent :

1. Le choix est difficile à inverser.
2. Un futur lecteur le trouverait surprenant sans contexte.
3. Il resulte d'un vrai compromis entre alternatives.

Garde l'ADR au format existant du dépôt et consigne contexte, décision et raison. Si un choix métier matériel reste ouvert, demandé à l'utilisateur et ne consigne pas de décision. Quand le choix est tranche et que les écritures documentaires sont autorisées, consigne-le sans autre boucle d'approbation par ADR. Ne transforme pas des choix d'implémentation ordinaires en ADR.

## Faits, rédaction et jugement

Le défaut est zéro agent supplémentaire. Quand des faits de dépôt indépendants exigent une couverture séparée, applique le [contrat d’exploration déléguée](../cstack/references/codex-runtime.md#exploration-déléguée) et utilise le rôle configuré `how explorer`. Établis les faits directement dans le parent quand la délégation n'ajoute pas de couverture. Quand un brouillon de document séparé est utile et que l'écriture est autorisée, utilise le rôle configuré `documentation`. Quand une passe indépendante de raisonnement ou de jugement est utile, utilise `judgment and prose`; cette synthèse ne compte pas comme exploration. Résous chaque rôle via le helper de confiance et transmets la sélection complète de modèle et d'effort de raisonnement; ne hard-code pas des noms de modèle et n'ajoute pas de rôle.

Le parent possède le jugement final et la vérification. Cette skill ne crée jamais d'objectifs, de changements d'implémentation, de trackers, de PR, de déploiements ou de messages externes. Ses seules écritures durables sont des documents de glossaire ou ADR explicitement autorisés.

Pour clarifier les exigences avant consignation de domaine, utilise [`$cstack:clarify`](../clarify/SKILL.md).
