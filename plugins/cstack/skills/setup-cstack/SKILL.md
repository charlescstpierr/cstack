---
name: setup-cstack
description: "Guider la configuration de projet cstack : préserver les consignes de projet, configurer ou mettre à jour les runtimes et choix facultatifs de modèle/effort et expliquer les workflows de préparation. Utiliser pour $cstack:setup-cstack ou les changements de configuration cstack."
---

# Configurer cstack

Lis le [contrat d’exécution natif Codex](../cstack/references/codex-runtime.md). L'usage de base de cstack n'exige aucune configuration. La configuration prépare seulement le projet courant; elle n'active jamais un flux de travail et ne change jamais la configuration globale.

## Suivre la progression en direct

Avant la première inspection, affiche une todo courte des étapes du setup demandé : découverte, choix, prévisualisation, application et vérification. Adapte-la au périmètre : une configuration modèle seule garde découverte, `show` et choix, puis `apply` et vérification par `resolve` ; une preview, une lecture seule ou le mode Plan excluent l’application et sa vérification.

Applique le [suivi visible commun](../cstack/references/codex-runtime.md#suivi-visible-du-workflow-et-des-délégués) : cases cochées au fil des résultats vérifiés, attentes et blocages explicites. Pour un résultat `partial`, garde application et vérification incomplètes jusqu'au succès relu. À l'étape des modèles, la todo indique seulement l'avancement ; les propositions précèdent toujours la configuration actuelle. Le suivi n'ajoute aucune approbation ni écriture.

## Decouvrir et présenter

1. Localise le workspace cible, normalement sa racine Git où le répertoire courant hors Git. Lis les `AGENTS.md`, `CLAUDE.md`, `docs/agents/cstack.md`, `docs/agents/issue-tracker.md`, conventions de domaine et `.cstack/models.json` existants quand ils sont presents. Inspecte seulement les fichiers de projet pertinents; ne lis pas les identifiants secrets. Résous le chemin absolu de ce bundle installe.
2. Respecte la portée demandée. Une demande de changement de modèles utilise seulement les commandes modèle seules ci-dessous. La configuration générale propose aussi les consignes de projet et conventions de tracker. Une demande de preview, lecture seule, annulation ou mode Plan n'écrit rien dans le projet; garde les choix proposés dans la conversation ou dans un artefact temporaire autorisé.
3. Fais l’inventaire de la machine décrit ci-dessous avant de proposer des runtimes, y compris lors d’un setup sans précision. Découvre ensuite les modèles et efforts depuis le schéma d'outil natif courant ou le catalogue de session faisant autorité. Pour une CLI prise en charge, le JSON brut de `codex debug models` fonctionne; sinon, utilise une carte de slugs confirmés vers listes d'efforts depuis le schéma réel. Un cache périmé n'est pas une preuve de disponibilité. Sans découverte, l'héritage reste disponible. Vérifie si le dispatch natif peut exprimer les deux champs sélectionnés, avec des rôles génériques et des réglages de fork pris en charge.
4. Exécute la commande modèle `show`. Si la demande concerne Claude Code ou un autre CLI, suis la section « Ajouter ou mettre à jour Claude Code » avant les recommandations natives. Commence la présentation des modèles par un tableau « Propositions de modèles d’agents » qui montre chaque rôle, chaque position de panel, le modèle/effort recommandé vérifié et sa raison. Montre ensuite les autres modèles/efforts confirmés disponibles pour personnaliser ces choix. Seulement après ces propositions, affiche la configuration actuelle; pour un rôle absent, indique alors qu’il hérite actuellement du parent. Ne commence jamais la réponse par « les agents héritent du parent » quand le catalogue permet de proposer des modèles. Propose dans cet ordre : accepter toutes les recommandations disponibles, choisir des groupes, personnaliser par rôle ou position de panel, conserver la configuration actuelle, utiliser l’héritage pour les rôles sélectionnés, ou annuler. Préserve les rôles non sélectionnés. Si aucun modèle n’a pu être découvert, explique l’échec de découverte avant de proposer l’héritage. Applique les choix déjà explicitement demandés sans redemander; invoquer simplement setup n'accepte pas les recommandations.
5. Explique chaque flux de travail de préparation avec les données `workflows` du preview de projet et le [contrat de flux de travail](../cstack/references/codex-runtime.md) : `clarify` et `domain` n'ont aucun délégué par défaut; une exploration déléguée suit le [contrat d’exploration déléguée](../cstack/references/codex-runtime.md#exploration-déléguée); Horizon utilise au moins deux explorateurs par recherche, normalement trois, en vagues si nécessaire. Nomme le rôle existant et son modèle/effort effectif pour chaque phase. L'implémentation ordinaire et les tailles de panels existantes restent inchangées. Ce sont des règles de dispatch, pas de nouveaux rôles de modèle.
6. Pour la préparation de projet, propose un bloc cstack passif dans `AGENTS.md` et `docs/agents/cstack.md`, en préservant les octets environnants. Le bloc charge le guide et, s'il existe, `CLAUDE.md` comme instructions seulement pendant une tâche où l'utilisateur invoque explicitement `$cstack:*`. Pendant une tâche ordinaire, il n'interdit pas de lire un fichier que l'utilisateur nomme. Le `CLAUDE.md` existant reste intact. Le contenu guide non géré existant ou les blocs marqueurs mal formés sont des conflits à expliquer et préserver, pas une permission de remplacer le fichier. Ne crée pas de `CONTEXT.md` vide ni de répertoires ADR.
7. Réutilise un document de tracker existant sauf si l'utilisateur a demandé un changement. Quand Horizon a besoin d'un choix, propose Markdown local ou le dépôt GitHub pertinent découvert depuis ce projet. Consigne une cible GitHub seulement après sa sélection; ne crée pas d'étiquettes, tickets, dépendances ou état distant pendant la configuration. Aucun choix de tracker n'est nécessaire pour une configuration modèle seule ou des workflows sans rapport.

## Détecter les choix disponibles sur la machine

Compare les choix du projet à l'environnement du processus Codex courant. Utilise le helper installé de confiance pour sonder chacun des runtimes `codex-cli`, `claude-code`, `cursor-agent` et `grok` avec `runtime/runtime.ts probe <runtime>` via le lanceur. Ces sondes inspectent le PATH, la version et les options du CLI sans génération. Réutilise les sondes récentes de la tâche si l'environnement n'a pas changé. Une demande limitée à un seul runtime peut limiter l'inventaire à celui-ci.

Pour les binaires présents, vérifie la connexion uniquement par une commande de statut officielle reconnue par leur aide. Codex expose `codex login status` ; Claude expose `claude auth status --json`. Garde seulement l'état connecté/non connecté/inconnu et, si utile, le mode de connexion déclaré. Ne reproduis pas l'adresse courriel, les identifiants de compte ni la sortie brute. Pour un autre CLI ou une version sans statut reconnu, indique « connexion inconnue ». Borne les commandes de statut à 15 secondes et traite un timeout comme inconnu. Ne lance pas de login, de génération, de recherche dans les credentials, les sessions privées ou les variables secrètes.

Présente un tableau runtime, présence/version, connexion, capacité de permissions et rôles déjà configurés. Le chemin natif Codex reste un choix distinct hérité de la session. Un binaire présent sans headless ou permissions compatibles n'est pas prêt au dispatch. La connexion déclarée ne prouve ni quota, ni modèle disponible, ni comportement de bout en bout.

Propose les choix d'après cet inventaire : conserver les réglages existants, ajouter un CLI disponible aux panels choisis, remplacer des rôles choisis, ou configurer explicitement un CLI pour plus tard. Signale les sélections sauvegardées devenues indisponibles et préserve-les tant qu'aucun remplacement n'est demandé. Ne propose pas les recommandations OpenAI pour Claude. Si le CLI ne publie pas de catalogue exploitable sans génération, propose son modèle par défaut et indique que ses modèles/efforts explicites restent non vérifiés. Ne présente pas Grok ou Cursor comme testés en connexion sur la seule foi d'une sonde.

## Previsualiser et appliquer la configuration de projet

Utilise directement le helper Python bundle de confiance, jamais une copie exécutable locale au projet. Place seulement les réglages acceptés dans un fichier JSON d'options hors du projet pendant la prévisualisation. Omets `model_choices` pour préserver tous les octets de modèles sauvegardés. Omets `tracker` ou utilise `keep` pour préserver un document de tracker existant et laisser absent un document absent.

```json
{
  "model_choices": {
    "how explorer": {"model": "gpt-5.6-luna", "reasoning_effort": "max"}
  },
  "tracker": {"mode": "local"}
}
```

Pour GitHub, utilise `{"mode":"github","owner":"selected-owner","repo":"selected-repo"}`. Les valeurs de modèle doivent être des sélections vérifiées, pas des défauts inconditionnels. Pour des consignes de projet sans changement de modèle ou tracker, utilise `{}`.

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/project.py --workspace <workspace> --catalog <live-catalog.json> preview --options <selected-options.json>
python3 <absolute-plugin>/skills/setup-cstack/scripts/project.py --workspace <workspace> --catalog <live-catalog.json> apply --plan <accepted-preview.json> --options <selected-options.json> --expected-plan-sha256 <approved-plan-sha256>
```

Garde le JSON de prévisualisation complet dans un fichier temporaire local autorisé. Montre son `plan_sha256`, les chemins de fichiers, actions, diffs et règles de flux de travail avant application; ne déverse pas dans la conversation les snapshots originaux en base64. Sauvegarde localement la prévisualisation exacte acceptée, conserve son `plan_sha256` depuis la sortie relue, puis passe cette valeur avec les mêmes options à apply. Ne reconstruis pas et ne modifie pas le plan à la main, et ne recalcule pas une empreinte d'approbation depuis un fichier changé après revue. Quand l'utilisateur a déjà approuvé ces changements exacts, procède sans autre relais de permission. Une prévisualisation périmée, altérée, conflictuelle ou invalide est rejetée. Rapporte ce résultat et crée une nouvelle prévisualisation relisible au lieu d'écraser le fichier modifié.

Le helper valide et stage toutes les éditions, puis remplace les fichiers individuellement. Les erreurs d'écriture ordinaires tentent un rollback sans écraser les éditions manuelles intervenues. Une interruption de processus peut laisser une configuration partielle; la même prévisualisation acceptée peut reprendre quand chaque cible correspond encore à ses octets originaux ou prévus. Rapporte `partial` honnêtement, conserve la prévisualisation, inspecte l'état et reprends l'opération acceptée. Ce n'est pas une transaction filesystem globalement atomique. Ne rapporte jamais un succès depuis une sortie échouée ou partielle.

Après succès, lis les vrais fichiers générés et les choix de modèle effectifs. Vérifie que le bloc cstack est unique, que les consignes existantes et les octets CLAUDE ont survécu, que l'état local est ignoré quand il est créé, et qu'aucun modèle non sélectionné n'a changé. Rapporte les chemins, comptes et réglages effectifs, pas des affirmations disant qu'un modèle a été exécuté. Les choix de `.cstack/models.json` s'appliquent sans redémarrage aux rôles résolus après leur écriture; un délégué déjà lancé garde sa sélection. Si `AGENTS.md` a changé, dis explicitement que la conversation actuelle garde l'ancien bloc et demande d'ouvrir une nouvelle conversation App ou une nouvelle session CLI pour charger le nouveau. Setup ne lance pas de sondes payantes de modèle et n'installe pas d'agents.

## Configuration modèle seule

Le helper existant reste disponible sans préparer les documents de projet :

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> show
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> apply --choices <selected-role-map.json> --expected-sha256 <show.sha256>
```

Sa sortie `show` fournit les choix exacts groupe-vers-rôle et les tailles de panel. Construis la carte de rôles sélectionnés seulement depuis les choix acceptés. Garde `.cstack/` non suivi sans remplacer les règles ignore existantes, puis relis et valide le résultat. Le modèle de la session parente reste inchange.

## Runtimes facultatifs

Les anciennes sélections et recommandations restent natives Codex. Pour un worker externe demandé, utilise le [contrat des workers CLI](../cstack/references/runtime-workers.md) : `codex-cli`, `claude-code`, `cursor-agent` ou `grok`. Les panels peuvent mélanger ces sélections et l’héritage natif. Le coordinateur prépare les commandes et rend une synthèse unique ; l’utilisateur ne pilote pas chaque CLI manuellement.

Une entrée `{ "runtime": "claude-code" }` utilise le défaut du CLI et ne nécessite aucun catalogue. Elle ne prouve pas que le CLI est installé, connecté ou disponible. Une entrée avec `model` exige une confirmation dans le catalogue de ce runtime ; `reasoning_effort` exige aussi `model`. N’utilise pas les recommandations OpenAI ni son catalogue pour valider Claude ou Grok. Le helper accepte le catalogue historique natif et la forme `{"runtimes":{"codex-native":{},"codex-cli":{},"claude-code":{},"cursor-agent":{},"grok":{}}}`, chaque objet associant des slugs confirmés à leurs efforts.

Applique seulement les choix de runtime acceptés, via `models.py show`, `apply` et `resolve`. Le parcours `project.py preview/apply` reste celui de la préparation des documents de projet. Ne change pas la configuration globale, ne copie aucun credential et ne lance ni login ni génération pendant le setup. La présence d’une commande officielle de login ne prouve pas les droits d’abonnement Grok Build.

## Ajouter ou mettre à jour Claude Code

Une demande de configuration après installation ou connexion de Claude Code réutilise ce setup. `claude -p` est le mode non interactif du binaire `claude`, pas un runtime nommé `claude-p`. Enregistre `runtime: "claude-code"` ; le runner construit les arguments.

1. Lis les choix sauvegardés avec `show`. Pour une demande ciblant Claude, sonde ses capacités avec `bash <absolute-plugin>/scripts/run-tool.sh runtime/runtime.ts probe claude-code`. Cette sonde ne génère pas de réponse et ne confirme pas le login. Un CLI absent peut être configuré pour plus tard si l'utilisateur le demande ; indique que son exécution reste non vérifiée.
2. Présente les rôles pertinents avec leurs valeurs actuelles. Les panels `arena runners`, `architect runners`, `interrogate reviewers` et `arena cross-judge pool` acceptent plusieurs entrées. Les rôles simples, dont `swarm workers`, `feature, refactoring`, `bug-fix` et `judgment and prose`, acceptent une sélection. Tous les autres rôles listés ci-dessous peuvent aussi choisir Claude. Distingue les rédacteurs et juges pour conserver une revue par un acteur distinct.
3. Applique la demande explicite. « Ajouter Claude » à un panel conserve son ordre et ses membres, puis ajoute `{"runtime":"claude-code"}` si cette entrée est absente. Ne duplique pas une entrée identique en répétant le setup. « Remplacer » change seulement les positions demandées. Pour un panel absent, pars des valeurs héritées effectives de `show` et du contrat ; pour un rôle simple, montre le remplacement proposé. Si le périmètre manque, demande quels panels ou rôles changer plutôt que basculer tous les agents. Une demande précise ne nécessite pas une seconde confirmation.
4. Construis les choix avec seulement les rôles concernés. Préserve les modèles et efforts explicites des autres membres. Sans modèle Claude demandé, utilise le défaut du CLI. Si un membre conservé nomme un modèle, valide le panel complet contre les catalogues correspondants avant sauvegarde ; une disponibilité inconnue ne justifie pas d'effacer ce membre.
5. Utilise `apply` avec l'empreinte relue de `show`, puis relis `models.json` et résous chaque rôle modifié. Confirme les sélections effectives, l'absence de doublon ajouté et la conservation des rôles non concernés. Les nouvelles délégations utilisent ces choix sans réinstaller le plugin. Une tâche déjà lancée garde sa sélection ; ne la redémarre pas depuis le setup.

Le setup ne lance ni `claude -p` ni login pour tester le compte. L'abonnement ou la connexion reste vérifiable par les mécanismes officiels de Claude ; le résultat d'un dispatch ultérieur doit être rapporté séparément de la sauvegarde réussie.

## Recommandations

Ces choix sont facultatifs et valides contre le catalogue live avant sélection :

| Travail | Modele | Effort de raisonnement | Justification |
| --- | --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` | Recherches bornées et explications. |
| Changements simples | `gpt-5.6-luna` | `max` | Petites éditions avec checks d'acceptation clairs. |
| Developpement | `gpt-6-astra` | `low` | Implementation avec jugement de conception. |
| Debogage difficile | `gpt-6-astra` | `medium` | Diagnostic de causes qui interagissent. |
| Revue de code | `gpt-6-astra` | `low` | Jugement sur la correction et le risque. |
| Architecture complexe | `gpt-6-astra` | `xhigh` | Conception transversale et compromis. |
| Documentation | `gpt-5.6-luna` | `max` | Prose focalisee à partir de faits établis. |

## Roles

Roles simples :

- `simple edits`
- `documentation`
- `feature, refactoring`
- `bug-fix`
- `perf-issue`
- `hillclimb`
- `judgment and prose`
- `hardest tasks`
- `how explorer`
- `how explainer`
- `why investigators`
- `why synthesizer`
- `reflect tooling`
- `reflect judgment, divergent, synthesizer`
- `swarm workers`

Roles de panel :

- `arena runners`
- `arena cross-judge pool`
- `architect runners`
- `interrogate reviewers`

Le pool de juge croisé fournit un juge, de préférence différent de l'auteur quand c'est disponible. Sans pool, utilise un juge indépendant avec modèle hérité. Les autres longueurs de listes de panel fixent le nombre demandé de tentatives. Ne prétends jamais à des familles de modèles différentes quand chaque passe a utilisé le même modèle.

Les valeurs peuvent être des chaînes de modèle legacy, `inherit-parent`, ou `{ "model": "confirmed-slug", "reasoning_effort": "supported-effort" }`; les panels contiennent ces valeurs. `simple edits` manquant retombe sur `feature, refactoring`; `documentation` manquant retombe sur `judgment and prose`. Les autres rôles manquants héritent. Les panels manquants utilisent trois tentatives, sauf le pool de juge croisé qui en utilise une.

Exemple n'exigeant aucun modèle particulier :

```json
{
  "feature, refactoring": "inherit-parent",
  "interrogate reviewers": ["inherit-parent", "inherit-parent", "inherit-parent"]
}
```

Une configuration sauvegardée ne prouve pas qu'un modèle peut tourner. Gère le rejet au premier dispatch réel comme spécifié dans le contrat d’exécution. Ne lance pas de travaux de test payants seulement pour finir la configuration.
