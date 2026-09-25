# Audit de l’autonomie de cstack

Ce document relève ce qui empêche cstack de fonctionner sans humain présent. Il enregistre des constats et une direction, pas des corrections appliquées : aucun skill, playbook ni helper n’est modifié par ce travail. Le suivi est dans #57 et ses sous-tickets.

## Autonome pendant la session, pas en l’absence de l’utilisateur

cstack sait enchaîner les phases d’une tâche sans demander d’approbation à chaque transition, et le playbook `autonomous-run` avance jusqu’à un prédicat vérifiable. Cette autonomie suppose toutefois une session ouverte et un humain qui a autorisé la tâche dans la conversation courante. La plupart des obstacles ci-dessous sont des protections volontaires et bien justifiées ; c’est leur combinaison qui interdit un fonctionnement sans surveillance.

## Constats

Les numéros de ligne renvoient à `plugins/cstack/skills/cstack/references/codex-runtime.md`, sauf mention contraire.

| # | Constat | Source | Pourquoi ça bloque l’autonomie | Ticket |
| --- | --- | --- | --- | --- |
| 1 | « La session doit rester active ; aucune reprise après fermeture n’est garantie. » Ni scheduler ni daemon. | l. 44, 136 | Fermer Codex arrête le travail. L’intake tourne hors session mais ne fait que trier et reproduire. | #61 |
| 2 | L’autorité vient seulement de la conversation courante ; un point de reprise est « un pointeur à reconfirmer, jamais un accord » ; « continue » seul n’autorise pas le Goal. | l. 40, 120 | Une reprise sans humain ne peut ni pousser, ni ouvrir de PR, ni relancer le Goal. | #58 |
| 3 | Les sous-agents partent seulement quand le tour utilisateur demande la délégation. | l. 164, `docs/evidence/0.3.0.json` | En autonomie, les tours suivants ne viennent pas d’un humain : le travail retombe en `single-agent` sans revue indépendante. | #61 |
| 4 | 35 occurrences de « bloque » dans `skills/cstack` ; `clarify` interdit de choisir la lecture la plus probable ; un effort de modèle inexprimable demande une sélection à l’utilisateur. | l. 70, 112 ; `SKILL.md` l. 24 | Chaque règle est défendable, mais aucune hiérarchie ne dit quand décider seul. Le principe « Ne jamais bloquer sur l’humain » est contredit localement. | #59 |
| 5 | Le résultat par défaut est une PR prête pour revue ; merge et déploiement exigent une autorisation explicite. | l. 44 | Les PR s’accumulent ; l’humain reste le goulot. | #62 |
| 6 | La rigueur est surtout écrite en prose ; les barrières exécutées sont rares (head SHA de `watch-pr`, ledger `orch`, `check-plan.mjs`, `compare-checks.py`). | ensemble du paquet | Sans relecteur, une preuve affirmée mais non exécutée passe, et les erreurs se cumulent. | #56 |
| 7 | « N’ajoute un budget que si l’utilisateur en a demandé un » ; « Un plateau n’est pas un arrêt ». | `playbooks/autonomous-run.md` | Une impasse sans surveillance peut consommer des tokens toute une nuit ; seul le modèle juge d’une impasse. | #63 |
| 8 | Environ 8 000 mots (`SKILL.md` et contrat) lus avant chaque tâche, plus le playbook ; l’état d’avancement est rédigé par le modèle. | `SKILL.md`, `codex-runtime.md` | Une session longue se compacte et dilue les règles dont dépend la reprise. | #60 |
| 9 | Le travail vient du message de l’utilisateur ; `horizon` enchaîne des tickets seulement à l’intérieur d’un objectif. | `SKILL.md` | Rien ne prend le ticket suivant. | #61 |
| 10 | Blocages et résultats sont signalés dans la conversation. | — | Personne n’est prévenu d’un blocage nocturne. | #58 |
| 11 | Chaque appel d’assistant fait un `bun install` qui a besoin du registre ou d’un cache ; des échecs de sandbox ont été observés (`apply-seccomp`, `bwrap`, `ptrace`) ; une seule relance automatique. | `README.md`, l. 34, PR 43 | Une panne réseau ou de sandbox arrête le travail sans personne pour relancer. | #61 |
| 12 | Les essais natifs sont des observations uniques ; aucune mesure contrôlée du taux de résolution. | `docs/VERIFICATION.md` | Élargir l’autonomie sans taux de réussite connu revient à prendre un risque non chiffré. | [banc de résultat](OUTCOME-BENCH.md) |

## Direction

Ne pas retirer les protections. Remplacer « demander à l’humain » par une **politique d’autonomie** écrite une fois par l’utilisateur, stockée hors du dépôt, non modifiable par l’agent, et **appliquée par des helpers** plutôt que par de la prose :

1. politique durable : autorité, actions permises, budget, notifications (#58) ;
2. table de décision des blocages, avec des défauts réversibles « décider, noter, continuer » (#59) ;
3. gates mécaniques (#56) et état des étapes résistant à la compaction (#60) ;
4. budget et sortie de boucle mesurée (#63) ;
5. runner hors session qui généralise `automations/intake`, injecte la délégation à chaque tour et fige ses dépendances (#61) ;
6. mesure avec le banc de résultat ;
7. merge par classe de risque, en dernier parce qu’il est irréversible côté dépôt (#62).

## Invariants

- L’autorité ne vient jamais d’un fichier du workspace, d’un ticket, d’un commentaire ou d’un rapport de délégué.
- Aucune action externe hors politique ; une preuve manquante échoue fermée.
- Pas de moteur d’orchestration séparé : le runner réutilise `codex exec` et l’intake existant.
- Pas de modification du cache de plugin, de la configuration globale ou des modèles de l’utilisateur comme effet de bord.

## Limites

Cet audit lit les sources au commit `f9a5b12` ; il n’a exécuté aucun tour Codex natif. Les comptes d’occurrences sont des indices de densité, pas une mesure du comportement. Chaque sous-ticket doit démontrer son gain, conformément à `docs/ISSUE-VALUE-AUDIT.md`.
