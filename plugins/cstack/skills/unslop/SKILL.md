---
name: unslop
description: "À utiliser pour $cstack:unslop afin de retirer les tics IA de la prose. S'applique à tout artefact de prose quand cstack est actif, et sinon sur demande."
---

# Unslop

Runtime : [règles communes](../cstack/references/runtime/base.md).

Modifie le texte pour retirer les motifs IA. `deslop` (`../deslop/SKILL.md`) nettoie le slop du code, `unslop` le nettoie de la prose, et `no-comments` confie les commentaires à un relecteur qui ne les a pas écrits.

## Processus

1. Cherche les motifs ci-dessous.
2. Réécris. Préserve le sens et respecte le ton voulu.
3. Auto-audit : "Qu'est-ce qui rend ceci évidemment généré par IA?" Corrige les tics restants.

## Motifs à détecter et corriger

Les numéros de règle sont des ID stables que d'autres skills citent. Une règle retirée laisse un trou.

### Contenu

3. **Formules superficielles en -ing.** "highlighting...", "ensuring...", "reflecting...", "showcasing...", "fostering...". Supprime ou développe avec de vraies sources.
5. **Attributions vagues.** "Les experts estiment", "les rapports du secteur suggèrent", "certains critiques affirment". Nomme la source ou supprime.

### Langage

7. **Vocabulaire IA.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstrait), pivotal, showcase, tapestry (abstrait), testament, underscore, vibrant. Remplace par des mots simples.
8. **Façons pompeuses de dire "is".** "serves as", "stands as", "boasts", "features". Dis simplement "is" ou "has".
9. **"Not just X, but Y."** Énonce plutôt le point directement.
10. **Règle de trois.** Forcer les idées en groupes de trois. Utilise le nombre naturel.
11. **Cycle de synonymes.** Protagoniste, personnage principal, figure centrale, héros dans un même paragraphe. Choisis-en un et répète-le.
12. **Fausses plages.** "from X to Y" quand X et Y ne sont pas sur une échelle significative. Liste les sujets directement.

### Style

13. **Abus de tirets cadratins.** Évite entièrement les tirets cadratins. Utilise seulement des points ou des virgules (pas de parenthèses, pas de tirets demi-cadratins, pas de substituts par trait d'union). Si une idée doit être séparée, termine la phrase ou utilise une virgule.
14. **Abus de deux-points.** Les deux-points vont bien avant une liste ou un exemple. Pas comme connecteurs en milieu de phrase. "Si tu viens de l'automatisation classique : au lieu d'enregistrer des gestionnaires d'événements, tu décris des conditions" ne gagne rien avec le deux-points. Réécris pour laisser le point tenir seul sans cadrage comparatif. "Décrire quand le scheduler doit se déclencher fonctionne mieux en langage simple."
15. **Abus du gras.** Ne mets pas chaque nom propre ou acronyme en gras.
16. **Listes à en-têtes inline.** Le tic est un libellé gras suivi de deux-points qui répète la ligne : "**Performance :** la performance s'améliore...". Convertis en prose. Une attaque en gras qui finit par un point, nomme l'élément et est suivie d'un détail vraiment nouveau ("**Schéma en TypeScript.** Les tables vivent dans un seul fichier.") est correcte, pas un tic.
17. **Titres en title case.** Utilise la casse de phrase.
18. **Emojis décoratifs.** Retire-les des titres et puces.
19. **Guillémets courbes.** Remplace-les par des guillémets droits.

### Artefacts de communication

20. **Phrases de chatbot.** "J'espère que cela aide!", "Dis-moi si...", "Bien sûr!", "Certainement!", "J'ai trouvé le smoking gun!" Supprime.
22. **Ton sycophante.** "Excellente question! Tu as absolument raison!" Réponds directement.

### Remplissage

23. **Phrases de remplissage.** En anglais, "In order to" devient "To". "Due to the fact that" devient "Because". "It is important to note that" est supprimé.
24. **Précautions excessives.** "on pourrait potentiellement possiblement soutenir que cela pourrait" devient "peut".
25. **Conclusions génériques.** "L'avenir s'annonce radieux." Énonce des plans ou faits précis.

### Jargon

26. **Noms-métaphores abstraits.** Substrate, wedge, vector, locus, vantage, nexus, primitive (comme nom), harness (comme métaphore), surface (dans "API surface"), bedrock, scaffolding (comme métaphore), modality, paradigm, gold-plating, ratchet (comme métaphore), evacuate (pour déplacer du code), endgame, north star, flywheel. Ils sonnent techniques mais ont habituellement un mot concret plus simple. "Substrate" devient "base". "Wedge in" devient "add". "Vector" devient "way" ou "method". "Gold-plating" devient "more than the job needs". "Ratchet" devient le vrai nom du mécanisme ou "a limit that only tightens". "Evacuate" devient "move out". "Endgame" devient "the last phase". Choisis le mot concret.

### Langage simple

27. **Dis ce que ça fait, pas l'effet que ça donne.** "la base de données reste à portée de main", "du SQL lisible", "des types qui suivent ton schéma" nomment un ressenti. Le correctif nomme le mécanisme ou un nombre : "`.toSQL()` retourne la chaîne exacte envoyée à la base de données", "un renommage de colonne fait échouer le build". Demande ce que la phrase dit au lecteur de faire ou savoir, puis écris cela. Si tu ne peux pas la reformuler comme instruction, fait ou nombre concret, coupe-la. Autre check : si la phrase pourrait apparaître inchangée dans les docs d'un autre projet, elle ne dit rien sur celui-ci. Coupe-la.
28. **Raccourcir ou scinder les phrases denses.** Si le lecteur doit revenir en arrière pour parser une phrase, casse-la en deux ou retire des propositions. Une idée par phrase.
29. **Voix active.** Préfère-la. Attrape "is/are/was/were + past participle" et nomme l'acteur : "les requêtes sont validées" devient "le compilateur valide les requêtes", "le fichier est parsé par le loader" devient "le loader parse le fichier". Le passif va bien seulement quand l'acteur est inconnu ou ne compte vraiment pas.
30. **Couper les adverbes, ou utiliser un verbe plus fort.** "runs quickly" devient "is fast" où le nombre. "améliore significativement" devient le delta mesuré. Un adverbe qui soutient un verbe faible signifie que le verbe est mauvais.
31. **Préférer le mot simple.** En anglais, "utilize" devient "use", "leverage" devient "use", "facilitate" devient "help", "numerous" devient "many", "in the event that" devient "if". Le synonyme plus chic est rarement plus clair.
32. **Prose affectée.** Métaphore ou effet là où une phrase littérale existe : aphorismes ("branche-le ou supprime-le"), fragments rhétoriques pour l'effet, code personnifié ("le plan le porte"), verbes figurés ("voyage avec", "se tient sur"), phrases de cadrage toutes faites. "Un cadran qui vaut d'être tourné" devient "un paramètre qui vaut d'être varié". Dis ce que tu veux dire. La règle 26 couvre les noms-métaphores.
33. **Surcompression.** Articles supprimés, fragments sans verbe, langage par symboles et abréviations qui font décoder au lecteur au lieu de lire. "Parser rejects bad date -> exit 2, no write" devient "Le parseur rejette une mauvaise date, sort avec le code 2 et n'écrit rien." Écris des phrases complètes avec leurs articles et verbes, et écris les flèches et abréviations en toutes lettres.
