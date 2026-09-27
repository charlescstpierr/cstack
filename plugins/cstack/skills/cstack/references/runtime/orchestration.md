# Orchestration requise

Partie du [contrat d’exécution Codex](../codex-runtime.md), lue quand sa situation se présente.

Avant d'exécuter ou de déléguer le travail qui en dépend, le coordinateur lit et applique le parcours d'orchestration requis. Deux zones de couverture indépendantes ou plus passent par Swarm. Plusieurs solutions valides concurrentes passent par Arena. Si les emplacements sont temporairement occupés, le coordinateur attend leur libération et lance chaque position dans un acteur distinct, par vagues si nécessaire. Cette exécution séquentielle peut satisfaire l'indépendance ; elle ne consiste pas à rejouer les positions dans une même session.

Un délégué qui reçoit une tranche déjà cadrée de candidat, de couverture, de revue ou de vérification exécute cette tranche normalement et ne recrée pas Arena ou Swarm. Un délégué qui découvre qu'une orchestration requise est encore en amont, et qui n'a pas reçu l'autorité explicite de la lancer, retourne `BLOCKED` avant d'exécuter le code ou la revue dépendante. Le rapport nomme `route: Arena|Swarm|Review`, les tranches ou candidats requis, les chemins d'artefacts proposés et les critères d'acceptation. Ce retour transmet les faits et critères, sans choisir de solution gagnante. Le coordinateur qui le reçoit lance la route demandée puis distribue des tranches bornées ; il ne renvoie pas la même orchestration à une feuille incapable de la lancer.

Une restriction locale de descendants conserve le retour `BLOCKED` au parent. À la racine sans parent, l'absence constatée d'outil de lancement natif ou un plafond déclaré de zéro permet des passes personnelles séparées avec l'étiquette `single-agent` et le statut `ISSUES`, en nommant l'indépendance manquante. Des places occupées ne sont pas une absence d'outil. Ce repli ne remplace jamais une sélection explicite de modèle ou de runtime refusée, qui reste bloquée.

Une interdiction explicite de délégation pour la demande entière, fixée par l'utilisateur ou une consigne supérieure, prime sur ce parcours : exécute le travail autorisé seul, étiquette `single-agent` et utilise `ISSUES` dans un rapport structuré en nommant l'indépendance manquante. Dans ces deux cas dégradés, l'ouverture d'une PR reste possible dans la portée de livraison autorisée, avec cette limite dans sa description ; ne prétends pas à une revue indépendante ni à un verdict de merge fondé sur elle. Cette exception ne couvre ni une feuille sans descendants ni des emplacements temporairement occupés.

Pour ce retour de blocage, le rapport structuré décrit le workflow demandé au complet, pas la sous-étape de préparation. N'écris pas "préparation terminée" quand le travail demandé reste bloqué. Utilise seulement les champs du schéma worker :

```json
{
  "status": "BLOCKED",
  "summary": "Workflow demandé bloqué: orchestration requise non lancée.",
  "checks": [],
  "findings": [
    "route: Arena|Swarm|Review",
    "scopes: <tranches ou candidats requis>",
    "artifact outputs: <chemins proposés>",
    "acceptance: <critères pour débloquer le workflow>"
  ]
}
```
