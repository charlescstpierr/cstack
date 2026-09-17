# Épistémique

Comment raisonner sur la confiance quand les preuves sont historiques, fragmentaires et parfois contradictoires, et comment la communiquer sans l'aplatir en fausse certitude.

Le code ne porte pas sa propre motivation. Tu peux lire ce que le code fait. Tu ne peux pas lire *pourquoi il existe*. Cela vit dans les commits, PR, tickets, docs et conversations, tous incomplets, biaisés et parfois entièrement manquants. Faire semblant du contraire produit des suppositions qui semblent confiantes et induisent l'utilisateur en erreur.

## Niveaux de confiance

Chaque affirmation dans la sortie finale doit appartenir à l'un de ces niveaux. Le niveau détermine dans quelle section l'affirmation va et comment elle est formulée.

### 1. Directe

Une citation textuelle explicite qui répond à la question. Pas "le code fait X donc l'auteur a dû vouloir X". Quelque chose qu'un auteur a réellement *écrit* et qui dit pourquoi.

Exemples :
- Une description de PR qui dit "ceci corrige le bug où les utilisateurs avec plus de 1000 éléments ne pouvaient pas paginer"
- Un ticket qui dit "nous ajoutons ceci parce que le client Acme l'a demandé dans sa revue de sécurité"
- Un commentaire de code qui dit "// borner à 100 parce que l'API amont rejette les valeurs plus grandes"
- Un doc de conception qui dit "nous avons choisi l'option A plutôt que l'option B parce qu'il nous faut une persistance entre redémarrages"
- Un message de chat de l'auteur disant "nous passons à cette approche car l'ancienne était flaky dans les tests"

Formulation : confiante, présent. "Ceci existe parce que X." Cite la source.

### 2. Soutenue

Plusieurs preuves indirectes convergent. Aucune source ne le dit explicitement seule, mais le motif entre sources le rend probable.

Exemples :
- Le titre de PR dit "améliorer les performances", le ticket est étiqueté "perf" et les commits voisins touchent tous le même hot path
- Plusieurs tests ont été ajoutés avec le changement, tous exerçant des cas limites à très grandes entrées
- Les autres PR de l'auteur la même semaine mentionnent toutes le même incident dans leurs descriptions

Formulation : confiante mais clairement dérivée. "Les preuves pointent fortement vers X : [les pièces précises]." Cite plusieurs sources.

### 3. Inférée

Une lecture raisonnable du contexte, mais rien ne la soutient explicitement. Le lecteur doit comprendre que c'est *ton interprétation*, pas un fait du dossier.

Exemples :
- La PR ne dit pas pourquoi, mais vu que l'erreur arrivait en production (selon le timing du channel incident) et que le fix a été merge le même jour, c'était probablement un hotfix.
- Le nom de fonction suggère une logique de retry. Le nombre de retries est 3. Cela correspond à la convention générale de l'équipe "3 retries" observée ailleurs dans le codebase.

Formulation : nuancée. "Il semble", "probablement", "suggère", "est cohérent avec", "une lecture est". Rends la chaîne d'inférence explicite : "Vu A et B, C semble probable parce que D."

### 4. Spéculative

Une hypothèse plausible, mais les preuves sont minces et d'autres explications conviennent aussi bien. Les présenter est utile, mais marque-les clairement comme suppositions.

Exemples :
- "Cela pourrait être un workaround pour un bug navigateur corrigé depuis, mais nous n'avons trouvé aucune preuve contemporaine."
- "Il est possible que ce seuil ait été choisi pour correspondre à un engagement SLA, mais aucun doc SLA ne le référence."

Formulation : explicitement spéculative. "Une possibilité est X, mais nous n'avons pas de preuve directe." Vit généralement dans la section "Hypothèses concurrentes" avec d'autres possibilités.

### 5. Inconnue

Tu as cherché et tu n'as pas trouvé. C'est un résultat valide et important. Documente-le.

Formulation : "Nous avons cherché X, Y et Z et trouvé aucune preuve du pourquoi." Sois précis sur *ce que* tu as cherché. "Nous n'avons pas pu trouver" est moins utile que "nous avons cherché dans le tracker avec les mots-clés A et B, scanné les 6 PR qui ont touché ce fichier depuis 2023, et grep le dépôt pour les littéraux correspondant au seuil. Rien n'a fait émerger de justification."

## Guide de formulation

### Mots qui portent de la confiance. À utiliser prudemment

Ceux-ci impliquent une confiance **Directe** ou **Soutenue**. Ne les utilise pas pour des inférences.

- "parce que". Implique une causalité prouvée
- "la raison est". Même chose
- "a été conçu pour". Revendique l'intention de l'auteur
- "corrige", "traite", "résout". Revendique que le changement a atteint son objectif
- "l'équipe a décidé". Revendique une décision de groupe

Si tu les utilises, il faut une citation immédiatement adjacente.

### Mots de nuance. À utiliser pour les inférences

- "semble"
- "paraît"
- "probablement"
- "suggère"
- "est cohérent avec"
- "une lecture est"
- "plausiblement"
- "a pu être"
- "les preuves pointent vers"

Ils signalent que tu interprètes, pas que tu rapportes. Utilise-les largement dans la section "Ce que nous pouvons raisonnablement inférer".

### Mots à éviter

- "évidemment". Si c'était évident, l'utilisateur ne demanderait pas
- "clairement". Précède presque toujours une affirmation qui n'est pas claire
- "bien sûr". Même chose
- "simplement" (comme dans "it's just X for performance"). Dismissif et cache souvent l'incertitude
- "je pense" / "je crois". Tu synthétises des preuves, tu ne donnes pas une opinion personnelle. Utilise plutôt "the evidence suggests".

### Éviter la rationalisation

Un code qui "a du sens" aujourd'hui a pu être écrit pour des raisons qui ne s'appliquent plus, ou qui étaient fausses au moment de l'écriture. Ne greffe pas une justification propre sur une histoire désordonnée.

Résiste à l'envie de :
- Supposer que l'auteur a fait la "bonne" chose et reconstruire une justification à rebours
- Supposer qu'un motif cohérent dans le codebase était intentionnel alors que ce peut être du copier-coller
- Transformer une absence de preuve en preuve d'absence ("personne n'a mentionné la sécurité, donc cela n'a pas dû compter")

## Le piège de la complaisance

Les utilisateurs formulent souvent les questions `why` avec une hypothèse intégrée : "Why do we do it this way, I assume it's for performance?" Ne la confirme pas simplement. Traite-la comme une candidate parmi d'autres et vérifie les preuves indépendamment. Si les preuves la soutiennent, dis-le avec citations. Sinon, dis-le et présente ce que les preuves *soutiennent*.

La supposition de l'utilisateur est une invite d'enquête, pas une conclusion à valider.

## Quand les preuves se contredisent

Si deux sources se contredisent (la description de PR dit une chose, le ticket une autre), expose les deux. Ne choisis pas celle qui donne le récit le plus propre. Motif typique :

- **Le ticket dit** "we need this for customer X's compliance requirement"
- **La PR dit** "cleaning up tech debt in this area"

Les deux peuvent être vrais (le ticket a motivé le travail, la PR est le cadrage de l'auteur), ou l'un peut être faux. Présente les deux avec leurs citations et laisse l'utilisateur juger.

## Quand les preuves manquent

Un honnête "nous ne savons pas" est l'une des sorties les plus précieuses de cette skill. L'utilisateur sait alors :

- La réponse n'est pas dans les endroits évidents
- Il faudra demander à un humain (auteur original, product owner, team lead)
- Ou il peut décider que la question ne mérite pas d'aller plus loin

Ne pas marquer un écart et le remplir par une supposition confiante nuit activement à l'utilisateur. Il agira sur la supposition.

Quand tu rencontres un écart, nomme-le concrètement :
- Quelle question tu essayais de résoudre
- Quelles sources tu as cherchées
- Ce que tu as cherché dans chacune
- Ce que tu as trouvé (rien, ou seulement du matériel tangentiel)

## Check de calibration avant finalisation

Avant de livrer la sortie, le synthétiseur doit relire chaque affirmation dans "Ce que nous avons trouvé" et "Ce que nous pouvons raisonnablement inférer" et demander :

1. Cette affirmation a-t-elle une citation ? Sinon, ajoute-en une ou déplace-la vers "Inférées" / "Hypothèses".
2. La formulation est-elle calibrée au niveau ? (Une affirmation Direct peut utiliser "parce que". Une affirmation Inférée ne le peut pas.)
3. Suis-je en train de traiter le code lui-même comme preuve de sa propre intention ? Si oui, ce n'est pas une preuve. Supprime ou reclassifie.
4. La sortie inclut-elle une section "Ce que nous ne savons pas" ? Si aucun écart n'est mentionné, c'est suspect. Soit les preuves étaient inhabituellement complètes, soit quelque chose est balayé sous le tapis.
