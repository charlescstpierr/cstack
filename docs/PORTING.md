# Portage de pstack vers cstack

Source : pstack 0.15.0, commit `27e2a62ff94f9af4b5e68435e41cdceacadb840c` de `cursor/plugins`.

`UPSTREAM.json` enregistre les 158 fichiers source et leurs identifiants Git. `PORTING.json` associe chaque fichier à une destination avec un statut et une raison. Aucun sous-ensemble issu du portage ChatGPT Web n'est utilisé comme base.

## Couverture

| Ensemble | Traitement |
| --- | --- |
| Mode principal | `poteto-mode` devient `$cstack:cstack`, avec routage à la demande et instructions natives. |
| Configuration | `setup-pstack` devient `$cstack:setup-cstack`, sans réglages globaux ni modèle imposé. |
| 23 principes | Texte de fond conservé dans `skills/cstack/references/principles/`, avec liens depuis les workflows et sans entrées de skill distinctes. |
| Skills spécialisés | Architecture, explication, investigation, revue, tests, personnalisation et vérification adaptés avec leurs références. |
| 23 playbooks | Procédures conservées, outils et règles de livraison adaptés à Codex. |
| Deux agents | Prompts embarqués transmis aux sous-agents natifs, sans installation de rôles nommés. |
| Suivi de PR et orchestration | Helpers Bun conservés ; collecte de piles avec `git` et `gh`, sans dépendance à Graphite. |
| Guide et visuels | Guide français et identité cstack ; retrait des captures spécifiques à Cursor. |
| `make-bot-ui` | Entrée explicite expliquant l'absence d'un service natif de webhooks Grok Bot. |
| Pack Benny | Notice documentaire uniquement ; aucune installation ni automatisation événementielle active. |

Les 47 entrées issues du premier portage incluent la notice `make-bot-ui`. La version 0.3.0 ajoute quatre préparations explicites : 51 entrées au total, dont 50 skills utilisables et une notice de limite.

Le catalogue courant réduit ces 51 entrées à 28 en déplaçant les 23 principes dans les références internes. Leurs anciennes commandes individuelles sont retirées ; les demandes nomment le principe dans `$cstack:cstack`. Les références conservent leur provenance et leurs règles, avec des chemins explicites depuis les consommateurs. Les autres skills et leurs politiques d'invocation restent disponibles. Les tâches ordinaires peuvent s'exécuter directement, avec exploration, conception et délégation lorsque leur coût est justifié par le travail.

## Compléments de Matt Pocock

Les ajouts adaptent le dépôt `mattpocock/skills` au commit `3cca18b368ae95cdbdebbff572ccafa662551015`, version 1.2.3. Leur inventaire et leurs empreintes sont dans `plugins/cstack/sources/matt-pocock.json` ; le copyright et la licence restent dans `plugins/cstack/LICENSE-MATT-POCOCK`. L'inventaire pstack original conserve ses 158 fichiers et son commit.

`grilling` devient `clarify`, `domain-modeling` devient `domain`, Wayfinder devient `horizon`, et le diagnostic d'architecture devient `audit-architecture`. Les méthodes de revue Standards/Spec enrichissent le panel existant d'`interrogate` ; les règles d'écriture pour agents enrichissent le playbook d'auteur. Aucun second routeur, modèle d'implémentation, setup global ou moteur de tickets n'est ajouté.

Les adaptations natives sont explicites : chemins locaux sous `.cstack/`, références de skills du même bundle, règles de modèles existantes, instruction de projet dans un bloc géré de `AGENTS.md`, pas de dépendance implicite aux skills installés de Matt. Horizon conserve ses portes de décision humaine et son arrêt avant l'implémentation. Le protocole exact de fichiers du setup est décrit dans le guide ; plusieurs remplacements de fichiers ne constituent pas une transaction atomique globale.

## Différences de fonctionnement

Codex qualifie les skills de plugin avec leur namespace. Le nom complet du mode principal est `$cstack:cstack` ; `$cstack` suffit pour chercher puis sélectionner ce skill dans le sélecteur interactif. Les prompts embarqués utilisent les noms complets pour fonctionner aussi dans `codex exec`. Ce comportement a été confirmé dans le [code natif de sélection des skills](https://github.com/openai/codex/blob/main/codex-rs/skills/src/selection.rs) et par un essai CLI réel.

- Les skills utilisent les outils réellement exposés par Codex. Aucun appel `Task` de Cursor, chemin de transcript Cursor ou nom de modèle propre à un fournisseur n'est requis.
- La délégation est native et limitée à la capacité de la session. Une exécution séquentielle faute de sous-agents est signalée. Une revue sur le même modèle n'est pas présentée comme une comparaison de modèles différents.
- Les modèles et efforts sont hérités par défaut. Le setup présente sept recommandations facultatives, validées dans le catalogue courant, et conserve les réglages non sélectionnés. Les objets `model` / `reasoning_effort` et les anciennes chaînes sont pris en charge. Chaque délégation transmet les deux champs sélectionnés ; si l’outil natif ne le permet pas, cstack signale la limite sans substitution ni instruction de prompt présentée comme configuration. La session principale reste inchangée.
- Les assistants sont exécutés depuis une copie inscriptible dans le projet. Le contenu du plugin installé reste immuable.
- La reprise repose sur les tâches accessibles, le contexte courant et des checkpoints locaux. Aucune lecture d'historiques d'autres projets ni promesse de survie de processus après fermeture de Codex.
- Un suivi périodique requiert une capacité de planification native disponible et une demande explicite. cstack n'ajoute pas de service permanent.
- Les outils GitHub, navigateur et autres connecteurs sont facultatifs. Une demande de statut ou une revue n'autorise pas à publier, envoyer un message ou fusionner.

## Compatibilité

Le paquet cible le format natif de plugin Codex et les sessions App et CLI qui prennent en charge les skills. Les assistants shell nécessitent un environnement bash/Python 3 ; les assistants TypeScript nécessitent Bun. Sur Windows, utiliser un environnement fournissant ces outils, tel que WSL. Les capacités disponibles peuvent varier selon la session et le compte.

La résolution des piles de PR exige une copie locale de chaque branche connectée et vérifie son SHA contre GitHub. Elle refuse de conclure si la collecte atteint 1 000 PRs, car l'historique pourrait être incomplet. La pagination constitue l'évolution prévue pour les dépôts qui dépassent cette limite.

L'identité de l'auteur upstream et la licence MIT sont préservées. Les liens vers Cursor servent à attribuer la source et à documenter les limites ; ils n'ajoutent aucune dépendance d'exécution.
