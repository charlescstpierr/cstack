---
name: recall
description: "À utiliser pour $cstack:recall, « retrouve mon travail sur X », « remets-moi à niveau », « sur quoi ai-je travaillé » ou « où en étais-je ». Reconstruit l'historique récent des tâches bornées au projet, l'état live et les preuves connectées en une capsule serrée de l'état courant."
---

# Recall

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md), [orchestration](../cstack/references/runtime/orchestration.md), [intégrations](../cstack/references/runtime/integrations.md).

**Avant de commencer ou reprendre le travail, tu reconstruis le contexte de travail récent de l'utilisateur et rends une capsule serrée de l'état actuel et de la prochaine chose à faire.**

Reste serre et dans le sujet. Lis seulement ce dont les fils dans la portée ont besoin, puis arrête.

Le contexte vit dans deux registres. L'historique des tâches bornées au projet contient ce que les agents précédents ont fait et décidé. Le registre partagé contient les symptômes, correctifs livrés ou revertés, et l'état externe courant. La skill `$cstack:why` cherche dans ce second registre via les outils de source control et de preuves connectées disponibles.

Préfère les outils natifs d'historique de tâches bornées au projet actif. S'ils sont indisponibles, utilise le contexte de la tâche courante et les checkpoints sauvegardés. Lis une transcription locale seulement quand ses propres métadonnées correspondent explicitement au projet et à la session demandés; n'infère jamais et ne scanne jamais un chemin de transcription global.

1. Classe, puis route. Une tâche précèdente spécifique à reprendre releve du playbook `session-pickup`, pas de celui-ci. Transformer des habitudes en skill durable releve de `$cstack:automate-me`. Si l'utilisateur t'a déjà donne une capsule d'état complète, utilise-la et saute l'extraction.
2. Verrouille la portée avant de chercher. Fixe la fenêtre ("récent" est une vraie plage, par défaut les 7 derniers jours), le sujet s'il est nommé, et le workspace (par défaut l'actif. Ne lis jamais les transcriptions d'un autre projet sans demandé). Reformule la portée. Ne transforme jamais silencieusement "all" en "récent N".
3. Déploie sur l'historique des tâches bornées au projet quand le corpus est assez grand. Cherche d'abord le sujet, lis seulement les tâches correspondantes et régions pertinentes, et saute la tâche active ainsi que le bruit évident de sous-agent, évaluation et test. Chaque extraction rend d'abord un index, une ligne par tâche : ID de tâche natif, date et sujet en une ligne. Choisis dans cet index les tâches qui servent la portée, puis développe seulement celles-ci selon le même schéma, un bloc par tâche : sujet, objectif utilisateur, décisions, fils ouverts, difficultés et corrections, et artefacts, en citant l'ID de tâche natif. Exclus les passages `<private>` selon [l'état](../cstack/references/runtime/etat.md). Pour une ou deux tâches, cherche directement. Ne saute pas le balayage d'historique parce qu'un sous-agent manque.
4. Balaie le registre partagé quand le sujet nomme une fonctionnalité, un fichier, un sous-système, une zone ou un bug. Remets-le à `$cstack:why`, en orientant la question vers l'état courant, les tentatives échouées et les rapports ouverts. Utilise seulement les sources connectées disponibles, consigne les manques, et exécute des investigations source indépendantes en parallèle avec l'extraction d'historique de tâches. Saute ceci pour un simple rappel d'activité sans cible nommée.
5. Vérifie contre l'état live. Prends les PR, branches et tickets que l'extraction et le balayage ont fait remonter, puis vérifie-les avec `git` et `gh`. Quand la réponse dépend de ce qu'un agent a vraiment fait (outils exécutés, fichiers lus, erreurs rencontrées), lis la transcription complète, pas seulement une copie locale réduite.
6. Écris le brief selon le contrat ci-dessous. Groupe par fil. Reste sur le sujet nommé.

## Contrat de sortie

Commence par la capsule, puis l'état des fils, puis les problèmes, puis la prochaine action. Les détails plus profonds vont plus bas ou sont coupes.

- **Capsule.** Au plus 5 puces. Ce qu'est ce travail et ou il en est globalement.
- **Fils.** Une ligne chacun, préfixée par exactement une étiquette d'état : `[merged #N]`, `[open PR #N]`, `[in flight <branch>]`, `[verified, uncommitted]`, `[reverted #N]` ou `[planned, not started]`. Un fil sans étiquette n'est pas encore termine, donc étiquette-le.
- **Problèmes.** Au plus 5, les récurrents. Inclus les symptômes que les utilisateurs continuent de signaler et tout correctif livré puis revert, pour que la prochaine tentative commence là où la dernière a échoué.
- **Prochaine action.** La seule prochaine action la plus utile, concrète.

Une fonctionnalité ou un ticket adjacent reste dehors sauf s'il bloque celui-ci. Quand la capsule et les lignes de fil dépassent un écran, coupe les détails avant les fils. Passe le brief par `$cstack:unslop`, cite les constats de tâche par ID de tâche natif et les constats du registre partagé par source, puis assainis le contexte privé avant toute sortie publique.

**Réponse :** le brief, selon le contrat ci-dessus.
