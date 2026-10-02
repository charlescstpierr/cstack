# cstack

Les processus de pstack 0.15.2 adaptés aux outils natifs de Codex App et CLI. Plugin `0.7.0`. Version amont épinglée `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`.

Les préparations `$cstack:clarify`, `$cstack:domain`, `$cstack:horizon` et `$cstack:audit-architecture` sont disponibles sur demande. La configuration peut préparer un bloc de projet dans `AGENTS.md` et les conventions documentaires, en conservant les instructions existantes. Voir [la configuration](docs/guide/01-setup.md) et [les processus de préparation](docs/guide/04-design.md).

Dans le sélecteur, cherchez `$cstack` et choisissez **cstack**. Pour une commande saisie en texte brut, utilisez `$cstack:cstack`, le nom natif complet de la compétence principale.

Activez `$cstack:cstack` dans une tâche pour choisir un processus d'investigation, d'implémentation, de revue ou de livraison vérifiée. Le mode reste limité à cette tâche et se désactive sur demande. L'installation seule n'active aucune compétence.

Le plugin expose 29 compétences. Ses [23 principes](docs/guide/08-principles.md) sont des références consultées au besoin, sans commandes individuelles dans le sélecteur. Pour en demander un, nommez-le dans votre demande à `$cstack:cstack`. L'exploration déléguée utilise au moins deux explorateurs, normalement trois angles distincts, puis une synthèse. Une cible unique ne réduit pas ce nombre à un. Codex exige que la demande de délégation figure dans votre tour : sélectionnez la compétence dans le sélecteur, dont le prompt par défaut la porte, ou ajoutez-la vous-même. Voir [le dépannage](docs/guide/10-recipes-and-pitfalls.md#un-seul-agent-travaille).

Pour une implémentation multi-phase, une demande explicite de Goal natif permet de garder le même objectif entre les playbooks jusqu’à une PR testée et revue. Voir [la continuation autonome](docs/guide/07-overnight.md).

`$cstack:deslop` nettoie un diff de code avant commit. `$cstack:unslop` nettoie la prose. `$cstack:no-comments` confie les commentaires à un relecteur qui ne les a pas écrits. `deslop` est original à cstack. pstack livrait `/deslop` dans `cursor-team-kit`, sans source portable.

`$cstack:setup-cstack` demande un budget de raisonnement, puis affiche sept recommandations de modèle et d'effort pour tous les rôles et positions de panel, puis la configuration actuelle et l'héritage éventuel. Vous pouvez accepter, personnaliser, conserver, choisir l'héritage pour certains rôles ou annuler. Les choix sélectionnés sont validés dans le catalogue courant puis enregistrés localement dans `.cstack/models.json`, en préservant les autres réglages. Le modèle de la session reste inchangé. Voir [le tableau de configuration](docs/guide/01-setup.md#configurer-cstack). Les instructions du projet, le mode Plan et les autorisations Codex restent prioritaires.

Le [guide](docs/guide/README.md) présente les commandes et les processus. Le [contrat d’exécution natif](skills/cstack/references/codex-runtime.md) décrit les sous-agents, l'état local, les scripts et les limites des intégrations. Les webhooks Grok Bot et Benny ne sont pas fournis comme services natifs ; le [pack intake](automations/intake/README.md) documente le déclenchement GitHub Actions compatible Codex.

Le [guide Codex et Claude](docs/guide/11-cli-workers.md) explique la configuration, les skills communs et le contexte partagé. Les [workers CLI facultatifs](skills/cstack/references/runtime-workers.md) permettent de mélanger Codex natif, Codex CLI, Claude Code, Cursor CLI et Grok Build dans les panels existants. Le coordinateur conserve les briefs, worktrees, rapports et revues ; les CLI gèrent eux-mêmes leur login, sans credentials dans CStack.

Les assistants TypeScript utilisent Bun et leurs dépendances verrouillées. Leur installation nécessite le registre de paquets ou un cache Bun déjà rempli. Le lanceur bash/Python 3.9 crée une copie temporaire distincte sous `~/.cache/cstack/stages/` pour chaque invocation, puis la nettoie. Les opérations GitHub nécessitent `git` et `gh` authentifié. Aucun cache de plugin ni réglage global n'est modifié.

La [livraison des PR](skills/cstack/playbooks/shipping.md) impose le head vérifié à GitHub et relit les merges en attente avant une réécriture. L’assistant `watch-pr/ship-pr` inspecte ou annule ces demandes ; il ne fusionne aucune PR. Les limites du contrôle de destination et des files de merge sont précisées dans [la référence de sécurité](skills/cstack/references/merge-safety.md).

Installation, mise à jour, diagnostic et retrait : `install.sh install`, `update`, `doctor` et `uninstall`, à la racine du dépôt. Voir [l'installation](https://github.com/charlescstpierr/cstack#installation). Ouvrez ensuite une nouvelle conversation.

Installation et sources : [charlescstpierr/cstack](https://github.com/charlescstpierr/cstack). Le dépôt est privé.

Licence MIT. Voir [LICENSE](LICENSE) et [NOTICE](NOTICE.md) pour la provenance et le crédit de Lauren Tan.
