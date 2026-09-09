# Portage de pstack vers cstack

Source : pstack 0.15.0, commit `27e2a62ff94f9af4b5e68435e41cdceacadb840c` de `cursor/plugins`.

`UPSTREAM.json` enregistre les 158 fichiers source et leurs identifiants Git. `PORTING.json` associe chaque fichier à une destination avec un statut et une raison. Aucun sous-ensemble issu du portage ChatGPT Web n'est utilisé comme base.

## Couverture

| Ensemble | Traitement |
| --- | --- |
| Mode principal | `poteto-mode` devient `$cstack`, avec routage à la demande et instructions natives. |
| Configuration | `setup-pstack` devient `$setup-cstack`, sans réglages globaux ni modèle imposé. |
| 23 principes | Texte de fond conservé, application limitée à la tâche explicitement activée. |
| Skills spécialisés | Architecture, explication, investigation, revue, tests, personnalisation et vérification adaptés avec leurs références. |
| 23 playbooks | Procédures conservées, outils et règles de livraison adaptés à Codex. |
| Deux agents | Prompts embarqués transmis aux sous-agents natifs, sans installation de rôles nommés. |
| Suivi de PR et orchestration | Helpers Bun conservés ; collecte de piles avec `git` et `gh`, sans dépendance à Graphite. |
| Guide et visuels | Guide français et identité cstack ; retrait des captures spécifiques à Cursor. |
| `make-bot-ui` | Entrée explicite expliquant l'absence d'un service natif de webhooks Grok Bot. |
| Pack Benny | Notice documentaire uniquement ; aucune installation ni automatisation événementielle active. |

Les 47 entrées du catalogue incluent la notice `make-bot-ui`. Il s'agit donc de 46 skills utilisables et d'une limite explicitement consultable, pas de 47 intégrations exécutables.

## Différences de fonctionnement

- Les skills utilisent les outils réellement exposés par Codex. Aucun appel `Task` de Cursor, chemin de transcript Cursor ou nom de modèle propre à un fournisseur n'est requis.
- La délégation est native et limitée à la capacité de la session. Une exécution séquentielle faute de sous-agents est signalée. Une revue sur le même modèle n'est pas présentée comme une comparaison de modèles différents.
- Les modèles sont hérités par défaut. La configuration locale de rôles est vérifiée à chaque utilisation ; une sélection explicite indisponible ne déclenche pas de substitution silencieuse.
- Les assistants sont exécutés depuis une copie inscriptible dans le projet. Le contenu du plugin installé reste immuable.
- La reprise repose sur les tâches accessibles, le contexte courant et des checkpoints locaux. Aucune lecture d'historiques d'autres projets ni promesse de survie de processus après fermeture de Codex.
- Un suivi périodique requiert une capacité de planification native disponible et une demande explicite. cstack n'ajoute pas de service permanent.
- Les outils GitHub, navigateur et autres connecteurs sont facultatifs. Une demande de statut ou une revue n'autorise pas à publier, envoyer un message ou fusionner.

## Compatibilité

Le paquet cible le format natif de plugin Codex et les sessions App et CLI qui prennent en charge les skills. Les assistants shell nécessitent un environnement bash/Python 3 ; les assistants TypeScript nécessitent Bun. Sur Windows, utiliser un environnement fournissant ces outils, tel que WSL. Les capacités disponibles peuvent varier selon la session et le compte.

La résolution des piles de PR exige une copie locale de chaque branche connectée et vérifie son SHA contre GitHub. Elle refuse de conclure si la collecte atteint 1 000 PRs, car l'historique pourrait être incomplet. La pagination constitue l'évolution prévue pour les dépôts qui dépassent cette limite.

L'identité de l'auteur upstream et la licence MIT sont préservées. Les liens vers Cursor servent à attribuer la source et à documenter les limites ; ils n'ajoutent aucune dépendance d'exécution.
