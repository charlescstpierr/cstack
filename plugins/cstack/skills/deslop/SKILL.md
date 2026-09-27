---
name: deslop
description: "À utiliser pour $cstack:deslop, « deslop it », « clean this diff », et comme passe pré-commit requise dans chaque playbook d'implémentation cstack. Retire le slop d'un diff de code avant commit ou revue. Utilise $cstack:unslop pour la prose et $cstack:no-comments pour une revue déléguée des commentaires."
---

# Deslop

Runtime : [règles communes](../cstack/references/runtime/base.md).

Le slop est du code qui survit à la revue parce que personne ne peut pointer la ligne fausse. Ce n'est pas une question de style. Les commentaires narratifs et le poids mort défensif donnent une impression d'inachevé, et le code en trop est l'endroit où se cache le prochain bug.

Trois nettoyages, trois cibles. `deslop` nettoie le code. [`unslop`](../unslop/SKILL.md) nettoie la prose. [`no-comments`](../no-comments/SKILL.md) confie les commentaires à un relecteur qui ne les a pas écrits.

Deslop s'exécute sur **le diff**, jamais sur le dépôt. Il retire du poids. Il ne change jamais le comportement.

## Quand il s'exécute

- Avant chaque commit d'un changement d'implémentation ou de documentation autorisé.
- Avant de remettre un diff à un relecteur, une PR ou une voie de vérification.
- Sur demande : `$cstack:deslop`, "deslop it", "nettoie ce diff".

Un playbook qui le saute conserve `deslop skipped: <reason>` dans son plan et sa réponse. Aucun saut silencieux.

## Borner la portée

1. Liste les chemins modifiés par la tâche elle-même. Utilise `git diff --stat` contre la base, ou `git diff --stat --cached` pour le travail stagé. N'élargis jamais aux fichiers que la tâche n'a pas touchés.
2. Lis en entier chaque hunk ajouté et modifié. Un hunk que tu n'as pas lu n'est pas desloped.
3. Préserve exactement les changements préexistants sans rapport, et dis-le dans le rapport.

## Le catalogue du slop

Classe chaque ligne ajoutée comme porteuse, slop ou incertaine. Supprime le slop. Garde les lignes incertaines et nomme chacune dans le rapport.

**Commentaires narratifs.** Un commentaire qui répète la ligne suivante, étiquette un bloc évident ou annonce une section. Supprime. Garde un commentaire seulement pour une raison non évidente que le code ne peut pas exprimer, ainsi que pour les licences, contrats publics, justifications d’accessibilité et contraintes d’outil vérifiées.

**Gardes non étayées.** Un null check, `try`/`catch`, défaut ou retour anticipé pour un état que les types, les sites d'appel ou un invariant excluent déjà. Supprime la garde et laisse le vrai contrat tenir. Garde-la quand un appelant hors du module peut vraiment produire cet état, et nomme l'appelant.

**Chemins de compatibilité morts.** Un fallback pour une forme qui n'existe plus, un alias gardé "for safety", une branche pour une version que le projet à abandonnée, un re-export laissé par une migration. Supprime, puis migre les appelants restants dans le même changement. Une demi-migration est du slop avec une échéance.

**Erreurs avalées.** Un `catch` qui logue puis continue, un `except` nu, une erreur convertie en valeur par défaut. Gère l'échec ou laisse-le se propager. Garde un avalement seulement quand le contrat environnant documente un comportement best-effort.

**Generalite spéculative.** Un paramètre, une option, un hook, une stratégie ou un flag de config avec un seul appelant et aucun second en vue. Une interface avec une seule implémentation. Une factory qui construit une seule chose. Inline.

**Cérémonie.** Un wrapper qui transmet ses arguments sans changement, un barrel file ajouté pour un seul symbole, une constante utilisée une seule fois près de sa définition, une variable qui existe seulement pour être retournée.

**Logique dupliquée.** Le même calcul colle à un second endroit au lieu d'être appele. Appelle-le. Quand les deux copies divergent vraiment, dis pourquoi dans le rapport au lieu d'extraire une abstraction partagée qui ne convient à aucune.

**État redondant.** Une valeur stockée dérivable d'un autre état, une paire de booléens qui encode une machine à états, un cache sans chemin d'invalidation. Derive-la, ou modélise les états.

**Résidus de placeholder.** `TODO`, `FIXME`, "implement later", code commenté, retour mock, stub qui retourne une constante plausible, logs de debug, fichier scratch. Termine-le dans la portée autorisée ou supprime-le et consigne le suivi dans la réponse. Ne livre jamais un placeholder comme s'il était la fonctionnalité.

**Éditions sans rapport.** Reformatage, réordonnancement d'imports, churn de renommage ou correction opportuniste hors de l'objet de la tâche. Revert ces hunks. Une vraie amélioration trouvée va dans la réponse comme suivi, pas dans ce diff.

**Rembourrage de tests.** Un test qui asserte un défaut, une copie de champ, un appel de transfert, un mock qui répète sa propre entrée, un simple "does not throw", ou une ligne de paramètre qui parcourt le même chemin que la ligne au-dessus. Supprime. Un test mérite sa place seulement quand un bug plausible le ferait échouer.

**Noms trompeurs.** `data`, `utils`, `helper`, `manager`, `temp`, `newThing`, `handleX` pour quelque chose qui n'est pas un handler. Renomme selon ce qu'est la valeur ou ce que fait la fonction. Renommer un symbole qui traverse la frontière du module est un changement public : fais-le seulement dans la portée autorisée et migre chaque appelant.

**Documentation inventée.** Une ligne de doc, une entrée de changelog ou un commentaire qui décrit un comportement que le diff n'implémente pas, ou une mesure que personne n'a prise. Supprime-la ou remplace-la par l'affirmation que tu peux vraiment soutenir.

## Prouver que c'était du poids

Deslop préserve le comportement par construction, donc il est verifiable.

1. Exécute la même vérification qui couvrait déjà le changement : le test, la commande ou la sonde d’exécution nommée par le playbook.
2. Une vérification qui passe d'un succès à un échec signifie qu'une ligne supprimée était porteuse. Restaure exactement cette ligne et reclasse-la. Ne "corrige" pas la vérification.
3. Quand aucune vérification ne couvre une ligne supprimée, dis-le dans le rapport. Une suppression non testée est une affirmation, pas une preuve.

## Interdit

- Changer le comportement, la sortie, les signatures publiques ou la sémantique d'erreur.
- Toucher des fichiers hors des chemins modifiés par la tâche.
- Supprimer licences, en-têtes de copyright, justifications d'accessibilité, notes de sécurité ou un commentaire qui consigne une contrainte d'outil ou de plateforme vérifiée.
- Extraire une nouvelle abstraction. Deslop ne fait que soustraire.
- Reécrire le travail non commit de quelqu'un d'autre.
- Declarer la passe terminée sans relancer la vérification propre au changement.

## Réponse

Un tableau plus les restes.

| catégorie | file:line | retire | pourquoi c'était du poids |
|---|---|---|---|

Puis :

- Lignes gardees comme incertaines, avec la raison pour laquelle chacune pourrait être porteuse.
- Suppressions qu'aucune vérification ne couvre.
- Suivis trouves mais volontairement exclus de ce diff.
- La commande de vérification relancee après la passe, et son résultat.
- `deslop skipped: <reason>` quand une étape de playbook n'a pas pu l'exécuter.
