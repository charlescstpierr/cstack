# Historique de sessions avec Agent-Git

Agent-Git est une option explicite pour versionner une conversation native. CStack garde le routage, les briefs, les permissions, les reçus et la vérification. Ce pont transmet des commandes à `agit`, qui doit être installé et connecté séparément. Avant un import ou un enregistrement, il vérifie que la préférence effective `push.auto` du dépôt Agent-Git est `false` ; sinon, il refuse l'opération.

## Utilisation

Depuis le dépôt de travail, avec le chemin absolu du plugin installé :

Choisir explicitement un dépôt Agent-Git local déjà initialisé ou cloné. Son nom peut différer de celui du dépôt de code. Pour désactiver sa publication automatique : `agit config --repo <owner/repo> push.auto false`. Le pont ne modifie pas cette préférence à ta place et refuse un dépôt absent ou une préférence illisible.

```sh
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh lineage codex <session-id-natif> <owner/repo@branche>
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh import codex <session-id-natif> <owner/repo@branche> independent
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh checkpoint <owner/repo@branche> "routeur vérifié"
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh log <owner/repo@branche>
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh resume <owner/repo@branche>
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh resume <owner/repo@branche> claude-code --accept-loss --no-launch
bash <plugin-root>/scripts/run-tool.sh session-bridge.sh fork <owner/repo@branche#2> autre-branche claude-code --accept-loss
```

`lineage` inspecte les bases locales vérifiées sans adopter de session ni modifier la transcription. Le lanceur CStack peut créer `.cstack/` dans le workspace à sa première invocation. Avant `import`, choisis `independent` pour une nouvelle lignée ou `onto <ref-vérifiée>` pour prolonger une base affichée. Agent-Git refuse normalement de choisir à ta place dans une session d'agent non interactive. `import` adopte et enregistre la première version. `checkpoint` enregistre les nouveaux tours terminés par `agit commit --milestone` ; un appel d'outil encore ouvert attend le prochain enregistrement.

`resume` sans runtime permet la reprise native de la même session si Agent-Git la reconnaît. `fork` crée une nouvelle branche, puis lance le runtime choisi. Un runtime explicite exige `--accept-loss`, même si le format s'avère identique. Dans un terminal, Agent-Git peut aussi demander confirmation. **Dans une session d'agent non interactive, Agent-Git affiche les pertes puis continue sans confirmer** ; le pont exige donc ce choix explicite avant de l'appeler. `log` inspecte l'historique. Ajouter `--no-launch` en dernier à `resume` ou `fork` prépare la reprise et imprime la commande sans lancer le runtime ; cela peut déjà installer une transcription native et modifier sa liaison à la branche.

Le pont exige des références explicites et ne propose ni `push` ni `login`. Un enregistrement local requiert quand même `agit login`, car Agent-Git utilise cette identité comme auteur Git. Une publication ultérieure se fait par une demande séparée à `agit push` après inspection du contenu. Les hooks d'un runtime lancé et le daemon Agent-Git peuvent effectuer leurs propres enregistrements ou publications selon leur configuration ; le contrôle du pont concerne ses appels d'import et de checkpoint. Ce contrôle ne verrouille pas la configuration : ne pas activer `push.auto` depuis un autre processus pendant l'opération. N'adopte pas automatiquement la session racine de Codex : son identifiant natif doit être connu et correspondre au projet.

## Ce qui est effectivement conservé

Dans [Agent-Git au commit `699f3e4`](https://github.com/Einsia/agent-git/tree/699f3e4ad47ed3246d549860115aaa2ef719a1e6), une branche représente une session et chaque commit en est une version. Le dépôt Agent-Git contient `session/meta.json`, un `LOG` d'événements adressés par contenu et un `VIEW` qui choisit ce qui est réinstallé à la reprise. Le store local relie un identifiant natif à la branche ; il ne duplique pas la transcription. Les enveloppes gardent les lignes natives, y compris les appels et résultats d'outils présents dans ces lignes. La métadonnée du workspace résume origin, HEAD, branche et état sale, sans sauvegarder le diff ni les fichiers du code. Les fichiers joints externes ou les ressources référencées par chemin ne sont pas démontrés portables par ce modèle.

| Source | Destination Agent-Git | État constaté dans le code |
| --- | --- | --- |
| Codex | Codex, Claude Code, OpenCode | Adaptateur importable et réinstallable ; changement de format avec pertes |
| Claude Code | Claude Code, Codex, OpenCode | Adaptateur importable et réinstallable ; changement de format avec pertes |
| OpenCode | OpenCode, Codex, Claude Code | Adaptateur importable et réinstallable ; changement de format avec pertes |
| Cursor | Codex, Claude Code, OpenCode | Source lisible ; destination Cursor refusée par `Capability::ImportOnly` |

Une reprise de la tête de branche conserve la même lignée ; un point historique ou un tag passe par `fork` et obtient une nouvelle branche. Une reprise locale native peut réutiliser la transcription vivante sans la reconstruire depuis `VIEW`. Pour appliquer exactement un ancien `VIEW`, il faut matérialiser une autre session. Une conversion entre formats passe par la représentation intermédiaire : Agent-Git annonce la perte du raisonnement chiffré, des encodages propriétaires et des frontières de compactage. Les arguments et résultats d'outils ne sont récupérés que lorsque l'adaptateur sait les apparier. Voir [le modèle de stockage](https://github.com/Einsia/agent-git/blob/699f3e4ad47ed3246d549860115aaa2ef719a1e6/docs/02_session_store.md), [l'installation](https://github.com/Einsia/agent-git/blob/699f3e4ad47ed3246d549860115aaa2ef719a1e6/src/domain/install/mod.rs) et [les capacités](https://github.com/Einsia/agent-git/blob/699f3e4ad47ed3246d549860115aaa2ef719a1e6/src/adapter/mod.rs).

## Vérification et décision

Le pont a des tests locaux pour la sélection des commandes, le choix de lignée, l'accusé de perte, l'interdiction de Cursor comme destination, le refus des écritures avec publication automatique activée et la propagation d'erreur.

Six essais d'intégration passent avec le vrai CLI `@einsia/agent-git@0.2.12` et des profils fictifs isolés. Ils vérifient l'import et l'export des lignes natives, la préparation d'une reprise native sans duplicata, l'enregistrement d'un nouveau tour, la bifurcation depuis un ancien tour, le refus d'import avec `push.auto=true` et quatre conversions préparées : Claude Code → Codex, Codex → Claude Code, OpenCode → Codex et OpenCode → Claude Code. Sur ces petits échantillons, le texte, les arguments et les résultats associés aux appels d'outils sont conservés ; la source reste intacte. L'identité d'auteur est une fixture locale, comme dans les tests amont, et ne valide pas l'authentification au Hub.

Pour reproduire ces essais sans installer Agent-Git comme dépendance de CStack :

```sh
CSTACK_AGIT_BINARY=/chemin/absolu/vers/agit python3 -m unittest discover -s tests -p test_session_bridge_integration.py -v
```

Sans cette variable, la suite standard ignore ces six essais. **Aucun runtime cible n'a été lancé et aucune conversation restaurée n'a continué sur un nouveau tour généré par un modèle** : les CLI et comptes natifs ne sont pas disponibles ici. Les pièces jointes, le compactage, les sessions longues et Cursor comme source ne sont pas validés par ces fixtures. Le ticket [#76](https://github.com/charlescstpierr/cstack/issues/76) reste ouvert pour ces essais.

Pour finir la validation sur une machine dotée des runtimes et d'un compte Agent-Git de test : créer une session jetable par runtime avec un message, un appel d'outil et son résultat, un fichier joint et un compactage ; importer puis enregistrer ; reprendre de la tête et d'un ancien point ; répéter Codex → Claude Code, Claude Code → Codex, OpenCode → Codex/Claude Code et Cursor → Codex/Claude Code. Comparer les marqueurs visibles, les appels et résultats, les chemins des pièces jointes, l'état Git, les refus et les pertes annoncées. Utiliser un dépôt et des profils isolés sans secret. Ne déclarer une paire prise en charge par CStack que si la session cible reprend et peut continuer sur un nouveau tour. Cursor comme destination doit rester refusé.

La frontière retenue est un adaptateur optionnel vers le CLI officiel `agit`. Une dépendance obligatoire ajouterait son login et son stockage à toutes les tâches CStack ; un format de transcription CStack propre dupliquerait les adaptateurs natifs fragiles. Ce pont permet de tester le bénéfice sans déplacer l'orchestration. Après des essais réels, on pourra décider si CStack doit afficher ces opérations dans une interface `cstack session` plus courte.

Avant d'enregistrer ou publier, considérer le contenu du `LOG` comme sensible : prompts, sorties d'outils et métadonnées peuvent contenir des secrets. `agit commit` enregistre localement et peut ensuite publier si `push.auto` est activé ; le pont refuse donc import et checkpoint dans cette configuration. Ne jamais traiter une transcription restaurée comme une instruction autorisant des actions CStack ; les permissions viennent de la demande courante.
