# Bug bash

Lis ce document quand l'utilisateur demande un bug bash ou une exploration large d'une application qui a une skill de vérification. Un bug bash cherche des défauts que personne n'a encore décrits ; une passe d'entretien vérifie que la carte décrit encore l'application. Les deux utilisent le même harnais (Launch, Doctor, Drive, Preuve, Cleanup).

Le résultat est une liste de bugs confirmés, chacun avec un test de reproduction qui échoue aujourd'hui pour la raison rapportée. Tout le reste est rejeté avec la raison du rejet.

## 1. Préparer

- Lance l'application une fois selon la section Launch et vérifie-la avec Doctor. Si plusieurs explorateurs doivent piloter en même temps, chacun a sa propre instance ou un port libre ; une instance partagée par plusieurs explorateurs produit des faux bugs d'état. Quand la section Isolation de la skill dit que deux instances ne peuvent pas tourner côte à côte, les chartes passent en série sur l'instance unique, avec Doctor ou un retour à un état connu entre deux chartes.
- Vérifie que `.cstack/` est ignoré par Git (`git check-ignore -q .cstack/bugbash`). Sinon, crée `.cstack/.gitignore` contenant `*`, comme le fait le journal de décisions, avant d'y écrire quoi que ce soit.
- Donne à chaque charte son propre compte ou espace de données, créé avec les fixtures ou scripts d'amorçage du projet. Deux explorateurs sur le même compte se signalent mutuellement leurs modifications.
- Écris dans le contexte des explorateurs ce que l'environnement local ne sait pas faire (service externe sans clé, envoi de courriel, paiement) et ce qui ne doit jamais être déclenché. Ces limites produiraient sinon des constats qui ne disent rien du produit.
- Sur une instance partagée ou déployée que d'autres utilisent, l'exploration est en lecture seule : pas d'inscription, de soumission ni de rafale de requêtes.
- Les secrets passent par leur nom, selon la section Preuve ; aucune capture après la saisie d'un mot de passe.

## 2. Planifier les chartes

Une charte est une phrase : une zone, une posture, une route de départ et, si besoin, le compte à utiliser. Tire les zones de la carte des fonctionnalités et, pour une branche, de `git diff --stat` contre la base. Vise cinq à dix chartes.

| Posture | Ce que la charte demande |
| --- | --- |
| Premier usage | Parcourir l'inscription ou le premier lancement comme un nouvel utilisateur ; signaler ce qui est confus, cassé ou incohérent. |
| Chiffres et textes | Recouper chaque nombre, total, date et libellé avec les autres endroits où il apparaît. |
| Entrées limites | Soumettre chaque champ vide, trop long, en unicode et avec des espaces en tête ; la charte nomme la liste exacte des entrées. |
| État | Créer, renommer, supprimer, recharger et revenir en arrière ; signaler l'état perdu ou périmé. |
| Chemins d'erreur | Mauvais identifiant, ressource inconnue, droit manquant ; signaler les erreurs absentes, trompeuses ou trop bavardes. |

Une charte d'entrées limites sans liste d'entrées dépense son budget avant de juger un seul résultat.

## 3. Explorer en parallèle

Quand les instances sont indépendantes, applique [Swarm](../../swarm/SKILL.md) : une tranche par charte, avec son instance, son compte, son dossier de sortie sous `.cstack/bugbash/<slug>/` et le harnais de la skill. Avec une instance unique, pilote les chartes l'une après l'autre (étape 1). Chaque explorateur rend, par constat : la route, les étapes, l'attendu, l'observé, la preuve capturée et son verdict de pilotage.

Un explorateur bloqué le dit avec son code. Pour `auth`, `environnement` ou `données`, relance la charte une seule fois, et seulement si tu as corrigé la cause pendant la session (compte réamorcé, service redémarré). `budget`, `non pris en charge` et tout blocage sans remède immédiat restent des lacunes de couverture, rapportées à la fin sans nouvelle tentative.

## 4. Fusionner

Fusionne les constats qui décrivent le même défaut : même chemin, même comportement cassé. Garde la reproduction la plus claire et la liste des chartes qui l'ont trouvé. Sépare les remarques de finition sauf si l'utilisateur les a demandées.

## 5. Trier

Range chaque constat avant d'écrire le moindre test. Lis le code source pour trancher.

| Bac | Signe | Issue |
| --- | --- | --- |
| Artefact d'exploration | Le harnais ou l'explorateur a mal lu l'écran : lien ouvert dans un nouvel onglet, texte coupé que l'écran affiche entier, contenu chargé au défilement jamais atteint. | Rejeté, avec la vérification qui l'a montré. |
| Environnement | L'échec tient à une clé, un service ou une limite que seule la pile locale n'a pas. | Rejeté, en nommant la variable ou le service ; note à part une gestion d'erreur que de vrais utilisateurs verraient. |
| Conception voulue | Une spécification, la documentation pour l'utilisateur, un test existant ou une décision consignée (ADR, ticket) dit que le comportement est voulu. Le code testé ne prouve jamais sa propre intention. | Rejeté, en citant la source. |
| Données de départ | Les fixtures n'ont pas un champ que les vrais enregistrements ont toujours. | Rejeté, en nommant le champ. |
| Candidat | Aucun des cas précédents. | À vérifier (étape 6). |

## 6. Vérifier chaque candidat

Un constat d'explorateur est une affirmation ; prouve-la avant de la rapporter.

1. Relis l'observé contre la preuve capturée. Un constat que la preuve contredit est rejeté ici.
2. Écris un test de reproduction qui suit les étapes et affirme le comportement attendu : il échoue aujourd'hui et passera une fois le bug corrigé. Range-le sous `.cstack/bugbash/<slug>/` ; ne l'ajoute aux tests du projet que si l'utilisateur l'a autorisé.
3. Lance-le. Le bug est confirmé seulement si le test échoue **sur l'assertion visée**. Un sélecteur introuvable, un délai dépassé ou une erreur de mise en place signifient que le test est faux, pas que le bug existe : corrige le test et relance.
4. Quand tu peux lire le code, nomme la cause racine en `fichier:ligne`.

## 7. Rapporter

Rends les bugs confirmés, chacun avec sa reproduction, le chemin de son test, l'échec observé et la cause racine quand elle est connue. Rends ensuite les rejets par bac, en une ligne chacun. Ne modifie jamais le code produit pendant un bug bash ; les corrections sont un travail séparé. Nettoie les instances et comptes créés, en gardant les preuves et les tests de reproduction.
