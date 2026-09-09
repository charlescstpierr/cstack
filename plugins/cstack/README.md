# cstack

Les workflows de pstack adaptés aux outils natifs de Codex App et CLI.

Activez `$cstack` dans une tâche pour choisir un workflow d'investigation, d'implémentation, de revue ou de livraison vérifiée. Le mode reste limité à cette tâche et se désactive sur demande. L'installation seule n'active aucun skill.

`$setup-cstack` configure des modèles par rôle dans le projet courant. Par défaut, les agents héritent du modèle de la session. Les instructions du projet, le mode Plan et les autorisations Codex restent prioritaires.

Le [guide](docs/guide/README.md) présente les commandes et les workflows. Le [contrat natif](skills/cstack/references/codex-runtime.md) décrit les sous-agents, l'état local, les scripts et les limites des intégrations. Les webhooks Grok Bot et le [pack Benny](automations/benny/README.md) ne sont pas fournis comme services natifs.

Les assistants TypeScript utilisent Bun et leurs dépendances verrouillées. Leur installation nécessite le registre de paquets ou un cache Bun déjà rempli. Le lanceur bash/Python crée une copie temporaire distincte sous `.cstack/tools/` pour chaque invocation, puis la nettoie. Les opérations GitHub nécessitent `git` et `gh` authentifié. Aucun cache de plugin ni réglage global n'est modifié.

Installation et sources : [charlescstpierr/cstack](https://github.com/charlescstpierr/cstack). Le dépôt est privé.

Licence MIT. Voir [LICENSE](LICENSE) et [NOTICE](NOTICE.md) pour la provenance et le crédit de Lauren Tan.
