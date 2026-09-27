---
name: technical-writing
description: "Standard de rédaction technique par couches : structure Diátaxis, phrases du style développeur Google, règles d'instructions STE, syntaxe Global English. Utiliser pour $cstack:technical-writing ou pour écrire ou relire docs, RFC, readmes, descriptions de PR ou messages de commit."
---

# Rédaction technique

Runtime : [règles communes](../cstack/references/runtime/base.md), [délégation](../cstack/references/runtime/delegation.md), [modèles](../cstack/references/runtime/modeles.md) · rôle : `documentation` pour déléguer un travail uniquement documentaire.

Le but est un texte qu'un ingénieur fatigué comprend à la première lecture. Quatre couches y mènent, avec une question chacune : quel type de document est-ce, comment les phrases s'adressent au lecteur, combien chaque phrase porte, et une phrase peut-elle être lue de deux façons. Applique les quatre.

Trois règles passent avant les couches :

- **Coupe chaque mot qui ne travaille pas.** Si la phrase survit sans un mot, le mot part. En anglais, "In order to" devient "to". "It is important to note that" ne sert à rien.
- **Utilise le mot court et ordinaire.** En anglais, "use", pas "utilize"; "help", pas "facilitate"; "do", pas "perform". Un mot long doit payer sa longueur par plus de précision.
- **Quand une règle rend une phrase moins bonne, corrige la phrase autrement ou laisse-la.** Les règles servent le lecteur. Une phrase qui suit toutes les règles et sonne comme écrite par une machine a échoué.

Le codebase est la liste de mots. Écris le vrai symbole, fichier, flag ou nom de commande, pas un synonyme ou une description.

N'invente pas de jargon. Utilise les mots qu'un développeur dirait à voix haute : "déplacer", "supprimer", "un budget qui ne fait que diminuer", pas "évacuer", "ratchet" ou "endgame". Un pattern nommé convient quand la doc dit ce qu'il signifie la première fois. Propose tout nouveau terme fautif et son remplacement comme ajout à la règle de métaphores abstraites de `unslop` dans ta réponse, avec le diff. Ne modifie pas cette skill.

## Varier le rythme

Les couches décident ce qu'un document dit et combien chaque phrase porte. Une doc peut leur obéir et quand même sembler écrite par une machine : chaque phrase coupée court, aucun point de vue, rien de spécifique.

- Mélange volontairement les longueurs de phrases. Les phrases courtes font atterrir un point. Les plus longues portent un fait avec sa condition ou sa conséquence.
- Une pensée par phrase ne signifie pas une seule longueur par phrase. Scinde la phrase qui porte deux pensées. Garde la phrase longue qui en porte une seule.
- Aie un point de vue quand le mode l'autorise. L'explication pèse les compromis; dis donc ce que tu en penses au lieu de lister seulement des avantages et inconvénients. La référence reste sèche.
- Préfère le spécifique au stérile. Pas "des changements de schéma peuvent causer des problèmes", mais "un renommage de colonne fait échouer le build".

## Choisir d'abord le mode (Diataxis)

Un document, un mode. Deux questions le choisissent : le contenu sert-il l'action (faire) ou la compréhension (penser), et sert-il l'apprentissage où le travail?

- Action + apprentissage : **tutoriel**.
- Action + travail : **guide pratique**.
- Compréhension + travail : **référence**.
- Compréhension + apprentissage : **explication**.

Utilise la boussole sur tout un document ou sur une seule phrase.

**Tutoriel : apprendre en faisant.** Tu es l'enseignant. La réussite de l'apprenant est ton travail, pas le sien. Ouvre en disant ce que l'apprenant construira, pas ce qu'il "apprendra". Chaque étape produit un résultat visible, tôt et souvent. Dis ce qu'il doit voir : sortie attendue, changement de prompt, ligne de log. Coupe l'explication à une proposition et un lien. Les pauses d'enseignement cassent la leçon. Reste concret. Écris en "nous", avec des commandes : "D'abord, fais x. Maintenant, fais y."

**Guide pratique : étapes vers un objectif.** Résous un problème qu'une personne a, pas une opération que la machine peut effectuer. Suppose la compétence. Saute l'enseignement. Action seulement : pas de digressions, pas de contexte, pas d'exhaustivité pour elle-même. Mets plutôt des liens. Autorise les embranchements et le jugement : "Si tu veux x, fais y." Nomme le guide par la tâche : "Comment calibrer le réseau radar", pas "calibration du réseau radar".

**Référence : faits pour consultation.** Décris. Seulement décris. Pas d'instruction, pas de persuasion, pas d'opinion. Sois sec, complet et certain. Énonce faits, options, limites et erreurs sans précautions molles. Miroite la structure de la chose décrite afin que code et docs se naviguent ensemble. Mets la matière là où les lecteurs l'attendent. Génère depuis le code quand c'est possible, pour rester vrai.

**Explication : compréhension et pourquoi.** Un sujet borné, lisible loin du produit. Chaque titre doit tolérer un "À propos de..." implicite devant lui. Ancre-toi sur une vraie question de pourquoi. Donne le contexte : décisions de conception, histoire, contraintes, alternatives. L'opinion est permise ici et nulle part ailleurs.

Ne mélange pas les modes : pas de tableaux de référence dans un tutoriel, pas de prise par la main de tutoriel dans une référence, pas d'argumentation dans un guide pratique. Sépare et lie plutôt.

Source : diataxis.fr, récupéré le 2026-07-18.

## Écrire des phrases pour le lecteur (style développeur Google)

- Parle au lecteur avec "tu", au présent. "Will" seulement pour les choses qui arriveront vraiment plus tard.
- Dis qui fait quoi : "le compilateur vérifie", pas "est vérifié". Le passif convient seulement quand l'acteur est inconnu ou hors sujet.
- Écris les instructions comme des commandes : "Clique sur Submit." Énonce les faits clairement. Jamais "should be done".
- Mets la condition avant l'instruction : "Pour supprimer le document, clique sur Delete." Le lecteur saute ce qui ne s'applique pas.
- Mets le cas courant d'abord. Les exceptions ensuite.
- Sonne comme un ami compétent. Pas de buzzwords, pas de langage figuré, pas de "please" dans les instructions, et jamais "simply", "easy" ou "quickly" dans une procédure. Si c'était simple, le lecteur ne serait pas là.
- N'annonce pas à l'avance ("nous prendrons bientôt en charge...") et ne commence pas deux phrases consécutives par la même formule.
- Lie avec des mots qui disent où le lien va : le titre de la page ou une courte description. Jamais "clique ici". Préfère une phrase de contexte sur la page à un lien hors de celle-ci.
- Les titres portent le point, pas seulement le sujet ("Choisir d'abord le mode", pas "Modes"). Casse de phrase. Un titre de tâche est un groupe verbal nu ("Créer une instance"). Un titre de concept est un groupe nominal. Un seul h1 par page, pas de niveaux sautés.
- Listes numérotées pour les séquences, puces pour le reste. Introduis une liste avec une phrase complète. Garde les éléments parallèles.
- Le code va en police code. Les éléments d'UI vont en gras. Utilise les virgules de série en anglais quand tu écris en anglais. Supprime "etc." et dis dès le départ qu'une liste est partielle.

Source : developers.google.com/style, récupéré le 2026-07-18.

## Charger une seule idée par phrase (règles STE)

- Une instruction par phrase. Une pensée par phrase ailleurs.
- Scinde les instructions de plus d'environ 20 mots et les autres phrases de plus d'environ 25.
- Mets l'avertissement ou la condition avant l'étape qu'il protège : "Si l'huile chaude touche ta peau, des blessures peuvent survenir."
- Garde "the" et "a" en anglais : "Remove backup file" se lit de deux façons. "Remove the backup file" se lit d'une seule.
- Donne à chaque mot un seul sens et un seul travail, puis garde-le. Si "check" signifie inspecter, ne l'utilise pas aussi pour retenir.
- Choisis un mot par action et tiens-t'y : "start", pas "start" ici et "initiate" la.
- Écris les procédures comme commandes directes, jamais comme narration et jamais au passif : "Installe le composant", pas "le composant doit être installé".
- Évite les mots en "-ing" quand tu peux. Ils prennent trop de fonctions grammaticales et créent des mauvaises lectures.

Source : asd-ste100.org (Issue 9, 2025), récupéré le 2026-07-18. Les règles numérotées et le dictionnaire vivent dans le PDF de spécification. Les principes ci-dessus sont le noyau transférable.

## Ne laisser aucune phrase ouverte à deux lectures (Global English)

- Garde les mots comme "only" et "not" près du mot qu'ils changent : "only fails on growth" et "fails only on growth" ne disent pas la même chose.
- Casse les longues chaînes nominales : "the proto import budget check script" devient "the script that checks the proto-import budget".
- Fais pointer chaque "it", "they" et "this" vers une seule chose évidente. Répète le nom en cas de doute. N'utilise jamais "this" ou "which" pour pointer vers toute une proposition.
- Ne supprime pas les verbes : "Phase 1 moves the converters and Phase 2 the runtime" laisse Phase 2 sans verbe. Donne-lui en un.
- Garde les petits mots qui montrent la structure. "Ensure that the switch is off" garde "that" parce qu'il force une seule lecture. N'échange jamais la clarté contre le nombre de mots.
- Répète l'article dans une série quand cela évite une mauvaise lecture : "the client and the host", pas "the client and host", quand ce sont deux choses.
- Dis quelles parties "and" ou "or" relient quand une phrase peut se grouper de deux façons. "Both...and", "either...or" et "if...then" sont des désambiguateurs gratuits.
- Utilise des points, pas des points-virgules. Remplace un tiret cadratin par une nouvelle phrase.
- Fais du texte entre parenthèses une unité grammaticale complète ou sa propre phrase. Ne forme jamais les pluriels avec "(s)".
- Pas de slashs : écris "a, b, or both" au lieu de "a/b" ou "and/or".
- Appelle chaque chose par un seul nom, partout. Une doc qui dit "la barrière", "le cliquet" et "le check de budget" pour une chose enseigne trois choses. Reformuler une phrase inchangée entre éditions coûte pareil. Ne churn pas ce qui n'a pas changé.
- Saute les idiomes, expressions familières, abréviations latines et métaphores. Un lecteur non natif, un traducteur et un agent parsant utilisent tous mieux les constructions simples.

Source : Kohl, The Global English Style Guide (SAS Press). Texte des consignes récupéré depuis Internet Archive et le chapitre exemple SAS, 2026-07-18.

## Voix et spécificités du dépôt

- Applique la skill **unslop** à chaque doc que cette skill touche. Cette skill possède le catalogue des signes de rédaction artificielle : vocabulaire IA, remplissage, précautions de langage et tics de formatage.
- Les descriptions de PR et messages de commit sont aussi de la rédaction. Toutes les couches sauf Diataxis s'y appliquent. Le corps d’une PR est un résumé qu'un relecteur peut lire en moins d'une minute. Ne colle pas les journaux de `swarm`, listes de SHA ou tableaux de métriques. Lie-les.
- Les textes de l’interface du produit ne sont pas de la documentation. Utilise les consignes de rédaction du produit pour elles.
- Indente les extraits de code avec des tabulations. Écris de vrais chemins et symboles. Rends chaque affirmation de compte ou d'arbre vraie au commit qui l'introduit, et inclus la commande qui la régénère.

## Exemple travaillé

Avant :

> La configuration des paramètres du script de budget du ratchet d'import de protos est effectuée via budget.json. Il est important de se rappeler que l'exécution avec --write, qui met à jour le budget enregistré dans Git pour refléter le compte actuel, ne doit être faite que lorsqu'on l'abaisse. En cas de dépassement, CI échoue.

Après :

> `budget.mjs` lit le budget enregistré dans Git depuis `budget.json` et compte les fichiers qui importent des protos. Si le compte dépasse le budget, CI échoue. Exécute `budget.mjs --write` seulement pour abaisser le budget.

## Liste de contrôle de revue

Applique-la à toute prose couverte par cette skill. L'élément 1 s'applique seulement aux ensembles de documents :

1. Chaque fichier a-t-il un seul mode Diátaxis, avec des liens là où les modes se rencontrent?
2. Chaque instruction est-elle écrite comme une commande, avec sa condition devant?
3. Une phrase porte-t-elle deux instructions ou deux pensées? Scinde-la.
4. Un mot peut-il être coupé sans perte de sens? Coupe-le.
5. "only" est-il près du mot qu'il change? Chaque "it" pointe-t-il vers une seule chose? Chaque proposition garde-t-elle son verbe?
6. Chaque chose a-t-elle exactement un nom dans toute la doc?
7. Un développeur dirait-il ces mots à voix haute? Remplace les métaphores inventées et synonymes chics par le mot simple ou le vrai nom du symbole.
8. Tous les symboles, chemins et comptes sont-ils réels à ce commit, avec les commandes qui régénèrent les nombres ?
