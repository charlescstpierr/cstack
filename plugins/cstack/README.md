# cstack

Les workflows de pstack 0.15.2 adaptés aux outils natifs de Codex App et CLI. Plugin `0.4.0`. Pin amont `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`.

Les préparations `$cstack:clarify`, `$cstack:domain`, `$cstack:horizon` et `$cstack:audit-architecture` sont disponibles sur demande. Le setup peut préparer un bloc de projet dans `AGENTS.md` et les conventions documentaires, en conservant les instructions existantes. Voir [la configuration](docs/guide/01-setup.md) et [les workflows de préparation](docs/guide/04-design.md).

Dans le sélecteur, cherchez `$cstack` et choisissez **cstack**. Pour une commande saisie en texte brut, utilisez `$cstack:cstack`, le nom natif complet du skill principal.

Activez `$cstack:cstack` dans une tâche pour choisir un workflow d'investigation, d'implémentation, de revue ou de livraison vérifiée. Le mode reste limité à cette tâche et se désactive sur demande. L'installation seule n'active aucun skill.

Le plugin expose 29 skills. Ses [23 principes](docs/guide/08-principles.md) sont des références consultées au besoin, sans commandes individuelles dans le sélecteur. Pour en demander un, nommez-le dans votre demande à `$cstack:cstack`. Les tâches simples s'exécutent directement ; les workflows d'exploration, de conception et de délégation restent disponibles quand ils apportent une information ou une vérification utile.

`$cstack:deslop` nettoie un diff de code avant commit. `$cstack:unslop` nettoie la prose. `$cstack:no-comments` confie les commentaires à un relecteur qui ne les a pas écrits. `deslop` est original à cstack. pstack livrait `/deslop` dans `cursor-team-kit`, sans source portable.

`$cstack:setup-cstack` affiche six recommandations de modèle et d'effort par rôle à accepter, personnaliser ou remplacer par l'héritage ; vous pouvez aussi annuler. Les choix sélectionnés sont validés dans le catalogue courant puis enregistrés localement dans `.cstack/models.json`, en préservant les autres réglages. Par défaut, les sous-agents héritent de la session, dont le modèle reste inchangé. Voir le [tableau du setup](docs/guide/01-setup.md#configurer-cstack). Les instructions du projet, le mode Plan et les autorisations Codex restent prioritaires.

Le [guide](docs/guide/README.md) présente les commandes et les workflows. Le [contrat natif](skills/cstack/references/codex-runtime.md) décrit les sous-agents, l'état local, les scripts et les limites des intégrations. Les webhooks Grok Bot et le [pack Benny](automations/benny/README.md) ne sont pas fournis comme services natifs.

Les assistants TypeScript utilisent Bun et leurs dépendances verrouillées. Leur installation nécessite le registre de paquets ou un cache Bun déjà rempli. Le lanceur bash/Python 3.9 crée une copie temporaire distincte sous `.cstack/tools/` pour chaque invocation, puis la nettoie. Les opérations GitHub nécessitent `git` et `gh` authentifié. Aucun cache de plugin ni réglage global n'est modifié.

Installation et sources : [charlescstpierr/cstack](https://github.com/charlescstpierr/cstack). Le dépôt est privé.

Licence MIT. Voir [LICENSE](LICENSE) et [NOTICE](NOTICE.md) pour la provenance et le crédit de Lauren Tan.
