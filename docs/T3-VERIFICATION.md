# Vérification de l'adaptation T3

Cette adaptation implémente le contrat consolidé V5 dans le résolveur, la synchronisation d'agents et une préparation sans lancement. Elle ne revendique pas un plugin installé chargé dans T3. Le contrat normatif est [runtime/t3.md](../plugins/cstack/skills/cstack/references/runtime/t3.md).

## Origine et frontière des preuves

La demande d'implémentation rapporte trois exécutions faites par le parent T3 Codex, avec métadonnées retournées pour Codex, Claude Agent et OpenCode. Ces observations ne sont pas reproduites par cet enfant, et l'identité effective des backends reste non vérifiée. Le parent rapporte aussi que `codex plugin list` n'a pas trouvé cstack. Le chargement installé est donc NON VÉRIFIÉ, sans installation globale autorisée.

Ce checkout fourni par T3 est `/home/charlescstpierr/.t3/worktrees/cstack/t3-2e23c27d`, branche `t3/t3-runtime-adaptation`. Les modifications et le commit de cette branche sont les artefacts d'écriture isolée à examiner depuis le parent. Aucun checkout créé en shell, aucun push, PR, délégué ou changement du checkout parent par cet enfant. Le chemin communiqué par le harnais ne prouve pas un confinement général du processus.

Les tests de catalogue emploient des identifiants `synthetic-*` et `fixture-*`. Ils prouvent les décisions des helpers sur des données contrôlées. Ils ne sont pas des traces d'hôte. Aucun nom de modèle de production n'est figé dans le chemin T3.

## Lecteurs examinés

Recherche de fermeture effectuée avec `rg -n 'models.json|selection|runtime|preflight' plugins/cstack scripts tests`. Les lecteurs d'exécution sont `setup-cstack/scripts/models.py`, `project.py`, `cstack/scripts/runtime/runtime.ts` et la nouvelle préparation `runtime/prepare.ts`. Le premier valide la forme globale, puis la disponibilité par position. Le second préserve les agents des rôles T3. Le lanceur refuse T3 avant probe ou processus CLI. La préparation accepte seulement la branche T3 et réutilise worker-context et worker-skills.

Les lecteurs d'analyse dans `scripts/outcome-bench.py` transportent la configuration sans dispatch T3. Les fixtures et tests des anciennes formes restent inchangés. Le run-tool copie le répertoire scripts complet dans son stage et n'ajoute aucun chemin d'orchestration. Les entrées runtime, setup, modèles, workers, activation, état, intégrations et playbooks de livraison/nettoyage renvoient au contrat prioritaire. Les autres skills restent passifs jusqu'à invocation et les instructions supérieures priment.

## Contrôles déterministes

Commandes reproductibles depuis la racine :

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
bun test plugins/cstack/skills/cstack/scripts/runtime/prepare.test.ts
bash scripts/check.sh
```

Le journal local de ce travail est `.cstack/t3-adaptation/decisions.tsv`. La sortie complète du check se trouve dans `.cstack/t3-adaptation/check.log`, artefact ignoré. Bun 1.4.0 a été trouvé sous `/tmp/cstack-tools/bun-native/package/bin/bun`, sans installation globale. Les permissions 0775 des exécutables du checkout ont été réalignées aux 0755 exigés par le validateur, sans changement du bit exécutable Git.

Les tests vérifient les positions ordonnées, blocages CLI et hors hôte, options exactes, contextes étrangers/périmés, héritage incomplet, fichier malformé global, agents gérés et manuels conservés, application explicite et preview sans recommandations Codex. La préparation est exercée avec PATH vide, contenu et empreinte exacts, mutation de snapshot, skill manquante et dépassement de transport. Le runner CLI reçoit une sélection T3 et des chemins dépendants inexistants, puis refuse avant de les utiliser.

Résultat final observé le 4 novembre 2026, sur Python 3.14.4 et Bun 1.4.0 :

| Contrôle | Résultat |
|---|---|
| Faits générés et validateur paquet | PASS, 29 skills et 158 références amont |
| Python | Succès, 1 ignoré sous Python 3.14 ; le rapport CI indique le nombre pour son commit |
| Bun dépôt | 29 succès, 0 échec |
| Bun assistants | 235 succès, 0 échec |
| Types stricts assistants et types racine | PASS |
| Syntaxe Bash et `git diff --check` | PASS |
| ShellCheck et Actionlint via Docker épinglé | NON EXÉCUTÉS, Docker absent |
| Grammaire Python 3.9 des deux helpers modifiés | PASS via `ast.parse(feature_version=(3,9))`, pas une exécution sous Python 3.9 |

Localement, `bash scripts/check.sh` atteint Docker puis sort avec `docker: command not found`. La [CI du commit 6fa0f11](https://github.com/charlescstpierr/cstack/actions/runs/41935526471) a exécuté le script complet avec succès, dont les deux contrôles Docker. Les correctifs ultérieurs exigent leur propre CI. Les nouvelles fixtures partagées `tests/fixtures/t3-selections.json` sont interprétées par les parsers Python et TypeScript. Le contrat T3 est inclus une seule fois dans le bundle avec son empreinte.

La CLI de préparation a été exercée sur ce commit avec un vrai brief local. Une borne d'essai de 32768 octets refuse le bundle sans troncature. Une borne de 131072 octets produit 127307 octets, dont le SHA-256 du prompt recalculé correspond au résultat. Ce test mesure la préparation locale et le refus de dépassement, pas le plafond de transport T3. Les reviewers ont comparé les fichiers du bundle aux blobs Git du commit ciblé.

## Smoke réel à exécuter par le coordinateur

Ne remplir aucun identifiant de session, environnement, empreinte ou limite transport à partir d'une supposition. Une étape non observable produit NON VÉRIFIÉ ou BLOCKED pour la capacité dépendante, jamais une valeur inventée.

1. Dans un fil Codex T3 déjà autorisé, invoquer explicitement cstack et constater son chargement réel. S'il n'est pas chargé, marquer cette capacité NON VÉRIFIÉE. Les contrôles de fichiers indépendants peuvent continuer. Ne pas installer le plugin globalement.
2. Relever outils disponibles, règles actives de découverte, contexte session/environnement accessible et sortie réelle de capabilities. Séparer la trace originale des données normalisées sans secrets. Si les métadonnées de recoupement manquent, marquer preuve d'hôte non établie et dispatch explicite BLOCKED. Ne pas fabriquer `sessionId` avec le titre d'un fil.
3. Transcrire uniquement les providers, modèles et options effectivement vérifiés dans le catalogue décrit par le contrat. Calculer les empreintes sur les octets réels. Une liste courte reste `modelsComplete: false`. Choisir les dates de validité selon les règles actives, et revalider avant dispatch. Conserver cible demandée et métadonnées retournées séparément.
4. Exécuter `models.py --workspace <workspace> --host t3 --catalog <catalogue> --host-context <contexte> show`. Examiner l'avertissement de compatibilité et sélectionner explicitement les positions. Utiliser `apply` seulement avec autorisation d'écriture projet, puis `preflight` pour les rôles requis. Aucun agent périmé n'est chargé à la place d'une position bloquée.
5. Préparer un dossier de tâche borné contenant le brief et les fichiers du snapshot. Calculer les SHA-256 sur les octets. Fournir la requête décrite dans le contrat à `runtime/runtime.ts prepare --request <requête absolue>`. Mesurer la taille réellement transportée avec des briefs bornés croissants et noter la dernière taille observée, sans revendiquer un maximum universel. Exiger la correspondance du target préflight et de la sélection préparée avant appel MCP.
6. Pour l'implémentation initiale autorisée, appeler directement `delegate_task` avec `isolation: "worktree"` et le target exact. Ne pas créer de checkout dans le prompt. Suivre `next`, relever chemin et branche retournés, lire l'artefact depuis le parent et comparer SHA/diff/statut. Cela mesure l'accès parent et la propriété host, pas un confinement absolu.
7. Pour chaque review, demander un nouveau worktree T3 et une nouvelle tâche. Fournir un commit de branche de tâche déjà autorisé ou reconstituer les fichiers du snapshot exact. Comparer leurs SHA et HEAD/status avant et après review. Rejeter un verdict sur une mauvaise source ou une mutation du checkout. N'intégrer aucune écriture du reviewer.
8. Dans un parent à la racine sans isolation liée adéquate, présenter un petit finding que le harnais réserve au parent. Observer zéro nouveau délégué et zéro écriture, commit, merge ou changement de checkout root. Le résultat doit être correction BLOCKED visible. Relever cette limitation et sa fréquence sur les essais. Dans un parent déjà isolé et autorisé, présenter le même finding et observer qu'il le corrige lui-même, avec diff et contrôles. Aucun nouveau fil top-level pour préparer cet essai sans demande utilisateur.
9. Sur une tâche bornée autorisée, mesurer `task_cancel`, la fin effective du travail et l'absence de modifications tardives observables. Aucun polling. Un acquittement d'annulation seul ne prouve pas la fin effective.
10. Le cycle PR exige une autorisation distincte dans cette tâche. Lorsqu'elle existe, mesurer création/reprise/push, liaison immédiate comme appel suivant, puis watch seulement en attente nécessaire ou demandée et handback/unwatch selon les règles actives. Cet enfant n'exécute aucune de ces actions.

## Capacités encore non vérifiées

Le chargement installé, la limite maximale de transport, l'annulation réelle, la reconstitution du snapshot dans un reviewer T3, les permissions effectivement imposées aux enfants, les deux cas parent/finding, et le cycle PR complet demandent encore les observations ci-dessus. La revue par trois fournisseurs appartient au parent. Une absence de preuve de backend effectif n'est pas une preuve d'incompatibilité.
