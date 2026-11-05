# Préparer, prévisualiser et appliquer

Après invocation dans T3, le [contrat T3](../../cstack/references/runtime/t3.md) prime pour catalogue, choix explicites et synchronisation. Le chemin T3 modèle seul utilise `models.py --host t3 --catalog ... --host-context ...`, sans conversion automatique ni CLI de repli.


Référence de [setup-cstack](../SKILL.md) : suivi des étapes, flux de préparation, bloc `AGENTS.md`, agents natifs, tracker, `project.py` et configuration modèle seule.

## Suivi des étapes

Avant la première inspection, affiche une todo courte des étapes du setup demandé : découverte, choix, prévisualisation, application et vérification. Adapte-la au périmètre : une configuration modèle seule garde découverte, `show` et choix, puis `apply` et vérification par `resolve` ; une preview, une lecture seule ou le mode Plan excluent l’application et sa vérification.

Applique le [suivi visible commun](../../cstack/references/runtime/suivi.md) : cases cochées au fil des résultats vérifiés, attentes et blocages explicites. Pour un résultat `partial`, garde application et vérification incomplètes jusqu'au succès relu. À l'étape des modèles, la todo indique seulement l'avancement ; les propositions précèdent toujours la configuration actuelle. Le suivi n'ajoute aucune approbation ni écriture.

## Expliquer les flux de préparation

Explique chaque flux de travail de préparation avec les données `workflows` du preview de projet et le [contrat de flux de travail](../../cstack/references/codex-runtime.md) : `clarify` et `domain` n'ont aucun délégué par défaut; une exploration déléguée suit le [contrat d’exploration déléguée](../../cstack/references/runtime/exploration.md), recherches Horizon comprises. Nomme le rôle existant et son modèle/effort effectif pour chaque phase. L'implémentation ordinaire et les tailles de panels existantes restent inchangées. Ce sont des règles de dispatch, pas de nouveaux rôles de modèle.

## Bloc AGENTS.md et agents natifs

Pour la préparation de projet, propose un bloc cstack passif dans `AGENTS.md` et `docs/agents/cstack.md`, en préservant les octets environnants. Le bloc charge le guide et, s'il existe, `CLAUDE.md` comme instructions seulement pendant une tâche où l'utilisateur invoque explicitement `$cstack:*`. Il garde aussi la conversation en mode cstack après une invocation explicite de `$cstack:cstack`, jusqu'à une demande d'arrêt, et demande de déléguer le travail indépendant. Pendant une tâche ordinaire, il n'interdit pas de lire un fichier que l'utilisateur nomme. Le `CLAUDE.md` existant reste intact. Le contenu guide non géré existant ou les blocs marqueurs mal formés sont des conflits à expliquer et préserver, pas une permission de remplacer le fichier. Ne crée pas de `CONTEXT.md` vide ni de répertoires ADR.

Propose par défaut les agents natifs du projet (`native_agents: true`) : `.codex/agents/cstack-explorer.toml`, `cstack-worker.toml` et `cstack-reviewer.toml`, avec les modèles/efforts natifs choisis pour `how explorer`, `feature, refactoring` et `judgment and prose` ; un rôle hérité laisse l'agent sans modèle, et un rôle confié à un CLI n'a pas d'agent (l'agent géré existant est supprimé). Sans `native_agents`, setup régénère seulement les agents gérés existants ; `native_agents: false` les supprime. Ces fichiers portent le marqueur `# cstack:managed` ; un agent de même nom sans ce marqueur est un conflit à expliquer, jamais remplacé.

## Tracker

Réutilise un document de tracker existant sauf si l'utilisateur a demandé un changement. Quand Horizon a besoin d'un choix, propose Markdown local ou le dépôt GitHub pertinent découvert depuis ce projet. Consigne une cible GitHub seulement après sa sélection; ne crée pas d'étiquettes, tickets, dépendances ou état distant pendant la configuration. Aucun choix de tracker n'est nécessaire pour une configuration modèle seule ou des workflows sans rapport.

## Prévisualiser et appliquer avec `project.py`

Utilise directement le helper Python bundle de confiance, jamais une copie exécutable locale au projet. Place seulement les réglages acceptés dans un fichier JSON d'options hors du projet pendant la prévisualisation. Omets `model_choices` pour préserver tous les octets de modèles sauvegardés. Omets `tracker` ou utilise `keep` pour préserver un document de tracker existant et laisser absent un document absent.

```json
{
  "model_choices": {
    "how explorer": {"model": "gpt-5.6-luna", "reasoning_effort": "max"}
  },
  "tracker": {"mode": "local"},
  "native_agents": true
}
```

Pour GitHub, utilise `{"mode":"github","owner":"selected-owner","repo":"selected-repo"}`. Les valeurs de modèle doivent être des sélections vérifiées, pas des défauts inconditionnels. Pour des consignes de projet sans changement de modèle ou tracker, utilise `{}`.

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/project.py --workspace <workspace> --catalog <live-catalog.json> preview --options <selected-options.json>
python3 <absolute-plugin>/skills/setup-cstack/scripts/project.py --workspace <workspace> --catalog <live-catalog.json> apply --plan <accepted-preview.json> --options <selected-options.json> --expected-plan-sha256 <approved-plan-sha256>
```

Garde le JSON de prévisualisation complet dans un fichier temporaire local autorisé. Montre son `plan_sha256`, les chemins de fichiers, actions, diffs et règles de flux de travail avant application; ne déverse pas dans la conversation les snapshots originaux en base64. Sauvegarde localement la prévisualisation exacte acceptée, conserve son `plan_sha256` depuis la sortie relue, puis passe cette valeur avec les mêmes options à apply. Ne reconstruis pas et ne modifie pas le plan à la main, et ne recalcule pas une empreinte d'approbation depuis un fichier changé après revue. Quand l'utilisateur a déjà approuvé ces changements exacts, procède sans autre relais de permission. Une prévisualisation périmée, altérée, conflictuelle ou invalide est rejetée. Rapporte ce résultat et crée une nouvelle prévisualisation relisible au lieu d'écraser le fichier modifié.

## Écriture partielle

Le helper valide et stage toutes les éditions, puis remplace les fichiers individuellement. Les erreurs d'écriture ordinaires tentent un rollback sans écraser les éditions manuelles intervenues. Une interruption de processus peut laisser une configuration partielle; la même prévisualisation acceptée peut reprendre quand chaque cible correspond encore à ses octets originaux ou prévus. Rapporte `partial` honnêtement, conserve la prévisualisation, inspecte l'état et reprends l'opération acceptée. Ce n'est pas une transaction filesystem globalement atomique. Ne rapporte jamais un succès depuis une sortie échouée ou partielle.

## Relire et vérifier

Après succès, lis les vrais fichiers générés et les choix de modèle effectifs. Vérifie que le bloc cstack est unique, que les consignes existantes et les octets CLAUDE ont survécu, que l'état local est ignoré quand il est créé, et qu'aucun modèle non sélectionné n'a changé. Rapporte les chemins, comptes et réglages effectifs, pas des affirmations disant qu'un modèle a été exécuté. Les choix de `.cstack/models.json` s'appliquent sans redémarrage aux rôles résolus après leur écriture; un délégué déjà lancé garde sa sélection. Si `AGENTS.md` a changé, dis explicitement que la conversation actuelle garde l'ancien bloc et demande d'ouvrir une nouvelle conversation App ou une nouvelle session CLI pour charger le nouveau. Setup ne lance pas de sondes payantes de modèle. Il n'écrit d'agents que les trois agents projet acceptés dans `.codex/agents/`, jamais dans `~/.codex`.

## Configuration modèle seule

Le helper existant reste disponible sans préparer les documents de projet :

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> show
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> preflight 'how explorer' 'judgment and prose'
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> apply --choices <selected-role-map.json> --expected-sha256 <show.sha256>
```

Sa sortie `show` fournit les choix exacts groupe-vers-rôle, les tailles de panel et `managed_agents`, les agents natifs gérés que `apply` alignera sur les nouveaux choix ; présente-les dans l'aperçu. La sortie d'`apply` donne `saved` et `agents` (`updated`, `removed`). Construis la carte de rôles sélectionnés seulement depuis les choix acceptés. Garde `.cstack/` non suivi sans remplacer les règles ignore existantes, puis relis et valide le résultat. Le modèle de la session parente reste inchange.


## Désactivation des agents natifs et rôles T3

`native_agents: false` retire les agents gérés pour les rôles Codex connus. Un agent correspondant à un rôle T3 sauvegardé reste intact ; `preserved_agents` dans le plan associe son chemin à `t3-role`. Ce signal ne le désactive pas dans Codex. Le préflight bloque le rôle T3 hors T3, même si cet agent périmé est encore visible. Les agents manuels ne sont jamais supprimés par ce réglage.

Si des agents gérés existent et que `models.json` est invalide, la désactivation est bloquée avant toute écriture. Le helper ne peut pas déterminer quels rôles doivent être préservés. Réparer le fichier puis produire un nouveau plan. La configuration et les agents existants restent intacts pendant ce blocage.
