# Portage de pstack vers cstack

Source : pstack 0.15.5, commit `12d587dfb20741cafc376c42c696c5f6e2a64487` de `cursor/plugins`. Pin précédent : 0.15.2, `889ec4b68fa5aab0e867dad71ec3fdf386ae48f3`.

`UPSTREAM.json` enregistre les 158 fichiers source et leurs identifiants Git. `PORTING.json` associe chaque fichier à une destination avec un statut et une raison. Aucun sous-ensemble issu du portage ChatGPT Web n'est utilisé comme base.

Le repin 0.15.2 vers 0.15.5 apporte cinq commits amont, portés à la main en français puis appliqués par le synchroniseur (45 cibles, résolution `write` du texte porté). `5bf2b15` (#366) ajoute la question de budget du setup, portée sans écrire de budget dans `models.json`. `70b2dc8` (#414) ajoute les rondes de vérification à partir du head code-ready, les règles de rebase, `children.tsv`, au moins deux voies d'audit, la règle du bruit de build et les briefs Swarm qui nomment SHA et méthode ; la règle d'autonomie totale va dans le principe « Ne jamais bloquer sur l'humain ». `12d587d` (#422) ajoute les lignes `start` du journal de décisions et l'exception du propriétaire en autopilot pour le rebase et babysit. Ne sont pas repris : les modèles par défaut et les noms de modèles (#414, #416), qu'`AGENTS.md` interdit de figer ; les consignes supprimées par #414 et `b0b9c7a` (#419), conservées faute de preuve sur Codex ; la lecture unifiée de la règle de modèle (#422), déjà couverte par `runtime/modeles.md`.

Le repin 0.15.0 vers 0.15.2 apporte trois commits amont. `f8abedd` exige que chaque affirmation porte sa preuve ou son étiquette (mesuré, inféré, guess) dans la même phrase. `f5bdd68` remplace les pronoms genrés par « the operator » et demande un message de statut dans le chat. `889ec4b` aligne les rôles code-delegate `bug-fix`, `perf-issue` et `hillclimb` sur le défaut déjà utilisé par fonctionnalité et refactorisation. Le setup cstack conserve le rôle d'exécution, mais recommande maintenant `gpt-6-astra` avec l'effort `medium` pour `bug-fix` au lieu du groupe développement `low`.

## Couverture

| Ensemble | Traitement |
| --- | --- |
| Mode principal | `poteto-mode` devient `$cstack:cstack`, avec routage à la demande et instructions natives. |
| Configuration | `setup-pstack` devient `$cstack:setup-cstack`, sans réglages globaux ni modèle imposé. |
| 23 principes | Texte de fond conservé dans `skills/cstack/references/principles/`, avec liens depuis les processus et sans entrées de compétence distinctes. |
| Compétences spécialisées | Architecture, explication, investigation, revue, tests, personnalisation et vérification adaptés avec leurs références. |
| 23 guides d'exécution | Procédures conservées, outils et règles de livraison adaptés à Codex. |
| Deux agents | Invites embarquées transmises aux sous-agents natifs, sans installation de rôles nommés. |
| Suivi de PR et orchestration | Assistants Bun conservés ; collecte de piles avec `git` et `gh`, sans dépendance à Graphite. |
| Guide et visuels | Guide français et identité cstack ; retrait des captures spécifiques à Cursor. |
| `make-bot-ui` | UI locale dont le serveur détient les identifiants et réveille `codex exec` ; pas de routine webhook hébergée. |
| Pack d'intake | Deux exécutions `codex exec` déclenchées par GitHub Actions, avec connecteurs MCP ; ni webhook entrant ni scheduler côté Codex. |
| `deslop` | Ajout original à cstack. Il remplace `/deslop` de `cursor-team-kit`, sans source portable. |

Les 47 entrées issues du premier portage incluent la notice `make-bot-ui`. La version 0.3.0 ajoute quatre préparations explicites : 51 entrées au total, dont 50 compétences utilisables et une note de limite.

Le catalogue a ensuite réduit ces 51 entrées à 28 en déplaçant les 23 principes dans les références internes. 0.4.0 ajoute `deslop`. Le catalogue courant compte 29 compétences. Les anciennes commandes de principes sont retirées ; les demandes nomment le principe dans `$cstack:cstack`. Les références conservent leur provenance et leurs règles, avec des chemins explicites depuis les consommateurs. Les autres compétences et leurs politiques d'invocation restent disponibles. Les tâches ordinaires peuvent s'exécuter directement, avec exploration, conception et délégation lorsque leur coût est justifié par le travail.

## Compléments de Matt Pocock

Les ajouts adaptent le dépôt `mattpocock/skills` au commit `3cca18b368ae95cdbdebbff572ccafa662551015`, version 1.2.3. Leur inventaire et leurs empreintes sont dans `plugins/cstack/sources/matt-pocock.json` ; le copyright et la licence restent dans `plugins/cstack/LICENSE-MATT-POCOCK`. L'inventaire pstack original conserve ses 158 fichiers et son commit.

`grilling` devient `clarify`, `domain-modeling` devient `domain`, Wayfinder devient `horizon`, et le diagnostic d'architecture devient `audit-architecture`. Les méthodes de revue Standards/Spec enrichissent le comité existant d'`interrogate` ; les règles d'écriture pour agents enrichissent le guide d'exécution d'auteur. Aucun second routeur, modèle d'implémentation, configuration globale ou moteur de tickets n'est ajouté.

Les adaptations natives sont explicites : chemins locaux sous `.cstack/`, références de compétences du même paquet, règles de modèles existantes, instruction de projet dans un bloc géré de `AGENTS.md`, pas de dépendance implicite aux compétences installées de Matt. Horizon conserve ses portes de décision humaine et son arrêt avant l'implémentation. Le protocole exact de fichiers de la configuration est décrit dans le guide ; plusieurs remplacements de fichiers ne constituent pas une transaction atomique globale.

## Différences de fonctionnement

Codex qualifie les compétences de plugin avec leur espace de noms. Le nom complet du mode principal est `$cstack:cstack` ; `$cstack` suffit pour chercher puis sélectionner cette compétence dans le sélecteur interactif. Les invites embarquées utilisent les noms complets pour fonctionner aussi dans `codex exec`. Ce comportement a été confirmé dans le [code natif de sélection des compétences](https://github.com/openai/codex/blob/a3ebd19fa40d8eb3183928e6a145ec64c33f1283/codex-rs/skills/src/selection.rs) et par un essai CLI réel.

- Les compétences utilisent les outils réellement exposés par Codex. Aucun appel `Task` de Cursor, chemin de transcript Cursor ou nom de modèle propre à un fournisseur n'est requis.
- La délégation est native et limitée à la capacité de la session. Une exécution séquentielle faute de sous-agents est signalée. Une revue sur le même modèle n'est pas présentée comme une comparaison de modèles différents.
- Les modèles et efforts sont hérités par défaut. La configuration présente d'abord sept recommandations facultatives pour tous les rôles et positions de panel, validées dans le catalogue courant, puis seulement l'état actuel et l'héritage éventuel. Elle conserve les réglages non sélectionnés. Les objets `model` / `reasoning_effort` et les anciennes chaînes sont pris en charge. Chaque délégation transmet les deux champs sélectionnés ; si l’outil natif ne le permet pas, cstack signale la limite sans substitution ni instruction d'invite présentée comme configuration. La session principale reste inchangée.
- Les assistants sont exécutés depuis une copie inscriptible dans le projet. Le contenu du plugin installé reste immuable.
- La reprise repose sur les tâches accessibles, le contexte courant et des points de reprise locaux. Aucune lecture d'historiques d'autres projets ni promesse de survie de processus après fermeture de Codex.
- Un suivi périodique requiert une capacité de planification native disponible et une demande explicite. cstack n'ajoute pas de service permanent.
- Les outils GitHub, navigateur et autres connecteurs sont facultatifs. Une demande de statut ou une revue n'autorise pas à publier, envoyer un message ou fusionner.

## Compatibilité

Le paquet cible le format natif de plugin Codex et les sessions App et CLI qui prennent en charge les compétences. Les assistants shell nécessitent bash et Python 3.9 ou plus récent. L'analyse du `config.toml` de Codex dans `scripts/verify-behavior.py` exige Python 3.11 ou plus récent. Les assistants TypeScript nécessitent Bun. Sur Windows, utiliser un environnement fournissant ces outils, tel que WSL. Les capacités disponibles peuvent varier selon la session et le compte.

La résolution `orch` des piles de PR exige une copie locale de chaque branche connectée et vérifie son SHA contre GitHub. Elle refuse de conclure dès que la collecte atteint 1 000 PRs, car l'historique pourrait être incomplet. Le watcher `watch-pr` a un contrat séparé : il refuse dès que GitHub signale 300 PRs ouvertes. La pagination constitue l'évolution prévue pour les dépôts qui dépassent ces limites.

L'identité de l'auteur amont et la licence MIT sont préservées. Les liens vers Cursor servent à attribuer la source et à documenter les limites ; ils n'ajoutent aucune dépendance d'exécution.
