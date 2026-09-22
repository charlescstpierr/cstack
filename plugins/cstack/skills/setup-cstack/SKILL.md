---
name: setup-cstack
description: "Guider la configuration de projet cstack : préserver les consignes de projet, configurer les choix facultatifs de modèle/effort et expliquer les workflows de préparation. Utiliser pour $cstack:setup-cstack ou les changements de configuration cstack."
---

# Configurer cstack

Lis le [contrat d’exécution natif Codex](../cstack/references/codex-runtime.md). L'usage de base de cstack n'exige aucune configuration. La configuration prépare seulement le projet courant; elle n'active jamais un flux de travail et ne change jamais la configuration globale.

## Decouvrir et présenter

1. Localise le workspace cible, normalement sa racine Git où le répertoire courant hors Git. Lis les `AGENTS.md`, `CLAUDE.md`, `docs/agents/cstack.md`, `docs/agents/issue-tracker.md`, conventions de domaine et `.cstack/models.json` existants quand ils sont presents. Inspecte seulement les fichiers de projet pertinents; ne lis pas les identifiants secrets. Résous le chemin absolu de ce bundle installe.
2. Respecte la portée demandée. Une demande de changement de modèles utilise seulement les commandes modèle seules ci-dessous. La configuration générale propose aussi les consignes de projet et conventions de tracker. Une demande de preview, lecture seule, annulation ou mode Plan n'écrit rien dans le projet; garde les choix proposés dans la conversation ou dans un artefact temporaire autorisé.
3. Découvre les modèles et efforts depuis le schéma d'outil natif courant ou le catalogue de session faisant autorité. Pour une CLI prise en charge, le JSON brut de `codex debug models` fonctionne; sinon, utilise une carte de slugs confirmés vers listes d'efforts depuis le schéma réel. Un cache périmé n'est pas une preuve de disponibilité. Sans découverte, l'héritage reste disponible. Vérifie si le dispatch natif peut exprimer les deux champs sélectionnés, avec des rôles génériques et des réglages de fork pris en charge.
4. Exécute la commande modèle `show`. Présente les choix existants avec les six recommandations ci-dessous, leurs raisons et toute paire indisponible. Propose acceptation, personnalisation par rôle, héritage ou annulation. Préserve les rôles non sélectionnés. Applique les choix déjà explicitement demandés sans redemander; invoquer simplement setup n'accepte pas les recommandations.
5. Explique chaque flux de travail de préparation avec les données `workflows` du preview de projet et le [contrat de flux de travail](../cstack/references/codex-runtime.md) : `clarify` et `domain` n'ont aucun délégué par défaut; Horizon a un enfant par ticket de recherche prêt; un audit d'architecture a au plus un explorateur initial. Nomme le rôle existant et son modèle/effort effectif pour chaque phase. L'implémentation ordinaire et les tailles de panels existantes restent inchangées. Ce sont des règles de dispatch, pas quatre nouveaux rôles de modèle.
6. Pour la préparation de projet, propose un bloc cstack passif dans `AGENTS.md` et `docs/agents/cstack.md`, en préservant les octets environnants. Le `CLAUDE.md` existant reste intact; le bloc AGENTS généré peut référencer ses conventions de projet partagées. Le contenu guide non géré existant où les blocs marqueurs mal formés sont des conflits à expliquer et préserver, pas une permission de remplacer le fichier. Ne crée pas de `CONTEXT.md` vide ni de répertoires ADR.
7. Réutilise un document de tracker existant sauf si l'utilisateur a demandé un changement. Quand Horizon a besoin d'un choix, propose Markdown local ou le dépôt GitHub pertinent découvert depuis ce projet. Consigne une cible GitHub seulement après sa sélection; ne crée pas d'étiquettes, tickets, dépendances ou état distant pendant la configuration. Aucun choix de tracker n'est nécessaire pour une configuration modèle seule ou des workflows sans rapport.

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

Après succès, lis les vrais fichiers générés et les choix de modèle effectifs. Vérifie que le bloc cstack est unique, que les consignes existantes et les octets CLAUDE ont survécu, que l'état local est ignoré quand il est créé, et qu'aucun modèle non sélectionné n'a changé. Rapporte les chemins, comptes et réglages effectifs, pas des affirmations disant qu'un modèle a été exécuté. Setup ne lance pas de sondes payantes de modèle, n'installe pas d'agents et n'exige pas de redémarrage pour utiliser ses réglages de projet.

## Configuration modèle seule

Le helper existant reste disponible sans préparer les documents de projet :

```sh
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> show
python3 <absolute-plugin>/skills/setup-cstack/scripts/models.py --workspace <workspace> --catalog <live-catalog.json> apply --choices <selected-role-map.json> --expected-sha256 <show.sha256>
```

Sa sortie `show` fournit les choix exacts groupe-vers-rôle et les tailles de panel. Construis la carte de rôles sélectionnés seulement depuis les choix acceptés. Garde `.cstack/` non suivi sans remplacer les règles ignore existantes, puis relis et valide le résultat. Le modèle de la session parente reste inchange.

## Runtimes facultatifs

Les anciennes sélections et recommandations restent natives Codex. Pour un worker externe demandé, utilise le [contrat des workers CLI](../cstack/references/runtime-workers.md) : `codex-cli`, `claude-code` ou `grok`. Les panels peuvent mélanger ces sélections et l’héritage natif. Le coordinateur prépare les commandes et rend une synthèse unique ; l’utilisateur ne pilote pas chaque CLI manuellement.

Une entrée `{ "runtime": "claude-code" }` utilise le défaut du CLI et ne nécessite aucun catalogue. Elle ne prouve pas que le CLI est installé, connecté ou disponible. Une entrée avec `model` exige une confirmation dans le catalogue de ce runtime ; `reasoning_effort` exige aussi `model`. N’utilise pas les recommandations OpenAI ni son catalogue pour valider Claude ou Grok. Le helper accepte le catalogue historique natif et la forme `{"runtimes":{"codex-native":{},"codex-cli":{},"claude-code":{},"cursor-agent":{},"grok":{}}}`, chaque objet associant des slugs confirmés à leurs efforts.

Applique seulement les choix de runtime acceptés, via les mêmes commandes `show`, `preview` et `apply`. Ne change pas la configuration globale, ne copie aucun credential et ne lance ni login ni génération pendant le setup. La présence d’une commande officielle de login ne prouve pas les droits d’abonnement Grok Build.

## Recommandations

Ces choix sont facultatifs et valides contre le catalogue live avant sélection :

| Travail | Modele | Effort de raisonnement | Justification |
| --- | --- | --- | --- |
| Exploration | `gpt-5.6-luna` | `max` | Recherches bornées et explications. |
| Changements simples | `gpt-5.6-luna` | `max` | Petites éditions avec checks d'acceptation clairs. |
| Developpement | `gpt-6-astra` | `low` | Implementation avec jugement de conception. |
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
