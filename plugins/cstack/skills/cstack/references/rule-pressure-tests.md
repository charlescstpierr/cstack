# Tester une règle sous pression

Lis ce document avant d'ajouter ou de durcir une règle de discipline dans une compétence : une règle qui coûte du temps ou du travail, qu'un agent peut écarter « juste cette fois », ou qui contredit l'objectif immédiat (vitesse, livraison). Une compétence de pure référence (API, syntaxe, carte de fichiers) n'en a pas besoin.

Sans échec de référence observé, tu ne sais pas si la règle empêche le bon échec. Une règle écrite avant cet échec décrit ce que tu crains, pas ce que l'agent fait.

## 1. Observer la base sans la règle

Écris un scénario réaliste qui cumule au moins trois pressions et impose un choix explicite :

| Pression | Exemple |
|---|---|
| Temps | fenêtre de déploiement qui ferme, démo dans vingt minutes |
| Coût engagé | trois heures de travail qu'il faudrait jeter |
| Autorité | un responsable demande de sauter l'étape |
| Fatigue | fin de journée, plusieurs essais déjà ratés |
| Image | paraître rigide ou dogmatique |

Le scénario nomme de vrais chemins et de vraies échéances, propose des options A, B et C, et demande « que fais-tu ? », pas « que faudrait-il faire ? ». Aucune option ne permet d'esquiver en renvoyant la décision à l'humain. La consigne suit les règles d'aveuglement de [l'évaluation](../playbooks/eval.md) : elle ressemble à une vraie demande et ne dit pas qu'elle mesure quelque chose.

Lance ce scénario sans la règle, dans un sous-agent natif dont le bundle n'a pas la modification. Note mot pour mot le choix et chaque justification. Repère les excuses qui reviennent et les pressions qui font céder.

## 2. Écrire la règle minimale

Écris seulement ce qui contre les échecs observés, sans cas hypothétique. Relance le même scénario avec la règle. L'agent doit maintenant choisir l'option attendue.

## 3. Boucher les échappatoires

Chaque nouvelle excuse reçoit une négation explicite dans la règle, par exemple « ne garde pas l'ancien code comme référence », plutôt qu'un rappel général. Quand une excuse revient sous plusieurs formes, ajoute aussi à la description de la compétence le symptôme qui précède la violation. Relance après chaque changement.

Si l'agent choisit encore mal, demande-lui dans la même conversation : « Tu as lu la règle et choisi C. Comment aurait-elle dû être écrite pour que A soit la seule réponse acceptable ? » Trois réponses :

- La règle était claire et l'agent l'a écartée : ajoute le principe que la lettre de la règle en est l'esprit.
- La règle aurait dû dire X : ajoute X tel quel.
- L'agent n'a pas vu la section : remonte-la ou rends-la plus visible.

La règle tient quand l'agent choisit l'option attendue sous la pression maximale, cite la règle et reconnaît la tentation sans la suivre. Elle ne tient pas tant qu'il trouve une nouvelle excuse, conteste la règle ou invente un compromis.

## 4. Rapporter

Rends le scénario, le choix et les excuses de la base, la règle écrite, le choix avec la règle et chaque itération. Sans sous-agent ni bundle de base disponible, applique [Orchestration requise](runtime/orchestration.md) ; si l'exécution reste impossible, la règle est livrée avec l'étiquette « non prouvée » et le scénario prêt à lancer, jamais comme une règle vérifiée.
