---
name: clarify
description: "À utiliser quand $cstack:clarify est sélectionné explicitement ou routé pendant une tâche cstack explicite. Résout les ambiguïtés d'alignement ou d'exigences avec les faits du dépôt et des tours de décision sur la frontière."
---

# Clarifier

Runtime : [règles communes](../cstack/references/runtime/base.md), [activation](../cstack/references/runtime/activation.md), [exploration](../cstack/references/runtime/exploration.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md) · rôles : `how explorer` (explorateurs), `judgment and prose` (synthèse).

Utilise cette skill quand l'utilisateur sélectionne explicitement `$cstack:clarify`, ou quand le coordinateur cstack actif ou ses skills de préparation routent ici. Ne l'active pas hors d'une tâche cstack ou demande de préparation explicitement sélectionnée. Une trace d'ambiguïté suffit : utilise-la s'il reste deux lectures raisonnables du résultat, du périmètre, du comportement ou de l'acceptation après avoir établi les faits. Si tu ne peux pas dire ce que tu livreras sans choisir une hypothèse à la place de l'utilisateur, route ici. Une demande courte ou un terme familier ne justifie pas à lui seul une question quand le dépôt et la conversation donnent une seule lecture ; si un fait ou une courte expérience tranche l'incertitude, fais-le et retourne au flux de travail de l'appelant.

## Trouver les faits avant de demander

Sépare les faits découvrables des décisions humaines avant de formuler les questions.

- Lis la demande, les fichiers courants, les consignes de projet, le mode et l'autorisation.
- Établis toi-même les faits du dépôt, en réutilisant [`$cstack:how`](../how/SKILL.md) pour les questions de flux de code et de responsabilité. Marque une inférence comme inférence et garde-la séparée du comportement observé.
- Si des faits indépendants gagnent une couverture séparée en lecture seule, applique le [contrat d’exploration déléguée](../cstack/references/runtime/exploration.md). Sinon, établis les faits directement dans le parent.
- Ne demande jamais à l'utilisateur un fait que le dépôt où les outils exposés peuvent établir. N'invente jamais un fait, ne réponds jamais à une décision métier matérielle et ne transforme jamais une recommandation en décision.

Le défaut est zéro agent supplémentaire. Si une passe séparée de recommandation ou de synthèse est vraiment utile, utilise le rôle `judgment and prose`. Ne crée pas de nouveau rôle ou panel.

## Interroger la frontière courante

Cartographie les décisions non tranchées et leurs prérequis. La **frontière** contient chaque décision dont les prérequis sont règles. Pose toute la frontière courante en un tour; reporte au prochain tour toute question qui dépend d'une autre réponse.

Quand l'entrée utilisateur structurée est disponible, utilise-la. Sinon, utilise cette forme compacte :

```text
Q1 : <décision> : <une décision, avec les options ou la contrainte pertinente>

Recommandation : <le choix le mieux étayé et pourquoi il correspond à l'objectif énoncé>
```

Numerote les questions et inclus une recommandation pour chacune. Les recommandations sont des propositions que l'utilisateur peut accepter, rejetér ou réviser. L'utilisateur possède la direction produit et les décisions métier matérielles. Une réponse "I don't know" garde la décision ouverte; ce n'est pas une permission de deviner.

Après chaque réponse, marque ce qui est tranché, recalcule la frontière et pose seulement les questions nouvellement débloquées. Continue jusqu'à ce que la frontière soit vide ou nomme la décision concrète non résolue qui bloque le progrès. Ne répète pas une question tranchée et ne redemande pas d'approbation quand les décisions de l'utilisateur et l'autorité d'implémentation couvrent déjà la prochaine étape réversible.

## Finir proprement

Quand la clarification se termine, retourne à l'appelant un registre tranché concis : décisions, contraintes étayées par des preuves, éléments non résolus et prochaine action recommandée.

- Si l'implémentation est autorisée et que les exigences sont tranchées, continue ou retourne au flux de travail de l'appelant sans autre portail d'approbation.
- Quand le routage vient de `$cstack:cstack`, ne demande pas "continue?". Rends le registre tranché pour que le coordinateur puisse choisir le playbook existant approprié et continuer à travailler dans l'autorisation déjà donnée par l'utilisateur.
- En mode Plan, pour du travail en lecture seule ou pour du travail uniquement design, retourne le brouillon dans le chat et ne modifie ni code ni documents.
- Clarify ne crée lui-même aucun objectif, tracker, PR, message ou changement d'implémentation. Après réception du registre tranché, l'appelant peut continuer son flux de travail déjà autorisé. Le vocabulaire durable et les registres ADR appartiennent à [`$cstack:domain`](../domain/SKILL.md), sous réserve des règles d'écriture de cette skill.
