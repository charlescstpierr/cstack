# Rubrique de revue

Relis avec les lentilles pertinentes. Toutes les lentilles ne s'appliquent pas à chaque changement. Fais preuve de jugement.

## Fidélité à la spec

Applique cette lentille seulement quand le parent fournit une spec, issue ou déclaration de conversation approuvée. Mappe chaque exigence vers un comportement observable et signale les comportements manquants, partiels, contradictoires ou non demandés. Cite la source approuvée pour chaque finding Spec. Quand le parent rapporte un écart de preuve Spec, enregistre cet écart et n'infère pas d'exigences depuis l'implémentation, les messages de commit ou le comportement apparent. Une finding Spec concrète reste actionnable même quand un seul reviewer a l'affectation Spec.

## Fidélité aux standards

Utilise les standards, instructions et configuration fournis par le dépôt comme autorité pour les findings Standards. Traite les préférences génériques et la lentille de qualité de code comme des appels au jugement, pas des violations dures. Cite la règle source ou étiquette la finding comme appel au jugement.

## Exactitude

Le code fait-il réellement ce que l'intention dit qu'il doit faire ?

- Cas limites : entrées vides, nil/undefined, valeurs frontières, accès concurrent
- Gestion d'erreurs : les erreurs sont-elles capturées, propagées ou avalées silencieusement ?
- Off-by-one, coercition de types, integer overflow, encodage de chaînes
- Gestion d'état : race conditions, stale closures, références pendantes
- Le happy path fonctionne-t-il ? Le sad path fonctionne-t-il ?
- Idempotence : que se passe-t-il si cette opération tourne deux fois, ou si une exécution précédente a planté à mi-chemin ? Si la réponse est "cela dépend de l'état laissé derrière", il manque une étape de réconciliation.
- Concurrence : si plusieurs acteurs peuvent toucher le même état mutable (fichiers, branches, données partagées), l'accès est-il sérialisé structurellement (verrous, phases séquentielles, propriété exclusive) ou par conventions qui ne tiendront pas ?

Quand tu trouves un bug potentiel, trace le chemin d'exécution. Ne signale pas seulement "ceci pourrait être nil". Montre la chaîne d'appels qui le rend nil.

## Causes racines vs symptômes

Le code corrige-t-il le vrai problème ou masque-t-il un symptôme ?

Répondre exige souvent de regarder au-delà des fichiers changés. Lis le code environnant (appelants, appelés, définitions de types, modules frères) et comprends l'architecture dans laquelle vit le changement. Utilise les outils disponibles (Read, Grep, Glob) pour explorer. Suis la chaîne d'appels. Lis les types. Comprends pourquoi le code existe avant de juger si le changement touche la bonne couche.

- Guard clauses qui masquent une violation d'invariant plus profonde
- Logique de retry qui cache un contrat cassé
- Casts de types qui taisent une erreur de modélisation
- Si tu vois un workaround, demande : pourquoi est-il nécessaire ? À quoi ressemblerait une vraie correction ?
- Correction dans le module A qui devrait vraiment être une correction du contrat du module B
- Instructions là où la structure serait meilleure : si la correction est un commentaire disant "ne fais pas X" ou une convention à retenir, demande si cela pourrait être une contrainte de type, une règle lint ou un check runtime qui rend l'erreur impossible

## Intégrité structurelle

Le code s'insère-t-il bien dans le système dont il fait partie ?

- Discipline des frontières : la validation est-elle aux frontières système ou dispersée dans la logique métier ? Valide les données une fois à leur entrée, puis fais-leur confiance en interne.
- Niveau d'abstraction : le code mélange-t-il orchestration haut niveau et détail bas niveau ?
- Couplage : ce changement introduit-il des dépendances qui rendront les changements futurs plus difficiles ?
- Ajustement du modèle de données : les structures de données correspondent-elles aux motifs d'accès réels ? La bonne structure rend le code aval évident. La mauvaise lutte partout.
- Boulonné vs intégré : le changement a-t-il été patché sur la conception existante, ou se lit-il comme si la conception l'avait toujours prévu ? Si la nouvelle exigence avait été connue dès le départ, le code ressemblerait-il à ceci ?
- Double chemins legacy : le changement introduit-il une nouvelle API en gardant l'ancienne vivante ? S'il n'y a pas de consommateurs externes, migre les appelants et supprime l'ancien chemin dans la même vague. Ne laisse pas des couches de compatibilité qui deviendront permanentes.

Ne pénalise pas du code simple pour absence d'abstraction. L'abstraction prématurée est pire que la duplication.

## Vérification

Peux-tu dire que ce code fonctionne en le lisant ?

- Y a-t-il des tests ? Testent-ils le comportement ou les détails d'implémentation ?
- Y a-t-il des assertions/invariants qui attraperaient les régressions ?
- Si c'est un bug fix : y a-t-il un test pour le bug ?
- Si cela touche une frontière d'intégration : le chemin complet est-il testé ?
- Vérifie la vraie chose, pas un proxy. Si le code vérifie la vivacité via mtime de fichier ou état caché au lieu de lire la valeur réelle, c'est un écart de vérification.
- Pour le travail délégué ou async : le code vérifie-t-il les artefacts de sortie réels, ou fait-il confiance aux auto-rapports et résumés ?

## Budget de complexité

La complexité est-elle justifiée par ce que le code accomplit ?

- Code qui pourrait être plus simple sans perdre exactitude ni clarté
- Abstractions qui ne servent qu'un site d'appel
- Configuration ou paramétrage pour des cas qui n'existent pas encore
- Code mort, imports inutilisés, paramètres vestigiaux
- Sur-ingénierie : chemins "just in case" sans appelants courants
- Chemins de compatibilité obsolètes gardés pour une stabilité transitoire qui n'est plus nécessaire. Si la migration est faite, supprime le scaffolding
- L'expérience utilisateur justifie-t-elle la complexité ? Chaque fonctionnalité, contrôle et option doit mériter sa place. Les fonctionnalités à moitié finies sont pires que les fonctionnalités absentes.

Plus simple est meilleur sauf si plus simple est faux. Trois lignes de duplication battent une abstraction prématurée.

## Sécurité

Signale seulement les problèmes de sécurité que tu peux réellement tracer dans le code. "Ceci pourrait être un vecteur d'injection" sans montrer le chemin d'entrée n'est pas utile.

- Entrée utilisateur qui va vers des sinks dangereux (SQL, shell, eval, innerHTML) sans sanitization
- Lacunes d'authentification/autorisation dans de nouveaux endpoints
- Secrets dans le code, les logs ou les messages d'erreur
- TOCTOU (time-of-check-time-of-use) dans les chemins critiques de sécurité
